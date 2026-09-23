#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path

from policy_eval import PolicyEvaluationError, evaluate_policy


class PolicyEvalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "user_policy.json"
        self._write({
            "userInstallId": "install-1",
            "unknownField": "VAULT_ONLY",
            "actions": {
                "PAYMENT": "USER_APPROVAL",
                "FILL_FORM": "POLICY_BASED",
                "SEARCH_PRODUCT": "AGENT_ALLOWED",
            },
            "fields": {
                "name": "AGENT_ALLOWED",
                "phone": "AGENT_ALLOWED",
                "email": "VAULT_ONLY",
                "password": "VAULT_ONLY",
                "ssn": "VAULT_ONLY",
            },
        })

    def tearDown(self) -> None:
        self.dir.cleanup()

    def _write(self, payload: dict) -> None:
        self.path.write_text(json.dumps(payload), encoding="utf-8")

    def _eval(self, action: str, fields: list[str], install: str = "install-1"):
        return evaluate_policy(
            policy_path=self.path,
            user_install_id=install,
            action_type=action,
            field_names=fields,
        )

    def test_payment_user_approval(self) -> None:
        result = self._eval("PAYMENT", [])
        self.assertEqual(result["decision"], "USER_APPROVAL")
        self.assertTrue(result["userApprovalRequired"])
        self.assertNotIn("value", result)
        self.assertNotIn("ssn", json.dumps(result))

    def test_fill_form_partial(self) -> None:
        result = self._eval("FILL_FORM", ["name", "phone", "ssn"])
        self.assertEqual(result["decision"], "PARTIAL")
        self.assertEqual(result["agentAllowed"], ["name", "phone"])
        self.assertEqual(result["vaultRequired"], ["ssn"])
        self.assertFalse(result["userApprovalRequired"])

    def test_dynamic_phone_update_same_process(self) -> None:
        first = self._eval("FILL_FORM", ["phone"])
        self.assertEqual(first["decision"], "AGENT_ALLOWED")
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload["fields"]["phone"] = "VAULT_ONLY"
        self._write(payload)
        second = self._eval("FILL_FORM", ["phone"])
        self.assertEqual(second["decision"], "VAULT_ONLY")
        self.assertEqual(second["vaultRequired"], ["phone"])

    def test_unknown_field_vault_only(self) -> None:
        result = self._eval("FILL_FORM", ["passport"])
        self.assertEqual(result["decision"], "VAULT_ONLY")
        self.assertEqual(result["vaultRequired"], ["passport"])

    def test_unknown_action_without_default_errors(self) -> None:
        with self.assertRaises(PolicyEvaluationError) as ctx:
            self._eval("LAUNCH_MISSILE", [])
        self.assertEqual(ctx.exception.code, "UNKNOWN_ACTION")

    def test_unknown_action_user_approval_default(self) -> None:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload["unknownAction"] = "USER_APPROVAL"
        self._write(payload)
        result = self._eval("OBSCURE_ACTION", [])
        self.assertEqual(result["decision"], "USER_APPROVAL")

    def test_unknown_action_agent_allowed_default_ignored(self) -> None:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload["unknownAction"] = "AGENT_ALLOWED"
        self._write(payload)
        with self.assertRaises(PolicyEvaluationError) as ctx:
            self._eval("OBSCURE_ACTION", [])
        self.assertEqual(ctx.exception.code, "UNKNOWN_ACTION")

    def test_search_product_agent_allowed(self) -> None:
        result = self._eval("SEARCH_PRODUCT", [])
        self.assertEqual(result["decision"], "AGENT_ALLOWED")
        self.assertFalse(result["userApprovalRequired"])

    def test_wrong_user_install_id(self) -> None:
        with self.assertRaises(PolicyEvaluationError) as ctx:
            self._eval("PAYMENT", [], install="other")
        self.assertEqual(ctx.exception.code, "INVALID_USER_INSTALL")

    def test_rejects_value_like_field_names(self) -> None:
        with self.assertRaises(PolicyEvaluationError) as ctx:
            self._eval("FILL_FORM", ["123456789"])
        self.assertEqual(ctx.exception.code, "INVALID_REQUEST")

    def test_malformed_policy(self) -> None:
        self.path.write_text("{not-json", encoding="utf-8")
        with self.assertRaises(PolicyEvaluationError) as ctx:
            self._eval("PAYMENT", [])
        self.assertEqual(ctx.exception.code, "MALFORMED_POLICY")

    def test_no_plaintext_in_result(self) -> None:
        result = self._eval("FILL_FORM", ["name", "ssn"])
        encoded = json.dumps(result)
        self.assertNotIn("123", encoded)
        self.assertIn("ssn", result["vaultRequired"])


if __name__ == "__main__":
    unittest.main()
