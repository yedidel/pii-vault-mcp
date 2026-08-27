#!/usr/bin/env python3
"""
End-to-end: register + SSE + send_action + wait for workflow.updated.

Requires (all running):
  - docker: db + kafka
  - Bridge (gradlew run)
  - Adapter (python adapter.py, MCP_TRANSPORT=http)
  - Mock Vault (python mock-vault/vault_sim.py)
  - Demo forms (python demo-forms/server.py) for FILL_FORM

Uses a real Gemini interaction.id so GeminiProvider wake can succeed.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import httpx

_GEMINI_CLIENT = Path(__file__).resolve().parent.parent / "gemini-client"
sys.path.insert(0, str(_GEMINI_CLIENT))

from interaction_store import ensure_interaction_id  # noqa: E402
from bridge_mcp import BridgeMcpClient  # noqa: E402

ADAPTER_BASE = os.getenv("ADAPTER_BASE", "http://127.0.0.1:8000").rstrip("/")
MCP_URL = os.getenv("BRIDGE_MCP_URL", f"{ADAPTER_BASE}/mcp")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
SSE_TIMEOUT_SECONDS = float(os.getenv("E2E_SSE_TIMEOUT_SECONDS", "120"))


def _auth_headers() -> dict[str, str]:
    token = os.getenv("ADAPTER_AUTH_TOKEN", "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


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


async def _wait_for_workflow_updated(
        *,
        platform: str,
        session_id: str,
        sse_token: str,
) -> dict:
    url = (
        f"{ADAPTER_BASE}/events"
        f"?platform={platform}&sessionId={session_id}&token={sse_token}"
    )

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
                    return payload

    raise RuntimeError("SSE stream closed before workflow.updated")


async def main() -> int:
    api_key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or ""
    ).strip()
    if not api_key:
        print("ERROR: set GEMINI_API_KEY or GOOGLE_API_KEY in agent-adapter/.env")
        return 1

    print("Ensuring Gemini interaction.id ...")
    interaction_id = ensure_interaction_id(api_key=api_key, model=GEMINI_MODEL)
    print(f"interaction.id = {interaction_id}")

    platform = "gemini"
    async with httpx.AsyncClient(timeout=15.0) as client:
        sse_token = await _register_session(
            client,
            platform=platform,
            session_id=interaction_id,
        )
    print(f"sseToken       = {sse_token[:20]}...")

    sse_task = asyncio.create_task(
        asyncio.wait_for(
            _wait_for_workflow_updated(
                platform=platform,
                session_id=interaction_id,
                sse_token=sse_token,
            ),
            timeout=SSE_TIMEOUT_SECONDS,
        ),
        name="wait-workflow-updated",
    )

    await asyncio.sleep(0.5)

    print("\nCalling send_action FILL_FORM via Adapter MCP ...")
    print("(must run in adapter.py process so webhook finds pending workflow)")
    async with BridgeMcpClient(interaction_id, mcp_url=MCP_URL) as bridge:
        raw = await bridge.call_tool(
            "send_action",
            {
                "agentId": "agent-123",
                "actionType": "FILL_FORM",
                "parameters": {
                    "name": "Dana",
                    "email": "dana@example.com",
                    "password": "Secret123",
                },
            },
        )
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {"error": raw}
    print("send_action result:", json.dumps(result, indent=2))

    if result.get("error"):
        sse_task.cancel()
        return 1

    print(
        f"\nWaiting for workflow.updated on SSE "
        f"(timeout {SSE_TIMEOUT_SECONDS}s) ..."
    )
    print("Approve in Mock Vault terminal if prompted (y).\n")

    try:
        event = await sse_task
    except asyncio.TimeoutError:
        print(
            f"ERROR: No workflow.updated within {SSE_TIMEOUT_SECONDS}s"
        )
        print(
            "Check: Bridge running? Mock Vault approved (y)? "
            "Adapter MCP_TRANSPORT=http? Gemini wake quota? "
            "Adapter logs for 'No pending workflow' or 'Gemini wake failed'."
        )
        return 1

    print("\n=== workflow.updated received ===")
    print(json.dumps(event, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
