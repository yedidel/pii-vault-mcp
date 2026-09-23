#!/usr/bin/env python3
"""
Live E2E: Gemini agent FILL_FORM → Mock Vault approval → Adapter wake → SSE.

Does not mock Gemini, Bridge, Mock Vault, webhook, or SSE.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import httpx
from google import genai

_GEMINI_CLIENT = Path(__file__).resolve().parent.parent / "gemini-client"
sys.path.insert(0, str(_GEMINI_CLIENT))

import client as gemini_client  # noqa: E402
from bridge_mcp import BridgeMcpClient  # noqa: E402
from interaction_store import ensure_interaction_id, reset_interaction_id  # noqa: E402
from interaction_updates import fetch_interaction, format_interaction  # noqa: E402

ADAPTER_BASE = os.getenv("ADAPTER_BASE", "http://127.0.0.1:8000").rstrip("/")
MCP_URL = os.getenv("BRIDGE_MCP_URL", f"{ADAPTER_BASE}/mcp")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
DIRECTORY_BASE = os.getenv("INSTALL_DIRECTORY_URL", "http://127.0.0.1:8010").rstrip("/")
SSE_TIMEOUT_SECONDS = float(os.getenv("E2E_SSE_TIMEOUT_SECONDS", "120"))
STORE_PATH = Path("/tmp/gemini-bridge-e2e-wake.json")


def _auth_headers() -> dict[str, str]:
    token = os.getenv("ADAPTER_AUTH_TOKEN", "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _safe_tool_result(raw: str) -> str:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw[:400]
    if isinstance(payload, dict):
        redacted = {
            key: value
            for key, value in payload.items()
            if key.lower() not in {"password", "email", "token", "sseToken", "apiKey"}
        }
        return json.dumps(redacted)
    return raw[:400]


async def _register_session(session_id: str) -> str:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{ADAPTER_BASE}/sessions/register",
            json={"platform": "gemini", "sessionId": session_id},
            headers={"Content-Type": "application/json", **_auth_headers()},
        )
        response.raise_for_status()
        token = str(response.json().get("sseToken") or "").strip()
        if not token:
            raise RuntimeError("register returned no sseToken")
        return token


async def _wait_for_workflow_updated(*, session_id: str, sse_token: str) -> dict:
    url = (
        f"{ADAPTER_BASE}/events"
        f"?platform=gemini&sessionId={session_id}&token={sse_token}"
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
                    print("STAGE SSE_CONNECTED", json.dumps(payload))
                    if os.getenv("E2E_AUTO_APPROVE_VAULT", "").strip() == "1":
                        with open("/tmp/mock-vault-stdin", "w", encoding="utf-8") as fifo:
                            fifo.write("y\n")
                        print("STAGE VAULT_APPROVAL_SENT y")
                    continue
                if name == "workflow.updated":
                    return payload
    raise RuntimeError("SSE stream closed before workflow.updated")


async def _fetch_last_submission() -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://127.0.0.1:9000/api/last-submission")
            if response.status_code != 200:
                return None
            payload = response.json()
            if isinstance(payload, dict):
                return {
                    "name": payload.get("name"),
                    "source": payload.get("source"),
                    "registeredAt": payload.get("registeredAt"),
                    "registrationId": payload.get("registrationId"),
                }
    except Exception as error:
        print("STAGE FORM_POLL_ERROR", type(error).__name__)
    return None


async def main() -> int:
    os.environ["BRIDGE_AGENT_ID"] = "agent-123"
    api_key = (
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    ).strip()
    if not api_key:
        print("FAIL: missing Gemini API key in environment/.env")
        return 1

    reset_interaction_id(STORE_PATH)
    os.environ["GEMINI_BRIDGE_INTERACTION_STORE"] = str(STORE_PATH)

    print("STAGE PRECHECK adapter", ADAPTER_BASE, "mcp", MCP_URL, "model", GEMINI_MODEL)
    bootstrap_id = ensure_interaction_id(
        api_key=api_key,
        model=GEMINI_MODEL,
        path=STORE_PATH,
    )
    print("STAGE AGENT_INTERACTION_CREATED original_id=", bootstrap_id)

    tool_names: list[str] = []
    send_action_session_id: str | None = None
    function_result_tip_id: str | None = None
    send_action_result: dict[str, Any] = {}

    genai_client = genai.Client(api_key=api_key)

    async with BridgeMcpClient(bootstrap_id, mcp_url=MCP_URL) as bridge:
        original_call_tool = bridge.call_tool

        async def tracing_call_tool(name: str, arguments: dict | None = None) -> str:
            nonlocal send_action_result
            tool_names.append(name)
            print("STAGE TOOL_CALL", name)
            raw = await original_call_tool(name, arguments)
            if name == "send_action":
                print("STAGE SEND_ACTION_SESSION", bridge.interaction_id)
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = {"raw": raw[:400]}
                if isinstance(parsed, dict):
                    send_action_result = {
                        "keys": sorted(parsed.keys()),
                        "workflowId": parsed.get("workflowId"),
                        "requestId": parsed.get("requestId"),
                        "status": parsed.get("status"),
                        "error": parsed.get("error"),
                        "pairingCode": parsed.get("pairingCode"),
                    }
                    print("STAGE SEND_ACTION_RESULT", json.dumps(send_action_result))
                else:
                    print("STAGE SEND_ACTION_NON_DICT", type(parsed).__name__)
            return raw

        bridge.call_tool = tracing_call_tool  # type: ignore[method-assign]

        prompt = (
            "Fill the registration form now using send_action. "
            "Use agentId agent-123, actionType FILL_FORM, and parameters "
            "name Dana, email dana@example.com, password Secret123. "
            "Do not call get_action_status. After send_action returns, stop."
        )
        print("STAGE GEMINI_USER_TURN starting tool loop")
        started = time.time()
        try:
            _response, tip_id, send_action_session_id = await gemini_client._run_tool_loop(
                genai_client=genai_client,
                bridge=bridge,
                interaction_id=bootstrap_id,
                model=GEMINI_MODEL,
                user_input=prompt,
            )
        except Exception as error:
            print("FAIL: Gemini tool loop", type(error).__name__, str(error)[:400])
            return 1
        function_result_tip_id = tip_id
        print(
            "STAGE TOOL_LOOP_DONE elapsed_s=",
            round(time.time() - started, 2),
            "tools=",
            tool_names,
            "send_action_session_id=",
            send_action_session_id,
            "function_result_tip_id=",
            function_result_tip_id,
        )

    if not send_action_session_id:
        print("FAIL: Gemini agent did not call send_action")
        return 1
    if "get_action_status" in tool_names:
        print("FAIL: get_action_status raced the wake path tools=", tool_names)
        return 1
    if send_action_result.get("error"):
        print("FAIL: send_action error", send_action_result.get("error"))
        return 1

    pairing_code = str(send_action_result.get("pairingCode") or "").strip()
    if pairing_code or not send_action_result.get("workflowId"):
        if not pairing_code:
            print("FAIL: send_action did not store a workflow and had no pairingCode")
            return 1
        print("STAGE PAIRING_REQUIRED code=", pairing_code)
        async with httpx.AsyncClient(timeout=15.0) as client:
            complete = await client.post(
                f"{DIRECTORY_BASE}/api/pair/complete",
                json={"pairingCode": pairing_code},
            )
            complete.raise_for_status()
            print(
                "STAGE PAIRING_COMPLETED",
                json.dumps(
                    {
                        "status": complete.json().get("status"),
                        "hasUserInstallId": bool(complete.json().get("userInstallId")),
                    }
                ),
            )
        print("STAGE PAIRING_WAIT adapter watcher")
        await asyncio.sleep(3.0)
        print("STAGE GEMINI_RETRY_SEND_ACTION after pairing")
        async with BridgeMcpClient(send_action_session_id, mcp_url=MCP_URL) as bridge:
            original_call_tool = bridge.call_tool

            async def tracing_call_tool(name: str, arguments: dict | None = None) -> str:
                nonlocal send_action_result
                tool_names.append(name)
                print("STAGE TOOL_CALL", name)
                raw = await original_call_tool(name, arguments)
                if name == "send_action":
                    print("STAGE SEND_ACTION_SESSION", bridge.interaction_id)
                    parsed = json.loads(raw)
                    send_action_result = {
                        "keys": sorted(parsed.keys()) if isinstance(parsed, dict) else [],
                        "workflowId": parsed.get("workflowId") if isinstance(parsed, dict) else None,
                        "requestId": parsed.get("requestId") if isinstance(parsed, dict) else None,
                        "status": parsed.get("status") if isinstance(parsed, dict) else None,
                        "error": parsed.get("error") if isinstance(parsed, dict) else None,
                    }
                    print("STAGE SEND_ACTION_RESULT", json.dumps(send_action_result))
                return raw

            bridge.call_tool = tracing_call_tool  # type: ignore[method-assign]
            retry_prompt = (
                "Vault pairing is complete. Call send_action again for FILL_FORM "
                "with agentId agent-123, name Dana, email dana@example.com, "
                "password Secret123. Do not call get_action_status."
            )
            _response, function_result_tip_id, send_action_session_id = (
                await gemini_client._run_tool_loop(
                    genai_client=genai_client,
                    bridge=bridge,
                    interaction_id=send_action_session_id,
                    model=GEMINI_MODEL,
                    user_input=retry_prompt,
                )
            )
            print(
                "STAGE TOOL_LOOP_RETRY_DONE tools=",
                tool_names,
                "send_action_session_id=",
                send_action_session_id,
                "function_result_tip_id=",
                function_result_tip_id,
            )

    if not send_action_result.get("workflowId"):
        print("FAIL: pending workflow was not stored")
        return 1
    if "get_action_status" in tool_names:
        print("FAIL: get_action_status raced the wake path tools=", tool_names)
        return 1

    print("STAGE SSE_SUBSCRIBE sessionId=", send_action_session_id)
    sse_token = await _register_session(send_action_session_id)
    print("STAGE SSE_TOKEN_PRESENT", bool(sse_token), "len", len(sse_token))

    print(
        "STAGE WAIT_VAULT_APPROVAL "
        "Approve Mock Vault now (y). Waiting for workflow.updated ..."
    )
    t0 = time.time()
    try:
        event = await asyncio.wait_for(
            _wait_for_workflow_updated(
                session_id=send_action_session_id,
                sse_token=sse_token,
            ),
            timeout=SSE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        print("FAIL: SSE timeout", SSE_TIMEOUT_SECONDS)
        return 1
    sse_wait_s = round(time.time() - t0, 2)
    print("STAGE SSE_WORKFLOW_UPDATED elapsed_s=", sse_wait_s)
    safe_event = {
        "type": event.get("type"),
        "status": event.get("status"),
        "workflowId": event.get("workflowId"),
        "requestId": event.get("requestId"),
        "sessionId": event.get("sessionId"),
        "resumeSessionId": event.get("resumeSessionId"),
    }
    print("STAGE SSE_EVENT", json.dumps(safe_event))

    resume_session_id = str(event.get("resumeSessionId") or "").strip()
    if not resume_session_id:
        print("FAIL: missing resumeSessionId")
        return 1
    if resume_session_id == send_action_session_id:
        print("FAIL: resumeSessionId equals original; no successor created")
        return 1
    if function_result_tip_id and resume_session_id == function_result_tip_id:
        print("FAIL: resumeSessionId is local function-result tip, not wake successor")
        return 1

    woke = fetch_interaction(genai_client, resume_session_id)
    woke_id = str(getattr(woke, "id", "") or resume_session_id).strip()
    output = format_interaction(woke) or ""
    print("STAGE GEMINI_WAKE_ORIGINAL", send_action_session_id)
    print("STAGE GEMINI_WAKE_PREVIOUS_INTERACTION_ID", send_action_session_id)
    print("STAGE GEMINI_WAKE_SUCCESSOR", woke_id)
    print("STAGE GEMINI_WAKE_OUTPUT", output[:800])
    if woke_id != resume_session_id:
        print("FAIL: fetched id != resumeSessionId")
        return 1
    if not output.strip():
        print("FAIL: successor has no agent output")
        return 1

    submission = await _fetch_last_submission()
    print("STAGE FORM_SUBMISSION", json.dumps(submission or {}))

    client_continues_from_successor = (
        resume_session_id == woke_id
        and resume_session_id != function_result_tip_id
        and resume_session_id != send_action_session_id
    )
    print(
        "STAGE CLIENT_CONTINUATION_CHOICE",
        json.dumps(
            {
                "wouldUseResumeSessionId": resume_session_id,
                "wouldNotUseFunctionResultTip": function_result_tip_id,
                "continuesFromSuccessor": client_continues_from_successor,
            }
        ),
    )
    print("STAGE PASS_GATES_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
