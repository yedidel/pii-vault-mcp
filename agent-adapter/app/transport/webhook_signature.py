import hashlib
import hmac
import os
import threading
import time

HEADER_NAME = "X-Webhook-Signature"
HEADER_TIMESTAMP = "X-Webhook-Timestamp"
HEADER_NONCE = "X-Webhook-Nonce"
PREFIX = "sha256="

_DEFAULT_MAX_AGE_SECONDS = 300
_DEFAULT_CLOCK_SKEW_SECONDS = 60

_lock = threading.Lock()
_seen_nonces: dict[str, float] = {}


def _replay_max_age_seconds() -> int:
    raw = os.getenv("WEBHOOK_REPLAY_MAX_AGE_SECONDS", "").strip()
    if not raw:
        return _DEFAULT_MAX_AGE_SECONDS
    try:
        value = int(raw)
    except ValueError:
        return _DEFAULT_MAX_AGE_SECONDS
    return max(1, value)


def _clock_skew_seconds() -> int:
    raw = os.getenv("WEBHOOK_REPLAY_CLOCK_SKEW_SECONDS", "").strip()
    if not raw:
        return _DEFAULT_CLOCK_SKEW_SECONDS
    try:
        value = int(raw)
    except ValueError:
        return _DEFAULT_CLOCK_SKEW_SECONDS
    return max(0, value)


def _signature_payload(timestamp: str, nonce: str, raw_body: bytes) -> bytes:
    prefix = f"{timestamp}.{nonce}.".encode("utf-8")
    return prefix + raw_body


def _purge_expired_nonces(now: float, ttl: float) -> None:
    expired = [nonce for nonce, seen_at in _seen_nonces.items() if now - seen_at > ttl]
    for nonce in expired:
        _seen_nonces.pop(nonce, None)


def _register_nonce(nonce: str, now: float, ttl: float) -> bool:
    """
    Returns True if nonce is new, False if it was already seen (replay).
    """
    with _lock:
        _purge_expired_nonces(now, ttl)
        if nonce in _seen_nonces:
            return False
        _seen_nonces[nonce] = now
        return True


def verify_webhook_signature(
    raw_body: bytes,
    header_value: str | None,
    timestamp_header: str | None = None,
    nonce_header: str | None = None,
) -> tuple[bool, str | None]:
    """
    Verifies HMAC-SHA256 over "{timestamp}.{nonce}.{body}" and replay guards.
    Returns (is_valid, error_message).
    """
    secret = os.getenv("WEBHOOK_SECRET", "").strip()

    if not secret:
        return False, "WEBHOOK_SECRET is not configured"

    if not header_value:
        return False, f"Missing required header {HEADER_NAME}"
    if not timestamp_header:
        return False, f"Missing required header {HEADER_TIMESTAMP}"
    if not nonce_header:
        return False, f"Missing required header {HEADER_NONCE}"

    if not header_value.startswith(PREFIX):
        return False, f"Invalid signature format, expected prefix '{PREFIX}'"

    timestamp_text = timestamp_header.strip()
    nonce = nonce_header.strip()
    if not timestamp_text or not nonce:
        return False, "Webhook timestamp and nonce must be non-empty"

    try:
        timestamp = int(timestamp_text)
    except ValueError:
        return False, "Invalid webhook timestamp"

    now = int(time.time())
    max_age = _replay_max_age_seconds()
    skew = _clock_skew_seconds()
    age = now - timestamp
    if age > max_age:
        return False, "Webhook timestamp is too old"
    if age < -skew:
        return False, "Webhook timestamp is too far in the future"

    ttl = float(max_age + skew)
    if not _register_nonce(nonce, float(now), ttl):
        return False, "Webhook nonce replay detected"

    expected_signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=_signature_payload(timestamp_text, nonce, raw_body),
        digestmod=hashlib.sha256,
    ).hexdigest()

    provided_signature = header_value[len(PREFIX):].strip()

    if not hmac.compare_digest(expected_signature, provided_signature):
        return False, "Signature verification failed"

    return True, None
