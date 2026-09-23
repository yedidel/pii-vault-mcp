from __future__ import annotations

CANONICAL_FILL_FORM_FIELDS = ("name", "email", "password")
FILL_FORM_INFRA_KEYS = frozenset({"formurl"})
FIELD_HANDLE_PREFIX = "vault://field/"
PII_REF_PREFIX = "vault://pii/"
KNOWN_POLICY_DECISIONS = frozenset({
    "AGENT_ALLOWED",
    "VAULT_ONLY",
    "USER_APPROVAL",
    "PARTIAL",
})


class FillFormPolicyError(Exception):
    pass


def fill_form_policy_field_names(params: dict[str, str] | None = None) -> list[str]:
    names: list[str] = list(CANONICAL_FILL_FORM_FIELDS)
    for key in params or {}:
        name = str(key).strip()
        if not name:
            continue
        if name.lower() in FILL_FORM_INFRA_KEYS:
            continue
        if name.lower() in {item.lower() for item in names}:
            continue
        names.append(name)
    return names


def field_handle(field_name: str) -> str:
    return f"{FIELD_HANDLE_PREFIX}{str(field_name).strip().lower()}"


def is_field_handle(value: str) -> bool:
    return str(value or "").startswith(FIELD_HANDLE_PREFIX)


def is_pii_ref(value: str) -> bool:
    return str(value or "").startswith(PII_REF_PREFIX)


def apply_live_fill_form_policy(
        params: dict[str, str],
        evaluation: dict,
        store=None,
) -> dict[str, str]:
    names = fill_form_policy_field_names(params)
    if not names:
        raise FillFormPolicyError("FILL_FORM has no privacy-controlled fields")

    if not isinstance(evaluation, dict):
        raise FillFormPolicyError("Malformed privacy policy response")

    decision = str(evaluation.get("decision") or "").strip().upper()
    if decision not in KNOWN_POLICY_DECISIONS:
        raise FillFormPolicyError("Unknown privacy policy decision")

    agent_allowed = [
        str(item).strip()
        for item in (evaluation.get("agentAllowed") or [])
        if str(item).strip()
    ]
    vault_required = [
        str(item).strip()
        for item in (evaluation.get("vaultRequired") or [])
        if str(item).strip()
    ]

    agent_keys = {item.lower() for item in agent_allowed}
    vault_keys = {item.lower() for item in vault_required}
    if agent_keys & vault_keys:
        raise FillFormPolicyError("Inconsistent privacy policy classification")

    requested = {name.lower() for name in names}
    classified = agent_keys | vault_keys
    if requested != classified:
        raise FillFormPolicyError(
            "Privacy policy result does not match requested fields"
        )

    sanitized = dict(params)
    for name in names:
        key = _param_key(sanitized, name)
        raw = str(sanitized.get(key) or "").strip()
        if name.lower() in vault_keys:
            if is_pii_ref(raw):
                sanitized[key] = raw
                continue
            sanitized[key] = field_handle(name)
            continue
        if not raw or is_field_handle(raw):
            raise FillFormPolicyError(
                f"FILL_FORM requires the agent to supply parameters.{name}"
            )
        sanitized[key] = raw
    return sanitized


def _param_key(params: dict[str, str], name: str) -> str:
    wanted = name.lower()
    for key in params:
        if str(key).strip().lower() == wanted:
            return key
    return name
