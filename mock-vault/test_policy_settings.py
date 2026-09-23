import json
import tempfile
import unittest
from http.client import HTTPConnection
from pathlib import Path

from policy_eval import (
    PolicyEvaluationError,
    demo_privacy_fields,
    evaluate_policy,
    load_policy,
    update_demo_privacy_fields,
)
from policy_http import start_policy_http_server


class PolicySettingsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "user_policy.json"
        self.values_path = Path(self.dir.name) / "vault_field_values.json"
        self._write({
            "userInstallId": "install-1",
            "unknownField": "VAULT_ONLY",
            "actions": {
                "PAYMENT": "USER_APPROVAL",
                "TRANSACTION": "USER_APPROVAL",
                "FILL_FORM": "POLICY_BASED",
            },
            "fields": {
                "name": "AGENT_ALLOWED",
                "email": "VAULT_ONLY",
                "password": "VAULT_ONLY",
                "phone": "VAULT_ONLY",
            },
        })
        self.values_path.write_text(json.dumps({
            "userInstallId": "install-1",
            "values": {
                "email": "test@example.com",
                "password": "Secret123",
            },
        }), encoding="utf-8")

    def tearDown(self) -> None:
        self.dir.cleanup()

    def _write(self, payload: dict) -> None:
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def test_reads_current_demo_fields(self) -> None:
        policy = load_policy(self.path)
        fields = demo_privacy_fields(policy)
        self.assertEqual(fields["name"], "AGENT_ALLOWED")
        self.assertEqual(fields["email"], "VAULT_ONLY")
        self.assertEqual(fields["password"], "VAULT_ONLY")
        self.assertNotIn("phone", fields)

    def test_valid_update_persists(self) -> None:
        updated = update_demo_privacy_fields(
            policy_path=self.path,
            user_install_id="install-1",
            fields={"name": "VAULT_ONLY"},
        )
        self.assertEqual(updated["name"], "VAULT_ONLY")
        stored = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(stored["fields"]["name"], "VAULT_ONLY")
        self.assertEqual(stored["fields"]["phone"], "VAULT_ONLY")
        self.assertEqual(stored["actions"]["PAYMENT"], "USER_APPROVAL")

    def test_invalid_field_rejected(self) -> None:
        with self.assertRaises(PolicyEvaluationError) as ctx:
            update_demo_privacy_fields(
                policy_path=self.path,
                user_install_id="install-1",
                fields={"ssn": "VAULT_ONLY"},
            )
        self.assertEqual(ctx.exception.code, "INVALID_REQUEST")

    def test_invalid_value_rejected(self) -> None:
        with self.assertRaises(PolicyEvaluationError) as ctx:
            update_demo_privacy_fields(
                policy_path=self.path,
                user_install_id="install-1",
                fields={"name": "USER_APPROVAL"},
            )
        self.assertEqual(ctx.exception.code, "INVALID_REQUEST")
        stored = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(stored["fields"]["name"], "AGENT_ALLOWED")

    def test_wrong_user_install_rejected(self) -> None:
        with self.assertRaises(PolicyEvaluationError) as ctx:
            update_demo_privacy_fields(
                policy_path=self.path,
                user_install_id="other-install",
                fields={"name": "VAULT_ONLY"},
            )
        self.assertEqual(ctx.exception.code, "INVALID_USER_INSTALL")
        stored = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(stored["fields"]["name"], "AGENT_ALLOWED")

    def test_http_get_and_put(self) -> None:
        server = start_policy_http_server(
            host="127.0.0.1",
            port=0,
            policy_path=self.path,
            values_path=self.values_path,
        )
        try:
            port = server.server_address[1]
            conn = HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", "/api/privacy?userInstallId=install-1")
            loaded = json.loads(conn.getresponse().read().decode("utf-8"))
            self.assertEqual(loaded["fields"]["name"], "AGENT_ALLOWED")

            conn.request(
                "PUT",
                "/api/privacy",
                body=json.dumps({
                    "userInstallId": "other",
                    "fields": {"name": "VAULT_ONLY"},
                }),
                headers={"Content-Type": "application/json"},
            )
            forbidden = conn.getresponse()
            self.assertEqual(forbidden.status, 403)
            forbidden.read()

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
            live = evaluate_policy(
                policy_path=self.path,
                user_install_id="install-1",
                action_type="FILL_FORM",
                field_names=["name"],
            )
            self.assertEqual(live["vaultRequired"], ["name"])
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
