"""Typed result objects returned by the SDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ActionType:
    """Supported Bridge action types (same as Adapter MCP send_action)."""

    PAYMENT = "PAYMENT"
    FILL_FORM = "FILL_FORM"
    TRANSACTION = "TRANSACTION"


DEFAULT_DEMO_FORM_URL = "http://127.0.0.1:9000/register"


TERMINAL_STATUSES = frozenset({
    "COMPLETED",
    "REJECTED",
    "FAILED",
    "FAILED_APP_NOT_INSTALLED",
    "UNTRUSTED",
})

IN_PROGRESS_STATUSES = frozenset({
    "RECEIVED",
    "IN_PROGRESS",
})


@dataclass(frozen=True)
class ActionResult:
    request_id: str
    workflow_id: str
    status: str
    description: str = ""
    raw: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActionResult":
        return cls(
            request_id=str(payload.get("requestId") or "").strip(),
            workflow_id=str(payload.get("workflowId") or "").strip(),
            status=str(payload.get("status") or "").strip(),
            description=str(payload.get("description") or "").strip(),
            raw=payload,
        )

    @property
    def is_terminal(self) -> bool:
        return self.status.upper() in TERMINAL_STATUSES


@dataclass(frozen=True)
class ActionStatus:
    request_id: str
    status: str
    result_data: str = ""
    raw: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActionStatus":
        return cls(
            request_id=str(payload.get("requestId") or "").strip(),
            status=str(payload.get("status") or "").strip(),
            result_data=str(payload.get("resultData") or "").strip(),
            raw=payload,
        )

    @property
    def is_terminal(self) -> bool:
        return self.status.upper() in TERMINAL_STATUSES
