from continuation.ContinuationService import ContinuationService
from continuation.providers.claude_provider import ClaudeProvider
from continuation.providers.gemini_provider import GeminiProvider
from continuation.session_registry import ClaudeSessionRegistry
from continuation.wake_dispatcher import WakeDispatcher
from continuation.webhook_continuation import WebhookContinuation
from workflow.workflow_service import WorkflowService


workflow_service = WorkflowService()

claude_session_registry = ClaudeSessionRegistry()

gemini_provider = GeminiProvider()

claude_provider = ClaudeProvider()

wake_dispatcher = WakeDispatcher(
    {
        "gemini": gemini_provider,
        "google": gemini_provider,
        "claude": claude_provider,
    }
)

continuation_service = ContinuationService(
    workflow_service,
    wake_dispatcher,
)

webhook_continuation = WebhookContinuation(
    continuation_service,
)
