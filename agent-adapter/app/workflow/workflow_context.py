from pathlib import Path

from continuation.ContinuationService import ContinuationService
from continuation.notifiers.sse_client_notifier import SseClientNotifier
from continuation.providers.claude_provider import ClaudeProvider
from continuation.providers.gemini_provider import GeminiProvider
from continuation.providers.openai_provider import OpenAIProvider
from continuation.session_registry import ClaudeSessionRegistry
from continuation.wake_dispatcher import WakeDispatcher
from continuation.webhook_continuation import WebhookContinuation
from session_registry import load_session_registry
from workflow.workflow_service import WorkflowService


_APP_DIR = Path(__file__).resolve().parent.parent

workflow_service = WorkflowService()

claude_session_registry = ClaudeSessionRegistry()
bridge_session_registry = load_session_registry(_APP_DIR)

gemini_provider = GeminiProvider()
claude_provider = ClaudeProvider()
openai_provider = OpenAIProvider()

# Shared across webhook wake path and GET /events subscriptions.
client_notifier = SseClientNotifier()

wake_dispatcher = WakeDispatcher(
    {
        "gemini": gemini_provider,
        "google": gemini_provider,
        "claude": claude_provider,
        "openai": openai_provider,
    },
    client_notifier=client_notifier,
)

continuation_service = ContinuationService(
    workflow_service,
    wake_dispatcher,
)

webhook_continuation = WebhookContinuation(
    continuation_service,
)
