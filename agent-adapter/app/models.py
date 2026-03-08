#define the structure of the request body for action request in json format.
# This will be used to map the incoming JSON request to a
# Python object that can be sent via gRPC to the Bridge server.
class ActionRequestModel():
    def __init__(self,agentId:str,userInstallId:str,actionType:str,actionParams:dict):
        self.agentId = agentId
        self.userInstallId = userInstallId
        self.actionType = actionType
        self.actionParams = actionParams