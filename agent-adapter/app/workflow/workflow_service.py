import main
from logutil import get_logger
from workflow.models import ActionRequestModel, WorkflowModel


logger = get_logger(__name__)


class WorkflowService:
    # stores workflows created by this adapter

    def __init__(self):
        # requestId -> WorkflowModel
        self.pending_workflows: dict[str, WorkflowModel] = {}

    def create_workflow(
            self,
            action_request: ActionRequestModel,
            platform: str,
            continuation_context: str,
    ) -> WorkflowModel:
        response = main.send_action(action_request)

        workflow_id = response.get("workflowId") or ""
        if not workflow_id:
            raise ValueError(
                "Bridge ActionResponse missing workflowId. "
                "Cannot create Adapter workflow without the authoritative Bridge id."
            )

        workflow = WorkflowModel(
            workflowId=workflow_id,
            requestId=response["requestId"],
            platform=platform,
            continuationContext=continuation_context,
            currentStatus=response["status"],
            actionType=action_request.actionType,
            description=response["description"],
        )

        self.pending_workflows[workflow.requestId] = workflow
        logger.info("Saved pending workflow: %s", workflow.requestId)

        return workflow

    def get_workflow(
            self,
            request_id: str,
    ) -> WorkflowModel | None:
        return self.pending_workflows.get(request_id)

    def update_status(
            self,
            request_id: str,
            status: str,
    ) -> WorkflowModel | None:
        workflow = self.get_workflow(request_id)

        if workflow is None:
            return None

        workflow.currentStatus = status
        return workflow

    def update_continuation_context(
            self,
            request_id: str,
            continuation_context: str,
    ) -> WorkflowModel | None:
        workflow = self.get_workflow(request_id)

        if workflow is None:
            return None

        workflow.continuationContext = continuation_context
        return workflow

    def remove_workflow(self, request_id: str) -> None:
        self.pending_workflows.pop(request_id, None)
