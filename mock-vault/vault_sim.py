import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import websockets
import base64
from pathlib import Path


def _load_adapter_env() -> None:
    env_file = Path(__file__).resolve().parent.parent / "agent-adapter" / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key != "ADAPTER_AUTH_TOKEN" or os.getenv(key):
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


_load_adapter_env()


# --- Professional Documentation ---
# This Mock Vault simulates the external security API.
# It handles "Encrypted" payloads by decoding Base64 data,
# simulating the decryption process that the real Vault would perform.
#
# Supported request types from Bridge:
#   payment_request   — PAYMENT actions (existing)
#   form_fill_request — FILL_FORM actions (demo HTML registration)

VAULT_DID = "did:ethr:0x19E7E376E7C213B7E7e7e46cc70A5dD086DAff2A"
DEFAULT_FORM_URL = "http://127.0.0.1:9000/register"
VAULT_REF_PREFIX = "vault://pii/"
ADAPTER_RESOLVE_URL = os.getenv(
    "ADAPTER_VAULT_RESOLVE_URL",
    "http://127.0.0.1:8000/vault/resolve",
).rstrip("/")
ADAPTER_AUTH_TOKEN = os.getenv("ADAPTER_AUTH_TOKEN", "").strip()


async def get_user_approval(prompt: str) -> bool:
    """
    Simulates user interaction.
    In a real scenario, the user would see the decrypted details on their device.
    """
    loop = asyncio.get_event_loop()
    print(f"\n[MOCK-VAULT] {prompt}")
    choice = await loop.run_in_executor(
        None,
        lambda: input("Authorize this action? (y/n): ")
    )
    return choice.lower() == "y"


def _is_vault_ref(value: str) -> bool:
    return isinstance(value, str) and value.startswith(VAULT_REF_PREFIX)


def _resolve_vault_refs(fields: dict) -> dict:
    refs = [
        str(value)
        for value in fields.values()
        if _is_vault_ref(str(value))
    ]
    if not refs:
        return dict(fields)

    headers = {"Content-Type": "application/json"}
    if ADAPTER_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {ADAPTER_AUTH_TOKEN}"

    body = json.dumps({"refs": refs}).encode("utf-8")
    request = urllib.request.Request(
        ADAPTER_RESOLVE_URL,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Adapter resolve failed HTTP {error.code}: {detail}"
        ) from error

    resolved = payload.get("resolved") or {}
    if not isinstance(resolved, dict):
        raise ValueError("Adapter resolve response missing resolved map")

    output = {}
    for key, value in fields.items():
        text = str(value)
        output[key] = resolved.get(text, value)

    for key, value in output.items():
        if _is_vault_ref(str(value)):
            raise ValueError(f"Unresolved vault ref for field {key}")

    return output


def _register_api_url(form_url: str) -> str:
    parsed = urllib.parse.urlparse(form_url.strip() or DEFAULT_FORM_URL)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid form_url: {form_url!r}")
    return f"{parsed.scheme}://{parsed.netloc}/api/register"


def _submit_registration(form_url: str, fields: dict) -> dict:
    api_url = _register_api_url(form_url)
    payload = {
        "name": str(fields.get("name") or "").strip(),
        "email": str(fields.get("email") or "").strip(),
        "password": str(fields.get("password") or ""),
        "source": "mock-vault",
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        api_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


async def handle_form_fill_request(data: dict) -> tuple[bool, str]:
    req_id = data.get("request_id")
    form_url = str(data.get("form_url") or DEFAULT_FORM_URL).strip()
    fields = data.get("fields") or {}
    if not isinstance(fields, dict):
        fields = {}

    field_summary = ", ".join(
        f"{key}=vault-ref" if _is_vault_ref(str(value)) else f"{key}={value!r}"
        for key, value in fields.items()
        if key != "password"
    )
    password_value = fields.get("password")
    if password_value:
        if _is_vault_ref(str(password_value)):
            field_summary += ", password=vault-ref"
        else:
            field_summary += ", password=***"

    approved = await get_user_approval(
        f"Form fill request {req_id}\n"
        f"  form_url: {form_url}\n"
        f"  fields: {field_summary or '(empty)'}"
    )
    if not approved:
        return False, "User declined form fill"

    try:
        resolved_fields = await asyncio.to_thread(_resolve_vault_refs, fields)
        print(f"[MOCK-VAULT] Resolved fields for {req_id}")
        result = await asyncio.to_thread(_submit_registration, form_url, resolved_fields)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        return False, f"Demo form HTTP {error.code}: {detail}"
    except Exception as error:
        return False, f"Form fill failed: {error}"

    registration_id = result.get("registrationId", "unknown")
    print(
        f"[MOCK-VAULT] Registered {resolved_fields.get('name')} "
        f"<{resolved_fields.get('email')}> id={registration_id}"
    )
    return True, f"Registration submitted to demo form (id={registration_id})"


async def handle_payment_request(data: dict) -> bool:
    encrypted_blob = data.get("data")
    decrypted_bytes = base64.b64decode(encrypted_blob)
    decrypted_text = decrypted_bytes.decode("utf-8")
    return await get_user_approval(f"Payment request\n  data: {decrypted_text}")


async def run_vault():
    uri = "ws://localhost:8081/vault-websocket"
    print(f"--- Mock Vault Online | DID: {VAULT_DID} ---")
    print(f"--- Demo form URL: {DEFAULT_FORM_URL} ---")

    async with websockets.connect(uri) as websocket:
        handshake = {
            "type": "connection_init",
            "did": VAULT_DID,
            "signature": "mock_handshake_sig",
        }
        await websocket.send(json.dumps(handshake))

        async for message in websocket:
            data = json.loads(message)

            if data.get("type") == "connection_ack":
                print("Connection to Bridge established.")
                continue

            req_id = data.get("request_id")
            request_type = data.get("type")

            if request_type == "payment_request":
                approved = await handle_payment_request(data)
                response = {
                    "type": "action_approved" if approved else "action_rejected",
                    "request_id": req_id,
                    "status": "SUCCESS" if approved else "USER_DECLINED",
                }
                if approved:
                    response["result_data"] = "Payment approved by user"
                else:
                    response["reason"] = "User declined payment"
                await websocket.send(json.dumps(response))
                print(f"Payment response for {req_id} sent.")
                continue

            if request_type == "form_fill_request":
                approved, message = await handle_form_fill_request(data)
                response = {
                    "type": "action_approved" if approved else "action_rejected",
                    "request_id": req_id,
                    "status": "SUCCESS" if approved else "USER_DECLINED",
                }
                if approved:
                    response["result_data"] = message
                else:
                    response["reason"] = message
                await websocket.send(json.dumps(response))
                status = "OK" if approved else "FAILED"
                print(f"[MOCK-VAULT] Form fill {status} for {req_id}: {message}")
                continue

            print(f"Unknown Vault message type: {request_type!r}")


if __name__ == "__main__":
    asyncio.run(run_vault())
