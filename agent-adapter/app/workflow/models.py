from typing import Dict

from pydantic import BaseModel


# structure of the action request sent to the Bridge
class ActionRequestModel(BaseModel):

    agentId: str
    userInstallId: str

    actionType: str

    parameters: Dict[str,str]

    connectorType: str

    connectorContext: str

    # local only
    platform: str
    sessionId: str


# information kept by the adapter for a running workflow
class WorkflowModel(BaseModel):
    # authoritative Bridge workflow id (from ActionResponse.workflow_id)
    workflowId: str

    # request id returned by the Bridge
    requestId: str

    # agent platform
    platform: str

    # platform continuation context
    # Gemini: interaction.id
    # Claude: Adapter continuation URL (http://127.0.0.1:8000/continuation/<session-id>)
    # OpenAI: conversation.id (conv_...)
    continuationContext: str

    # current workflow status
    currentStatus: str

    # action type
    actionType: str

    # response description from the Bridge
    description: str


# notification received from the Bridge webhook
class ContinuationNotification(BaseModel):
    workflowId: str
    requestId: str
    status: str
    message: str