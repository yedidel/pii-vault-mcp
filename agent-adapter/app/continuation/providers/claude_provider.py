import requests
from continuation.claude_url_allowlist import is_allowed_claude_wake_url
from continuation.wake_provider import WakeProvider
from logutil import get_logger
from workflow.models import ContinuationNotification, WorkflowModel


logger = get_logger(__name__)


class ClaudeProvider(WakeProvider):

    def wake(
            self,
            workflow: WorkflowModel,
            notification: ContinuationNotification,
    ) -> None:
        """
        Wake a Claude Code session through its continuation URL.

        For Claude, continuationContext is the Adapter-stable continuation
        endpoint for this session, for example:

            http://127.0.0.1:8000/continuation/<session-id>

        The Adapter resolves session-id -> Channel ingress and forwards the
        wake payload unchanged. Direct Channel ingress URLs still work for
        single-session / legacy setups.
        """

        ingress = workflow.continuationContext

        if not ingress:
            raise ValueError(
                "Missing continuationContext "
                "(Claude continuation URL)."
            )
        if not is_allowed_claude_wake_url(ingress):
            raise ValueError(
                f"Claude wake URL is not allowed: {ingress!r}"
            )

        payload = {
            "requestId": notification.requestId,
            "workflowId": notification.workflowId,
            "status": notification.status,
            "message": notification.message,
        }

        try:
            response = requests.post(
                ingress,
                json=payload,
                timeout=5,
            )

            response.raise_for_status()

        except requests.RequestException as error:
            raise RuntimeError(
                f"Failed to wake Claude agent "
                f"requestId={notification.requestId}: {error}"
            ) from error

        logger.info(
            "Woke Claude agent requestId=%s channel=%s",
            notification.requestId,
            ingress,
        )
