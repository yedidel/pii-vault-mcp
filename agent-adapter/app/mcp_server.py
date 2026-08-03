import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

import main
from workflow import models
from continuation.continuation_provider import DefaultContinuationProvider
from transport.webhook_http import process_bridge_webhook
from workflow.workflow_context import claude_session_registry, workflow_service


BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "vault_config.json"

ADAPTER_HOST = os.getenv("ADAPTER_HOST", "0.0.0.0")
ADAPTER_PORT = int(os.getenv("ADAPTER_PORT", "8000"))
# Public base used when issuing continuation URLs to Claude sessions.
ADAPTER_PUBLIC_BASE = os.getenv(
    "ADAPTER_PUBLIC_BASE",
    f"http://127.0.0.1:{ADAPTER_PORT}",
).rstrip("/")

# One FastMCP instance = one set of tools for both STDIO and HTTP MCP
mcp = FastMCP(
    "bridge-adapter",
    host=ADAPTER_HOST,
    port=ADAPTER_PORT,
    streamable_http_path="/mcp",
)

with open(CONFIG_PATH, encoding="utf-8") as config_file:
    config = json.load(config_file)

USER_INSTALL_ID = config["userInstallId"]
continuation_provider = DefaultContinuationProvider()


def _is_local_ingress(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme != "http":
        return False
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        return False
    if not parsed.path.endswith("/wake"):
        return False
    return True


@mcp.custom_route("/webhook/bridge", methods=["POST"])
async def bridge_webhook_route(request: Request) -> Response:
    # Continuation Transport endpoint on the MCP HTTP server
    payload = await request.json()
    notification = models.ContinuationNotification(**payload)
    body, status_code = process_bridge_webhook(notification)
    return JSONResponse(body, status_code=status_code)


@mcp.custom_route("/continuation/register", methods=["POST"])
async def register_claude_session(request: Request) -> Response:
    payload = await request.json()
    ingress_url = str(payload.get("ingressUrl") or "").strip()

    if not _is_local_ingress(ingress_url):
        return JSONResponse(
            {
                "error": (
                    "ingressUrl must be a local Claude Channel wake URL, "
                    "e.g. http://127.0.0.1:<port>/wake"
                ),
            },
            status_code=400,
        )

    session = claude_session_registry.register(ingress_url)
    continuation_url = (
        f"{ADAPTER_PUBLIC_BASE}/continuation/{session.session_id}"
    )

    print(
        "Registered Claude session "
        f"sessionId={session.session_id} ingress={session.ingress_url}"
    )

    return JSONResponse(
        {
            "sessionId": session.session_id,
            "continuationUrl": continuation_url,
            "ingressUrl": session.ingress_url,
        }
    )


@mcp.custom_route("/continuation/{session_id}", methods=["DELETE"])
async def unregister_claude_session(request: Request) -> Response:
    session_id = request.path_params["session_id"]
    removed = claude_session_registry.unregister(session_id)
    if not removed:
        return JSONResponse(
            {"error": f"Unknown sessionId={session_id}"},
            status_code=404,
        )

    print(f"Unregistered Claude session sessionId={session_id}")
    return JSONResponse({"status": "ok", "sessionId": session_id})


@mcp.custom_route("/continuation/{session_id}", methods=["POST"])
async def forward_claude_continuation(request: Request) -> Response:
    session_id = request.path_params["session_id"]
    session = claude_session_registry.get(session_id)
    if session is None:
        return JSONResponse(
            {"error": f"Unknown sessionId={session_id}"},
            status_code=404,
        )

    payload = await request.json()

    try:
        upstream = requests.post(
            session.ingress_url,
            json=payload,
            timeout=5,
        )
    except requests.RequestException as error:
        # Channel process likely exited; drop the stale mapping.
        claude_session_registry.unregister(session_id)
        return JSONResponse(
            {
                "error": (
                    f"Claude Channel unreachable for sessionId={session_id}: "
                    f"{error}"
                ),
            },
            status_code=502,
        )

    if upstream.status_code >= 400:
        return JSONResponse(
            {
                "error": "Claude Channel rejected wake payload",
                "upstreamStatus": upstream.status_code,
                "upstreamBody": upstream.text,
            },
            status_code=502,
        )

    claude_session_registry.touch(session_id)
    return JSONResponse(
        {
            "status": "ok",
            "sessionId": session_id,
            "requestId": payload.get("requestId"),
        }
    )


@mcp.custom_route("/", methods=["GET"])
async def health_route(_request: Request) -> Response:
    return JSONResponse({"message": "Adapter MCP HTTP server running"})


@mcp.tool(
    description="""
    Send an action request to the Bridge system.
    
    Required parameters:
    
    platform:
    - "gemini"
    - "claude"
    
    sessionId:
    - Gemini: the current Interactions API interaction.id.
    - Claude: the Adapter continuation URL for this session,
      returned by the bridge-wake channel tool get_continuation_context,
      for example: http://127.0.0.1:8000/continuation/<session-id>
    
    Allowed action types:
    - PAYMENT
    - TRANSACTION
    - FILL_FORM
"""
)
def send_action(
        agentId: str,
        actionType: str,
        parameters: dict[str, str],
        sessionId: str,
        platform: str,
):
    # TEMP POC logging — verify BeforeTool rewrite reaches the Adapter.
    print(
        f"[send_action POC] received sessionId={sessionId!r} "
        f"platform={platform!r} agentId={agentId!r} actionType={actionType!r}"
    )

    try:
        continuation_target = continuation_provider.resolve()

        action_request = models.ActionRequestModel(
            agentId=agentId,
            userInstallId=USER_INSTALL_ID,
            actionType=actionType,
            parameters=parameters,
            connectorType=continuation_target.connector_type,
            connectorContext=continuation_target.connector_context,
            platform=platform,
            sessionId=sessionId,
        )

        # sessionId is Adapter-local wake context (Gemini interaction.id or
        # Claude continuation URL). connectorContext is what Bridge POSTs to.
        workflow = workflow_service.create_workflow(
            action_request=action_request,
            platform=platform,
            continuation_context=sessionId,
        )

        return {
            "workflowId": workflow.workflowId,
            "requestId": workflow.requestId,
            "status": workflow.currentStatus,
            "description": workflow.description,
            # TEMP POC echo — makes the received sessionId visible in tool result.
            "pocReceivedSessionId": sessionId,
        }

    except Exception as error:
        return {
            "error": str(error),
        }


@mcp.tool(
    description=(
            "Get the status of a previously sent action request "
            "from the Bridge system"
    )
)
def get_action_status(request_id: str):
    try:
        response = None
        current_status = None

        # temporary polling support
        for _ in range(20):
            response = main.get_status(request_id)
            current_status = response["status"]

            if current_status not in {
                "RECEIVED",
                "IN_PROGRESS",
            }:
                return {
                    "requestId": response["requestId"],
                    "status": current_status,
                    "resultData": response["resultData"],
                }

            time.sleep(1)

        if response is None:
            return {
                "error": "No response received from Bridge",
            }

        return {
            "requestId": response["requestId"],
            "status": current_status,
            "message": "Workflow is still running",
        }

    except Exception as error:
        return {
            "error": str(error),
        }


if __name__ == "__main__":
    raise SystemExit(
        "Start the Adapter with: python adapter.py\n"
        "Set MCP_TRANSPORT=stdio|http"
    )
