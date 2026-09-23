import tempfile
import unittest
from pathlib import Path

from cryptography.fernet import Fernet

from vault_store import PiiVaultStore


class PiiSanitizeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        path = Path(self.dir.name) / "pii_vault.json"
        self.store = PiiVaultStore(store_path=path, key=Fernet.generate_key())

    def tearDown(self) -> None:
        self.dir.cleanup()

    def test_plaintext_email_password_become_refs(self) -> None:
        out = self.store.sanitize_fill_form_parameters(
            {"name": "Dana", "email": "dana@example.com", "password": "Secret123"},
            vault_required=["email", "password"],
        )
        self.assertEqual(out["name"], "Dana")
        self.assertTrue(out["email"].startswith("vault://pii/email/"))
        self.assertTrue(out["password"].startswith("vault://pii/password/"))

    def test_existing_ref_is_unchanged(self) -> None:
        token = self.store.store("email", "a@b.com")
        out = self.store.sanitize_fill_form_parameters(
            {"email": token, "password": "x"},
            vault_required=["email", "password"],
        )
        self.assertEqual(out["email"], token)
        self.assertTrue(out["password"].startswith("vault://pii/password/"))

    def test_public_store_rejects_name(self) -> None:
        with self.assertRaises(ValueError):
            self.store.store("name", "Dana")

    def test_policy_store_accepts_name(self) -> None:
        token = self.store.store_policy_field("name", "Dana")
        self.assertTrue(token.startswith("vault://pii/name/"))
        self.assertEqual(self.store.resolve(token), "Dana")

    def test_resolve_roundtrip(self) -> None:
        token = self.store.store("email", "a@b.com")
        from transport.vault_resolve_http import resolve_vault_refs
        resolved = resolve_vault_refs(self.store, [token])
        self.assertEqual(resolved[token], "a@b.com")


if __name__ == "__main__":
    unittest.main()
