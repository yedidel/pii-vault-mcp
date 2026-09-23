import os

import requests
from continuation.claude_url_allowlist import (
    is_adapter_continuation_url,
    is_allowed_claude_wake_url,
)
from continuation.wake_provider import WakeProvider
from logutil import get_logger
from workflow.models import ContinuationNotification, WorkflowModel


logger = get_logger(__name__)


def _redact_token(text: str) -> str:
    token = os.getenv("ADAPTER_AUTH_TOKEN", "").strip()
    if not token:
        return text
    return text.replace(token, "[redacted]")


def _adapter_continuation_headers(wake_url: str) -> dict[str, str]:
    """Bearer header only for this Adapter's protected continuation URL.

    Local bridge-wake /wake posts stay unauthenticated.
    """
    if not is_adapter_continuation_url(wake_url):
        return {}
    token = os.getenv("ADAPTER_AUTH_TOKEN", "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


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
    headers = _adapter_continuation_headers(ingress)
    try:
        if headers:
            response = requests.post(
                ingress,
                json=payload,
                headers=headers,
                timeout=5,
            )
        else:
            response = requests.post(ingress, json=payload, timeout=5)
    except requests.RequestException as error:
        redacted = _redact_token(str(error))
        if redacted != str(error):
            raise requests.RequestException(redacted) from None
        raise
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
            detail = _redact_token(str(error))
            message = (
                "Failed to wake Claude agent "
                f"requestId={notification.requestId}: {detail}"
            )
            if detail != str(error):
                raise RuntimeError(message) from None
            raise RuntimeError(message) from error

        logger.info(
            "Woke Claude agent requestId=%s channel=%s",
            notification.requestId,
            ingress,
        )
