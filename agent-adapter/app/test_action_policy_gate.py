import unittest
from unittest.mock import MagicMock

from action_policy_gate import ActionPolicyError, enforce_send_action_policy


class ActionPolicyGateTest(unittest.TestCase):
    def test_fill_form_evaluates_once_and_injects_handles(self) -> None:
        evaluate = MagicMock(return_value={
            "decision": "PARTIAL",
            "agentAllowed": ["name"],
            "vaultRequired": ["email", "password"],
        })
        out = enforce_send_action_policy(
            evaluate_fn=evaluate,
            agent_id="agent-123",
            user_install_id="install-1",
            action_type="FILL_FORM",
            params={"name": "Test User"},
        )
        evaluate.assert_called_once()
        self.assertEqual(
            evaluate.call_args.kwargs["field_names"][:3],
            ["name", "email", "password"],
        )
        self.assertEqual(out["name"], "Test User")
        self.assertEqual(out["email"], "vault://field/email")
        self.assertEqual(out["password"], "vault://field/password")

    def test_payment_user_approval_is_not_rejected(self) -> None:
        evaluate = MagicMock(return_value={
            "decision": "USER_APPROVAL",
            "agentAllowed": [],
            "vaultRequired": [],
            "userApprovalRequired": True,
        })
        params = {"amount": "100", "currency": "ILS"}
        out = enforce_send_action_policy(
            evaluate_fn=evaluate,
            agent_id="agent-123",
            user_install_id="install-1",
            action_type="PAYMENT",
            params=params,
        )
        evaluate.assert_called_once_with(
            agent_id="agent-123",
            user_install_id="install-1",
            action_type="PAYMENT",
            field_names=[],
        )
        self.assertEqual(out, params)

    def test_unknown_decision_fails_closed(self) -> None:
        evaluate = MagicMock(return_value={"decision": "MAYBE"})
        with self.assertRaises(ActionPolicyError):
            enforce_send_action_policy(
                evaluate_fn=evaluate,
                agent_id="agent-123",
                user_install_id="install-1",
                action_type="PAYMENT",
                params={"amount": "1", "currency": "ILS"},
            )

    def test_evaluation_exception_fails_closed(self) -> None:
        evaluate = MagicMock(side_effect=RuntimeError("timeout"))
        with self.assertRaises(ActionPolicyError):
            enforce_send_action_policy(
                evaluate_fn=evaluate,
                agent_id="agent-123",
                user_install_id="install-1",
                action_type="TRANSACTION",
                params={"transactionId": "t1"},
            )


if __name__ == "__main__":
    unittest.main()
