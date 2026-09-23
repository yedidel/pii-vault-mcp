from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class PairingState:
    user_install_id: str | None = None
    pending_pairing_code: str | None = None
    paired_at: str | None = None
    pending_platform: str | None = None
    pending_session_id: str | None = None
    pending_action_summary: str | None = None


class PairingStore:
    """Local Adapter state: paired user_install_id and pending pairing code."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()

    def _read_unlocked(self) -> PairingState:
        if not self._path.exists():
            return PairingState()
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return PairingState()
        if not isinstance(raw, dict):
            return PairingState()
        return PairingState(
            user_install_id=_optional_str(raw.get("userInstallId")),
            pending_pairing_code=_optional_str(raw.get("pendingPairingCode")),
            paired_at=_optional_str(raw.get("pairedAt")),
            pending_platform=_optional_str(raw.get("pendingPlatform")),
            pending_session_id=_optional_str(raw.get("pendingSessionId")),
            pending_action_summary=_optional_str(
                raw.get("pendingActionSummary"),
            ),
        )

    def _write_unlocked(self, state: PairingState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "userInstallId": state.user_install_id,
            "pendingPairingCode": state.pending_pairing_code,
            "pairedAt": state.paired_at,
            "pendingPlatform": state.pending_platform,
            "pendingSessionId": state.pending_session_id,
            "pendingActionSummary": state.pending_action_summary,
        }
        self._path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

    def load(self) -> PairingState:
        with self._lock:
            return self._read_unlocked()

    def save(self, state: PairingState) -> None:
        with self._lock:
            self._write_unlocked(state)

    def set_pending_pairing(
            self,
            pairing_code: str,
            *,
            platform: str | None = None,
            session_id: str | None = None,
            action_summary: str | None = None,
    ) -> None:
        with self._lock:
            state = self._read_unlocked()
            if state.user_install_id:
                return
            state.pending_pairing_code = pairing_code.strip()
            state.pending_platform = (platform or "").strip() or None
            state.pending_session_id = (session_id or "").strip() or None
            state.pending_action_summary = (action_summary or "").strip() or None
            self._write_unlocked(state)

    def clear_pending_pairing(self) -> None:
        with self._lock:
            state = self._read_unlocked()
            state.pending_pairing_code = None
            state.pending_platform = None
            state.pending_session_id = None
            state.pending_action_summary = None
            self._write_unlocked(state)

    def set_paired(self, user_install_id: str) -> None:
        with self._lock:
            state = self._read_unlocked()
            state.user_install_id = user_install_id.strip()
            state.pending_pairing_code = None
            state.pending_platform = None
            state.pending_session_id = None
            state.pending_action_summary = None
            state.paired_at = datetime.now(timezone.utc).isoformat()
            self._write_unlocked(state)

    def clear_paired(self) -> None:
        with self._lock:
            state = self._read_unlocked()
            state.user_install_id = None
            state.paired_at = None
            self._write_unlocked(state)

    def clear(self) -> None:
        with self._lock:
            if self._path.exists():
                self._path.unlink()


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def load_pairing_store(base_dir: Path) -> PairingStore:
    return PairingStore(base_dir / "data" / "pairing.json")
