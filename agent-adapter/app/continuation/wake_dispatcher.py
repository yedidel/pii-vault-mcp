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

        # Publish workflow.updated before the provider API call so POLLING
        # (and WEBHOOK) SSE is not blocked by Gemini/OpenAI retries.
        if route_session_id:
            self._notify_client(
                workflow=workflow,
                notification=notification,
                session_id=route_session_id,
                resume_session_id=None,
            )

        wake_error: Exception | None = None
        try:
            provider.wake(
                workflow,
                notification,
            )
        except Exception as error:
            wake_error = error
            logger.exception(
                "Provider wake failed platform=%s requestId=%s",
                platform,
                notification.requestId,
            )

        resume_session_id = (workflow.continuationContext or "").strip()
        if (
                route_session_id
                and resume_session_id
                and resume_session_id != route_session_id
        ):
            self._notify_client(
                workflow=workflow,
                notification=notification,
                session_id=route_session_id,
                resume_session_id=resume_session_id,
            )

        if wake_error is not None:
            raise wake_error

    def _notify_client(
            self,
            *,
            workflow: WorkflowModel,
            notification: ContinuationNotification,
            session_id: str,
            resume_session_id: str | None,
    ) -> None:
        self.client_notifier.notify(
            ClientNotifyEvent(
                workflowId=workflow.workflowId,
                requestId=workflow.requestId or notification.requestId,
                platform=workflow.platform,
                sessionId=session_id,
                status=notification.status,
                resumeSessionId=resume_session_id,
            )
        )
        logger.debug(
            "Notified client platform=%s sessionId=%s resumeSessionId=%s",
            workflow.platform,
            session_id,
            resume_session_id,
        )
