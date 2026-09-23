from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import json
from pathlib import Path

from mcp_server import pii_vault_store
from transport.client_events_http import handle_client_events
from transport.sessions_http import handle_session_register
from transport.vault_resolve_http import handle_vault_resolve_request
from transport.webhook_http import handle_bridge_webhook_request
from workflow.workflow_context import (
    bridge_session_registry,
    client_notifier,
    pairing_service,
)

# FastAPI app used in MCP_TRANSPORT=stdio
# Continuation Transport (Bridge webhook) + client SSE + localhost vault resolve.
app = FastAPI()

with open(Path(__file__).resolve().parent / "vault_config.json", encoding="utf-8") as config_file:
    _config = json.load(config_file)


@app.get("/")
async def root():
    return {"message": "Adapter webhook server running"}


@app.post("/webhook/bridge")
async def bridge_webhook(request: Request):
    body, status_code = await handle_bridge_webhook_request(request)
    return JSONResponse(content=body, status_code=status_code)


@app.post("/vault/resolve")
async def vault_resolve(request: Request):
    response = await handle_vault_resolve_request(request, pii_vault_store)
    return response


@app.get("/events")
async def client_events(request: Request):
    return await handle_client_events(
        request,
        client_notifier,
        bridge_session_registry,
    )


@app.post("/sessions/register")
async def register_bridge_session(request: Request):
    return await handle_session_register(
        request,
        bridge_session_registry,
        pairing_service.resolve_for_session(),
    )
