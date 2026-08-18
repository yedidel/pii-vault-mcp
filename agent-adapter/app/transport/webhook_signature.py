import hashlib
import hmac
import os

HEADER_NAME = "X-Webhook-Signature"
PREFIX = "sha256="


def verify_webhook_signature(raw_body: bytes, header_value: str | None) -> tuple[bool, str | None]:
    """
    Verifies HMAC-SHA256 signature against the configured WEBHOOK_SECRET.
    Returns (is_valid, error_message).
    """
    secret = os.getenv("WEBHOOK_SECRET", "").strip()

    # Allow requests if secret is not set (development fallback)
    if not secret:
        return True, None

    if not header_value:
        return False, f"Missing required header {HEADER_NAME}"

    if not header_value.startswith(PREFIX):
        return False, f"Invalid signature format, expected prefix '{PREFIX}'"

    expected_signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    provided_signature = header_value[len(PREFIX):].strip()

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(expected_signature, provided_signature):
        return False, "Signature verification failed"

    return True, None