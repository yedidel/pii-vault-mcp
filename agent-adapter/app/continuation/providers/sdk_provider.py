from continuation.wake_provider import WakeProvider
from logutil import get_logger
from workflow.models import ContinuationNotification, WorkflowModel


logger = get_logger(__name__)


class SdkProvider(WakeProvider):
    """
    No-op wake for bridge-sdk clients.

    SDK apps poll get_action_status or listen on SSE; they do not run
    an LLM that needs a platform-specific continuation inject.
    """

    def wake(
            self,
            workflow: WorkflowModel,
            notification: ContinuationNotification,
    ) -> None:
        logger.info(
            "SDK wake noop requestId=%s status=%s sessionId=%s",
            notification.requestId,
            notification.status,
            workflow.continuationContext,
        )
