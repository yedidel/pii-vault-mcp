import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import websockets
import base64
from pathlib import Path

from policy_eval import (
    DEFAULT_POLICY_PATH,
    PolicyEvaluationError,
    error_to_ws_payload,
    evaluate_policy,
    evaluation_to_ws_payload,
)
from policy_http import HOST as PRIVACY_HOST, PORT as PRIVACY_PORT, start_policy_http_server
from vault_field_values import (
    DEFAULT_VALUES_PATH,
    MissingVaultValueError,
    get_field_value,
)


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
# This Mock Vault simulates the external Vault WebSocket peer.
# Payment payloads from Bridge are Base64-encoded, not encrypted.
#
# Supported request types from Bridge:
#   payment_request   — PAYMENT actions (existing)
#   form_fill_request — FILL_FORM actions (demo HTML registration)

VAULT_DID = "did:ethr:0x19E7E376E7C213B7E7e7e46cc70A5dD086DAff2A"
DEFAULT_FORM_URL = "http://127.0.0.1:9000/register"
VAULT_REF_PREFIX = "vault://pii/"
FIELD_HANDLE_PREFIX = "vault://field/"
ADAPTER_RESOLVE_URL = os.getenv(
    "ADAPTER_VAULT_RESOLVE_URL",
    "http://127.0.0.1:8000/vault/resolve",
).rstrip("/")
ADAPTER_AUTH_TOKEN = os.getenv("ADAPTER_AUTH_TOKEN", "").strip()


def _is_approval_choice(choice: str) -> bool:
    normalized = (choice or "").replace("\r", "").strip().lower()
    return normalized in {"y", "yes"}


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
    approved = _is_approval_choice(choice)
    print(
        "[MOCK-VAULT] Authorization "
        f"{'approved' if approved else 'declined'} "
        f"choice={choice!r}"
    )
    return approved


def _is_field_handle(value: str) -> bool:
    return isinstance(value, str) and value.startswith(FIELD_HANDLE_PREFIX)


def _is_vault_ref(value: str) -> bool:
    return isinstance(value, str) and value.startswith(VAULT_REF_PREFIX)


def _resolve_vault_refs(
        fields: dict,
        adapter_resolve=None,
        values_path=DEFAULT_VALUES_PATH,
) -> dict:
    output = {}
    adapter_refs = []
    for key, value in fields.items():
        text = str(value)
        if _is_field_handle(text):
            field_name = text[len(FIELD_HANDLE_PREFIX):].strip().lower()
            if field_name != str(key).strip().lower():
                raise ValueError(f"Vault field handle mismatch for {key}")
            output[key] = get_field_value(values_path, field_name)
            continue
        if _is_vault_ref(text):
            adapter_refs.append(text)
        output[key] = value

    if not adapter_refs:
        return output

    resolver = adapter_resolve or _adapter_resolve_refs
    resolved = resolver(adapter_refs)
    for key, value in list(output.items()):
        text = str(value)
        if _is_vault_ref(text) and not _is_field_handle(text):
            output[key] = resolved.get(text, value)

    for key, value in output.items():
        if _is_field_handle(str(value)) or _is_vault_ref(str(value)):
            raise ValueError(f"Unresolved vault ref for field {key}")

    return output


def _adapter_resolve_refs(refs: list[str]) -> dict:
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
    return resolved


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
        f"{key}=vault-handle" if _is_field_handle(str(value))
        else f"{key}=vault-ref" if _is_vault_ref(str(value))
        else f"{key}={value!r}"
        for key, value in fields.items()
        if key != "password"
    )
    password_value = fields.get("password")
    if password_value:
        if _is_field_handle(str(password_value)):
            field_summary += ", password=vault-handle"
        elif _is_vault_ref(str(password_value)):
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
    except MissingVaultValueError as error:
        return False, str(error)
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
    encoded_blob = data.get("data")
    decoded_bytes = base64.b64decode(encoded_blob)
    decoded_text = decoded_bytes.decode("utf-8")
    return await get_user_approval(f"Payment request\n  data: {decoded_text}")


async def run_vault():
    uri = "ws://localhost:8081/vault-websocket"
    print(f"--- Mock Vault Online | DID: {VAULT_DID} ---")
    print(f"--- Demo form URL: {DEFAULT_FORM_URL} ---")
    http_server = start_policy_http_server()
    print(
        f"--- Privacy preferences: http://{PRIVACY_HOST}:{PRIVACY_PORT}/privacy ---"
    )

    try:
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

                if request_type == "policy_evaluation_request":
                    policy_request_id = str(data.get("policy_request_id") or "").strip()
                    field_names = data.get("field_names") or []
                    if not isinstance(field_names, list):
                        field_names = []
                    try:
                        result = evaluate_policy(
                            policy_path=DEFAULT_POLICY_PATH,
                            user_install_id=str(data.get("user_install_id") or ""),
                            action_type=str(data.get("action_type") or ""),
                            field_names=[str(name) for name in field_names],
                        )
                        response = evaluation_to_ws_payload(
                            policy_request_id=policy_request_id,
                            result=result,
                        )
                    except PolicyEvaluationError as error:
                        response = error_to_ws_payload(
                            policy_request_id=policy_request_id,
                            error=error,
                        )
                    await websocket.send(json.dumps(response))
                    print(
                        f"[MOCK-VAULT] Policy eval id={policy_request_id} "
                        f"ok={response.get('ok')} "
                        f"decision={response.get('decision') or response.get('error_code')}"
                    )
                    continue

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
                    print(
                        f"Payment response for {req_id} sent "
                        f"type={response['type']} status={response['status']}"
                    )
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
    finally:
        http_server.shutdown()


if __name__ == "__main__":
    asyncio.run(run_vault())
