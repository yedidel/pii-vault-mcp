import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import bridge_mcp


def _adapter_send_action_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "agentId": {"type": "string"},
            "actionType": {"type": "string"},
            "parameters": {
                "type": "object",
                "additionalProperties": {"type": "string"},
            },
            "sessionId": {"type": "string"},
            "platform": {"type": "string"},
        },
        "required": [
            "agentId",
            "actionType",
            "parameters",
            "sessionId",
            "platform",
        ],
    }


class SendActionSchemaTest(unittest.TestCase):
    def test_model_facing_schema_hides_infrastructure_fields(self) -> None:
        tools = [
            SimpleNamespace(
                name="send_action",
                description="Required parameters: platform, sessionId",
                input_schema=_adapter_send_action_schema(),
            ),
            SimpleNamespace(
                name="evaluate_user_policy",
                description="Query policy",
                input_schema={
                    "type": "object",
                    "properties": {
                        "actionType": {"type": "string"},
                        "fieldNames": {"type": "array"},
                        "agentId": {"type": "string"},
                    },
                },
            ),
            SimpleNamespace(
                name="store_pii",
                description="Store PII",
                input_schema={
                    "type": "object",
                    "properties": {
                        "fieldType": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["fieldType", "value"],
                },
            ),
        ]
        functions = bridge_mcp.mcp_tools_to_openai_functions(tools)
        by_name = {item["name"]: item for item in functions}

        send_schema = by_name["send_action"]["parameters"]
        send_props = send_schema.get("properties") or {}
        send_required = send_schema.get("required") or []
        for field in ("agentId", "platform", "sessionId"):
            self.assertNotIn(field, send_props)
            self.assertNotIn(field, send_required)
        self.assertIn("actionType", send_required)
        self.assertIn("parameters", send_required)
        description = by_name["send_action"]["description"]
        self.assertIn("Do not ask the user for platform", description)

        policy_props = (by_name["evaluate_user_policy"]["parameters"].get("properties") or {})
        self.assertIn("agentId", policy_props)
        store_required = by_name["store_pii"]["parameters"].get("required") or []
        self.assertEqual(store_required, ["fieldType", "value"])


class SendActionInjectTest(unittest.TestCase):
    def test_injects_trusted_fields_and_ignores_model_values(self) -> None:
        client = bridge_mcp.BridgeMcpClient.__new__(bridge_mcp.BridgeMcpClient)
        client.conversation_id = "conv_trusted"

        with patch.dict(
            os.environ,
            {"BRIDGE_AGENT_ID": "agent-123", "OPENAI_BRIDGE_AGENT_ID": ""},
            clear=False,
        ):
            prepared = client._prepare_arguments(
                "send_action",
                {
                    "agentId": "default",
                    "actionType": "PAYMENT",
                    "parameters": {"amount": "100", "currency": "ILS"},
                    "platform": "claude",
                    "sessionId": "hijacked-session",
                },
            )

        self.assertEqual(prepared["platform"], "openai")
        self.assertEqual(prepared["sessionId"], "conv_trusted")
        self.assertEqual(prepared["agentId"], "agent-123")
        self.assertEqual(prepared["actionType"], "PAYMENT")
        self.assertEqual(
            prepared["parameters"],
            {"amount": "100", "currency": "ILS"},
        )

    def test_other_tools_are_not_rewritten(self) -> None:
        client = bridge_mcp.BridgeMcpClient.__new__(bridge_mcp.BridgeMcpClient)
        client.conversation_id = "conv_trusted"
        args = {
            "actionType": "FILL_FORM",
            "fieldNames": ["name", "email"],
            "agentId": "agent-123",
        }
        prepared = client._prepare_arguments("evaluate_user_policy", args)
        self.assertEqual(prepared, args)


if __name__ == "__main__":
    unittest.main()
