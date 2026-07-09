from mcp.server.fastmcp import FastMCP
import json
import main
import models
import time
from workflow_service import WorkflowService
from pathlib import Path

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "vault_config.json"

mcp = FastMCP("bridge-adapter")

with open(CONFIG_PATH) as f:
    config = json.load(f)

# Note: This is currently the fallback static ID from the config.
# Down the line, you can pass a dynamic dynamic user/session ID from the agent platform if available.
USER_INSTALL_ID = config["userInstallId"]

#workflow_service = WorkflowService()


@mcp.tool(
    description="""Send an action request to the Bridge system to perform an operation such as payment or form filling
    Allowed action types:
    - PAYMENT → parameters: amount, currency
    - TRANSACTION → parameters: amount, currency, target
    - FILL_FORM → parameters: id, email, password, name"""
)
def send_action(
        agentId: str,
        actionType: str,
        parameters: dict[str, str],
        sessionId: str,
        platform: str
):
    """
    Send an action request to the Bridge system.

    Allowed action types:
    PAYMENT
    TRANSACTION
    FILL_FORM
    """

    try:
        # Create action request payload
        action_request = models.ActionRequestModel(
            agentId=agentId,
            userInstallId=USER_INSTALL_ID,
            actionType=actionType,
            parameters=parameters,
            platform=platform,
            sessionId=sessionId
        )

        # Send action to bridge via the gRPC/HTTP main client wrapper
        response = main.send_action(action_request)

        # Check if the Bridge returned a status indicating the Vault app is not paired/installed
        if response and response.get("status") == "FAILED_APP_NOT_INSTALLED":
            description = response.get("description", "")

            # Parse the pipe-delimited pairing details: "PAIRING_REQUIRED|QR_URL|TOKEN"
            if description.startswith("PAIRING_REQUIRED"):
                parts = description.split("|")
                qr_code_url = parts[1]
                pairing_token = parts[2]

                # Return a structured instructional message directly to the AI agent
                return (
                    f"### ⚠️ SECURE VAULT PAIRING REQUIRED\n"
                    f"No secure vault application is linked to this account.\n\n"
                    f"Please scan this QR Code directly with your camera:\n\n"
                    f"![QR Code]({qr_code_url})\n\n"  
                    f"**Pairing Token:** `{pairing_token}`\n\n"
                    f"Once paired, please let me know."
                )

        return response

    except Exception as e:
        return {"error": str(e)}


# get status of action
@mcp.tool(
    description="Get the status of a previously sent action request to the Bridge system"
)
def get_action_status(request_id: str):

    try:
        response = None
        current_status = None

        # poll bridge status
        for _ in range(20):

            response = main.get_status(request_id)

            current_status = response["status"]

            if current_status not in [
                "RECEIVED",
                "IN_PROGRESS"
            ]:
                return {
                    "requestId": response["requestId"],
                    "status": current_status,
                    "resultData": response["resultData"]
                }

            time.sleep(1)

        if response is None:
            return {
                "error": "No response received from bridge"
            }

        return {
            "requestId": response["requestId"],
            "status": current_status,
            "message": "Workflow still running"
        }

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")