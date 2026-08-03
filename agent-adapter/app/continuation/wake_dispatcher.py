from continuation.client_notifier import ClientNotifier, ClientNotifyEvent, NoopClientNotifier
from continuation.wake_provider import WakeProvider
from logutil import get_logger
from workflow.models import ContinuationNotification, WorkflowModel


logger = get_logger(__name__)


class WakeDispatcher:

    def __init__(
            self,
            providers: dict[str, WakeProvider],
            client_notifier: ClientNotifier | None = None,
    ):
        self.providers = providers
        self.client_notifier = client_notifier or NoopClientNotifier()

    def wake(
            self,
            workflow: WorkflowModel,
            notification: ContinuationNotification,
    ) -> None:

        platform = workflow.platform.lower()

        provider = self.providers.get(platform)

        if provider is None:
            raise ValueError(
                f"No wake provider registered for platform '{platform}'"
            )

        # Route to the session the client already subscribed to (pre-wake).
        # Providers like Gemini may rotate continuationContext during wake.
        route_session_id = (workflow.continuationContext or "").strip()

        # Only notify after a successful platform wake.
        provider.wake(
            workflow,
            notification,
        )

        if not route_session_id:
            return

        resume_session_id = (workflow.continuationContext or "").strip()
        resume: str | None = None
        if resume_session_id and resume_session_id != route_session_id:
            resume = resume_session_id

        self.client_notifier.notify(
            ClientNotifyEvent(
                workflowId=workflow.workflowId,
                requestId=workflow.requestId or notification.requestId,
                platform=workflow.platform,
                sessionId=route_session_id,
                status=notification.status,
                resumeSessionId=resume,
            )
        )
        logger.debug(
            "Notified client platform=%s sessionId=%s resumeSessionId=%s",
            workflow.platform,
            route_session_id,
            resume,
        )
