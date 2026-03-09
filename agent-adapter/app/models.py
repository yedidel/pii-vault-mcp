from pydantic import BaseModel
from typing import Dict
#define the structure of the request body for action request in json format.
# This will be used to map the incoming JSON request to a
# Python object that can be sent via gRPC to the Bridge server.
class ActionRequestModel(BaseModel):
    agentId: str
    userInstallId: str
    actionType: str
    parameters: Dict[str, str]