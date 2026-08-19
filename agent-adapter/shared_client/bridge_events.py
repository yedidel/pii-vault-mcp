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

import importlib.util
from pathlib import Path

_AUTH_FILE = Path(__file__).resolve().parent / "auth.py"
_AUTH_SPEC = importlib.util.spec_from_file_location(
    "shared_client_auth",
    _AUTH_FILE,
)
if _AUTH_SPEC is None or _AUTH_SPEC.loader is None:
    raise ImportError(f"Cannot load auth from {_AUTH_FILE}")
_AUTH_MOD = importlib.util.module_from_spec(_AUTH_SPEC)
_AUTH_SPEC.loader.exec_module(_AUTH_MOD)
get_auth_headers = _AUTH_MOD.get_auth_headers


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
                headers={
                    "Accept": "text/event-stream",
                    **get_auth_headers(),
                },
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