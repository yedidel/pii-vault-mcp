"""Low-level MCP transport to the Agent Adapter."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from bridge_sdk.auth import get_auth_headers

DEFAULT_MCP_URL = os.getenv("BRIDGE_MCP_URL", "http://127.0.0.1:8000/mcp")
SDK_PLATFORM = "sdk"


def _tool_result_to_dict(result: Any) -> dict[str, Any]:
    if getattr(result, "structuredContent", None) is not None:
        content = result.structuredContent
        if isinstance(content, dict):
            return content
        return {"value": content}

    parts: list[str] = []
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
        else:
            parts.append(str(block))

    if not parts:
        return {"isError": bool(getattr(result, "isError", False))}

    combined = "\n".join(parts).strip()
    try:
        parsed = json.loads(combined)
    except json.JSONDecodeError:
        return {"message": combined}

    if isinstance(parsed, dict):
        return parsed
    return {"value": parsed}


class McpTransport:
    """Connect to Adapter MCP and call tools."""

    def __init__(
            self,
            *,
            session_id: str,
            mcp_url: str | None = None,
            platform: str = SDK_PLATFORM,
    ) -> None:
        self.session_id = session_id.strip()
        if not self.session_id:
            raise ValueError("session_id is required")

        self.mcp_url = (mcp_url or DEFAULT_MCP_URL).rstrip("/")
        self.platform = platform.strip().lower() or SDK_PLATFORM

        self._session: ClientSession | None = None
        self._transport_cm = None
        self._session_cm = None
        self._http_client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "McpTransport":
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

        try:
            self._transport_cm = streamable_http_client(
                self.mcp_url,
                http_client=self._http_client,
            )
            streams = await self._transport_cm.__aenter__()
            read_stream, write_stream = streams[0], streams[1]

            self._session_cm = ClientSession(read_stream, write_stream)
            self._session = await self._session_cm.__aenter__()
            await self._session.initialize()
        except Exception as error:
            await self.close()
            message = str(error)
            if "401" in message or "Unauthorized" in message:
                raise RuntimeError(
                    "Adapter returned 401 Unauthorized for MCP. "
                    "Set ADAPTER_AUTH_TOKEN in agent-adapter/.env (or export it) "
                    "to match the running Adapter."
                ) from error
            raise

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

    def _prepare_send_action(self, arguments: dict[str, Any]) -> dict[str, Any]:
        args = dict(arguments or {})
        parameters = args.get("parameters") or {}
        if isinstance(parameters, str):
            try:
                parameters = json.loads(parameters)
            except json.JSONDecodeError:
                parameters = {}
        if not isinstance(parameters, dict):
            parameters = {}
        args["parameters"] = {
            str(key): "" if value is None else str(value)
            for key, value in parameters.items()
        }
        args["platform"] = self.platform
        args["sessionId"] = self.session_id

        default_agent = (
            os.getenv("BRIDGE_AGENT_ID")
            or os.getenv("BRIDGE_SDK_AGENT_ID")
            or "agent-123"
        ).strip()
        agent_id = str(args.get("agentId") or "").strip()
        if not agent_id:
            args["agentId"] = default_agent
        return args

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._session is None:
            raise RuntimeError("MCP transport is not connected")

        args = dict(arguments or {})
        if name == "send_action":
            args = self._prepare_send_action(args)

        result = await self._session.call_tool(name, arguments=args)
        return _tool_result_to_dict(result)
