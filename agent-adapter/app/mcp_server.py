from mcp.server.fastmcp import FastMCP
import main
from models import ActionRequestModel

mcp=FastMCP("bridge-adapter")


@mcp.tool(
    description="""Send an action request to the Bridge system to perform an operation such as payment or form filling
    Allowed action types:
    - PAYMENT → parameters: amount, currency
    - TRANSACTION → parameters: amount, currency, target
    - FILL_FORM → parameters: id, email, password, name"""
)
def send_action(agentId: str, userInstallId: str,actionType:str ,parameters:dict[str, str]):
    """
    Send an action request to the Bridge system.
    Allowed action types:
    PAYMENT
    TRANSACTION
    FILL_FORM
    """
    response= main.send_action(ActionRequestModel(
        agentId=agentId,
        userInstallId=userInstallId,
        actionType=actionType,
        parameters=parameters
    ))
    return {
        "requestId": response["requestId"],
        "status": response["status"],
        "description": response["description"]
    }

@mcp.tool(
    description="Get the status of a previously sent action request to the Bridge system"
)
def get_action_status(requestId: str):
    response= main.get_status(requestId)
    return {
        "requestId": response["requestId"],
        "status": response["status"],
        "resultData": response["resultData"]
    }
if __name__ == "__main__":
    mcp.run()