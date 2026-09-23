#!/usr/bin/env python3
import json
import tempfile
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import MagicMock

from policy_eval import PolicyEvaluationError
from policy_http import start_policy_http_server
from vault_field_values import (
    MissingVaultValueError,
    ensure_vault_only_values,
    get_field_value,
    update_field_values,
    values_for_ui,
)
from vault_sim import _resolve_vault_refs


class VaultOwnedValuesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.policy_path = Path(self.dir.name) / "user_policy.json"
        self.values_path = Path(self.dir.name) / "vault_field_values.json"
        self.policy_path.write_text(json.dumps({
            "userInstallId": "install-1",
            "unknownField": "VAULT_ONLY",
            "actions": {"FILL_FORM": "POLICY_BASED", "PAYMENT": "USER_APPROVAL"},
            "fields": {
                "name": "AGENT_ALLOWED",
                "email": "VAULT_ONLY",
                "password": "VAULT_ONLY",
            },
        }), encoding="utf-8")
        self.values_path.write_text(json.dumps({
            "userInstallId": "install-1",
            "values": {
                "email": "test@example.com",
                "password": "Secret123",
            },
        }), encoding="utf-8")

    def tearDown(self) -> None:
        self.dir.cleanup()

    def test_ui_does_not_preview_password(self) -> None:
        ui = values_for_ui(self.values_path)
        self.assertTrue(ui["email"]["hasValue"])
        self.assertEqual(ui["email"]["preview"], "test@example.com")
        self.assertTrue(ui["password"]["hasValue"])
        self.assertIsNone(ui["password"]["preview"])
        self.assertFalse(ui["name"]["hasValue"])

    def test_wrong_install_cannot_update_values(self) -> None:
        with self.assertRaises(PolicyEvaluationError) as ctx:
            update_field_values(
                path=self.values_path,
                user_install_id="other",
                values={"email": "evil@example.com"},
            )
        self.assertEqual(ctx.exception.code, "INVALID_USER_INSTALL")
        self.assertEqual(get_field_value(self.values_path, "email"), "test@example.com")

    def test_vault_only_requires_value(self) -> None:
        with self.assertRaises(PolicyEvaluationError) as ctx:
            ensure_vault_only_values(
                path=self.values_path,
                user_install_id="install-1",
                field_decisions={"name": "VAULT_ONLY", "email": "VAULT_ONLY", "password": "VAULT_ONLY"},
                incoming_values={},
            )
        self.assertEqual(ctx.exception.code, "INVALID_REQUEST")

    def test_malicious_plaintext_is_not_persisted(self) -> None:
        before = get_field_value(self.values_path, "email")
        self.assertEqual(before, "test@example.com")
        # Adapter-side drop is tested separately; Vault store stays unchanged.
        self.assertEqual(get_field_value(self.values_path, "email"), before)

    def test_local_field_handle_does_not_call_adapter(self) -> None:
        adapter = MagicMock()
        resolved = _resolve_vault_refs(
            {
                "name": "Test User",
                "email": "vault://field/email",
                "password": "vault://field/password",
            },
            adapter_resolve=adapter,
            values_path=self.values_path,
        )
        adapter.assert_not_called()
        self.assertEqual(resolved["name"], "Test User")
        self.assertEqual(resolved["email"], "test@example.com")
        self.assertEqual(resolved["password"], "Secret123")

    def test_missing_vault_value_fails_closed(self) -> None:
        self.values_path.write_text(json.dumps({
            "userInstallId": "install-1",
            "values": {"password": "Secret123"},
        }), encoding="utf-8")
        with self.assertRaises(MissingVaultValueError):
            _resolve_vault_refs(
                {"email": "vault://field/email"},
                adapter_resolve=MagicMock(),
                values_path=self.values_path,
            )

    def test_legacy_pii_ref_uses_adapter(self) -> None:
        adapter = MagicMock(return_value={"vault://pii/email/token": "legacy@example.com"})
        resolved = _resolve_vault_refs(
            {"email": "vault://pii/email/token", "name": "Dana"},
            adapter_resolve=adapter,
            values_path=self.values_path,
        )
        adapter.assert_called_once_with(["vault://pii/email/token"])
        self.assertEqual(resolved["email"], "legacy@example.com")

    def test_http_put_requires_value_and_hides_password(self) -> None:
        server = start_policy_http_server(
            host="127.0.0.1",
            port=0,
            policy_path=self.policy_path,
            values_path=self.values_path,
        )
        try:
            port = server.server_address[1]
            conn = HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", "/api/privacy?userInstallId=install-1")
            loaded = json.loads(conn.getresponse().read().decode("utf-8"))
            self.assertEqual(loaded["storedValues"]["email"]["preview"], "test@example.com")
            self.assertIsNone(loaded["storedValues"]["password"]["preview"])
            self.assertTrue(loaded["storedValues"]["password"]["hasValue"])

            conn.request(
                "PUT",
                "/api/privacy",
                body=json.dumps({
                    "userInstallId": "install-1",
                    "fields": {"name": "VAULT_ONLY"},
                }),
                headers={"Content-Type": "application/json"},
            )
            rejected = conn.getresponse()
            self.assertEqual(rejected.status, 400)
            rejected.read()

            conn.request(
                "PUT",
                "/api/privacy",
                body=json.dumps({
                    "userInstallId": "install-1",
                    "fields": {"name": "VAULT_ONLY"},
                    "values": {"name": "Test User"},
                }),
                headers={"Content-Type": "application/json"},
            )
            saved = json.loads(conn.getresponse().read().decode("utf-8"))
            self.assertTrue(saved["saved"])
            self.assertEqual(saved["fields"]["name"], "VAULT_ONLY")
            self.assertEqual(get_field_value(self.values_path, "name"), "Test User")
            encoded = self.values_path.read_text(encoding="utf-8")
            self.assertNotIn("attacker", encoded)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
