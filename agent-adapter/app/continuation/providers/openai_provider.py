import os

from openai import OpenAI

from continuation.wake_provider import WakeProvider
from logutil import get_logger
from workflow.models import ContinuationNotification, WorkflowModel


logger = get_logger(__name__)

# Model is wake-layer config only; Bridge stays unaware.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6")


def wake_openai_with_message(
        *,
        conversation_id: str,
        message: str,
) -> str:
    conversation_id = conversation_id.strip()
    if not conversation_id:
        raise ValueError("conversation_id is required")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY in environment")

    client = OpenAI(api_key=api_key)
    client.responses.create(
        model=OPENAI_MODEL,
        conversation=conversation_id,
        input=message,
        parallel_tool_calls=False,
    )
    return conversation_id


class OpenAIProvider(WakeProvider):

    def wake(
            self,
            workflow: WorkflowModel,
            notification: ContinuationNotification,
    ) -> None:
        """
        Append a Bridge workflow update into an existing OpenAI conversation.

        continuationContext is an opaque client-supplied Conversations API
        conversation.id (conv_...). The Adapter never creates it. The id is
        stable across wakes and is not rewritten.
        """
        conversation_id = (workflow.continuationContext or "").strip()

        if not conversation_id:
            raise ValueError(
                "Missing continuationContext (OpenAI conversation.id). "
                "Pass conversation.id as sessionId when calling send_action."
            )

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Missing OPENAI_API_KEY in environment")

        message = (
            f"Bridge workflow update.\n"
            f"requestId: {notification.requestId}\n"
            f"workflowId: {notification.workflowId}\n"
            f"status: {notification.status}\n"
            f"message: {notification.message}"
        )

        try:
            wake_openai_with_message(
                conversation_id=conversation_id,
                message=message,
            )
        except Exception as error:
            logger.error(
                "OpenAI wake failed requestId=%s: %s",
                notification.requestId,
                error,
            )
            raise

        logger.info(
            "Woke OpenAI agent requestId=%s conversation=%s",
            notification.requestId,
            conversation_id,
        )
