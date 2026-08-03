from fastapi import FastAPI
from fastapi.responses import JSONResponse

from workflow import models
from transport.webhook_http import process_bridge_webhook

# FastAPI app used in MCP_TRANSPORT=stdio
# Exposes only Continuation Transport (Bridge webhook), not MCP.
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
