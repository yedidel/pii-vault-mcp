import asyncio
import unittest

from continuation.notifiers.sse_client_notifier import SseClientNotifier
from continuation.client_notifier import ClientNotifyEvent


class SseQueueTest(unittest.TestCase):
    def test_replace_subscriber_when_queue_full_does_not_raise(self) -> None:
        async def run() -> None:
            notifier = SseClientNotifier()
            first = notifier.subscribe("openai", "s1")
            event = ClientNotifyEvent(
                workflowId="w",
                requestId="r",
                platform="openai",
                sessionId="s1",
                status="COMPLETED",
            )
            while True:
                try:
                    first.put_nowait(event)
                except asyncio.QueueFull:
                    break
            notifier.subscribe("openai", "s1")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
