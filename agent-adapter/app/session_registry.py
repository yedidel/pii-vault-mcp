from __future__ import annotations

import os
import secrets
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

SSE_TOKEN_PREFIX = "sse_"
DEFAULT_TTL_SECONDS = int(
    os.getenv("SESSION_REGISTRY_TTL_SECONDS", str(24 * 3600))
)
# Placeholder ids from vault_config.json before real vault pairing.
LEGACY_USER_INSTALL_IDS = frozenset({
    "some-value",
    "device_123",
})


class SessionConflictError(PermissionError):
    """Session is already bound to a different user_install_id."""


@dataclass(frozen=True)
class SessionRecord:
    user_install_id: str
    platform: str
    session_id: str
    sse_token: str
    created_at: datetime
    expires_at: datetime
    ingress_url: str | None = None


class SessionRegistry:
    """
    Maps (platform, sessionId) to user_install_id and an opaque SSE token.

    One row per client session. The token is a capability secret for GET /events.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_registry (
                    platform TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    user_install_id TEXT NOT NULL,
                    sse_token TEXT NOT NULL UNIQUE,
                    ingress_url TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    PRIMARY KEY (platform, session_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_session_sse_token
                ON session_registry(sse_token)
                """
            )

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    def _row_to_record(self, row: sqlite3.Row) -> SessionRecord:
        return SessionRecord(
            user_install_id=str(row["user_install_id"]),
            platform=str(row["platform"]),
            session_id=str(row["session_id"]),
            sse_token=str(row["sse_token"]),
            ingress_url=(
                str(row["ingress_url"])
                if row["ingress_url"] is not None
                else None
            ),
            created_at=self._parse_dt(str(row["created_at"])),
            expires_at=self._parse_dt(str(row["expires_at"])),
        )

    def get(self, platform: str, session_id: str) -> SessionRecord | None:
        platform = platform.strip().lower()
        session_id = session_id.strip()
        if not platform or not session_id:
            return None

        with self._lock:
            return self._get_unlocked(platform, session_id)

    def _get_unlocked(
            self,
            platform: str,
            session_id: str,
    ) -> SessionRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT platform, session_id, user_install_id, sse_token,
                       ingress_url, created_at, expires_at
                FROM session_registry
                WHERE platform = ? AND session_id = ?
                """,
                (platform, session_id),
            ).fetchone()

        if row is None:
            return None
        return self._row_to_record(row)

    def _delete_unlocked(self, platform: str, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM session_registry
                WHERE platform = ? AND session_id = ?
                """,
                (platform, session_id),
            )

    def register(
            self,
            user_install_id: str,
            platform: str,
            session_id: str,
            *,
            ingress_url: str | None = None,
    ) -> SessionRecord:
        platform = platform.strip().lower()
        session_id = session_id.strip()
        user_install_id = user_install_id.strip()
        if not platform or not session_id or not user_install_id:
            raise ValueError("user_install_id, platform, and session_id are required")

        with self._lock:
            existing = self._get_unlocked(platform, session_id)
            now = datetime.now(timezone.utc)

            if existing is not None:
                if existing.user_install_id != user_install_id:
                    if existing.user_install_id in LEGACY_USER_INSTALL_IDS:
                        self._delete_unlocked(platform, session_id)
                    elif user_install_id in LEGACY_USER_INSTALL_IDS:
                        # Client startup before pairing.json reload; keep the
                        # real install binding already stored for this session.
                        if existing.expires_at > now:
                            return existing
                        self._delete_unlocked(platform, session_id)
                    else:
                        # Vault re-paired on this adapter — rebind session.
                        self._delete_unlocked(platform, session_id)
                elif existing.expires_at > now:
                    return existing
                else:
                    self._delete_unlocked(platform, session_id)

            expires_at = now + timedelta(seconds=DEFAULT_TTL_SECONDS)
            sse_token = SSE_TOKEN_PREFIX + secrets.token_urlsafe(32)
            ingress = (ingress_url or "").strip() or None

            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO session_registry (
                        platform,
                        session_id,
                        user_install_id,
                        sse_token,
                        ingress_url,
                        created_at,
                        expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        platform,
                        session_id,
                        user_install_id,
                        sse_token,
                        ingress,
                        now.isoformat(),
                        expires_at.isoformat(),
                    ),
                )

            return SessionRecord(
                user_install_id=user_install_id,
                platform=platform,
                session_id=session_id,
                sse_token=sse_token,
                ingress_url=ingress,
                created_at=now,
                expires_at=expires_at,
            )

    def ensure_bound(
            self,
            user_install_id: str,
            platform: str,
            session_id: str,
    ) -> SessionRecord:
        """
        Bind the session to this adapter user on first send_action,
        or verify an existing binding matches.
        """
        return self.register(user_install_id, platform, session_id)

    def verify_sse_token(
            self,
            platform: str,
            session_id: str,
            token: str,
    ) -> bool:
        platform = platform.strip().lower()
        session_id = session_id.strip()
        token = token.strip()
        if not platform or not session_id or not token:
            return False

        with self._lock:
            record = self._get_unlocked(platform, session_id)
            if record is None:
                return False
            if record.expires_at <= datetime.now(timezone.utc):
                self._delete_unlocked(platform, session_id)
                return False

        return secrets.compare_digest(record.sse_token, token)


def load_session_registry(base_dir: Path) -> SessionRegistry:
    db_path = base_dir / "data" / "sessions.sqlite3"
    return SessionRegistry(db_path)
