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
            requestId=response["requestId"],
            currentStatus=response["status"],
            platform=platform,
            agentSessionId=session_id,
            actionType=action_request.actionType,
            #create id
            workflowId= str(uuid.uuid4()),
            description=response["description"]
        )

    def check_workflow_status(self,workflowId:str):

        for _ in range(20):

            response = main.get_status(requestId)

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

        return {
            "requestId": response["requestId"],
            "status": current_status,
            "message": "Workflow still running"
        }


