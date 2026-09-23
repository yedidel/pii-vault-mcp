import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from continuation.wake_provider import WakeProvider
from logutil import get_logger
from workflow.models import ContinuationNotification, WorkflowModel


logger = get_logger(__name__)

_ADAPTER_ENV = Path(__file__).resolve().parents[3] / ".env"

WAKE_SYSTEM_INSTRUCTION = """
You are a Bridge-enabled Gemini agent.

The following message is an authoritative asynchronous workflow update from
the Bridge Adapter after a user-approved vault action. Treat it as the
result of the send_action you already requested. Acknowledge the outcome
and continue the user's task. Do not ask the user to re-approve an action
that already completed.
""".strip()


def _load_adapter_env() -> None:
    load_dotenv(_ADAPTER_ENV)


def _gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip() or "gemini-3.6-flash"


def describe_gemini_error(error: BaseException) -> str:
    """Safe Gemini/API error summary. Never includes API keys."""
    parts = [type(error).__name__]
    code = getattr(error, "code", None)
    if code is not None:
        parts.append(f"http={code}")
    status = getattr(error, "status", None)
    if status:
        parts.append(f"status={status}")

    message = getattr(error, "message", None) or str(error)
    details = getattr(error, "details", None)
    request_id = None
    if isinstance(details, dict):
        inner = details.get("error") if isinstance(details.get("error"), dict) else details
        if isinstance(inner, dict):
            request_id = (
                inner.get("requestId")
                or inner.get("request_id")
                or details.get("requestId")
            )
            inner_status = inner.get("status") or inner.get("code")
            if inner_status and not status:
                parts.append(f"gemini={inner_status}")
            inner_message = inner.get("message")
            if inner_message:
                message = inner_message

    response = getattr(error, "response", None)
    if response is not None:
        http_status = getattr(response, "status_code", None)
        if http_status is not None and code is None:
            parts.append(f"http={http_status}")
        body = getattr(response, "text", None)
        if isinstance(body, str) and body.strip() and "message=" not in " ".join(parts):
            parts.append(f"body={body.strip()[:400]}")

    redacted = str(message).replace(os.getenv("GEMINI_API_KEY") or "", "")
    redacted = redacted.replace(os.getenv("GOOGLE_API_KEY") or "", "")
    parts.append(f"message={redacted[:500]}")
    if request_id:
        parts.append(f"geminiRequestId={request_id}")
    return " ".join(parts)


def build_gemini_wake_message(
        workflow: WorkflowModel,
        notification: ContinuationNotification,
) -> str:
    return (
        "Bridge workflow update.\n"
        f"requestId: {notification.requestId}\n"
        f"workflowId: {notification.workflowId}\n"
        f"actionType: {workflow.actionType}\n"
        f"status: {notification.status}\n"
        f"message: {notification.message}\n"
        "The vault action you requested has finished. Continue from this result."
    )


def wake_gemini_with_message(
        *,
        previous_interaction_id: str,
        message: str,
) -> str:
    _load_adapter_env()
    previous_interaction_id = previous_interaction_id.strip()
    if not previous_interaction_id:
        raise ValueError("previous_interaction_id is required")

    api_key = (
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    ).strip()
    if not api_key:
        raise ValueError(
            "Missing GEMINI_API_KEY or GOOGLE_API_KEY in environment"
        )

    model = _gemini_model()
    client = genai.Client(api_key=api_key)
    try:
        interaction = client.interactions.create(
            model=model,
            previous_interaction_id=previous_interaction_id,
            system_instruction=WAKE_SYSTEM_INSTRUCTION,
            input=message,
        )
    except Exception as error:
        logger.error(
            "Gemini interactions.create failed previous=%s model=%s %s",
            previous_interaction_id,
            model,
            describe_gemini_error(error),
        )
        raise

    interaction_id = str(getattr(interaction, "id", "") or "").strip()
    if not interaction_id:
        raise RuntimeError("Gemini wake returned no interaction id")

    output = (getattr(interaction, "output_text", None) or "").strip()
    logger.info(
        "Gemini wake created interaction previous=%s new=%s outputChars=%s",
        previous_interaction_id,
        interaction_id,
        len(output),
    )
    return interaction_id


class GeminiProvider(WakeProvider):

    def wake(
            self,
            workflow: WorkflowModel,
            notification: ContinuationNotification,
    ) -> None:

        previous_interaction_id = (workflow.continuationContext or "").strip()

        if not previous_interaction_id:
            raise ValueError(
                "Missing continuationContext (Gemini interaction.id). "
                "Pass the current interaction.id as sessionId when calling send_action."
            )

        message = build_gemini_wake_message(workflow, notification)

        try:
            interaction_id = wake_gemini_with_message(
                previous_interaction_id=previous_interaction_id,
                message=message,
            )
        except Exception as error:
            logger.error(
                "Gemini wake failed requestId=%s previous=%s %s",
                notification.requestId,
                previous_interaction_id,
                describe_gemini_error(error),
            )
            raise

        workflow.continuationContext = interaction_id

        from workflow.workflow_context import workflow_service

        workflow_service.update_continuation_context(
            notification.requestId,
            interaction_id,
        )

        logger.info(
            "Woke Gemini agent requestId=%s previous=%s new=%s",
            notification.requestId,
            previous_interaction_id,
            interaction_id,
        )
