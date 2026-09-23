from __future__ import annotations

import secrets
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATUS_ACTIVE = "ACTIVE"
STATUS_UNINSTALLED = "UNINSTALLED"
PAIRING_PENDING = "PENDING"
PAIRING_COMPLETED = "COMPLETED"

DEFAULT_PAIRING_TTL_SECONDS = 600


@dataclass(frozen=True)
class InstallRecord:
    user_install_id: str
    vault_service_url: str
    status: str
    created_at: datetime
    last_seen_at: datetime


@dataclass(frozen=True)
class PairingSession:
    pairing_code: str
    status: str
    expires_at: datetime
    user_install_id: str | None = None


class DirectoryStore:
    """SQLite backing store for install ↔ vault URL mappings."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS installs (
                    user_install_id TEXT PRIMARY KEY,
                    vault_service_url TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pairing_sessions (
                    pairing_code TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    user_install_id TEXT,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def start_pairing(
            self,
            *,
            ttl_seconds: int = DEFAULT_PAIRING_TTL_SECONDS,
    ) -> PairingSession:
        now = self._now()
        pairing_code = secrets.token_urlsafe(8)
        expires_at = now + timedelta(seconds=ttl_seconds)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO pairing_sessions (
                    pairing_code, status, user_install_id,
                    expires_at, created_at
                ) VALUES (?, ?, NULL, ?, ?)
                """,
                (
                    pairing_code,
                    PAIRING_PENDING,
                    expires_at.isoformat(),
                    now.isoformat(),
                ),
            )

        return PairingSession(
            pairing_code=pairing_code,
            status=PAIRING_PENDING,
            expires_at=expires_at,
        )

    def complete_pairing(
            self,
            pairing_code: str,
            *,
            vault_service_url: str,
    ) -> InstallRecord:
        pairing_code = pairing_code.strip()
        vault_service_url = vault_service_url.strip()
        if not pairing_code or not vault_service_url:
            raise ValueError("pairing_code and vault_service_url are required")

        now = self._now()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT pairing_code, status, user_install_id, expires_at
                FROM pairing_sessions
                WHERE pairing_code = ?
                """,
                (pairing_code,),
            ).fetchone()

            if row is None:
                raise KeyError("pairing_code not found")

            expires_at = self._parse_dt(str(row["expires_at"]))
            if expires_at <= now:
                raise PermissionError("pairing_code expired")

            if str(row["status"]) == PAIRING_COMPLETED:
                existing_id = str(row["user_install_id"] or "").strip()
                if not existing_id:
                    raise RuntimeError("completed pairing missing user_install_id")
                install = conn.execute(
                    """
                    SELECT user_install_id, vault_service_url, status,
                           created_at, last_seen_at
                    FROM installs
                    WHERE user_install_id = ?
                    """,
                    (existing_id,),
                ).fetchone()
                if install is None:
                    raise RuntimeError("completed pairing install missing")
                return InstallRecord(
                    user_install_id=str(install["user_install_id"]),
                    vault_service_url=str(install["vault_service_url"]),
                    status=str(install["status"]),
                    created_at=self._parse_dt(str(install["created_at"])),
                    last_seen_at=self._parse_dt(str(install["last_seen_at"])),
                )

            user_install_id = f"install_{uuid.uuid4().hex}"
            conn.execute(
                """
                INSERT INTO installs (
                    user_install_id, vault_service_url, status,
                    created_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_install_id,
                    vault_service_url,
                    STATUS_ACTIVE,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            conn.execute(
                """
                UPDATE pairing_sessions
                SET status = ?, user_install_id = ?
                WHERE pairing_code = ?
                """,
                (PAIRING_COMPLETED, user_install_id, pairing_code),
            )

        return InstallRecord(
            user_install_id=user_install_id,
            vault_service_url=vault_service_url,
            status=STATUS_ACTIVE,
            created_at=now,
            last_seen_at=now,
        )

    def get_pairing(self, pairing_code: str) -> PairingSession | None:
        pairing_code = pairing_code.strip()
        if not pairing_code:
            return None

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT pairing_code, status, user_install_id, expires_at
                FROM pairing_sessions
                WHERE pairing_code = ?
                """,
                (pairing_code,),
            ).fetchone()

        if row is None:
            return None

        return PairingSession(
            pairing_code=str(row["pairing_code"]),
            status=str(row["status"]),
            expires_at=self._parse_dt(str(row["expires_at"])),
            user_install_id=(
                str(row["user_install_id"])
                if row["user_install_id"] is not None
                else None
            ),
        )

    def get_install(self, user_install_id: str) -> InstallRecord | None:
        user_install_id = user_install_id.strip()
        if not user_install_id:
            return None

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT user_install_id, vault_service_url, status,
                       created_at, last_seen_at
                FROM installs
                WHERE user_install_id = ?
                """,
                (user_install_id,),
            ).fetchone()

        if row is None:
            return None

        return InstallRecord(
            user_install_id=str(row["user_install_id"]),
            vault_service_url=str(row["vault_service_url"]),
            status=str(row["status"]),
            created_at=self._parse_dt(str(row["created_at"])),
            last_seen_at=self._parse_dt(str(row["last_seen_at"])),
        )
