import requests
from continuation.claude_url_allowlist import is_allowed_claude_wake_url
from continuation.wake_provider import WakeProvider
from logutil import get_logger
from workflow.models import ContinuationNotification, WorkflowModel


logger = get_logger(__name__)


def wake_claude_with_message(
        *,
        wake_url: str,
        message: str,
        request_id: str,
        workflow_id: str,
        status: str,
) -> str:
    ingress = wake_url.strip()
    if not ingress:
        raise ValueError("wake_url is required")
    if not is_allowed_claude_wake_url(ingress):
        raise ValueError(f"Claude wake URL is not allowed: {ingress!r}")

    payload = {
        "requestId": request_id,
        "workflowId": workflow_id,
        "status": status,
        "message": message,
    }
    response = requests.post(ingress, json=payload, timeout=5)
    response.raise_for_status()
    return ingress


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

        try:
            wake_claude_with_message(
                wake_url=ingress,
                message=notification.message,
                request_id=notification.requestId,
                workflow_id=notification.workflowId,
                status=notification.status,
            )
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
