from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING

from continuation.client_notifier import ClientNotifier, VaultPairedEvent
from continuation.providers.claude_provider import wake_claude_with_message
from continuation.providers.gemini_provider import wake_gemini_with_message
from continuation.providers.openai_provider import wake_openai_with_message
from logutil import get_logger
from pairing_store import PairingStore

if TYPE_CHECKING:
    from pairing_service import PairingService

logger = get_logger(__name__)

_DEFAULT_INTERVAL_SECONDS = 2.0
_DEFAULT_TIMEOUT_SECONDS = 600.0


def _poll_interval_seconds() -> float:
    raw = os.getenv("ADAPTER_PAIR_POLL_INTERVAL_SECONDS", "").strip()
    if not raw:
        return _DEFAULT_INTERVAL_SECONDS
    try:
        return max(0.5, float(raw))
    except ValueError:
        return _DEFAULT_INTERVAL_SECONDS


def _poll_timeout_seconds() -> float:
    raw = os.getenv("ADAPTER_PAIR_POLL_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return _DEFAULT_TIMEOUT_SECONDS
    try:
        return max(30.0, float(raw))
    except ValueError:
        return _DEFAULT_TIMEOUT_SECONDS


def _pairing_complete_message(
        *,
        user_install_id: str,
        action_summary: str,
) -> str:
    message = (
        "Vault pairing completed successfully.\n"
        f"userInstallId: {user_install_id}\n"
    )
    if action_summary:
        message += (
            f"Pending action: {action_summary}\n"
            "Call send_action now with the same parameters to continue."
        )
    else:
        message += (
            "The user's vault is connected. "
            "Continue the pending action with send_action."
        )
    return message


def _wake_after_pairing(
        *,
        platform: str,
        session_id: str,
        user_install_id: str,
        message: str,
) -> str:
    platform_normalized = platform.strip().lower()
    if platform_normalized == "gemini":
        return wake_gemini_with_message(
            previous_interaction_id=session_id,
            message=message,
        )
    if platform_normalized == "openai":
        return wake_openai_with_message(
            conversation_id=session_id,
            message=message,
        )
    if platform_normalized == "claude":
        return wake_claude_with_message(
            wake_url=session_id,
            message=message,
            request_id=f"pairing-{user_install_id}",
            workflow_id="pairing",
            status="PAIRED",
        )
    raise ValueError(f"Unsupported pairing wake platform: {platform!r}")


class PairingWatcher:
    """
    Poll Install Directory until pending vault pairing completes,
    then wake the agent and notify the client via SSE.
    """

    def __init__(
            self,
            *,
            pairing_service: PairingService,
            pairing_store: PairingStore,
            client_notifier: ClientNotifier,
    ) -> None:
        self._pairing_service = pairing_service
        self._pairing_store = pairing_store
        self._client_notifier = client_notifier
        self._stop_event = asyncio.Event()
        self._interval_seconds = _poll_interval_seconds()
        self._timeout_seconds = _poll_timeout_seconds()
        self._pairing_started_at: float | None = None

    def stop(self) -> None:
        self._stop_event.set()

    async def run(self) -> None:
        if not self._pairing_service.directory_enabled:
            logger.info("Pairing watcher disabled (INSTALL_DIRECTORY_URL unset)")
            return

        logger.info(
            "Pairing watcher started interval=%ss timeout=%ss",
            self._interval_seconds,
            self._timeout_seconds,
        )
        while not self._stop_event.is_set():
            await self._poll_once()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._interval_seconds,
                )
            except asyncio.TimeoutError:
                continue

        logger.info("Pairing watcher stopped")

    async def _poll_once(self) -> None:
        state = self._pairing_store.load()
        if not state.pending_pairing_code or not state.pending_session_id:
            self._pairing_started_at = None
            return

        if self._pairing_started_at is None:
            self._pairing_started_at = asyncio.get_running_loop().time()

        elapsed = asyncio.get_running_loop().time() - self._pairing_started_at
        if elapsed > self._timeout_seconds:
            logger.warning(
                "Pairing timeout pairingCode=%s sessionId=%s",
                state.pending_pairing_code,
                state.pending_session_id,
            )
            self._pairing_store.clear_pending_pairing()
            self._pairing_started_at = None
            return

        resolved = await asyncio.to_thread(
            self._pairing_service.check_pending_pairing,
        )
        if resolved is None:
            return

        platform = (state.pending_platform or "").strip().lower()
        session_id = (state.pending_session_id or "").strip()
        action_summary = (state.pending_action_summary or "").strip()
        user_install_id = resolved.user_install_id

        if not platform or not session_id:
            logger.info(
                "Pairing complete userInstallId=%s (no wake: missing platform/session)",
                user_install_id,
            )
            self._pairing_started_at = None
            return

        message = _pairing_complete_message(
            user_install_id=user_install_id,
            action_summary=action_summary,
        )

        try:
            resume_session_id = await asyncio.to_thread(
                _wake_after_pairing,
                platform=platform,
                session_id=session_id,
                user_install_id=user_install_id,
                message=message,
            )
        except Exception as error:
            logger.error(
                "Pairing wake failed platform=%s sessionId=%s: %s",
                platform,
                session_id,
                error,
            )
            return

        self._client_notifier.notify_vault_paired(
            VaultPairedEvent(
                platform=platform,
                sessionId=session_id,
                userInstallId=user_install_id,
                resumeSessionId=resume_session_id,
            )
        )
        logger.info(
            "Pairing complete userInstallId=%s platform=%s sessionId=%s resume=%s",
            user_install_id,
            platform,
            session_id,
            resume_session_id,
        )

        self._pairing_started_at = None
