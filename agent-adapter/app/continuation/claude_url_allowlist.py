import os
import re
from urllib.parse import urlparse

_LOCAL_HOSTS = {"127.0.0.1", "localhost"}
_SESSION_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def adapter_public_base() -> str:
    port = os.getenv("ADAPTER_PORT", "8000")
    return os.getenv(
        "ADAPTER_PUBLIC_BASE",
        f"http://127.0.0.1:{port}",
    ).rstrip("/")


def is_allowed_claude_wake_url(url: str) -> bool:
    raw = (url or "").strip().rstrip("/")
    if not raw:
        return False

    try:
        parsed = urlparse(raw)
    except Exception:
        return False

    if parsed.scheme != "http":
        return False
    if parsed.hostname not in _LOCAL_HOSTS:
        return False

    path = (parsed.path or "").rstrip("/")

    if path.endswith("/wake"):
        return True

    if not path.startswith("/continuation/"):
        return False

    session_id = path.removeprefix("/continuation/").strip("/")
    if not session_id or "/" in session_id:
        return False
    if not _SESSION_ID_RE.match(session_id):
        return False

    base = urlparse(adapter_public_base())
    if parsed.hostname != base.hostname:
        return False
    if parsed.port != base.port:
        return False

    return True