import os
import time
import unittest

from workflow.models import WorkflowModel
from workflow.workflow_service import WorkflowService


class PendingEvictTest(unittest.TestCase):
    def test_get_workflow_evicts_expired(self) -> None:
        os.environ["ADAPTER_PENDING_WORKFLOW_TTL_SECONDS"] = "60"
        service = WorkflowService()
        workflow = WorkflowModel(
            workflowId="w1",
            requestId="expired-1",
            platform="sdk",
            continuationContext="ctx",
            currentStatus="RECEIVED",
            actionType="PAYMENT",
            description="",
            createdAt=time.time() - 120,
        )
        service.pending_workflows[workflow.requestId] = workflow
        self.assertIsNone(service.get_workflow("expired-1"))


if __name__ == "__main__":
    unittest.main()
