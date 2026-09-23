import unittest
from unittest.mock import patch

from mcp_server import evaluate_user_policy
from pairing_service import PairingRequired


class EvaluateUserPolicyToolTest(unittest.TestCase):
    def test_pairing_required_does_not_call_bridge(self) -> None:
        required = PairingRequired(
            pairing_code="code",
            qr_url="http://localhost:8010/pair?code=code",
            expires_at="soon",
            message="pair",
        )
        with patch(
            "mcp_server.pairing_service.resolve",
            return_value=required,
        ), patch("mcp_server.main.evaluate_policy") as evaluate:
            result = evaluate_user_policy("FILL_FORM", ["name"])
        evaluate.assert_not_called()
        self.assertIn("pairingCode", result)

    def test_success_forwards_names_only(self) -> None:
        class Resolved:
            user_install_id = "install-1"

        with patch(
            "mcp_server.pairing_service.resolve",
            return_value=Resolved(),
        ), patch(
            "mcp_server.main.evaluate_policy",
            return_value={
                "policyRequestId": "p1",
                "actionType": "FILL_FORM",
                "decision": "PARTIAL",
                "agentAllowed": ["name"],
                "vaultRequired": ["ssn"],
                "userApprovalRequired": False,
            },
        ) as evaluate:
            result = evaluate_user_policy(
                "FILL_FORM",
                ["name", "ssn"],
                agentId="agent-123",
            )
        evaluate.assert_called_once_with(
            agent_id="agent-123",
            user_install_id="install-1",
            action_type="FILL_FORM",
            field_names=["name", "ssn"],
        )
        self.assertEqual(result["decision"], "PARTIAL")
        self.assertNotIn("error", result)

    def test_grpc_error_has_no_decision(self) -> None:
        class Resolved:
            user_install_id = "install-1"

        with patch(
            "mcp_server.pairing_service.resolve",
            return_value=Resolved(),
        ), patch(
            "mcp_server.main.evaluate_policy",
            side_effect=RuntimeError("POLICY_ERROR code=UNAVAILABLE details='No active Vault connection'"),
        ):
            result = evaluate_user_policy("PAYMENT", [])
        self.assertIn("error", result)
        self.assertNotIn("decision", result)

    def test_adapter_module_does_not_reference_policy_file(self) -> None:
        import inspect
        import mcp_server
        source = inspect.getsource(mcp_server)
        self.assertNotIn("user_policy.json", source)


if __name__ == "__main__":
    unittest.main()
