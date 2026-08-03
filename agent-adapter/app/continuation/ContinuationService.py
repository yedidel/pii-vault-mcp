from continuation.wake_dispatcher import WakeDispatcher
from workflow.models import ContinuationNotification
from workflow.workflow_service import WorkflowService


class ContinuationService:
    # Shared continuation logic for all inbound strategies.

    def __init__(
            self,
            workflow_service: WorkflowService,
            wake_dispatcher: WakeDispatcher,
    ):
        self.workflow_service = workflow_service
        self.wake_dispatcher = wake_dispatcher

    def handle(
            self,
            notification: ContinuationNotification,
    ) -> bool:

        workflow = self.workflow_service.get_workflow(
            notification.requestId
        )

        if workflow is None:
            print(
                "No pending workflow found for request: "
                f"{notification.requestId}"
            )
            return False

        self.workflow_service.update_status(
            notification.requestId,
            notification.status,
        )

        self.wake_dispatcher.wake(
            workflow,
            notification,
        )

        if self._is_final_status(notification.status):
            self.workflow_service.remove_workflow(
                notification.requestId
            )

            print(
                "Removed completed workflow: "
                f"{notification.requestId}"
            )

        return True

    @staticmethod
    def _is_final_status(status: str) -> bool:
        return status.upper() in {
            "COMPLETED",
            "REJECTED",
            "FAILED",
            "FAILED_APP_NOT_INSTALLED",
            "UNTRUSTED",
        }