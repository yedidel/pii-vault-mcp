import hmac
import os
from starlette.requests import Request

AUTH_HEADER = "Authorization"
BEARER_PREFIX = "Bearer "


def adapter_auth_token() -> str | None:
    value = os.getenv("ADAPTER_AUTH_TOKEN", "").strip()
    return value or None


def verify_adapter_auth(request: Request) -> tuple[bool, str | None]:
    expected = adapter_auth_token()
    if expected is None:
        # Backward compatibility: authentication disabled if env is not set
        return True, None

    header = request.headers.get(AUTH_HEADER)
    if not header or not header.startswith(BEARER_PREFIX):
        return False, "Missing or invalid Authorization header"

    provided = header[len(BEARER_PREFIX):].strip()
    if not hmac.compare_digest(provided, expected):
        return False, "Invalid adapter auth token"

    return True, None


def is_public_adapter_path(path: str, method: str) -> bool:
    if path == "/":
        return True
    if path == "/webhook/bridge" and method.upper() == "POST":
        return True
    return False