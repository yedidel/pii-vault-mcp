from pydantic import BaseModel
from typing import Dict
#define the structure of the request body for action request in json format.
# This will be used to map the incoming JSON request to a
# Python object that can be sent via gRPC to the Bridge server.

#struct of the request from agent to bridge
class ActionRequestModel(BaseModel):
    #id of agent came from tool call
    agentId: str
    #id of vault that the user install
    userInstallId: str
    #which workflow we want to make
    actionType: str
    #the information of the action
    parameters: Dict[str, str]

    #for work flow

    #platform of agent
    platform: str
    #session id of agent
    sessionId: str


class WorkflowModel(BaseModel):
    #internal id work flow
    workflowId:str
    #id from bridge
    requestId:str
    #like claude, gpt
    platform:str
    #session of chat
    agentSessionId:str

