"""
Re-export shared session registration helper.

Source of truth: agent-adapter/shared_client/session_register.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SHARED_FILE = (
    Path(__file__).resolve().parent.parent
    / "shared_client"
    / "session_register.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "shared_client_session_register",
    _SHARED_FILE,
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot load shared session_register from {_SHARED_FILE}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

adapter_base_from_mcp_url = _MODULE.adapter_base_from_mcp_url
register_bridge_session = _MODULE.register_bridge_session

__all__ = ["adapter_base_from_mcp_url", "register_bridge_session"]
