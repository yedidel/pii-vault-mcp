"""
Re-export shared Adapter SSE subscriber.

Source of truth: agent-adapter/shared_client/bridge_events.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SHARED_FILE = (
    Path(__file__).resolve().parent.parent / "shared_client" / "bridge_events.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "shared_client_bridge_events",
    _SHARED_FILE,
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot load shared bridge_events from {_SHARED_FILE}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

subscribe_client_events = _MODULE.subscribe_client_events

__all__ = ["subscribe_client_events"]
