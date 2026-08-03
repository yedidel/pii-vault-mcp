from abc import ABC, abstractmethod

from workflow.models import ContinuationNotification, WorkflowModel


class WakeProvider(ABC):

    @abstractmethod
    def wake(
            self,
            workflow: WorkflowModel,
            notification: ContinuationNotification,
    ) -> None:
        """
        Wake the agent for the given workflow update.
        """
        pass