from continuation.ContinuationService import ContinuationService
from workflow.models import ContinuationNotification


class WebhookContinuation:
    # handles notifications that arrived via Bridge Webhook

    def __init__(self, continuation_service: ContinuationService):
        self.continuation_service = continuation_service

    def handle(
            self,
            notification: ContinuationNotification,
    ) -> bool:
        return self.continuation_service.handle(notification)
