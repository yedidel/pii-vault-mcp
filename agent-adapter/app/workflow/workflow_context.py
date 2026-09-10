from pathlib import Path

from continuation.ContinuationService import ContinuationService
from continuation.notifiers.sse_client_notifier import SseClientNotifier
from continuation.providers.claude_provider import ClaudeProvider
from continuation.providers.gemini_provider import GeminiProvider
from continuation.providers.openai_provider import OpenAIProvider
from continuation.session_registry import ClaudeSessionRegistry
from continuation.wake_dispatcher import WakeDispatcher
from continuation.polling_continuation import PollingContinuation
from continuation.polling_worker import PollingWorker
from continuation.pairing_watcher import PairingWatcher
from continuation.webhook_continuation import WebhookContinuation
from pairing_service import load_pairing_service
from pairing_store import load_pairing_store
from session_registry import load_session_registry
from workflow.workflow_service import WorkflowService
import json


_APP_DIR = Path(__file__).resolve().parent.parent

with open(_APP_DIR / "vault_config.json", encoding="utf-8") as _config_file:
    _vault_config = json.load(_config_file)

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

polling_continuation = PollingContinuation(
    continuation_service,
)

polling_worker = PollingWorker(
    workflow_service=workflow_service,
    polling_continuation=polling_continuation,
)

pairing_service = load_pairing_service(
    _APP_DIR,
    legacy_user_install_id=str(_vault_config["userInstallId"]),
)

pairing_watcher = PairingWatcher(
    pairing_service=pairing_service,
    pairing_store=load_pairing_store(_APP_DIR),
    client_notifier=client_notifier,
)
