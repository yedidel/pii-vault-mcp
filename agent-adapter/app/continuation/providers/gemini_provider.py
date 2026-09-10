import os

from google import genai

from continuation.wake_provider import WakeProvider
from logutil import get_logger
from workflow.models import ContinuationNotification, WorkflowModel


logger = get_logger(__name__)

# model is wake layer config only bridge stay unaware.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


def wake_gemini_with_message(
        *,
        previous_interaction_id: str,
        message: str,
) -> str:
    previous_interaction_id = previous_interaction_id.strip()
    if not previous_interaction_id:
        raise ValueError("previous_interaction_id is required")

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "Missing GEMINI_API_KEY or GOOGLE_API_KEY in environment"
        )

    client = genai.Client(api_key=api_key)
    interaction = client.interactions.create(
        model=GEMINI_MODEL,
        previous_interaction_id=previous_interaction_id,
        input=message,
    )
    interaction_id = str(getattr(interaction, "id", "") or "").strip()
    if not interaction_id:
        raise RuntimeError("Gemini wake returned no interaction id")
    return interaction_id


class GeminiProvider(WakeProvider):

    def wake(
            self,
            workflow: WorkflowModel,
            notification: ContinuationNotification,
    ) -> None:

        previous_interaction_id = workflow.continuationContext

        if not previous_interaction_id:
            raise ValueError(
                "Missing continuationContext (Gemini interaction.id). "
                "Pass the current interaction.id as sessionId when calling send_action."
            )

        message = (
            f"Bridge workflow update.\n"
            f"requestId: {notification.requestId}\n"
            f"workflowId: {notification.workflowId}\n"
            f"status: {notification.status}\n"
            f"message: {notification.message}"
        )

        try:
            interaction_id = wake_gemini_with_message(
                previous_interaction_id=previous_interaction_id,
                message=message,
            )
        except Exception as error:
            logger.error(
                "Gemini wake failed requestId=%s: %s",
                notification.requestId,
                error,
            )
            raise

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
