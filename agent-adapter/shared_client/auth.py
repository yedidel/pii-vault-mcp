import os

AUTH_HEADER = "Authorization"
BEARER_PREFIX = "Bearer "


def get_auth_headers() -> dict[str, str]:
    token = os.getenv("ADAPTER_AUTH_TOKEN", "").strip()
    if not token:
        return {}
    return {AUTH_HEADER: f"{BEARER_PREFIX}{token}"}