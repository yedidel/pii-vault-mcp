import os
import unittest
from unittest.mock import MagicMock, patch

from continuation.ContinuationService import ContinuationService
from continuation.client_notifier import ClientNotifyEvent
from continuation.providers.gemini_provider import (
    GeminiProvider,
    build_gemini_wake_message,
    describe_gemini_error,
)
from continuation.wake_dispatcher import WakeDispatcher
from continuation.wake_provider import WakeProvider
from workflow.models import ContinuationNotification, WorkflowModel


class _RecordingNotifier:
    def __init__(self) -> None:
        self.events: list[ClientNotifyEvent] = []

    def notify(self, event: ClientNotifyEvent) -> None:
        self.events.append(event)

    def notify_vault_paired(self, event) -> None:
        return


class _FakeAPIError(Exception):
    def __init__(self) -> None:
        super().__init__("Gemini wake failed")
        self.code = 400
        self.status = "INVALID_ARGUMENT"
        self.message = "previous_interaction_id is invalid"
        self.details = {
            "error": {
                "message": "previous_interaction_id is invalid",
                "status": "INVALID_ARGUMENT",
                "requestId": "gem-req-1",
            }
        }


def _workflow(*, continuation: str = "parent-interaction-id") -> WorkflowModel:
    return WorkflowModel(
        workflowId="wf-1",
        requestId="req-1",
        platform="gemini",
        continuationContext=continuation,
        currentStatus="RECEIVED",
        actionType="FILL_FORM",
        description="queued",
    )


def _notification() -> ContinuationNotification:
    return ContinuationNotification(
        workflowId="wf-1",
        requestId="req-1",
        status="COMPLETED",
        message="Action completed successfully",
    )


class DescribeGeminiErrorTest(unittest.TestCase):
    def test_includes_http_status_and_gemini_message(self) -> None:
        summary = describe_gemini_error(_FakeAPIError())
        self.assertIn("http=400", summary)
        self.assertIn("previous_interaction_id is invalid", summary)
        self.assertIn("gem-req-1", summary)
        self.assertNotIn("AIza", summary)


class GeminiWakePayloadTest(unittest.TestCase):
    def test_payload_includes_ids_status_and_action_type(self) -> None:
        message = build_gemini_wake_message(_workflow(), _notification())
        self.assertIn("requestId: req-1", message)
        self.assertIn("workflowId: wf-1", message)
        self.assertIn("actionType: FILL_FORM", message)
        self.assertIn("status: COMPLETED", message)
        self.assertIn("Action completed successfully", message)
        self.assertIn("vault action you requested has finished", message)


class GeminiProviderWakeTest(unittest.TestCase):
    def test_successful_wake_resumes_stored_interaction_id(self) -> None:
        captured: dict = {}

        class _Interactions:
            def create(self, **kwargs):
                captured.update(kwargs)
                result = MagicMock()
                result.id = "successor-interaction-id"
                result.output_text = "The registration form was submitted successfully."
                return result

        fake_client = MagicMock()
        fake_client.interactions = _Interactions()
        workflow = _workflow()
        service = MagicMock()
        service.update_continuation_context.return_value = workflow

        with patch(
            "continuation.providers.gemini_provider.genai.Client",
            return_value=fake_client,
        ), patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "gemini-3.6-flash"},
            clear=False,
        ), patch(
            "workflow.workflow_context.workflow_service",
            service,
        ):
            GeminiProvider().wake(workflow, _notification())

        self.assertEqual(
            captured["previous_interaction_id"],
            "parent-interaction-id",
        )
        self.assertIn("status: COMPLETED", captured["input"])
        self.assertIn("actionType: FILL_FORM", captured["input"])
        self.assertIn("requestId: req-1", captured["input"])
        self.assertEqual(workflow.continuationContext, "successor-interaction-id")
        service.update_continuation_context.assert_called_once_with(
            "req-1",
            "successor-interaction-id",
        )

    def test_api_failure_does_not_rotate_continuation_context(self) -> None:
        class _Interactions:
            def create(self, **kwargs):
                raise _FakeAPIError()

        fake_client = MagicMock()
        fake_client.interactions = _Interactions()
        workflow = _workflow()

        with patch(
            "continuation.providers.gemini_provider.genai.Client",
            return_value=fake_client,
        ), patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "test-key"},
            clear=False,
        ):
            with self.assertRaises(_FakeAPIError):
                GeminiProvider().wake(workflow, _notification())

        self.assertEqual(workflow.continuationContext, "parent-interaction-id")

    def test_missing_continuation_context_fails_before_api(self) -> None:
        with self.assertRaises(ValueError):
            GeminiProvider().wake(_workflow(continuation=""), _notification())


class _FailingProvider(WakeProvider):
    def wake(self, workflow, notification) -> None:
        raise _FakeAPIError()


class _SucceedingProvider(WakeProvider):
    def wake(self, workflow, notification) -> None:
        workflow.continuationContext = "successor-interaction-id"


class WakeDispatcherSseTest(unittest.TestCase):
    def test_sse_notifies_on_successful_wake_with_resume_id(self) -> None:
        notifier = _RecordingNotifier()
        dispatcher = WakeDispatcher(
            {"gemini": _SucceedingProvider()},
            client_notifier=notifier,
        )
        dispatcher.wake(_workflow(), _notification())
        self.assertGreaterEqual(len(notifier.events), 1)
        event = notifier.events[-1]
        self.assertEqual(event.sessionId, "parent-interaction-id")
        self.assertEqual(event.resumeSessionId, "successor-interaction-id")
        self.assertEqual(event.status, "COMPLETED")

    def test_sse_notifies_before_provider_wake_returns(self) -> None:
        notifier = _RecordingNotifier()

        class _BlockingUntilNotified(WakeProvider):
            def wake(self, workflow, notification) -> None:
                self.events_during_wake = list(notifier.events)

        provider = _BlockingUntilNotified()
        dispatcher = WakeDispatcher(
            {"gemini": provider},
            client_notifier=notifier,
        )
        dispatcher.wake(_workflow(), _notification())
        self.assertGreaterEqual(len(provider.events_during_wake), 1)
        self.assertEqual(provider.events_during_wake[0].status, "COMPLETED")
        self.assertIsNone(provider.events_during_wake[0].resumeSessionId)

    def test_sse_notifies_even_when_gemini_wake_fails(self) -> None:
        notifier = _RecordingNotifier()
        dispatcher = WakeDispatcher(
            {"gemini": _FailingProvider()},
            client_notifier=notifier,
        )
        with self.assertRaises(_FakeAPIError):
            dispatcher.wake(_workflow(), _notification())
        self.assertEqual(len(notifier.events), 1)
        event = notifier.events[0]
        self.assertEqual(event.sessionId, "parent-interaction-id")
        self.assertIsNone(event.resumeSessionId)
        self.assertEqual(event.status, "COMPLETED")


class WorkflowCompletionReachesGeminiTest(unittest.TestCase):
    def test_continuation_service_wakes_gemini_on_completed_webhook(self) -> None:
        workflow = _workflow()
        provider = MagicMock()
        notifier = _RecordingNotifier()
        service = MagicMock()
        service.get_workflow.return_value = workflow
        dispatcher = WakeDispatcher(
            {"gemini": provider},
            client_notifier=notifier,
        )
        continuation = ContinuationService(service, dispatcher)
        handled = continuation.handle(_notification())
        self.assertTrue(handled)
        provider.wake.assert_called_once()
        args, _kwargs = provider.wake.call_args
        self.assertIs(args[0], workflow)
        self.assertEqual(args[1].status, "COMPLETED")
        self.assertEqual(len(notifier.events), 1)
        service.remove_workflow.assert_called_once_with("req-1")


class GeminiLiveWakeTest(unittest.TestCase):
    """Real Interactions API: successor turn after a COMPLETED wake payload."""

    def test_live_wake_produces_next_turn_output(self) -> None:
        from pathlib import Path

        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
        api_key = (
            os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        ).strip()
        if not api_key:
            self.skipTest("GEMINI_API_KEY / GOOGLE_API_KEY not set")

        from google import genai

        from continuation.providers.gemini_provider import wake_gemini_with_message

        model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        client = genai.Client(api_key=api_key)
        parent = client.interactions.create(
            model=model,
            input=(
                "You requested a FILL_FORM action and are waiting for the "
                "user's vault to finish. Reply with one short sentence."
            ),
        )
        parent_id = str(parent.id or "").strip()
        self.assertTrue(parent_id)

        workflow = _workflow(continuation=parent_id)
        successor_id = wake_gemini_with_message(
            previous_interaction_id=parent_id,
            message=build_gemini_wake_message(workflow, _notification()),
        )
        self.assertTrue(successor_id)
        self.assertNotEqual(successor_id, parent_id)

        child = client.interactions.get(successor_id, include_input=True)
        output = (getattr(child, "output_text", None) or "").strip()
        self.assertTrue(
            output,
            "Gemini wake successor produced no agent output_text",
        )


if __name__ == "__main__":
    unittest.main()
