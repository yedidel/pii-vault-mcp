import time
from continuations import resume_agent
import main
from models import ActionRequestModel, WorkflowModel
import uuid


# manage async workflow orchestration
class WorkflowService:
    #create work flow with parameters from send_action in tools
    def create_workflow(self,action_request:ActionRequestModel,platform:str,session_id:str):
        response=main.send_action(action_request)
        return WorkflowModel(
            workflowId=str(uuid.uuid4()),
            requestId=response["requestId"],
            currentStatus=response["status"],
            platform=platform,
            agentSessionId=session_id,
            actionType=action_request.actionType,
            #create id
            description=response["description"]
        )




