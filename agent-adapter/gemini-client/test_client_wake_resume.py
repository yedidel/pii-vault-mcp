import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import client as gemini_client


class ContinueAfterSendActionTest(unittest.TestCase):
    def test_stops_tool_loop_after_send_action(self) -> None:
        async def run() -> None:
            send_call = SimpleNamespace(
                id="call-1",
                type="function_call",
                name="send_action",
                arguments={"actionType": "FILL_FORM"},
            )
            first = SimpleNamespace(steps=[send_call], id="parent-id")
            after_result = SimpleNamespace(steps=[], id="after-function-result")

            genai_client = MagicMock()
            genai_client.interactions.create.return_value = after_result

            bridge = MagicMock()
            bridge.gemini_tools = []
            bridge.call_tool = AsyncMock(return_value='{"requestId":"req-1"}')

            _interaction, tip_id, send_id = await gemini_client._continue_tool_calls(
                genai_client=genai_client,
                bridge=bridge,
                interaction=first,
                model="gemini-3.6-flash",
                tip_id="parent-id",
            )
            self.assertEqual(send_id, "parent-id")
            self.assertEqual(tip_id, "after-function-result")
            self.assertEqual(genai_client.interactions.create.call_count, 1)
            kwargs = genai_client.interactions.create.call_args.kwargs
            self.assertEqual(kwargs["previous_interaction_id"], "parent-id")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
