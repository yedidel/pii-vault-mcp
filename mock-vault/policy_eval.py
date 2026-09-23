"""
User privacy policy evaluator.

Owned by Mock Vault. Reads the policy file on every evaluation so the next
query observes edits without a process restart.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

DECISIONS = frozenset({"AGENT_ALLOWED", "VAULT_ONLY", "USER_APPROVAL"})
AGGREGATE_PARTIAL = "PARTIAL"
ACTION_POLICY_BASED = "POLICY_BASED"
ALLOWED_UNKNOWN_ACTION_DEFAULT = frozenset({"USER_APPROVAL"})
ALLOWED_UNKNOWN_FIELD_DEFAULT = frozenset({"VAULT_ONLY"})
DEMO_PRIVACY_FIELDS = ("name", "email", "password")
DEMO_PRIVACY_DECISIONS = frozenset({"AGENT_ALLOWED", "VAULT_ONLY"})

DEFAULT_POLICY_PATH = Path(__file__).resolve().parent / "user_policy.json"
_POLICY_WRITE_LOCK = threading.Lock()


class PolicyEvaluationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def load_policy(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise PolicyEvaluationError(
            "MALFORMED_POLICY",
            "Policy file is missing",
        ) from error
    except json.JSONDecodeError as error:
        raise PolicyEvaluationError(
            "MALFORMED_POLICY",
            "Policy file is not valid JSON",
        ) from error
    if not isinstance(raw, dict):
        raise PolicyEvaluationError(
            "MALFORMED_POLICY",
            "Policy file must be a JSON object",
        )
    return raw


def evaluate_policy(
        *,
        policy_path: Path,
        user_install_id: str,
        action_type: str,
        field_names: list[str],
) -> dict[str, Any]:
    policy = load_policy(policy_path)
    expected_install = str(policy.get("userInstallId") or "").strip()
    provided_install = (user_install_id or "").strip()
    if not expected_install or expected_install != provided_install:
        raise PolicyEvaluationError(
            "INVALID_USER_INSTALL",
            "user_install_id does not match Vault policy identity",
        )

    action = (action_type or "").strip().upper()
    if not action:
        raise PolicyEvaluationError(
            "INVALID_REQUEST",
            "action_type is required",
        )

    names = [
        str(name).strip()
        for name in field_names
        if str(name).strip()
    ]
    for name in names:
        if not _is_field_name(name):
            raise PolicyEvaluationError(
                "INVALID_REQUEST",
                "field_names must be names only, not values",
            )

    actions = policy.get("actions")
    if actions is not None and not isinstance(actions, dict):
        raise PolicyEvaluationError(
            "MALFORMED_POLICY",
            "actions must be an object",
        )
    action_rule = str((actions or {}).get(action) or "").strip().upper()

    if not action_rule:
        unknown_action = str(policy.get("unknownAction") or "").strip().upper()
        if unknown_action in ALLOWED_UNKNOWN_ACTION_DEFAULT:
            return _action_result(
                action,
                unknown_action,
                user_approval_required=(unknown_action == "USER_APPROVAL"),
            )
        raise PolicyEvaluationError(
            "UNKNOWN_ACTION",
            f"No Vault policy for action {action}",
        )

    if action_rule == ACTION_POLICY_BASED:
        return _evaluate_fields(policy, action, names)

    if action_rule not in DECISIONS:
        raise PolicyEvaluationError(
            "MALFORMED_POLICY",
            f"Invalid action decision for {action}",
        )

    return _action_result(
        action,
        action_rule,
        user_approval_required=(action_rule == "USER_APPROVAL"),
    )


def _evaluate_fields(
        policy: dict[str, Any],
        action: str,
        field_names: list[str],
) -> dict[str, Any]:
    fields = policy.get("fields")
    if fields is not None and not isinstance(fields, dict):
        raise PolicyEvaluationError(
            "MALFORMED_POLICY",
            "fields must be an object",
        )
    field_map = {
        str(key).strip().lower(): str(value).strip().upper()
        for key, value in (fields or {}).items()
    }
    unknown_field = str(policy.get("unknownField") or "VAULT_ONLY").strip().upper()
    if unknown_field not in ALLOWED_UNKNOWN_FIELD_DEFAULT:
        unknown_field = "VAULT_ONLY"

    agent_allowed: list[str] = []
    vault_required: list[str] = []
    user_approval_required = False

    for name in field_names:
        rule = field_map.get(name.lower()) or unknown_field
        if rule == "USER_APPROVAL":
            user_approval_required = True
            vault_required.append(name)
            continue
        if rule == "AGENT_ALLOWED":
            agent_allowed.append(name)
            continue
        vault_required.append(name)

    if agent_allowed and vault_required:
        decision = "PARTIAL"
    elif agent_allowed:
        decision = "AGENT_ALLOWED"
    elif user_approval_required and not agent_allowed:
        decision = "USER_APPROVAL"
    elif vault_required:
        decision = "VAULT_ONLY"
    else:
        decision = "PARTIAL"

    return {
        "ok": True,
        "actionType": action,
        "decision": decision,
        "agentAllowed": agent_allowed,
        "vaultRequired": vault_required,
        "userApprovalRequired": user_approval_required,
    }


def _action_result(
        action: str,
        decision: str,
        *,
        user_approval_required: bool,
) -> dict[str, Any]:
    return {
        "ok": True,
        "actionType": action,
        "decision": decision,
        "agentAllowed": [],
        "vaultRequired": [],
        "userApprovalRequired": user_approval_required,
    }


def _is_field_name(name: str) -> bool:
    if not name or len(name) > 64:
        return False
    if any(ch.isspace() for ch in name):
        return False
    if "@" in name or name.isdigit():
        return False
    return True


def demo_privacy_fields(policy: dict[str, Any]) -> dict[str, str]:
    fields = policy.get("fields")
    if fields is not None and not isinstance(fields, dict):
        raise PolicyEvaluationError(
            "MALFORMED_POLICY",
            "fields must be an object",
        )
    field_map = {
        str(key).strip().lower(): str(value).strip().upper()
        for key, value in (fields or {}).items()
    }
    result: dict[str, str] = {}
    for name in DEMO_PRIVACY_FIELDS:
        rule = field_map.get(name, "VAULT_ONLY")
        if rule not in DEMO_PRIVACY_DECISIONS:
            rule = "VAULT_ONLY"
        result[name] = rule
    return result


def update_demo_privacy_fields(
        *,
        policy_path: Path,
        user_install_id: str,
        fields: dict[str, str],
) -> dict[str, str]:
    provided_install = (user_install_id or "").strip()
    if not provided_install:
        raise PolicyEvaluationError(
            "INVALID_USER_INSTALL",
            "user_install_id is required",
        )
    if not isinstance(fields, dict) or not fields:
        raise PolicyEvaluationError(
            "INVALID_REQUEST",
            "fields must be a non-empty object",
        )

    patch: dict[str, str] = {}
    for raw_name, raw_value in fields.items():
        name = str(raw_name).strip().lower()
        value = str(raw_value).strip().upper()
        if name not in DEMO_PRIVACY_FIELDS:
            raise PolicyEvaluationError(
                "INVALID_REQUEST",
                f"Unsupported privacy field: {raw_name}",
            )
        if value not in DEMO_PRIVACY_DECISIONS:
            raise PolicyEvaluationError(
                "INVALID_REQUEST",
                f"Unsupported privacy value for {name}",
            )
        patch[name] = value

    with _POLICY_WRITE_LOCK:
        policy = load_policy(policy_path)
        expected_install = str(policy.get("userInstallId") or "").strip()
        if not expected_install or expected_install != provided_install:
            raise PolicyEvaluationError(
                "INVALID_USER_INSTALL",
                "user_install_id does not match Vault policy identity",
            )
        current_fields = policy.get("fields")
        if current_fields is None:
            current_fields = {}
        if not isinstance(current_fields, dict):
            raise PolicyEvaluationError(
                "MALFORMED_POLICY",
                "fields must be an object",
            )
        merged = dict(current_fields)
        merged.update(patch)
        policy["fields"] = merged
        _atomic_write_json(policy_path, policy)
        return demo_privacy_fields(policy)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".user_policy.",
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


def evaluation_to_ws_payload(
        *,
        policy_request_id: str,
        result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "type": "policy_evaluation_response",
        "ok": True,
        "policy_request_id": policy_request_id,
        "action_type": result["actionType"],
        "decision": result["decision"],
        "agent_allowed": result["agentAllowed"],
        "vault_required": result["vaultRequired"],
        "user_approval_required": result["userApprovalRequired"],
    }


def error_to_ws_payload(
        *,
        policy_request_id: str,
        error: PolicyEvaluationError,
) -> dict[str, Any]:
    return {
        "type": "policy_evaluation_response",
        "ok": False,
        "policy_request_id": policy_request_id,
        "error_code": error.code,
        "error": error.message,
    }
