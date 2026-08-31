from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
import asyncio
import os
from transport.auth_middleware import AdapterAuthMiddleware
import uvicorn

from logutil import configure_logging, get_logger
from mcp_server import mcp
from server import app
from workflow.workflow_context import polling_worker


# MCP Transport: how the LLM connects to this Adapter
# Continuation Transport (Bridge webhook) is always HTTP.
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio").lower()
ADAPTER_HOST = os.getenv("ADAPTER_HOST", "0.0.0.0")
ADAPTER_PORT = int(os.getenv("ADAPTER_PORT", "8000"))

logger = get_logger(__name__)


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
    asgi_app = AdapterAuthMiddleware(mcp.streamable_http_app())
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
    configure_logging()
    polling_task = asyncio.create_task(
        polling_worker.run(),
        name="adapter-polling-worker",
    )

    try:
        if MCP_TRANSPORT == "stdio":
            # LLM <-> Adapter: STDIO
            # Bridge <-> Adapter: HTTP POST /webhook/bridge
            logger.info(
                "Starting Adapter: MCP_TRANSPORT=stdio, "
                "webhook on http://%s:%s/webhook/bridge, "
                "events on http://%s:%s/events, "
                "polling worker enabled",
                ADAPTER_HOST,
                ADAPTER_PORT,
                ADAPTER_HOST,
                ADAPTER_PORT,
            )
            await asyncio.gather(
                run_mcp_stdio(),
                run_webhook_server(),
                polling_task,
            )
            return

        if MCP_TRANSPORT == "http":
            # LLM <-> Adapter: Streamable HTTP /mcp
            # Bridge <-> Adapter: HTTP POST /webhook/bridge (same server)
            logger.info(
                "Starting Adapter: MCP_TRANSPORT=http, "
                "MCP on http://%s:%s/mcp, "
                "webhook on http://%s:%s/webhook/bridge, "
                "events on http://%s:%s/events, "
                "polling worker enabled",
                ADAPTER_HOST,
                ADAPTER_PORT,
                ADAPTER_HOST,
                ADAPTER_PORT,
                ADAPTER_HOST,
                ADAPTER_PORT,
            )
            await asyncio.gather(
                run_mcp_http_server(),
                polling_task,
            )
            return

        raise ValueError(
            f"Unsupported MCP_TRANSPORT={MCP_TRANSPORT!r}. "
            "Use 'stdio' or 'http'."
        )
    finally:
        polling_worker.stop()
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass


def main():
    asyncio.run(run_adapter())


if __name__ == "__main__":
    main()
