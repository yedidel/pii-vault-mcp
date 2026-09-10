"""Optional Bearer token for Adapter HTTP endpoints."""

from __future__ import annotations

import os

from bridge_sdk.env import load_adapter_env

AUTH_HEADER = "Authorization"
BEARER_PREFIX = "Bearer "
_env_loaded = False


def get_auth_headers() -> dict[str, str]:
    global _env_loaded
    if not _env_loaded:
        load_adapter_env()
        _env_loaded = True

    token = os.getenv("ADAPTER_AUTH_TOKEN", "").strip()
    if not token:
        return {}
    return {AUTH_HEADER: f"{BEARER_PREFIX}{token}"}
