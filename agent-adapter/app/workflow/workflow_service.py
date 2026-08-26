import main
import time
from logutil import get_logger
from workflow.models import ActionRequestModel, WorkflowModel
import os
import time

_DEFAULT_PENDING_TTL = 3600
_DEFAULT_MAX_PENDING = 500


def _pending_ttl_seconds() -> int:
    raw = os.getenv("ADAPTER_PENDING_WORKFLOW_TTL_SECONDS", "").strip()
    if not raw:
        return _DEFAULT_PENDING_TTL
    try:
        return max(60, int(raw))
    except ValueError:
        return _DEFAULT_PENDING_TTL


def _max_pending_workflows() -> int:
    raw = os.getenv("ADAPTER_MAX_PENDING_WORKFLOWS", "").strip()
    if not raw:
        return _DEFAULT_MAX_PENDING
    try:
        return max(1, int(raw))
    except ValueError:
        return _DEFAULT_MAX_PENDING

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
            createdAt=time.time(),
        )
        self._enforce_pending_limit()
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
    def _evict_expired(self) -> None:
        ttl = _pending_ttl_seconds()
        now = time.time()
        expired = [
            request_id
            for request_id, wf in self.pending_workflows.items()
            if wf.createdAt is not None and (now - wf.createdAt) > ttl
        ]
        for request_id in expired:
            self.pending_workflows.pop(request_id, None)
            logger.info("Evicted expired pending workflow: %s", request_id)


    def _enforce_pending_limit(self) -> None:
        self._evict_expired()
        if len(self.pending_workflows) >= _max_pending_workflows():
            raise PendingWorkflowLimitError(
                f"Too many pending workflows (max {_max_pending_workflows()})"
            )


class PendingWorkflowLimitError(Exception):
    pass


