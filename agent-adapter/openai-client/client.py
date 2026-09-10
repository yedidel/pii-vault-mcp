#!/usr/bin/env python3
"""
Minimal OpenAI Bridge client.

Mirrors Claude bridge-wake / Gemini hooks:

  1. Auto-create or reuse Conversations API conversation.id
  2. Connect to bridge-adapter MCP (Streamable HTTP)
  3. Chat via Responses API with conversation=conversation.id
  4. Expose Adapter MCP tools to GPT as function tools
  5. Inject platform=openai + sessionId=conversation.id on send_action
  6. Subscribe to Adapter GET /events for this session
  7. Bridge → OpenAIProvider wakes Conversation; client is notified via SSE
     and fetches + renders new conversation items
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()
import argparse
import asyncio
import json
import os
import sys
from typing import Any
from urllib.parse import urlparse, urlunparse

from openai import OpenAI

from bridge_events import subscribe_client_events
from bridge_mcp import BridgeMcpClient
from conversation_store import (
    ensure_conversation_id,
    reset_conversation_id,
    save_sse_token,
)
from session_register import adapter_base_from_mcp_url, register_bridge_session
from conversation_updates import (
    fetch_new_conversation_items,
    format_conversation_item,
    latest_conversation_item_id,
)


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6")
MAX_TOOL_TURNS = int(os.getenv("OPENAI_BRIDGE_MAX_TOOL_TURNS", "12"))

SYSTEM_INSTRUCTIONS = """
You are a Bridge-enabled OpenAI agent.

You have access to bridge-adapter MCP tools, including send_action and
get_action_status.

When the user asks you to start a Bridge workflow (payment, transaction,
or form fill), call send_action.

Rules for send_action:
- Always use platform=\"openai\".
- Always pass sessionId as the current OpenAI conversation.id provided below.
- Always put action data under the nested object \"parameters\".
  Never leave parameters as {}.
  Never place amount/currency/id/name at the top level of the tool call.
- PAYMENT example:
  {
    \"agentId\": \"default\",
    \"actionType\": \"PAYMENT\",
    \"parameters\": {\"amount\": \"100\", \"currency\": \"ILS\"},
    \"sessionId\": \"<conversation.id>\",
    \"platform\": \"openai\"
  }

After send_action returns a requestId / workflowId, you may call
get_action_status to check progress. Asynchronous Bridge updates are also
appended into THIS same OpenAI conversation by OpenAIProvider — treat those
as authoritative workflow updates when they appear.
""".strip()


def _require_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY in environment")
    return api_key


def _events_url_from_mcp_url(mcp_url: str) -> str:
    """
    Derive Adapter /events from the MCP URL.

    http://127.0.0.1:8000/mcp  ->  http://127.0.0.1:8000/events
    """
    override = os.getenv("BRIDGE_EVENTS_URL", "").strip()
    if override:
        return override.rstrip("/")

    parsed = urlparse(mcp_url)
    return urlunparse(
        (parsed.scheme, parsed.netloc, "/events", "", "", "")
    )


def _print_assistant(text: str) -> None:
    text = (text or "").strip()
    if text:
        print(f"\nassistant> {text}\n")


def _extract_function_calls(response: Any) -> list[Any]:
    return [
        item
        for item in (response.output or [])
        if getattr(item, "type", None) == "function_call"
    ]


def _session_instructions(conversation_id: str) -> str:
    return (
        SYSTEM_INSTRUCTIONS
        + f"\n\nCurrent conversation.id (use as send_action sessionId): "
        + conversation_id
    )


def _pairing_continue_message(user_install_id: str) -> str:
    return (
        "Vault pairing completed successfully.\n"
        f"userInstallId: {user_install_id}\n"
        "Call send_action now with the same parameters as before to continue."
    )


async def _run_tool_loop(
        *,
        openai_client: OpenAI,
        bridge: BridgeMcpClient,
        conversation_id: str,
        model: str,
        user_input: str | list[dict[str, Any]],
        include_instructions: bool = True,
) -> Any:
    tools = bridge.openai_tools
    create_kwargs: dict[str, Any] = {
        "model": model,
        "conversation": conversation_id,
        "input": user_input,
        "tools": tools or None,
        "parallel_tool_calls": False,
    }
    if include_instructions:
        create_kwargs["instructions"] = _session_instructions(conversation_id)

    response = openai_client.responses.create(**create_kwargs)

    for _ in range(MAX_TOOL_TURNS):
        function_calls = _extract_function_calls(response)
        if not function_calls:
            return response

        tool_outputs: list[dict[str, Any]] = []
        for call in function_calls:
            name = call.name
            try:
                arguments = json.loads(call.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {}

            if not isinstance(arguments, dict):
                arguments = {}

            output = await bridge.call_tool(name, arguments)
            if not isinstance(output, str):
                output = json.dumps(output, ensure_ascii=False)

            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": output,
                }
            )

        # Submit tool outputs on the conversation so Adapter wakes can append
        # later without hitting orphaned function_call items.
        response = openai_client.responses.create(
            model=model,
            conversation=conversation_id,
            input=tool_outputs,
            tools=tools or None,
            parallel_tool_calls=False,
        )

    print(
        f"warning> stopped after {MAX_TOOL_TURNS} tool turns without a final answer",
        file=sys.stderr,
    )
    return response


async def chat_loop(
        *,
        model: str,
        mcp_url: str,
        reset: bool,
) -> None:
    api_key = _require_api_key()

    if reset:
        reset_conversation_id()
        print("conversation store cleared")

    conversation_id = ensure_conversation_id(api_key=api_key)
    openai_client = OpenAI(api_key=api_key)
    events_url = _events_url_from_mcp_url(mcp_url)
    adapter_base_url = adapter_base_from_mcp_url(mcp_url)
    sse_token = await register_bridge_session(
        adapter_base_url=adapter_base_url,
        platform="openai",
        session_id=conversation_id,
    )
    save_sse_token(sse_token)

    # Seed cursor so SSE-driven fetches only show post-subscribe deltas.
    item_cursor = latest_conversation_item_id(openai_client, conversation_id)
    cursor_lock = asyncio.Lock()

    print(f"conversation.id = {conversation_id}")
    print(f"model           = {model}")
    print(f"bridge mcp      = {mcp_url}")
    print(f"bridge events   = {events_url}")
    print("Type a message. Ctrl+C or empty line to exit.\n")

    async def on_client_event(payload: dict[str, Any]) -> None:
        nonlocal item_cursor
        event_type = str(payload.get("type") or "workflow.updated").strip()
        if event_type == "vault.paired":
            user_install_id = str(payload.get("userInstallId") or "").strip()
            print(f"\nvault> paired userInstallId={user_install_id}")
            try:
                response = await _run_tool_loop(
                    openai_client=openai_client,
                    bridge=bridge,
                    conversation_id=conversation_id,
                    model=model,
                    user_input=_pairing_continue_message(user_install_id),
                    include_instructions=False,
                )
            except Exception as error:
                message = str(error)
                if "No tool output found for function call" in message:
                    print(
                        "\nerror> OpenAI conversation has a stale tool call. "
                        "Run with --reset-conversation and try again.\n",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"\nerror> continue after pairing failed: {error}\n",
                        file=sys.stderr,
                    )
            else:
                _print_assistant(getattr(response, "output_text", "") or "")

            async with cursor_lock:
                item_cursor = await asyncio.to_thread(
                    latest_conversation_item_id,
                    openai_client,
                    conversation_id,
                )
            print("you> ", end="", flush=True)
            return

        print(
            f"\nworkflow> status={payload.get('status')} "
            f"requestId={payload.get('requestId')}"
        )

        async with cursor_lock:
            items, item_cursor = await asyncio.to_thread(
                fetch_new_conversation_items,
                openai_client,
                conversation_id,
                item_cursor,
            )
        for item in items:
            rendered = format_conversation_item(item)
            if rendered:
                print(f"\n{rendered}\n")
        print("you> ", end="", flush=True)

    async with BridgeMcpClient(conversation_id, mcp_url=mcp_url) as bridge:
        events_task = asyncio.create_task(
            subscribe_client_events(
                events_url=events_url,
                platform="openai",
                session_id=conversation_id,
                token=sse_token,
                on_event=on_client_event,
            ),
            name="bridge-client-events",
        )

        try:
            while True:
                try:
                    user_text = (
                        await asyncio.to_thread(input, "you> ")
                    ).strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break

                if not user_text:
                    break

                try:
                    response = await _run_tool_loop(
                        openai_client=openai_client,
                        bridge=bridge,
                        conversation_id=conversation_id,
                        model=model,
                        user_input=user_text,
                    )
                except Exception as error:
                    message = str(error)
                    if "No tool output found for function call" in message:
                        print(
                            "\nerror> OpenAI conversation has a stale tool call. "
                            "Run with --reset-conversation and try again.\n",
                            file=sys.stderr,
                        )
                    raise
                _print_assistant(getattr(response, "output_text", "") or "")

                # Advance cursor past items produced by this interactive turn
                # so the SSE handler does not re-print them.
                async with cursor_lock:
                    item_cursor = await asyncio.to_thread(
                        latest_conversation_item_id,
                        openai_client,
                        conversation_id,
                    )
        finally:
            events_task.cancel()
            try:
                await events_task
            except asyncio.CancelledError:
                pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="OpenAI Bridge client (Responses + Conversations + Adapter MCP)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--mcp-url",
        default=os.getenv("BRIDGE_MCP_URL", "http://127.0.0.1:8000/mcp"),
        help="bridge-adapter Streamable HTTP MCP URL",
    )
    parser.add_argument(
        "--reset-conversation",
        action="store_true",
        help="Delete the local conversation store and create a new conversation.id",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        asyncio.run(
            chat_loop(
                model=args.model,
                mcp_url=args.mcp_url,
                reset=args.reset_conversation,
            )
        )
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
