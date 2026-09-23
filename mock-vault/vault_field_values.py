"""
Vault-owned stored field values.

Separate from user_policy.json (decisions) and from Adapter pii_vault.json.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from policy_eval import DEMO_PRIVACY_FIELDS, PolicyEvaluationError

DEFAULT_VALUES_PATH = Path(__file__).resolve().parent / "vault_field_values.json"
_VALUES_WRITE_LOCK = threading.Lock()
PASSWORD_FIELDS = frozenset({"password"})


class MissingVaultValueError(Exception):
    def __init__(self, field_name: str) -> None:
        super().__init__(f"No Vault-owned value stored for {field_name}")
        self.field_name = field_name


def load_values(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise PolicyEvaluationError(
            "MALFORMED_POLICY",
            "Vault value file is missing",
        ) from error
    except json.JSONDecodeError as error:
        raise PolicyEvaluationError(
            "MALFORMED_POLICY",
            "Vault value file is not valid JSON",
        ) from error
    if not isinstance(raw, dict):
        raise PolicyEvaluationError(
            "MALFORMED_POLICY",
            "Vault value file must be a JSON object",
        )
    return raw


def get_field_value(path: Path, field_name: str) -> str:
    name = str(field_name or "").strip().lower()
    payload = load_values(path)
    values = payload.get("values")
    if not isinstance(values, dict):
        raise MissingVaultValueError(name)
    stored = values.get(name)
    if stored is None:
        raise MissingVaultValueError(name)
    text = str(stored)
    if name == "password":
        if not text:
            raise MissingVaultValueError(name)
        return text
    text = text.strip()
    if not text:
        raise MissingVaultValueError(name)
    return text


def has_field_value(path: Path, field_name: str) -> bool:
    try:
        get_field_value(path, field_name)
        return True
    except (MissingVaultValueError, PolicyEvaluationError):
        return False


def values_for_ui(path: Path) -> dict[str, dict[str, Any]]:
    payload = load_values(path)
    values = payload.get("values")
    if not isinstance(values, dict):
        values = {}
    result: dict[str, dict[str, Any]] = {}
    for name in DEMO_PRIVACY_FIELDS:
        raw = values.get(name)
        present = raw is not None and str(raw) != ""
        if name in PASSWORD_FIELDS:
            result[name] = {"hasValue": present, "preview": None}
            continue
        preview = str(raw).strip() if present else None
        result[name] = {
            "hasValue": bool(preview),
            "preview": preview or None,
        }
    return result


def update_field_values(
        *,
        path: Path,
        user_install_id: str,
        values: dict[str, str],
) -> dict[str, dict[str, Any]]:
    provided_install = (user_install_id or "").strip()
    if not provided_install:
        raise PolicyEvaluationError(
            "INVALID_USER_INSTALL",
            "user_install_id is required",
        )
    if not isinstance(values, dict):
        raise PolicyEvaluationError(
            "INVALID_REQUEST",
            "values must be an object",
        )

    patch: dict[str, str] = {}
    for raw_name, raw_value in values.items():
        name = str(raw_name).strip().lower()
        if name not in DEMO_PRIVACY_FIELDS:
            raise PolicyEvaluationError(
                "INVALID_REQUEST",
                f"Unsupported privacy field: {raw_name}",
            )
        if raw_value is None:
            continue
        text = str(raw_value)
        if name in PASSWORD_FIELDS:
            if text == "":
                continue
            patch[name] = text
            continue
        text = text.strip()
        if not text:
            continue
        patch[name] = text

    with _VALUES_WRITE_LOCK:
        payload = load_values(path)
        expected = str(payload.get("userInstallId") or "").strip()
        if not expected or expected != provided_install:
            raise PolicyEvaluationError(
                "INVALID_USER_INSTALL",
                "user_install_id does not match Vault value identity",
            )
        current = payload.get("values")
        if current is None:
            current = {}
        if not isinstance(current, dict):
            raise PolicyEvaluationError(
                "MALFORMED_POLICY",
                "values must be an object",
            )
        merged = dict(current)
        merged.update(patch)
        payload["values"] = merged
        _atomic_write_json(path, payload)
        return values_for_ui(path)


def ensure_vault_only_values(
        *,
        path: Path,
        user_install_id: str,
        field_decisions: dict[str, str],
        incoming_values: dict[str, str],
) -> None:
    incoming = {
        str(key).strip().lower(): value
        for key, value in (incoming_values or {}).items()
    }
    for name, decision in field_decisions.items():
        if str(decision).strip().upper() != "VAULT_ONLY":
            continue
        provided = incoming.get(name)
        if provided is not None and str(provided) != "":
            continue
        if has_field_value(path, name):
            continue
        raise PolicyEvaluationError(
            "INVALID_REQUEST",
            f"Vault-only {name} requires a stored value",
        )


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".vault_field_values.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
