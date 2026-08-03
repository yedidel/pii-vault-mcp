from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from workflow import models
from transport.client_events_http import handle_client_events
from transport.webhook_http import process_bridge_webhook
from workflow.workflow_context import client_notifier

# FastAPI app used in MCP_TRANSPORT=stdio
# Exposes Continuation Transport (Bridge webhook) + client SSE events.
app = FastAPI()


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
    return await handle_client_events(request, client_notifier)
