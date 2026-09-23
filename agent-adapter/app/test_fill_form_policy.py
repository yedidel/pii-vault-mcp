import unittest
from unittest.mock import patch

from fill_form_enforcement import (
    FillFormPolicyError,
    apply_live_fill_form_policy,
    fill_form_policy_field_names,
)
from mcp_server import send_action
from pairing_service import PairingRequired
from workflow.models import WorkflowModel


class FillFormLivePolicyTest(unittest.TestCase):
    def _partial_eval(self, *, name_vault: bool = False) -> dict:
        if name_vault:
            return {
                "decision": "VAULT_ONLY",
                "agentAllowed": [],
                "vaultRequired": ["name", "email", "password"],
            }
        return {
            "decision": "PARTIAL",
            "agentAllowed": ["name"],
            "vaultRequired": ["email", "password"],
        }

    def test_policy_field_names_are_canonical_not_values(self) -> None:
        names = fill_form_policy_field_names({
            "formUrl": "http://127.0.0.1:9000/register",
            "name": "Dana Secret",
        })
        self.assertEqual(names[:3], ["name", "email", "password"])
        self.assertNotIn("Dana Secret", names)

    def test_mixed_ownership_agent_supplies_name_only(self) -> None:
        out = apply_live_fill_form_policy(
            {"name": "Test User"},
            self._partial_eval(),
        )
        self.assertEqual(out["name"], "Test User")
        self.assertEqual(out["email"], "vault://field/email")
        self.assertEqual(out["password"], "vault://field/password")

    def test_all_vault_owned_agent_supplies_nothing(self) -> None:
        out = apply_live_fill_form_policy({}, self._partial_eval(name_vault=True))
        self.assertEqual(out["name"], "vault://field/name")
        self.assertEqual(out["email"], "vault://field/email")
        self.assertEqual(out["password"], "vault://field/password")

    def test_agent_allowed_name_required_again(self) -> None:
        with self.assertRaises(FillFormPolicyError):
            apply_live_fill_form_policy({}, self._partial_eval())

    def test_malicious_vault_only_plaintext_is_dropped(self) -> None:
        out = apply_live_fill_form_policy(
            {
                "name": "Test User",
                "email": "attacker-supplied@example.com",
                "password": "stolen",
            },
            self._partial_eval(),
        )
        self.assertEqual(out["email"], "vault://field/email")
        self.assertEqual(out["password"], "vault://field/password")
        self.assertNotIn("attacker-supplied@example.com", out.values())
        self.assertNotIn("stolen", out.values())

    def test_legacy_pii_ref_kept_for_vault_only(self) -> None:
        out = apply_live_fill_form_policy(
            {
                "name": "Test User",
                "email": "vault://pii/email/token",
            },
            self._partial_eval(),
        )
        self.assertEqual(out["email"], "vault://pii/email/token")
        self.assertEqual(out["password"], "vault://field/password")

    def test_unknown_decision_fails_closed(self) -> None:
        with self.assertRaises(FillFormPolicyError):
            apply_live_fill_form_policy(
                {"name": "Dana"},
                {
                    "decision": "WHATEVER",
                    "agentAllowed": ["name"],
                    "vaultRequired": ["email", "password"],
                },
            )

    def test_inconsistent_coverage_fails_closed(self) -> None:
        with self.assertRaises(FillFormPolicyError):
            apply_live_fill_form_policy(
                {"name": "Dana"},
                {
                    "decision": "PARTIAL",
                    "agentAllowed": ["name"],
                    "vaultRequired": ["email"],
                },
            )

    def test_policy_change_without_adapter_restart(self) -> None:
        first = apply_live_fill_form_policy(
            {"name": "Dana"},
            self._partial_eval(),
        )
        self.assertEqual(first["name"], "Dana")
        second = apply_live_fill_form_policy(
            {"name": "Dana"},
            self._partial_eval(name_vault=True),
        )
        self.assertEqual(second["name"], "vault://field/name")


class SendActionFillFormPolicyTest(unittest.TestCase):
    def _workflow(self) -> WorkflowModel:
        return WorkflowModel(
            workflowId="w1",
            requestId="r1",
            platform="openai",
            continuationContext="sess",
            currentStatus="RECEIVED",
            actionType="FILL_FORM",
            description="ok",
        )

    def _paired(self):
        class Resolved:
            user_install_id = "install-1"
        return Resolved()

    def test_skipping_evaluate_user_policy_still_enforces(self) -> None:
        with patch(
            "mcp_server.pairing_service.resolve",
            return_value=self._paired(),
        ), patch(
            "mcp_server.bridge_session_registry.ensure_bound",
        ), patch(
            "mcp_server.main.evaluate_policy",
            return_value={
                "decision": "PARTIAL",
                "agentAllowed": ["name"],
                "vaultRequired": ["email", "password"],
            },
        ) as evaluate, patch(
            "mcp_server.workflow_service.create_workflow",
            return_value=self._workflow(),
        ) as create:
            result = send_action(
                agentId="agent-123",
                actionType="FILL_FORM",
                parameters={"name": "Test User"},
                sessionId="sess-1",
                platform="openai",
            )
        self.assertNotIn("error", result)
        evaluate.assert_called_once()
        self.assertEqual(
            evaluate.call_args.kwargs["field_names"][:3],
            ["name", "email", "password"],
        )
        params = create.call_args.kwargs["action_request"].parameters
        self.assertEqual(params["name"], "Test User")
        self.assertEqual(params["email"], "vault://field/email")
        self.assertEqual(params["password"], "vault://field/password")

    def test_malicious_email_never_reaches_bridge(self) -> None:
        with patch(
            "mcp_server.pairing_service.resolve",
            return_value=self._paired(),
        ), patch(
            "mcp_server.bridge_session_registry.ensure_bound",
        ), patch(
            "mcp_server.main.evaluate_policy",
            return_value={
                "decision": "PARTIAL",
                "agentAllowed": ["name"],
                "vaultRequired": ["email", "password"],
            },
        ), patch(
            "mcp_server.workflow_service.create_workflow",
            return_value=self._workflow(),
        ) as create:
            result = send_action(
                agentId="agent-123",
                actionType="FILL_FORM",
                parameters={
                    "name": "Test User",
                    "email": "attacker-supplied@example.com",
                },
                sessionId="sess-1",
                platform="openai",
            )
        self.assertNotIn("error", result)
        params = create.call_args.kwargs["action_request"].parameters
        self.assertEqual(params["email"], "vault://field/email")
        self.assertNotEqual(params["email"], "attacker-supplied@example.com")

    def test_missing_agent_allowed_name_never_sends(self) -> None:
        with patch(
            "mcp_server.pairing_service.resolve",
            return_value=self._paired(),
        ), patch(
            "mcp_server.bridge_session_registry.ensure_bound",
        ), patch(
            "mcp_server.main.evaluate_policy",
            return_value={
                "decision": "PARTIAL",
                "agentAllowed": ["name"],
                "vaultRequired": ["email", "password"],
            },
        ), patch(
            "mcp_server.workflow_service.create_workflow",
        ) as create:
            result = send_action(
                agentId="agent-123",
                actionType="FILL_FORM",
                parameters={},
                sessionId="sess-1",
                platform="openai",
            )
        self.assertIn("error", result)
        create.assert_not_called()

    def test_policy_timeout_never_sends(self) -> None:
        with patch(
            "mcp_server.pairing_service.resolve",
            return_value=self._paired(),
        ), patch(
            "mcp_server.bridge_session_registry.ensure_bound",
        ), patch(
            "mcp_server.main.evaluate_policy",
            side_effect=RuntimeError("POLICY_ERROR code=DEADLINE_EXCEEDED details='timeout'"),
        ), patch(
            "mcp_server.workflow_service.create_workflow",
        ) as create, patch(
            "mcp_server.main.send_action",
        ) as grpc_send:
            result = send_action(
                agentId="agent-123",
                actionType="FILL_FORM",
                parameters={"name": "Test User"},
                sessionId="sess-1",
                platform="openai",
            )
        self.assertIn("error", result)
        create.assert_not_called()
        grpc_send.assert_not_called()

    def test_payment_user_approval_proceeds_after_one_policy_eval(self) -> None:
        workflow = self._workflow()
        workflow.actionType = "PAYMENT"
        with patch(
            "mcp_server.pairing_service.resolve",
            return_value=self._paired(),
        ), patch(
            "mcp_server.bridge_session_registry.ensure_bound",
        ), patch(
            "mcp_server.main.evaluate_policy",
            return_value={
                "decision": "USER_APPROVAL",
                "agentAllowed": [],
                "vaultRequired": [],
                "userApprovalRequired": True,
            },
        ) as evaluate, patch(
            "mcp_server.workflow_service.create_workflow",
            return_value=workflow,
        ) as create:
            result = send_action(
                agentId="agent-123",
                actionType="PAYMENT",
                parameters={"amount": "10", "currency": "ILS"},
                sessionId="sess-1",
                platform="openai",
            )
        self.assertNotIn("error", result)
        evaluate.assert_called_once_with(
            agent_id="agent-123",
            user_install_id="install-1",
            action_type="PAYMENT",
            field_names=[],
        )
        create.assert_called_once()
        params = create.call_args.kwargs["action_request"].parameters
        self.assertEqual(params["amount"], "10")
        self.assertEqual(params["currency"], "ILS")

    def test_transaction_automatically_evaluates_policy(self) -> None:
        workflow = self._workflow()
        workflow.actionType = "TRANSACTION"
        with patch(
            "mcp_server.pairing_service.resolve",
            return_value=self._paired(),
        ), patch(
            "mcp_server.bridge_session_registry.ensure_bound",
        ), patch(
            "mcp_server.main.evaluate_policy",
            return_value={
                "decision": "USER_APPROVAL",
                "agentAllowed": [],
                "vaultRequired": [],
                "userApprovalRequired": True,
            },
        ) as evaluate, patch(
            "mcp_server.workflow_service.create_workflow",
            return_value=workflow,
        ) as create:
            result = send_action(
                agentId="agent-123",
                actionType="TRANSACTION",
                parameters={"transactionId": "t1", "account": "a1"},
                sessionId="sess-1",
                platform="openai",
            )
        self.assertNotIn("error", result)
        evaluate.assert_called_once_with(
            agent_id="agent-123",
            user_install_id="install-1",
            action_type="TRANSACTION",
            field_names=[],
        )
        create.assert_called_once()

    def test_payment_unknown_decision_never_sends(self) -> None:
        with patch(
            "mcp_server.pairing_service.resolve",
            return_value=self._paired(),
        ), patch(
            "mcp_server.bridge_session_registry.ensure_bound",
        ), patch(
            "mcp_server.main.evaluate_policy",
            return_value={"decision": "NOT_A_REAL_DECISION"},
        ), patch(
            "mcp_server.workflow_service.create_workflow",
        ) as create, patch(
            "mcp_server.main.send_action",
        ) as grpc_send:
            result = send_action(
                agentId="agent-123",
                actionType="PAYMENT",
                parameters={"amount": "100", "currency": "ILS"},
                sessionId="sess-1",
                platform="openai",
            )
        self.assertIn("error", result)
        create.assert_not_called()
        grpc_send.assert_not_called()

    def test_payment_policy_timeout_never_sends(self) -> None:
        with patch(
            "mcp_server.pairing_service.resolve",
            return_value=self._paired(),
        ), patch(
            "mcp_server.bridge_session_registry.ensure_bound",
        ), patch(
            "mcp_server.main.evaluate_policy",
            side_effect=RuntimeError("POLICY_ERROR code=UNAVAILABLE details='No active Vault connection'"),
        ), patch(
            "mcp_server.workflow_service.create_workflow",
        ) as create, patch(
            "mcp_server.main.send_action",
        ) as grpc_send:
            result = send_action(
                agentId="agent-123",
                actionType="PAYMENT",
                parameters={"amount": "100", "currency": "ILS"},
                sessionId="sess-1",
                platform="openai",
            )
        self.assertIn("error", result)
        create.assert_not_called()
        grpc_send.assert_not_called()

    def test_pairing_required_skips_policy_and_send(self) -> None:
        required = PairingRequired(
            pairing_code="code",
            qr_url="http://localhost:8010/pair?code=code",
            expires_at="soon",
            message="pair",
        )
        with patch(
            "mcp_server.pairing_service.resolve",
            return_value=required,
        ), patch("mcp_server.main.evaluate_policy") as evaluate, patch(
            "mcp_server.workflow_service.create_workflow",
        ) as create:
            result = send_action(
                agentId="agent-123",
                actionType="FILL_FORM",
                parameters={"name": "Test User"},
                sessionId="sess-1",
                platform="openai",
            )
        evaluate.assert_not_called()
        create.assert_not_called()
        self.assertIn("pairingCode", result)

    def test_public_store_pii_still_rejects_name(self) -> None:
        from mcp_server import store_pii
        result = store_pii("name", "Dana")
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
