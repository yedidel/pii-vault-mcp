from __future__ import annotations

from fill_form_enforcement import (
    KNOWN_POLICY_DECISIONS,
    apply_live_fill_form_policy,
    fill_form_policy_field_names,
)

SUPPORTED_SEND_ACTION_TYPES = frozenset({"FILL_FORM", "PAYMENT", "TRANSACTION"})


class ActionPolicyError(Exception):
    pass


def policy_field_names_for_action(
        action_type: str,
        params: dict[str, str],
) -> list[str]:
    if action_type == "FILL_FORM":
        return fill_form_policy_field_names(params)
    return []


def enforce_send_action_policy(
        *,
        evaluate_fn,
        agent_id: str,
        user_install_id: str,
        action_type: str,
        params: dict[str, str],
) -> dict[str, str]:
    """
    Live Vault policy gate. Calls EvaluatePolicy once, then enforces.

    USER_APPROVAL permits the existing Bridge/Guardian/Vault workflow.
    It does not reject at the Adapter and does not add a second prompt.
    """
    try:
        evaluation = evaluate_fn(
            agent_id=agent_id,
            user_install_id=user_install_id,
            action_type=action_type,
            field_names=policy_field_names_for_action(action_type, params),
        )
    except ActionPolicyError:
        raise
    except Exception as error:
        raise ActionPolicyError(
            "Privacy policy evaluation failed. "
            f"The action was not sent. {error}"
        ) from error

    _require_known_decision(evaluation)

    if action_type == "FILL_FORM":
        try:
            return apply_live_fill_form_policy(params, evaluation)
        except Exception as error:
            raise ActionPolicyError(str(error)) from error

    return dict(params)


def _require_known_decision(evaluation: dict) -> None:
    if not isinstance(evaluation, dict):
        raise ActionPolicyError("Malformed privacy policy response")
    decision = str(evaluation.get("decision") or "").strip().upper()
    if decision not in KNOWN_POLICY_DECISIONS:
        raise ActionPolicyError("Unknown privacy policy decision")
