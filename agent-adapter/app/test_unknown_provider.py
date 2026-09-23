import unittest
from unittest.mock import MagicMock

from continuation.ContinuationService import ContinuationService
from continuation.wake_dispatcher import WakeDispatcher
from workflow.models import ContinuationNotification, WorkflowModel


class UnknownProviderTest(unittest.TestCase):
    def test_unknown_platform_does_not_raise(self) -> None:
        workflow = WorkflowModel(
            workflowId="w1",
            requestId="r1",
            platform="unknown-platform",
            continuationContext="ctx",
            currentStatus="RECEIVED",
            actionType="PAYMENT",
            description="",
        )
        service = MagicMock()
        service.get_workflow.return_value = workflow
        dispatcher = WakeDispatcher(providers={})
        continuation = ContinuationService(service, dispatcher)
        handled = continuation.handle(
            ContinuationNotification(
                workflowId="w1",
                requestId="r1",
                status="COMPLETED",
                message="done",
            )
        )
        self.assertTrue(handled)
        service.remove_workflow.assert_called_once_with("r1")


if __name__ == "__main__":
    unittest.main()
