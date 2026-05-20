from mcp.server.fastmcp import FastMCP
import json
import main
import models
from models import ActionRequestModel
import time
from workflow_service import WorkflowService

mcp=FastMCP("bridge-adapter")
with open("vault_config.json") as f:
    config = json.load(f)

USER_INSTALL_ID = config["userInstallId"]

workflow_service = WorkflowService()



@mcp.tool(
    description="""Send an action request to the Bridge system to perform an operation such as payment or form filling
    Allowed action types:
    - PAYMENT → parameters: amount, currency
    - TRANSACTION → parameters: amount, currency, target
    - FILL_FORM → parameters: id, email, password, name"""
)
def send_action(agentId: str,actionType:str ,parameters:dict[str, str],sessionId: str,platform: str):
    """
    Send an action request to the Bridge system.
    Allowed action types:
    PAYMENT
    TRANSACTION
    FILL_FORM
    """
    try:
        #create action request
        actionRequest = models.ActionRequestModel(
            agentId=agentId,
            userInstallId=USER_INSTALL_ID,
            actionType=actionType,
            parameters=parameters
        )
        #create workflow with the request
        return workflow_service.create_workflow(actionRequest,platform,sessionId)

    except Exception as e:
        return {"error": str(e)}

@mcp.tool(
    description="Get the status of a previously sent action request to the Bridge system"
)

def get_action_status(requestId: str):

    try:


    except Exception as e:
        return {"error": str(e)}




CONTINUATION_HANDLERS = {
    "claude": handle_claude,
    "openai": handle_openai
}


if __name__ == "__main__":
    mcp.run(transport="stdio")