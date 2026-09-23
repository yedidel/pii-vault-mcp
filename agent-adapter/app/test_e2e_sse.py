#!/usr/bin/env python3
"""
WEBHOOK + SSE end-to-end: register, send_action FILL_FORM, wait for
workflow.updated.

Validates Adapter delivery of a matching terminal SSE event. Does not
require Gemini wake/resume (tested in test_gemini_wake.py and
test_e2e_wake_resume.py).

Requires (all running):
  - docker: db + kafka
  - Bridge (./gradlew bootRun)
  - Adapter (MCP_TRANSPORT=http, CONNECTOR_TYPE=WEBHOOK)
  - Mock Vault (approve with y)
  - Demo forms for FILL_FORM
  - pairing completed if INSTALL_DIRECTORY_URL is set
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ADAPTER_BASE = os.getenv("ADAPTER_BASE", "http://127.0.0.1:8000").rstrip("/")
MCP_URL = os.getenv("BRIDGE_MCP_URL", f"{ADAPTER_BASE}/mcp")
SSE_TIMEOUT_SECONDS = float(os.getenv("E2E_SSE_TIMEOUT_SECONDS", "120"))
# SdkProvider is a no-op wake; SSE is still emitted by WakeDispatcher first.
SSE_PLATFORM = "sdk"

_UNEXPECTED_TERMINAL = frozenset({
    "REJECTED",
    "FAILED",
    "FAILED_APP_NOT_INSTALLED",
    "UNTRUSTED",
    "EXPIRED",
})


def _auth_headers() -> dict[str, str]:
    token = os.getenv("ADAPTER_AUTH_TOKEN", "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _tool_result_to_text(result: Any) -> str:
    if getattr(result, "structuredContent", None) is not None:
        return json.dumps(result.structuredContent, default=str)

    parts: list[str] = []
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
        else:
            parts.append(str(block))

    if parts:
        return "\n".join(parts)

    return json.dumps({"isError": bool(getattr(result, "isError", False))})


async def _register_session(
        client: httpx.AsyncClient,
        *,
        platform: str,
        session_id: str,
) -> str:
    response = await client.post(
        f"{ADAPTER_BASE}/sessions/register",
        json={"platform": platform, "sessionId": session_id},
        headers={"Content-Type": "application/json", **_auth_headers()},
    )
    response.raise_for_status()
    body = response.json()
    sse_token = str(body.get("sseToken") or "").strip()
    if not sse_token:
        raise RuntimeError("register returned no sseToken")
    return sse_token


async def _sse_workflow_updated_producer(
        *,
        platform: str,
        session_id: str,
        sse_token: str,
        queue: asyncio.Queue,
) -> None:
    url = (
        f"{ADAPTER_BASE}/events"
        f"?platform={platform}&sessionId={session_id}&token={sse_token}"
    )

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                    "GET",
                    url,
                    headers={"Accept": "text/event-stream", **_auth_headers()},
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
                        print("SSE connected:", json.dumps(payload))
                        continue
                    if name == "workflow.updated":
                        await queue.put(payload)
    except asyncio.CancelledError:
        raise
    except Exception as error:
        await queue.put({"__sse_error__": str(error)})
        raise
    else:
        await queue.put({"__sse_closed__": True})


async def _call_send_action_fill_form(
        *,
        platform: str,
        session_id: str,
) -> dict:
    headers = _auth_headers()
    async with httpx.AsyncClient(
            headers=headers or None,
            follow_redirects=True,
            timeout=httpx.Timeout(30.0, read=300.0),
    ) as http:
        async with streamable_http_client(
                MCP_URL,
                http_client=http,
        ) as streams:
            read_stream = streams[0]
            write_stream = streams[1]
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(
                    "send_action",
                    {
                        "agentId": "agent-123",
                        "actionType": "FILL_FORM",
                        "parameters": {
                            "name": "Dana",
                            "email": "dana@example.com",
                            "password": "Secret123",
                        },
                        "platform": platform,
                        "sessionId": session_id,
                    },
                )
    raw = _tool_result_to_text(result)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"error": raw}
    if not isinstance(parsed, dict):
        return {"error": raw}
    return parsed


def _ids_match(event: dict, workflow_id: str, request_id: str) -> bool:
    event_workflow = str(event.get("workflowId") or "").strip()
    event_request = str(event.get("requestId") or "").strip()
    return event_workflow == workflow_id and event_request == request_id


async def _wait_for_matching_completed(
        *,
        queue: asyncio.Queue,
        workflow_id: str,
        request_id: str,
        timeout_seconds: float,
) -> dict:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds

    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise asyncio.TimeoutError()
        try:
            event = await asyncio.wait_for(queue.get(), timeout=remaining)
        except asyncio.TimeoutError:
            raise

        if event.get("__sse_error__"):
            raise RuntimeError(f"SSE stream failed: {event['__sse_error__']}")
        if event.get("__sse_closed__"):
            raise RuntimeError(
                "SSE stream closed before matching workflow.updated"
            )

        if not _ids_match(event, workflow_id, request_id):
            print(
                "Ignoring unrelated workflow.updated "
                f"workflowId={event.get('workflowId')!r} "
                f"requestId={event.get('requestId')!r}"
            )
            continue

        status = str(event.get("status") or "").strip().upper()
        if status == "COMPLETED":
            return event
        if status in _UNEXPECTED_TERMINAL or status:
            raise RuntimeError(
                "Matching workflow.updated had unexpected status "
                f"{status or '(empty)'}; expected COMPLETED"
            )


async def main() -> int:
    platform = SSE_PLATFORM
    session_id = f"sse-webhook-e2e-{uuid.uuid4()}"

    print(f"Registering SSE session platform={platform} sessionId={session_id}")
    async with httpx.AsyncClient(timeout=15.0) as client:
        sse_token = await _register_session(
            client,
            platform=platform,
            session_id=session_id,
        )
    print(f"sseToken       = {sse_token[:20]}...")

    event_queue: asyncio.Queue = asyncio.Queue()
    sse_task = asyncio.create_task(
        _sse_workflow_updated_producer(
            platform=platform,
            session_id=session_id,
            sse_token=sse_token,
            queue=event_queue,
        ),
        name="sse-workflow-updated-producer",
    )

    await asyncio.sleep(0.5)

    print("\nCalling send_action FILL_FORM via Adapter MCP ...")
    print("(Adapter MCP_TRANSPORT=http; CONNECTOR_TYPE=WEBHOOK)")
    result = await _call_send_action_fill_form(
        platform=platform,
        session_id=session_id,
    )
    print("send_action result:", json.dumps(result, indent=2))

    if result.get("error"):
        sse_task.cancel()
        print("FAIL: send_action returned an error")
        return 1

    workflow_id = str(result.get("workflowId") or "").strip()
    request_id = str(result.get("requestId") or "").strip()
    if not workflow_id or not request_id:
        sse_task.cancel()
        print("FAIL: send_action did not return workflowId and requestId")
        return 1

    print(
        f"\nWaiting for matching workflow.updated "
        f"workflowId={workflow_id} requestId={request_id} "
        f"(timeout {SSE_TIMEOUT_SECONDS}s) ..."
    )
    print("Approve in Mock Vault terminal if prompted (y).\n")

    try:
        event = await _wait_for_matching_completed(
            queue=event_queue,
            workflow_id=workflow_id,
            request_id=request_id,
            timeout_seconds=SSE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        print(
            f"ERROR: No matching workflow.updated within "
            f"{SSE_TIMEOUT_SECONDS}s "
            f"(workflowId={workflow_id} requestId={request_id})"
        )
        print(
            "Check: Bridge running? Mock Vault approved (y)? "
            "Adapter MCP_TRANSPORT=http? CONNECTOR_TYPE=WEBHOOK? "
            "Adapter logs for HMAC / 'No pending workflow'."
        )
        return 1
    except RuntimeError as error:
        print(f"FAIL: {error}")
        return 1
    finally:
        sse_task.cancel()
        try:
            await sse_task
        except asyncio.CancelledError:
            pass

    print("\n=== workflow.updated received ===")
    print(json.dumps(event, indent=2))

    resume_session_id = str(event.get("resumeSessionId") or "").strip()
    if not resume_session_id:
        print(
            "resumeSessionId is null on the initial event "
            "(expected; Gemini resume is tested separately)"
        )

    print("\nPASS: WEBHOOK + SSE E2E completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
