from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel


class ClientNotifyEvent(BaseModel):
    """
    Platform-agnostic signal that a workflow has new data available.

    Never carries conversation / interaction message bodies.
    sessionId is the opaque routing key the client subscribed with
    (continuationContext at the start of wake).

    resumeSessionId is set when a provider rotates continuationContext
    during wake (e.g. Gemini interaction chaining). Clients that need the
    successor session fetch from their platform using this id, then may
    re-subscribe. OpenAI leaves this unset (conversation.id is stable).
    """

    type: Literal["workflow.updated"] = "workflow.updated"
    workflowId: str
    requestId: str
    platform: str
    sessionId: str
    status: str
    resumeSessionId: str | None = None


class ClientNotifier(ABC):

    @abstractmethod
    def notify(self, event: ClientNotifyEvent) -> None:
        """
        Deliver a notification to the client subscribed for
        (event.platform, event.sessionId). No-op if none is connected.
        """


class NoopClientNotifier(ClientNotifier):
    """Default notifier when no client transport is wired."""

    def notify(self, event: ClientNotifyEvent) -> None:
        return
