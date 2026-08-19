"""
MCP client for the local bridge-adapter HTTP server.

Connects over Streamable HTTP, lists tools, and executes tool calls.
Injects platform=openai and sessionId=<conversation.id> into send_action
(same role as Gemini BeforeTool hooks / Claude get_continuation_context).

Also normalizes MCP JSON Schemas for the OpenAI Responses function-calling
surface: free-form dict[str,str] schemas (object + additionalProperties only)
often cause models to emit parameters={} or flatten keys to the top level.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
from typing import Any
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

_SHARED_AUTH = (
        Path(__file__).resolve().parent.parent / "shared_client" / "auth.py"
)
_AUTH_SPEC = importlib.util.spec_from_file_location(
    "shared_client_auth",
    _SHARED_AUTH,
)
if _AUTH_SPEC is None or _AUTH_SPEC.loader is None:
    raise ImportError(f"Cannot load shared auth from {_SHARED_AUTH}")
_AUTH_MOD = importlib.util.module_from_spec(_AUTH_SPEC)
_AUTH_SPEC.loader.exec_module(_AUTH_MOD)
get_auth_headers = _AUTH_MOD.get_auth_headers

DEFAULT_MCP_URL = os.getenv(
    "BRIDGE_MCP_URL",
    "http://127.0.0.1:8000/mcp",
)

SEND_ACTION_TOP_LEVEL = {
    "agentId",
    "actionType",
    "parameters",
    "sessionId",
    "platform",
}

# Explicit keys help Responses function-calling fill nested maps.
SEND_ACTION_PARAMETER_PROPERTIES = {
    "amount": {
        "type": "string",
        "description": "Payment amount, e.g. \"100\".",
    },
    "currency": {
        "type": "string",
        "description": "ISO currency code, e.g. \"ILS\" or \"USD\".",
    },
    "id": {
        "type": "string",
        "description": "Form field id for FILL_FORM.",
    },
    "name": {
        "type": "string",
        "description": "Form field name for FILL_FORM.",
    },
    "email": {
        "type": "string",
        "description": "Email for FILL_FORM.",
    },
    "password": {
        "type": "string",
        "description": "Password for FILL_FORM.",
    },
    "transactionId": {
        "type": "string",
        "description": "Transaction id for TRANSACTION.",
    },
    "account": {
        "type": "string",
        "description": "Account identifier for TRANSACTION.",
    },
}


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


def _is_freeform_string_map(schema: Any) -> bool:
    if not isinstance(schema, dict):
        return False
    if schema.get("type") != "object":
        return False
    properties = schema.get("properties")
    if properties:
        return False
    additional = schema.get("additionalProperties")
    if additional is True:
        return True
    if isinstance(additional, dict) and additional.get("type") == "string":
        return True
    return False


def _enrich_send_action_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Make send_action.parameters usable by OpenAI function calling.

    MCP/Pydantic emit dict[str,str] as:
      {"type":"object","additionalProperties":{"type":"string"}}
    Models frequently respond with parameters={} for that shape.
    """
    enriched = copy.deepcopy(schema)
    if enriched.get("type") != "object":
        enriched = {"type": "object", "properties": {}}

    properties = dict(enriched.get("properties") or {})
    parameters_schema = properties.get("parameters")

    if not isinstance(parameters_schema, dict):
        parameters_schema = {
            "type": "object",
            "additionalProperties": {"type": "string"},
        }

    if _is_freeform_string_map(parameters_schema) or not parameters_schema.get(
            "properties"
    ):
        parameters_schema = {
            "type": "object",
            "description": (
                "Action-specific string key/value pairs. "
                "PAYMENT requires amount and currency. "
                "Do not leave this object empty when the user provided values."
            ),
            "properties": copy.deepcopy(SEND_ACTION_PARAMETER_PROPERTIES),
            "additionalProperties": {"type": "string"},
        }

    properties["parameters"] = parameters_schema
    enriched["properties"] = properties

    required = list(enriched.get("required") or [])
    for key in ("agentId", "actionType", "parameters"):
        if key not in required:
            required.append(key)
    enriched["required"] = required

    return enriched


def mcp_tools_to_openai_functions(tools: list[Any]) -> list[dict[str, Any]]:
    """Convert MCP tool descriptors into Responses API function tools."""
    functions: list[dict[str, Any]] = []
    for tool in tools:
        parameters = (
                getattr(tool, "input_schema", None)
                or getattr(tool, "inputSchema", None)
                or {
                    "type": "object",
                    "properties": {},
                }
        )
        if not isinstance(parameters, dict):
            parameters = {"type": "object", "properties": {}}
        else:
            parameters = copy.deepcopy(parameters)

        if tool.name == "send_action":
            parameters = _enrich_send_action_schema(parameters)

        functions.append(
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description or tool.name,
                "parameters": parameters,
            }
        )
    return functions


def normalize_send_action_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Recover parameters when the model flattens amount/currency to top-level
    or encodes parameters as a JSON string.
    """
    args = dict(arguments or {})
    parameters = args.get("parameters", {})

    if isinstance(parameters, str):
        try:
            parsed = json.loads(parameters)
        except json.JSONDecodeError:
            parsed = {}
        parameters = parsed if isinstance(parsed, dict) else {}

    if not isinstance(parameters, dict):
        parameters = {}

    parameters = {
        str(key): "" if value is None else str(value)
        for key, value in parameters.items()
    }

    orphans = {
        key: value
        for key, value in args.items()
        if key not in SEND_ACTION_TOP_LEVEL
    }
    for key, value in orphans.items():
        if key not in parameters or parameters[key] in {"", "null", "None"}:
            parameters[key] = "" if value is None else str(value)
        args.pop(key, None)

    args["parameters"] = parameters
    return args


class BridgeMcpClient:
    """
    Thin wrapper around the Adapter MCP server.

    Owns no Bridge/Adapter business logic — only transport + send_action inject.
    """

    def __init__(
            self,
            conversation_id: str,
            mcp_url: str | None = None,
    ):
        self.conversation_id = conversation_id.strip()
        if not self.conversation_id:
            raise ValueError("conversation_id is required")

        self.mcp_url = (mcp_url or DEFAULT_MCP_URL).rstrip("/")
        self._session: ClientSession | None = None
        self._transport_cm = None
        self._session_cm = None
        self._http_client: httpx.AsyncClient | None = None
        self._openai_tools: list[dict[str, Any]] = []

    @property
    def openai_tools(self) -> list[dict[str, Any]]:
        return self._openai_tools

    async def __aenter__(self) -> "BridgeMcpClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def connect(self) -> None:
        self._http_client = httpx.AsyncClient(
            headers=get_auth_headers(),
            follow_redirects=True,
            timeout=httpx.Timeout(30.0, read=300.0),
        )
        await self._http_client.__aenter__()

        self._transport_cm = streamable_http_client(
            self.mcp_url,
            http_client=self._http_client,
        )
        streams = await self._transport_cm.__aenter__()
        read_stream = streams[0]
        write_stream = streams[1]

        self._session_cm = ClientSession(read_stream, write_stream)
        self._session = await self._session_cm.__aenter__()
        await self._session.initialize()

        listed = await self._session.list_tools()
        self._openai_tools = mcp_tools_to_openai_functions(list(listed.tools))

    async def close(self) -> None:
        if self._session_cm is not None:
            await self._session_cm.__aexit__(None, None, None)
            self._session_cm = None
            self._session = None

        if self._transport_cm is not None:
            await self._transport_cm.__aexit__(None, None, None)
            self._transport_cm = None

        if self._http_client is not None:
            await self._http_client.__aexit__(None, None, None)
            self._http_client = None

    def _prepare_arguments(
            self,
            name: str,
            arguments: dict[str, Any],
    ) -> dict[str, Any]:
        args = dict(arguments or {})

        # Client-owned bootstrap inject — Adapter stays agnostic.
        if name == "send_action":
            args = normalize_send_action_arguments(args)
            args["platform"] = "openai"
            args["sessionId"] = self.conversation_id

            # Prefer a real agent id over model placeholders like "..." or blanks.
            default_agent_id = (
                    os.getenv("BRIDGE_AGENT_ID")
                    or os.getenv("OPENAI_BRIDGE_AGENT_ID")
                    or "agent-123"
            ).strip()
            agent_id = str(args.get("agentId") or "").strip()
            if (not agent_id) or agent_id in {"...", "…", "string", "agentId"}:
                args["agentId"] = default_agent_id

        return args

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        if self._session is None:
            raise RuntimeError("Bridge MCP client is not connected")

        prepared = self._prepare_arguments(name, arguments or {})
        result = await self._session.call_tool(name, arguments=prepared)
        return _tool_result_to_text(result)