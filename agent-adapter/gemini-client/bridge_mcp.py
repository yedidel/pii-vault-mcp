"""
MCP client for the local bridge-adapter HTTP server (Gemini).

Always overwrites send_action platform, sessionId, and agentId from
trusted runtime. Maps MCP tools to Gemini Interactions function tools.
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

_OPENAI_BRIDGE_MCP = (
        Path(__file__).resolve().parent.parent / "openai-client" / "bridge_mcp.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "openai_bridge_mcp_helpers",
    _OPENAI_BRIDGE_MCP,
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot load helpers from {_OPENAI_BRIDGE_MCP}")
_HELPERS = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_HELPERS)

normalize_send_action_arguments = _HELPERS.normalize_send_action_arguments
_enrich_send_action_schema = _HELPERS._enrich_send_action_schema
inject_send_action_runtime_fields = _HELPERS.inject_send_action_runtime_fields
trusted_agent_id = _HELPERS.trusted_agent_id
PROVIDER_SEND_ACTION_DESCRIPTION = _HELPERS.PROVIDER_SEND_ACTION_DESCRIPTION
get_auth_headers = _HELPERS.get_auth_headers

DEFAULT_MCP_URL = os.getenv(
    "BRIDGE_MCP_URL",
    "http://127.0.0.1:8000/mcp",
)


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


def mcp_tools_to_gemini_functions(tools: list[Any]) -> list[dict[str, Any]]:
    """Convert MCP tool descriptors into Gemini Interactions function tools."""
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

        description = tool.description or tool.name
        if tool.name == "send_action":
            parameters = _enrich_send_action_schema(parameters)
            description = PROVIDER_SEND_ACTION_DESCRIPTION

        functions.append(
            {
                "type": "function",
                "name": tool.name,
                "description": description,
                "parameters": parameters,
            }
        )
    return functions


class BridgeMcpClient:
    """
    Thin wrapper around the Adapter MCP server for the Gemini client.
    """

    def __init__(
            self,
            interaction_id: str,
            mcp_url: str | None = None,
    ):
        self.interaction_id = interaction_id.strip()
        if not self.interaction_id:
            raise ValueError("interaction_id is required")

        self.mcp_url = (mcp_url or DEFAULT_MCP_URL).rstrip("/")
        self._session: ClientSession | None = None
        self._transport_cm = None
        self._session_cm = None
        self._http_client: httpx.AsyncClient | None = None
        self._gemini_tools: list[dict[str, Any]] = []

    @property
    def gemini_tools(self) -> list[dict[str, Any]]:
        return self._gemini_tools

    def set_interaction_id(self, interaction_id: str) -> None:
        interaction_id = interaction_id.strip()
        if not interaction_id:
            raise ValueError("interaction_id must be non-empty")
        self.interaction_id = interaction_id

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
        self._gemini_tools = mcp_tools_to_gemini_functions(list(listed.tools))


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

        if name == "send_action":
            args = inject_send_action_runtime_fields(
                args,
                platform="gemini",
                session_id=self.interaction_id,
                agent_id=trusted_agent_id(
                    "BRIDGE_AGENT_ID",
                    "GEMINI_BRIDGE_AGENT_ID",
                ),
            )

        return args

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        if self._session is None:
            raise RuntimeError("Bridge MCP client is not connected")

        prepared = self._prepare_arguments(name, arguments or {})
        result = await self._session.call_tool(name, arguments=prepared)
        return _tool_result_to_text(result)