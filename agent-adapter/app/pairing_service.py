from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from install_directory_client import InstallDirectoryClient, load_install_directory_client
from logutil import get_logger
from pairing_store import PairingStore, load_pairing_store

logger = get_logger(__name__)

PAIRING_COMPLETED = "COMPLETED"
STATUS_UNINSTALLED = "UNINSTALLED"


@dataclass(frozen=True)
class PairingRequired:
    pairing_code: str
    qr_url: str
    expires_at: str
    message: str


@dataclass(frozen=True)
class PairingResolved:
    user_install_id: str


class PairingService:
    def __init__(
            self,
            *,
            store: PairingStore,
            directory: InstallDirectoryClient | None,
            legacy_user_install_id: str,
    ) -> None:
        self._store = store
        self._directory = directory
        self._legacy_user_install_id = legacy_user_install_id.strip()

    @property
    def directory_enabled(self) -> bool:
        return self._directory is not None

    def resolve_for_session(self) -> str:
        """
        SSE /sessions/register: allow startup before vault pairing.

        Uses paired install when available; otherwise legacy placeholder
        until send_action completes pairing.
        """
        if self._directory is None:
            return self._legacy_user_install_id

        state = self._store.load()

        if state.user_install_id:
            install_id = self._session_install_id(state.user_install_id)
            if install_id is not None:
                return install_id

        if state.pending_pairing_code:
            resolved = self._try_complete_pending(state.pending_pairing_code)
            if resolved is not None:
                return resolved.user_install_id

        return self._legacy_user_install_id

    def resolve(
            self,
            *,
            platform: str | None = None,
            session_id: str | None = None,
            action_summary: str | None = None,
    ) -> PairingResolved | PairingRequired:
        if self._directory is None:
            return PairingResolved(user_install_id=self._legacy_user_install_id)

        state = self._store.load()

        if state.user_install_id:
            outcome = self._resolve_paired_install(state.user_install_id)
            if outcome is not None:
                return outcome

        if state.pending_pairing_code:
            resolved = self._try_complete_pending(state.pending_pairing_code)
            if resolved is not None:
                return resolved
            existing = self._reuse_pending_if_valid(state.pending_pairing_code)
            if existing is not None:
                return existing
            self._store.clear_pending_pairing()

        return self._start_pairing(
            platform=platform,
            session_id=session_id,
            action_summary=action_summary,
        )

    def _session_install_id(self, user_install_id: str) -> str | None:
        assert self._directory is not None
        install = self._directory.get_install(user_install_id)
        if install is None:
            logger.warning(
                "Paired install missing from Directory userInstallId=%s",
                user_install_id,
            )
            self._store.clear_paired()
            return None
        if install.status == STATUS_UNINSTALLED:
            logger.warning(
                "Vault install uninstalled userInstallId=%s",
                user_install_id,
            )
            self._store.clear_paired()
            return None
        return install.user_install_id

    def _resolve_paired_install(
            self,
            user_install_id: str,
    ) -> PairingResolved | None:
        assert self._directory is not None
        install = self._directory.get_install(user_install_id)
        if install is None:
            logger.warning(
                "Paired install missing from Directory userInstallId=%s",
                user_install_id,
            )
            self._store.clear_paired()
            return None
        if install.status == STATUS_UNINSTALLED:
            logger.warning(
                "Vault install uninstalled userInstallId=%s",
                user_install_id,
            )
            self._store.clear_paired()
            return None
        return PairingResolved(user_install_id=install.user_install_id)

    def _start_pairing(
            self,
            *,
            platform: str | None,
            session_id: str | None,
            action_summary: str | None,
    ) -> PairingRequired:
        assert self._directory is not None
        started = self._directory.start_pairing()
        self._store.set_pending_pairing(
            started.pairing_code,
            platform=platform,
            session_id=session_id,
            action_summary=action_summary,
        )
        logger.info(
            "Pairing required pairingCode=%s qrUrl=%s",
            started.pairing_code,
            started.qr_url,
        )
        return PairingRequired(
            pairing_code=started.pairing_code,
            qr_url=started.qr_url,
            expires_at=started.expires_at,
            message=(
                "Vault app pairing required. Open qrUrl in a browser and "
                "tap Connect Mock Vault. The agent will continue automatically "
                "when pairing completes."
            ),
        )

    def _reuse_pending_if_valid(self, pairing_code: str) -> PairingRequired | None:
        assert self._directory is not None
        try:
            body = self._directory.get_pairing(pairing_code)
        except Exception as error:
            logger.warning("Pending pairing lookup failed: %s", error)
            return None

        if body.get("expired"):
            logger.info("Pending pairing expired pairingCode=%s", pairing_code)
            return None

        status = str(body.get("status") or "").strip().upper()
        if status != "PENDING":
            return None

        code = str(body.get("pairingCode") or pairing_code).strip()
        expires_at = str(body.get("expiresAt") or "").strip()
        qr_url = f"{self._directory.base_url}/pair?code={code}"
        logger.info("Reusing pending pairing pairingCode=%s", code)
        return PairingRequired(
            pairing_code=code,
            qr_url=qr_url,
            expires_at=expires_at,
            message=(
                "Vault app pairing required. Open qrUrl in a browser and "
                "tap Connect Mock Vault. The agent will continue automatically "
                "when pairing completes."
            ),
        )

    def check_pending_pairing(self) -> PairingResolved | None:
        state = self._store.load()
        if not state.pending_pairing_code:
            return None
        return self._try_complete_pending(state.pending_pairing_code)

    def _try_complete_pending(
            self,
            pairing_code: str,
    ) -> PairingResolved | None:
        assert self._directory is not None
        try:
            body = self._directory.get_pairing(pairing_code)
        except Exception as error:
            logger.warning("Pairing status lookup failed: %s", error)
            return None

        if body.get("expired"):
            return None
        if str(body.get("status") or "") != PAIRING_COMPLETED:
            return None

        user_install_id = str(body.get("userInstallId") or "").strip()
        if not user_install_id:
            return None

        install = self._directory.get_install(user_install_id)
        if install is None or install.status == STATUS_UNINSTALLED:
            return None

        self._store.set_paired(user_install_id)
        logger.info("Pairing completed userInstallId=%s", user_install_id)
        return PairingResolved(user_install_id=user_install_id)

    def pairing_required_response(self, required: PairingRequired) -> dict:
        return {
            "error": "pairing_required",
            "message": required.message,
            "pairingCode": required.pairing_code,
            "qrUrl": required.qr_url,
            "expiresAt": required.expires_at,
        }

def load_pairing_service(
        base_dir: Path,
        *,
        legacy_user_install_id: str,
) -> PairingService:
    return PairingService(
        store=load_pairing_store(base_dir),
        directory=load_install_directory_client(),
        legacy_user_install_id=legacy_user_install_id,
    )
