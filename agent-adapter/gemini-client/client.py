#!/usr/bin/env python3
"""
Minimal Gemini Bridge client.

Parallel to openai-client:

  1. Auto-create or reuse Interactions API interaction.id
  2. Connect to bridge-adapter MCP (Streamable HTTP)
  3. Chat via Interactions API with previous_interaction_id chaining
  4. Expose Adapter MCP tools as Gemini function tools
  5. Inject platform=gemini + sessionId=interaction.id on send_action
  6. Subscribe to Adapter GET /events for the send_action sessionId
  7. Bridge → GeminiProvider wakes a new Interaction; client is notified
     via SSE, fetches + renders it, then re-subscribes to that id
"""

from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()

import argparse
import asyncio
import os
import sys
from typing import Any
from urllib.parse import urlparse, urlunparse

from google import genai

from bridge_events import subscribe_client_events
from bridge_mcp import BridgeMcpClient
from interaction_store import (
    ensure_interaction_id,
    reset_interaction_id,
    save_interaction_id,
)
from interaction_updates import fetch_interaction, format_interaction


DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
MAX_TOOL_TURNS = int(os.getenv("GEMINI_BRIDGE_MAX_TOOL_TURNS", "12"))

SYSTEM_INSTRUCTIONS = """
You are a Bridge-enabled Gemini agent.

You have access to bridge-adapter MCP tools, including send_action and
get_action_status.

When the user asks you to start a Bridge workflow (payment, transaction,
or form fill), call send_action.

Rules for send_action:
- Always use platform=\"gemini\".
- Always pass sessionId as the current Gemini interaction.id provided below.
- Always put action data under the nested object \"parameters\".
  Never leave parameters as {}.
  Never place amount/currency/id/name at the top level of the tool call.
- PAYMENT example:
  {
    \"agentId\": \"default\",
    \"actionType\": \"PAYMENT\",
    \"parameters\": {\"amount\": \"100\", \"currency\": \"ILS\"},
    \"sessionId\": \"<interaction.id>\",
    \"platform\": \"gemini\"
  }

After send_action returns a requestId / workflowId, you may call
get_action_status to check progress. Asynchronous Bridge updates continue
this interaction chain via GeminiProvider — treat those as authoritative
workflow updates when they appear.
""".strip()


def _require_api_key() -> str:
    api_key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or ""
    ).strip()
    if not api_key:
        raise SystemExit("Missing GEMINI_API_KEY or GOOGLE_API_KEY in environment")
    return api_key


def _events_url_from_mcp_url(mcp_url: str) -> str:
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


def _extract_function_calls(interaction: Any) -> list[Any]:
    calls: list[Any] = []
    for step in getattr(interaction, "steps", None) or []:
        if getattr(step, "type", None) == "function_call":
            calls.append(step)
    return calls


async def _run_tool_loop(
        *,
        genai_client: genai.Client,
        bridge: BridgeMcpClient,
        interaction_id: str,
        model: str,
        user_input: str | list[dict[str, Any]],
        on_send_action_session: Any = None,
) -> tuple[Any, str, str | None]:
    """
    Returns (final_interaction, tip_interaction_id, send_action_session_id).

    send_action_session_id is the sessionId actually injected into Bridge —
    the SSE subscription must stay on that id until the wake arrives.
    """
    tools = bridge.gemini_tools or None
    tip_id = interaction_id
    send_action_session_id: str | None = None

    bridge.set_interaction_id(tip_id)

    interaction = genai_client.interactions.create(
        model=model,
        previous_interaction_id=tip_id,
        system_instruction=SYSTEM_INSTRUCTIONS
        + f"\n\nCurrent interaction.id (use as send_action sessionId): "
        + tip_id,
        input=user_input,
        tools=tools,
    )
    tip_id = (interaction.id or tip_id).strip()
    bridge.set_interaction_id(tip_id)

    for _ in range(MAX_TOOL_TURNS):
        function_calls = _extract_function_calls(interaction)
        if not function_calls:
            return interaction, tip_id, send_action_session_id

        tool_outputs: list[dict[str, Any]] = []
        for call in function_calls:
            name = call.name
            arguments = getattr(call, "arguments", None) or {}
            if not isinstance(arguments, dict):
                arguments = {}

            bridge.set_interaction_id(tip_id)
            output = await bridge.call_tool(name, arguments)

            if name == "send_action":
                send_action_session_id = tip_id
                if on_send_action_session is not None:
                    await on_send_action_session(send_action_session_id)

            tool_outputs.append(
                {
                    "type": "function_result",
                    "call_id": call.id,
                    "name": name,
                    "result": output,
                }
            )

        interaction = genai_client.interactions.create(
            model=model,
            previous_interaction_id=tip_id,
            system_instruction=SYSTEM_INSTRUCTIONS
            + f"\n\nCurrent interaction.id (use as send_action sessionId): "
            + tip_id,
            input=tool_outputs,
            tools=tools,
        )
        tip_id = (interaction.id or tip_id).strip()
        bridge.set_interaction_id(tip_id)

    print(
        f"warning> stopped after {MAX_TOOL_TURNS} tool turns without a final answer",
        file=sys.stderr,
    )
    return interaction, tip_id, send_action_session_id


class _EventsSubscription:
    """Manage a single SSE subscription that can be restarted on session rotate."""

    def __init__(
            self,
            *,
            events_url: str,
            on_event,
    ) -> None:
        self.events_url = events_url
        self.on_event = on_event
        self.session_id = ""
        self._task: asyncio.Task | None = None

    async def start(self, session_id: str) -> None:
        session_id = session_id.strip()
        if not session_id:
            raise ValueError("session_id is required for SSE subscribe")

        if (
                self._task is not None
                and not self._task.done()
                and self.session_id == session_id
        ):
            return

        await self.stop()
        self.session_id = session_id
        self._task = asyncio.create_task(
            subscribe_client_events(
                events_url=self.events_url,
                platform="gemini",
                session_id=self.session_id,
                on_event=self.on_event,
            ),
            name="bridge-client-events",
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None


async def chat_loop(
        *,
        model: str,
        mcp_url: str,
        reset: bool,
) -> None:
    api_key = _require_api_key()

    if reset:
        reset_interaction_id()
        print("interaction store cleared")

    interaction_id = ensure_interaction_id(api_key=api_key, model=model)
    genai_client = genai.Client(api_key=api_key)
    events_url = _events_url_from_mcp_url(mcp_url)

    print(f"interaction.id = {interaction_id}")
    print(f"model          = {model}")
    print(f"bridge mcp     = {mcp_url}")
    print(f"bridge events  = {events_url}")
    print("Type a message. Ctrl+C or empty line to exit.\n")

    tip_lock = asyncio.Lock()
    events: _EventsSubscription | None = None
    awaiting_wake_session_id: str | None = None

    async def on_workflow_updated(payload: dict[str, Any]) -> None:
        nonlocal interaction_id, awaiting_wake_session_id

        resume_session_id = str(payload.get("resumeSessionId") or "").strip()
        if not resume_session_id:
            print(
                "error> workflow.updated missing resumeSessionId",
                file=sys.stderr,
            )
            return

        print(
            f"\nworkflow> status={payload.get('status')} "
            f"requestId={payload.get('requestId')}"
        )

        try:
            interaction = await asyncio.to_thread(
                fetch_interaction,
                genai_client,
                resume_session_id,
            )
        except Exception as error:
            print(
                f"error> interactions.get failed: {error}",
                file=sys.stderr,
            )
            return

        fetched_id = (getattr(interaction, "id", None) or resume_session_id).strip()
        rendered = format_interaction(interaction)
        if rendered:
            print(f"\nassistant> {rendered}\n")

        async with tip_lock:
            interaction_id = fetched_id
            save_interaction_id(interaction_id)
            bridge.set_interaction_id(interaction_id)
            awaiting_wake_session_id = None
            if events is not None:
                await events.start(interaction_id)

        print("you> ", end="", flush=True)

    async with BridgeMcpClient(interaction_id, mcp_url=mcp_url) as bridge:
        events = _EventsSubscription(
            events_url=events_url,
            on_event=on_workflow_updated,
        )
        await events.start(interaction_id)

        async def on_send_action_session(session_id: str) -> None:
            nonlocal awaiting_wake_session_id
            async with tip_lock:
                awaiting_wake_session_id = session_id
                await events.start(session_id)

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

                async with tip_lock:
                    current_id = interaction_id

                response, tip_id, _send_action_session_id = await _run_tool_loop(
                    genai_client=genai_client,
                    bridge=bridge,
                    interaction_id=current_id,
                    model=model,
                    user_input=user_text,
                    on_send_action_session=on_send_action_session,
                )
                _print_assistant(getattr(response, "output_text", "") or "")

                async with tip_lock:
                    if awaiting_wake_session_id:
                        if events.session_id != awaiting_wake_session_id:
                            await events.start(awaiting_wake_session_id)
                        bridge.set_interaction_id(awaiting_wake_session_id)
                    else:
                        interaction_id = tip_id
                        save_interaction_id(interaction_id)
                        bridge.set_interaction_id(interaction_id)
                        await events.start(interaction_id)
        finally:
            await events.stop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gemini Bridge client (Interactions + Adapter MCP + SSE notify)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--mcp-url",
        default=os.getenv("BRIDGE_MCP_URL", "http://127.0.0.1:8000/mcp"),
        help="bridge-adapter Streamable HTTP MCP URL",
    )
    parser.add_argument(
        "--reset-interaction",
        action="store_true",
        help="Delete the local interaction store and create a new interaction.id",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        asyncio.run(
            chat_loop(
                model=args.model,
                mcp_url=args.mcp_url,
                reset=args.reset_interaction,
            )
        )
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
