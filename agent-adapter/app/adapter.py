import asyncio
import os

import uvicorn

from mcp_server import mcp
from server import app


# MCP Transport: how the LLM connects to this Adapter
# Continuation Transport (Bridge webhook) is always HTTP.
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio").lower()
ADAPTER_HOST = os.getenv("ADAPTER_HOST", "0.0.0.0")
ADAPTER_PORT = int(os.getenv("ADAPTER_PORT", "8000"))


async def run_webhook_server():
    # Continuation Transport only (used with MCP over STDIO)
    config = uvicorn.Config(
        app=app,
        host=ADAPTER_HOST,
        port=ADAPTER_PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def run_mcp_http_server():
    # MCP over Streamable HTTP + /webhook/bridge on the same ASGI app
    asgi_app = mcp.streamable_http_app()
    config = uvicorn.Config(
        app=asgi_app,
        host=ADAPTER_HOST,
        port=ADAPTER_PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def run_mcp_stdio():
    await mcp.run_stdio_async()


async def run_adapter():
    # Log to stderr so STDIO MCP protocol on stdout stays clean.
    import sys

    if MCP_TRANSPORT == "stdio":
        # LLM <-> Adapter: STDIO
        # Bridge <-> Adapter: HTTP POST /webhook/bridge
        print(
            f"Starting Adapter: MCP_TRANSPORT=stdio, "
            f"webhook on http://{ADAPTER_HOST}:{ADAPTER_PORT}/webhook/bridge",
            file=sys.stderr,
        )
        await asyncio.gather(
            run_mcp_stdio(),
            run_webhook_server(),
        )
        return

    if MCP_TRANSPORT == "http":
        # LLM <-> Adapter: Streamable HTTP /mcp
        # Bridge <-> Adapter: HTTP POST /webhook/bridge (same server)
        print(
            f"Starting Adapter: MCP_TRANSPORT=http, "
            f"MCP on http://{ADAPTER_HOST}:{ADAPTER_PORT}/mcp, "
            f"webhook on http://{ADAPTER_HOST}:{ADAPTER_PORT}/webhook/bridge",
            file=sys.stderr,
        )
        await run_mcp_http_server()
        return

    raise ValueError(
        f"Unsupported MCP_TRANSPORT={MCP_TRANSPORT!r}. "
        "Use 'stdio' or 'http'."
    )


def main():
    asyncio.run(run_adapter())


if __name__ == "__main__":
    main()
