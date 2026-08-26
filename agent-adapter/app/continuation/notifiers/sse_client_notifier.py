from __future__ import annotations

import asyncio
import threading

from continuation.client_notifier import ClientNotifier, ClientNotifyEvent
from logutil import get_logger

import os

_DEFAULT_MAX_SSE = 100
_DEFAULT_QUEUE_MAXSIZE = 32


def _max_sse_connections() -> int:
    raw = os.getenv("ADAPTER_MAX_SSE_CONNECTIONS", "").strip()
    if not raw:
        return _DEFAULT_MAX_SSE
    try:
        return max(1, int(raw))
    except ValueError:
        return _DEFAULT_MAX_SSE


def _sse_queue_maxsize() -> int:
    raw = os.getenv("ADAPTER_SSE_QUEUE_MAXSIZE", "").strip()
    if not raw:
        return _DEFAULT_QUEUE_MAXSIZE
    try:
        return max(1, int(raw))
    except ValueError:
        return _DEFAULT_QUEUE_MAXSIZE


class SseConnectionLimitError(Exception):
    pass
logger = get_logger(__name__)


def _subscriber_key(platform: str, session_id: str) -> tuple[str, str]:
    return (platform.strip().lower(), session_id.strip())


class SseClientNotifier(ClientNotifier):
    """
    Route notifications to exactly one SSE subscriber per
    (platform, sessionId). Never broadcasts across sessions.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # (platform, sessionId) -> queue for that connection only
        self._subscribers: dict[tuple[str, str], asyncio.Queue] = {}

    def subscribe(
            self,
            platform: str,
            session_id: str,
    ) -> asyncio.Queue:
        key = _subscriber_key(platform, session_id)
        if not key[0] or not key[1]:
            raise ValueError("platform and sessionId are required")

        queue: asyncio.Queue = asyncio.Queue(maxsize=_sse_queue_maxsize())
        with self._lock:
            previous = self._subscribers.get(key)

            if previous is None and len(self._subscribers) >= _max_sse_connections():
                raise SseConnectionLimitError(
                    f"Too many SSE connections (max {_max_sse_connections()})"
                )

            self._subscribers[key] = queue
        # Close the previous connection for this key, if any.
        if previous is not None:
            previous.put_nowait(None)

        return queue

    def unsubscribe(
            self,
            platform: str,
            session_id: str,
            queue: asyncio.Queue,
    ) -> None:
        key = _subscriber_key(platform, session_id)
        with self._lock:
            if self._subscribers.get(key) is queue:
                del self._subscribers[key]

    def notify(self, event: ClientNotifyEvent) -> None:
        key = _subscriber_key(event.platform, event.sessionId)
        if not key[0] or not key[1]:
            return

        with self._lock:
            queue = self._subscribers.get(key)

        if queue is None:
            logger.warning(
                "No client subscriber for platform=%s sessionId=%s "
                "requestId=%s",
                event.platform,
                event.sessionId,
                event.requestId,
            )
            return

        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(
                "SSE queue full for platform=%s sessionId=%s requestId=%s",
                event.platform,
                event.sessionId,
                event.requestId,
            )
            return

        logger.debug(
            "Delivered client notification platform=%s sessionId=%s "
            "requestId=%s",
            event.platform,
            event.sessionId,
            event.requestId,
        )

