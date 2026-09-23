from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4


@dataclass
class ClaudeSession:
    session_id: str
    ingress_url: str
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_seen_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ClaudeSessionRegistry:
    """
    Maps Claude Channel session ids to local Channel ingress URLs.

    Adapter-local only. Bridge never sees these mappings.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ClaudeSession] = {}
        self._lock = Lock()

    def register(self, ingress_url: str) -> ClaudeSession:
        ingress = ingress_url.strip().rstrip("/")
        if not ingress:
            raise ValueError("ingress_url is required")

        session = ClaudeSession(
            session_id=str(uuid4()),
            ingress_url=ingress,
        )

        with self._lock:
            self._sessions[session.session_id] = session

        return session

    def get(self, session_id: str) -> ClaudeSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.last_seen_at = datetime.now(timezone.utc)
            return session

    def unregister(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def touch(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is not None:
                session.last_seen_at = datetime.now(timezone.utc)
