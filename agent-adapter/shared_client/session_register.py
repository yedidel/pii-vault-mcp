"""
Register a Bridge client session and obtain an SSE capability token.

Source of truth for Gemini/OpenAI clients.
"""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse

import httpx

import importlib.util
from pathlib import Path

_AUTH_FILE = Path(__file__).resolve().parent / "auth.py"
_AUTH_SPEC = importlib.util.spec_from_file_location(
    "shared_client_auth",
    _AUTH_FILE,
)
if _AUTH_SPEC is None or _AUTH_SPEC.loader is None:
    raise ImportError(f"Cannot load auth from {_AUTH_FILE}")
_AUTH_MOD = importlib.util.module_from_spec(_AUTH_SPEC)
_AUTH_SPEC.loader.exec_module(_AUTH_MOD)
get_auth_headers = _AUTH_MOD.get_auth_headers


def adapter_base_from_mcp_url(mcp_url: str) -> str:
    parsed = urlparse(mcp_url)
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


async def register_bridge_session(
        *,
        adapter_base_url: str,
        platform: str,
        session_id: str,
) -> str:
    """
    POST /sessions/register and return sseToken.

    userInstallId is resolved server-side from vault_config.json.
    """
    base = adapter_base_url.rstrip("/")
    url = f"{base}/sessions/register"
    payload = {
        "platform": platform.strip().lower(),
        "sessionId": session_id.strip(),
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                **get_auth_headers(),
            },
        )
        response.raise_for_status()
        body = response.json()

    token = str(body.get("sseToken") or "").strip()
    if not token:
        raise RuntimeError("Adapter /sessions/register returned no sseToken")
    return token
