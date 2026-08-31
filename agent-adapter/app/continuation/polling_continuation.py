from continuation.ContinuationService import ContinuationService
from workflow.models import ContinuationNotification


class PollingContinuation:
    """Handles workflow completion discovered by polling Bridge status."""

    def __init__(self, continuation_service: ContinuationService):
        self.continuation_service = continuation_service

    def handle(
            self,
            notification: ContinuationNotification,
    ) -> bool:
        return self.continuation_service.handle(notification)
