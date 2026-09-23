import asyncio
import os
import unittest
from unittest.mock import MagicMock, patch

import requests

from continuation.providers.claude_provider import (
    ClaudeProvider,
    wake_claude_with_message,
)
from continuation.session_registry import ClaudeSessionRegistry
from workflow.models import ContinuationNotification, WorkflowModel

TOKEN = "claude-channel-test-token"
SESSION_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
ADAPTER_CONTINUATION = (
    f"http://127.0.0.1:8000/continuation/{SESSION_ID}"
)
CHANNEL_WAKE = "http://127.0.0.1:55604/wake"


class ClaudeWakeAuthTest(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {
            key: os.environ.get(key)
            for key in (
                "ADAPTER_AUTH_TOKEN",
                "ADAPTER_PUBLIC_BASE",
                "ADAPTER_PORT",
            )
        }
        os.environ["ADAPTER_AUTH_TOKEN"] = TOKEN
        os.environ["ADAPTER_PUBLIC_BASE"] = "http://127.0.0.1:8000"
        os.environ["ADAPTER_PORT"] = "8000"

    def tearDown(self) -> None:
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _notification(self) -> ContinuationNotification:
        return ContinuationNotification(
            workflowId="w1",
            requestId="r1",
            status="COMPLETED",
            message="Action completed successfully",
        )

    def _workflow(self, continuation: str) -> WorkflowModel:
        return WorkflowModel(
            workflowId="w1",
            requestId="r1",
            platform="claude",
            continuationContext=continuation,
            currentStatus="IN_PROGRESS",
            actionType="FILL_FORM",
            description="",
        )

    def test_provider_posts_bearer_to_adapter_continuation_url(self) -> None:
        response = MagicMock()
        response.raise_for_status.return_value = None
        with patch(
            "continuation.providers.claude_provider.requests.post",
            return_value=response,
        ) as post:
            returned = wake_claude_with_message(
                wake_url=ADAPTER_CONTINUATION,
                message="Action completed successfully",
                request_id="r1",
                workflow_id="w1",
                status="COMPLETED",
            )

        self.assertEqual(returned, ADAPTER_CONTINUATION)
        args, kwargs = post.call_args
        self.assertEqual(args[0], ADAPTER_CONTINUATION)
        self.assertEqual(
            kwargs["headers"]["Authorization"],
            f"Bearer {TOKEN}",
        )
        self.assertEqual(
            kwargs["json"],
            {
                "requestId": "r1",
                "workflowId": "w1",
                "status": "COMPLETED",
                "message": "Action completed successfully",
            },
        )
        self.assertEqual(kwargs["timeout"], 5)

    def test_provider_wake_keeps_continuation_url(self) -> None:
        response = MagicMock()
        response.raise_for_status.return_value = None
        with patch(
            "continuation.providers.claude_provider.requests.post",
            return_value=response,
        ) as post:
            ClaudeProvider().wake(
                self._workflow(ADAPTER_CONTINUATION),
                self._notification(),
            )

        self.assertEqual(post.call_args.args[0], ADAPTER_CONTINUATION)
        self.assertEqual(
            post.call_args.kwargs["headers"]["Authorization"],
            f"Bearer {TOKEN}",
        )
        self.assertNotIn("/wake", post.call_args.args[0])

    def test_direct_wake_url_has_no_authorization(self) -> None:
        response = MagicMock()
        response.raise_for_status.return_value = None
        with patch(
            "continuation.providers.claude_provider.requests.post",
            return_value=response,
        ) as post:
            wake_claude_with_message(
                wake_url=CHANNEL_WAKE,
                message="Action completed successfully",
                request_id="r1",
                workflow_id="w1",
                status="COMPLETED",
            )

        _args, kwargs = post.call_args
        self.assertEqual(post.call_args.args[0], CHANNEL_WAKE)
        self.assertNotIn("headers", kwargs)
        self.assertEqual(kwargs["json"]["status"], "COMPLETED")

    def test_wake_error_does_not_include_token(self) -> None:
        with patch(
            "continuation.providers.claude_provider.requests.post",
            side_effect=requests.RequestException(f"boom {TOKEN}"),
        ):
            with self.assertRaises(RuntimeError) as caught:
                ClaudeProvider().wake(
                    self._workflow(ADAPTER_CONTINUATION),
                    self._notification(),
                )

        message = str(caught.exception)
        self.assertNotIn(TOKEN, message)
        self.assertIn("[redacted]", message)
        self.assertIn("requestId=r1", message)
        self.assertNotIn("Authorization", message)

    def test_forward_to_channel_wake_stays_unauthenticated(self) -> None:
        import mcp_server

        registry = ClaudeSessionRegistry()
        session = registry.register(CHANNEL_WAKE)
        request = MagicMock()
        request.path_params = {"session_id": session.session_id}
        payload = {
            "requestId": "r1",
            "workflowId": "w1",
            "status": "COMPLETED",
            "message": "Action completed successfully",
        }

        async def read_json():
            return payload

        request.json = read_json
        upstream = MagicMock()
        upstream.status_code = 200
        upstream.text = ""

        with patch.object(mcp_server, "claude_session_registry", registry):
            with patch("mcp_server.requests.post", return_value=upstream) as post:
                asyncio.run(mcp_server.forward_claude_continuation(request))

        args, kwargs = post.call_args
        self.assertEqual(args[0], CHANNEL_WAKE)
        self.assertEqual(kwargs["json"], payload)
        self.assertEqual(kwargs["timeout"], 5)
        self.assertNotIn("headers", kwargs)
        self.assertNotIn(TOKEN, str(kwargs))
