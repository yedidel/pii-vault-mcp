#!/usr/bin/env python3
"""Minimal MCP server for BeforeTool rewrite POC. Not part of production Adapter."""

from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

HOST = os.getenv("POC_MCP_HOST", "127.0.0.1")
PORT = int(os.getenv("POC_MCP_PORT", "8010"))
LOG_PATH = Path(
    os.getenv(
        "POC_SEND_ACTION_LOG",
        str(Path.home() / ".gemini" / "send-action-poc.log"),
    )
)

mcp = FastMCP(
    "bridge-adapter",
    host=HOST,
    port=PORT,
    streamable_http_path="/mcp",
)


def _log(message: str) -> None:
    line = f"[send_action POC] {message}\n"
    print(line, end="", flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line)


@mcp.tool(description="POC send_action — logs received sessionId.")
def send_action(
        agentId: str,
        actionType: str,
        parameters: dict[str, str],
        sessionId: str,
        platform: str,
):
    _log(
        f"received sessionId={sessionId!r} platform={platform!r} "
        f"agentId={agentId!r} actionType={actionType!r} "
        f"parameters={json.dumps(parameters)}"
    )
    return {
        "status": "poc-ok",
        "pocReceivedSessionId": sessionId,
        "platform": platform,
        "agentId": agentId,
        "actionType": actionType,
    }


if __name__ == "__main__":
    import uvicorn

    print(f"POC MCP listening on http://{HOST}:{PORT}/mcp", flush=True)
    uvicorn.run(mcp.streamable_http_app(), host=HOST, port=PORT, log_level="info")
