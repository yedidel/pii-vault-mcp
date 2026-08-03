from continuation.wake_provider import WakeProvider
from workflow.models import ContinuationNotification, WorkflowModel


class WakeDispatcher:

    def __init__(
            self,
            providers: dict[str, WakeProvider],
    ):
        self.providers = providers

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

        provider.wake(
            workflow,
            notification,
        )