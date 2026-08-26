from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse

from continuation.client_notifier import ClientNotifyEvent
from continuation.notifiers.sse_client_notifier import (
    SseClientNotifier,
    SseConnectionLimitError,
)


async def sse_event_stream(
        notifier: SseClientNotifier,
        platform: str,
        session_id: str,
        queue: asyncio.Queue,
) -> AsyncIterator[bytes]:
    try:
        connected = {
            "type": "connected",
            "platform": platform.strip().lower(),
            "sessionId": session_id.strip(),
        }
        yield _sse_frame("connected", connected)

        while True:
            item = await queue.get()
            if item is None:
                break

            if not isinstance(item, ClientNotifyEvent):
                continue

            yield _sse_frame("workflow.updated", item.model_dump())
    finally:
        notifier.unsubscribe(platform, session_id, queue)


def _sse_frame(event_name: str, payload: dict) -> bytes:
    data = json.dumps(payload, separators=(",", ":"))
    return f"event: {event_name}\ndata: {data}\n\n".encode("utf-8")


async def handle_client_events(
        request: Request,
        notifier: SseClientNotifier,
) -> StreamingResponse | JSONResponse:
    platform = str(request.query_params.get("platform") or "").strip()
    session_id = str(request.query_params.get("sessionId") or "").strip()

    if not platform or not session_id:
        return JSONResponse(
            {
                "detail": (
                    "Query parameters 'platform' and 'sessionId' "
                    "are required"
                ),
            },
            status_code=400,
        )

    try:
        queue = notifier.subscribe(platform, session_id)
    except SseConnectionLimitError as error:
        return JSONResponse({"detail": str(error)}, status_code=503)

    return StreamingResponse(
        sse_event_stream(notifier, platform, session_id, queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )