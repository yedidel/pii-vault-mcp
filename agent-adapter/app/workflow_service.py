from continuations import resume_agent
import main


# manage async workflow orchestration
class WorkflowService:

    # create a new async workflow
    def create_workflow(
            self,
            action_request,
            platform: str,
            session_reference: str
    ):

        # send the request to the bridge backend
        response = main.send_action(action_request)

        return {
            "taskId": response["requestId"],
            "requestId": response["requestId"],
            "status": response["status"],
            "platform": platform,
            "sessionReference": session_reference
        }

    # check workflow status from the backend
    def check_workflow_status(
            self,
            request_id: str,
            platform: str
    ):

        status_response = main.get_status(request_id)

        current_status = status_response["status"]

        # continue the agent workflow when the task finishes
        if current_status not in [
            "RECEIVED",
            "IN_PROGRESS"
        ]:

            task = {
                "taskId": request_id,
                "platform": platform
            }

            event = {
                "event": "TASK_COMPLETED",
                "status": current_status
            }

            resume_agent(task, event)

        return status_response