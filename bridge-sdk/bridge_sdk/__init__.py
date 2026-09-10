"""Python SDK for The Bridge (via Agent Adapter MCP)."""

from bridge_sdk.client import BridgeClient
from bridge_sdk.exceptions import BridgeError, BridgeTimeoutError, PairingRequiredError
from bridge_sdk.models import ActionResult, ActionStatus, ActionType

__all__ = [
    "BridgeClient",
    "BridgeError",
    "PairingRequiredError",
    "BridgeTimeoutError",
    "ActionResult",
    "ActionStatus",
    "ActionType",
]

__version__ = "0.1.0"
