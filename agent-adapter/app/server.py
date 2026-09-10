from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import json
from pathlib import Path

from workflow import models
from transport.client_events_http import handle_client_events
from transport.sessions_http import handle_session_register
from transport.webhook_http import process_bridge_webhook
from workflow.workflow_context import (
    bridge_session_registry,
    client_notifier,
    pairing_service,
)

# FastAPI app used in MCP_TRANSPORT=stdio
# Exposes Continuation Transport (Bridge webhook) + client SSE events.
app = FastAPI()

with open(Path(__file__).resolve().parent / "vault_config.json", encoding="utf-8") as config_file:
    _config = json.load(config_file)


@app.get("/")
async def root():
    return {"message": "Adapter webhook server running"}


@app.post("/webhook/bridge")
async def bridge_webhook(
        notification: models.ContinuationNotification,
):
    body, status_code = process_bridge_webhook(notification)
    return JSONResponse(content=body, status_code=status_code)


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
