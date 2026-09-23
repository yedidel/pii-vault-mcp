from __future__ import annotations

import json
import os
import secrets
import threading
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

VAULT_REF_PREFIX = "vault://pii/"
ALLOWED_FIELD_TYPES = frozenset({"email", "password", "ssn", "phone"})


class PiiVaultStore:
    def __init__(self, store_path: Path, key: bytes):
        self._store_path = store_path
        self._fernet = Fernet(key)
        self._lock = threading.Lock()
        self._entries: dict[str, dict[str, str]] = {}
        self._load()

    @staticmethod
    def is_ref(value: str) -> bool:
        return value.startswith(VAULT_REF_PREFIX)

    def store(self, field_type: str, value: str) -> str:
        field_type = field_type.strip().lower()
        if field_type not in ALLOWED_FIELD_TYPES:
            raise ValueError(f"Unsupported fieldType: {field_type}")
        return self._store_encrypted(field_type, value)

    def store_policy_field(self, field_type: str, value: str) -> str:
        field_type = _internal_field_type(field_type)
        return self._store_encrypted(field_type, value)

    def _store_encrypted(self, field_type: str, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must be non-empty")

        token_id = secrets.token_urlsafe(16)
        ciphertext = self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

        with self._lock:
            self._load()
            self._entries[token_id] = {
                "fieldType": field_type,
                "ciphertext": ciphertext,
            }
            self._persist()

        return f"{VAULT_REF_PREFIX}{field_type}/{token_id}"

    def resolve(self, ref: str) -> str:
        if not self.is_ref(ref):
            return ref

        suffix = ref[len(VAULT_REF_PREFIX):]
        parts = suffix.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid vault reference: {ref}")

        field_type, token_id = parts[0].strip().lower(), parts[1].strip()
        if not field_type or not token_id:
            raise ValueError(f"Invalid vault reference: {ref}")

        with self._lock:
            self._load()
            entry = self._entries.get(token_id)

        if entry is None:
            raise KeyError(f"Unknown vault token: {token_id}")
        if entry["fieldType"] != field_type:
            raise ValueError(f"Vault reference field type mismatch for {ref}")

        try:
            return self._fernet.decrypt(entry["ciphertext"].encode("ascii")).decode("utf-8")
        except InvalidToken as error:
            raise ValueError(f"Unable to decrypt vault token: {token_id}") from error

    def resolve_many(self, refs: list[str]) -> dict[str, str]:
        return {ref: self.resolve(ref) for ref in refs}

    def sanitize_fill_form_parameters(
            self,
            params: dict[str, str],
            vault_required: list[str],
    ) -> dict[str, str]:
        sanitized = dict(params)
        for key in vault_required:
            raw = str(sanitized.get(key) or "").strip()
            if not raw or self.is_ref(raw):
                continue
            sanitized[key] = self.store_policy_field(key, raw)
        return sanitized

    def _load(self) -> None:
        if not self._store_path.exists():
            return
        raw = json.loads(self._store_path.read_text(encoding="utf-8"))
        entries = raw.get("entries") if isinstance(raw, dict) else None
        if isinstance(entries, dict):
            self._entries = {
                str(token_id): {
                    "fieldType": str(entry.get("fieldType") or ""),
                    "ciphertext": str(entry.get("ciphertext") or ""),
                }
                for token_id, entry in entries.items()
                if isinstance(entry, dict)
            }

    def _persist(self) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"entries": self._entries}
        self._store_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def load_vault_store(base_dir: Path) -> PiiVaultStore:
    data_dir = base_dir / "data"
    store_path = data_dir / "pii_vault.json"
    key = _load_or_create_key(data_dir)
    return PiiVaultStore(store_path=store_path, key=key)


def _internal_field_type(field_type: str) -> str:
    name = (field_type or "").strip().lower()
    if not name or len(name) > 64:
        raise ValueError(f"Unsupported fieldType: {field_type}")
    if any(ch.isspace() for ch in name):
        raise ValueError(f"Unsupported fieldType: {field_type}")
    if not all(ch.isalnum() or ch in {"_", "-"} for ch in name):
        raise ValueError(f"Unsupported fieldType: {field_type}")
    return name


def _load_or_create_key(data_dir: Path) -> bytes:
    env_key = os.getenv("VAULT_STORE_KEY", "").strip()
    if env_key:
        return env_key.encode("utf-8")

    key_path = data_dir / ".vault_key"
    if key_path.exists():
        return key_path.read_bytes().strip()

    data_dir.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    key_path.write_bytes(key)
    return key
