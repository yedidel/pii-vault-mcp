"""SSE subscription to Adapter GET /events."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlencode

import httpx

from bridge_sdk.auth import get_auth_headers
from bridge_sdk.exceptions import BridgeTimeoutError

OnEvent = Callable[[dict[str, Any]], Awaitable[None] | None]


async def register_session(
        *,
        adapter_base_url: str,
        platform: str,
        session_id: str,
) -> str:
    """POST /sessions/register and return sseToken."""
    base = adapter_base_url.rstrip("/")
    url = f"{base}/sessions/register"
    payload = {
        "platform": platform.strip().lower(),
        "sessionId": session_id.strip(),
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json", **get_auth_headers()},
        )
        response.raise_for_status()
        body = response.json()

    token = str(body.get("sseToken") or "").strip()
    if not token:
        raise RuntimeError("Adapter /sessions/register returned no sseToken")
    return token


async def wait_for_workflow_event(
        *,
        events_url: str,
        platform: str,
        session_id: str,
        token: str,
        request_id: str | None = None,
        timeout: float = 120.0,
) -> dict[str, Any]:
    """
    Block until workflow.updated (optionally matching request_id) or vault.paired.

    Requires Adapter SdkProvider (platform=sdk) so wake + SSE notify succeed.
    """
    base = events_url.rstrip("/")
    query = urlencode({
        "platform": platform.strip(),
        "sessionId": session_id.strip(),
        "token": token.strip(),
    })
    url = f"{base}?{query}"
    request_id_normalized = (request_id or "").strip()

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
                "GET",
                url,
                headers={"Accept": "text/event-stream", **get_auth_headers()},
        ) as response:
            response.raise_for_status()

            event_name = "message"
            data_lines: list[str] = []

            async for line in response.aiter_lines():
                if line is None:
                    continue
                if line.startswith(":"):
                    continue
                if line.startswith("event:"):
                    event_name = line[6:].strip() or "message"
                    continue
                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
                    continue
                if line != "":
                    continue

                if not data_lines:
                    event_name = "message"
                    continue

                raw = "\n".join(data_lines)
                data_lines = []
                name = event_name
                event_name = "message"

                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                if name == "connected":
                    continue
                if name not in {"workflow.updated", "vault.paired"}:
                    continue

                if request_id_normalized:
                    event_request_id = str(payload.get("requestId") or "").strip()
                    if event_request_id and event_request_id != request_id_normalized:
                        continue

                return payload

    raise BridgeTimeoutError(f"No workflow event within {timeout}s")


async def subscribe_client_events(
        *,
        events_url: str,
        platform: str,
        session_id: str,
        token: str,
        on_event: OnEvent,
) -> None:
    """Long-lived SSE loop (for advanced integrations)."""
    base = events_url.rstrip("/")
    query = urlencode({
        "platform": platform.strip(),
        "sessionId": session_id.strip(),
        "token": token.strip(),
    })
    url = f"{base}?{query}"

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
                "GET",
                url,
                headers={"Accept": "text/event-stream", **get_auth_headers()},
        ) as response:
            response.raise_for_status()

            event_name = "message"
            data_lines: list[str] = []

            async for line in response.aiter_lines():
                if line is None:
                    continue
                if line.startswith(":"):
                    continue
                if line.startswith("event:"):
                    event_name = line[6:].strip() or "message"
                    continue
                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
                    continue
                if line != "":
                    continue

                if not data_lines:
                    event_name = "message"
                    continue

                raw = "\n".join(data_lines)
                data_lines = []
                name = event_name
                event_name = "message"

                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                if name == "connected":
                    continue
                if name not in {"workflow.updated", "vault.paired"}:
                    continue

                result = on_event(payload)
                if isinstance(result, Awaitable):
                    await result
