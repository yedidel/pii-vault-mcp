"""
Generic Adapter client-events SSE subscriber.

Platform-agnostic: only needs platform + sessionId routing keys.
Reusable by OpenAI and Gemini clients.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlencode

import httpx


OnEvent = Callable[[dict[str, Any]], Awaitable[None] | None]


async def subscribe_client_events(
        *,
        events_url: str,
        platform: str,
        session_id: str,
        on_event: OnEvent,
) -> None:
    """
    Long-lived SSE subscription to Adapter GET /events.

    Only receives events for this exact (platform, sessionId).
    """
    base = events_url.rstrip("/")
    query = urlencode(
        {
            "platform": platform.strip(),
            "sessionId": session_id.strip(),
        }
    )
    url = f"{base}?{query}"

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
                "GET",
                url,
                headers={"Accept": "text/event-stream"},
        ) as response:
            response.raise_for_status()

            event_name = "message"
            data_lines: list[str] = []

            async for line in response.aiter_lines():
                if line is None:
                    continue

                if line.startswith(":"):
                    # SSE comment / keepalive
                    continue

                if line.startswith("event:"):
                    event_name = line[6:].strip() or "message"
                    continue

                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
                    continue

                if line == "":
                    if not data_lines:
                        event_name = "message"
                        continue

                    raw = "\n".join(data_lines)
                    data_lines = []
                    name = event_name
                    event_name = "message"

                    if name != "workflow.updated":
                        continue

                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    if not isinstance(payload, dict):
                        continue

                    result = on_event(payload)
                    if isinstance(result, Awaitable):
                        await result
