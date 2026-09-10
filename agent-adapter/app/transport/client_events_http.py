from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse

from continuation.client_notifier import ClientNotifyEvent, VaultPairedEvent
from continuation.notifiers.sse_client_notifier import (
    SseClientNotifier,
    SseConnectionLimitError,
)
from session_registry import SessionRegistry


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

            if isinstance(item, ClientNotifyEvent):
                yield _sse_frame("workflow.updated", item.model_dump())
                continue

            if isinstance(item, VaultPairedEvent):
                yield _sse_frame("vault.paired", item.model_dump())
    finally:
        notifier.unsubscribe(platform, session_id, queue)


def _sse_frame(event_name: str, payload: dict) -> bytes:
    data = json.dumps(payload, separators=(",", ":"))
    return f"event: {event_name}\ndata: {data}\n\n".encode("utf-8")


async def handle_client_events(
        request: Request,
        notifier: SseClientNotifier,
        session_registry: SessionRegistry,
) -> StreamingResponse | JSONResponse:
    platform = str(request.query_params.get("platform") or "").strip()
    session_id = str(request.query_params.get("sessionId") or "").strip()
    token = str(request.query_params.get("token") or "").strip()

    if not platform or not session_id or not token:
        return JSONResponse(
            {
                "detail": (
                    "Query parameters 'platform', 'sessionId', and "
                    "'token' are required"
                ),
            },
            status_code=400,
        )

    if not session_registry.verify_sse_token(platform, session_id, token):
        return JSONResponse(
            {"detail": "Invalid or expired session token"},
            status_code=401,
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