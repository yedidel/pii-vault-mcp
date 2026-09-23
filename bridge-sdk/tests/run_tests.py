#!/usr/bin/env python3
"""
Bridge SDK test runner — offline unit tests + optional live integration tests.

Usage:
  python bridge-sdk/tests/run_tests.py           # all (skip live if stack down)
  python bridge-sdk/tests/run_tests.py --live    # fail if stack not running
  python bridge-sdk/tests/run_tests.py --offline-only
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import tempfile
import uuid
from pathlib import Path

# repo root on path for install-directory import
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "install-directory"))

from bridge_sdk.env import load_adapter_env
from bridge_sdk.exceptions import PairingRequiredError
from bridge_sdk.models import ActionResult, ActionStatus, TERMINAL_STATUSES


class TestResult:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors: list[str] = []

    def ok(self, name: str) -> None:
        self.passed += 1
        print(f"  PASS  {name}")

    def fail(self, name: str, detail: str) -> None:
        self.failed += 1
        self.errors.append(f"{name}: {detail}")
        print(f"  FAIL  {name} — {detail}")

    def skip(self, name: str, reason: str) -> None:
        self.skipped += 1
        print(f"  SKIP  {name} — {reason}")


def test_models(results: TestResult) -> None:
    r = ActionResult.from_dict({
        "requestId": "req-1",
        "workflowId": "wf-1",
        "status": "RECEIVED",
    })
    if r.request_id == "req-1" and not r.is_terminal:
        results.ok("ActionResult parsing")
    else:
        results.fail("ActionResult parsing", repr(r))

    s = ActionStatus.from_dict({"requestId": "req-1", "status": "COMPLETED"})
    if s.is_terminal and "COMPLETED" in TERMINAL_STATUSES:
        results.ok("ActionStatus terminal detection")
    else:
        results.fail("ActionStatus terminal detection", repr(s))


def test_directory_store(results: TestResult) -> None:
    from directory_store import DirectoryStore

    tmp = Path(tempfile.mkdtemp())
    db_path = tmp / "test.sqlite3"
    try:
        store = DirectoryStore(db_path)
        session = store.start_pairing()
        if not session.pairing_code:
            results.fail("DirectoryStore.start_pairing", "empty code")
            return
        record = store.complete_pairing(
            session.pairing_code,
            vault_service_url="ws://127.0.0.1:8081/vault-websocket",
        )
        if not record.user_install_id.startswith("install_"):
            results.fail("DirectoryStore.complete_pairing", record.user_install_id)
            return
        fetched = store.get_install(record.user_install_id)
        if fetched and fetched.status == "ACTIVE":
            results.ok("DirectoryStore pairing lifecycle")
        else:
            results.fail("DirectoryStore pairing lifecycle", "install not active")

        again = store.complete_pairing(
            session.pairing_code,
            vault_service_url="ws://127.0.0.1:8081/vault-websocket",
        )
        if again.user_install_id == record.user_install_id:
            results.ok("DirectoryStore idempotent complete_pairing")
        else:
            results.fail("DirectoryStore idempotent complete_pairing", "different id")
        del store
    finally:
        try:
            db_path.unlink(missing_ok=True)
            tmp.rmdir()
        except OSError:
            pass


def test_env_loader(results: TestResult) -> None:
    path = load_adapter_env()
    if path and path.is_file():
        results.ok(f"load_adapter_env found {path.name}")
    else:
        results.skip("load_adapter_env", "agent-adapter/.env not found")


async def _http_ok(url: str) -> bool:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(url)
            return r.status_code == 200
    except Exception:
        return False


async def stack_health(results: TestResult) -> bool:
    checks = {
        "Adapter root": "http://127.0.0.1:8000/",
        "Install Directory /health": "http://127.0.0.1:8010/health",
    }
    all_ok = True
    for name, url in checks.items():
        if await _http_ok(url):
            results.ok(name)
        else:
            all_ok = False
            results.fail(name, f"no response from {url}")
    return all_ok


async def test_sdk_connect(results: TestResult) -> None:
    from bridge_sdk import BridgeClient

    try:
        async with BridgeClient(session_id=f"sdk-test-{uuid.uuid4().hex}") as client:
            if client._transport is not None:
                results.ok("BridgeClient MCP connect + register")
            else:
                results.fail("BridgeClient MCP connect", "no transport")
    except Exception as error:
        results.fail("BridgeClient MCP connect", str(error))


async def test_payment_missing_params(results: TestResult) -> None:
    from bridge_sdk import BridgeClient, BridgeError

    try:
        async with BridgeClient(session_id=f"sdk-test-{uuid.uuid4().hex}") as client:
            payload = await client._require_transport().call_tool(
                "send_action",
                {
                    "agentId": "agent-123",
                    "actionType": "PAYMENT",
                    "parameters": {},
                },
            )
            if "error" in payload and "amount" in str(payload.get("error", "")).lower():
                results.ok("PAYMENT rejects empty parameters")
            else:
                results.fail("PAYMENT rejects empty parameters", repr(payload))
    except BridgeError as error:
        if "amount" in str(error).lower():
            results.ok("PAYMENT rejects empty parameters")
        else:
            results.fail("PAYMENT rejects empty parameters", str(error))
    except Exception as error:
        results.fail("PAYMENT rejects empty parameters", str(error))


async def test_invalid_request_id_status(results: TestResult) -> None:
    from bridge_sdk import BridgeClient

    try:
        async with BridgeClient(session_id=f"sdk-test-{uuid.uuid4().hex}") as client:
            status = await client.get_action_status("00000000-0000-0000-0000-000000000000")
            # Bridge may return error or unknown status — should not crash SDK
            if status.request_id or status.status or status.raw:
                results.ok("get_action_status unknown id (no crash)")
            else:
                results.fail("get_action_status unknown id", "empty response")
    except Exception as error:
        # gRPC not found is acceptable
        if "not found" in str(error).lower() or "error" in str(error).lower():
            results.ok("get_action_status unknown id (expected error)")
        else:
            results.fail("get_action_status unknown id", str(error))


async def test_pairing_required_shape(results: TestResult) -> None:
    """If vault unpaired, send_action must raise PairingRequiredError with qrUrl."""
    from bridge_sdk import BridgeClient

    # Use fresh session; may still be paired globally — skip if payment succeeds
    try:
        async with BridgeClient(session_id=f"sdk-test-{uuid.uuid4().hex}") as client:
            try:
                await client.send_payment(amount="1", currency="ILS")
                results.skip(
                    "PairingRequiredError shape",
                    "vault already paired on this Adapter",
                )
            except PairingRequiredError as error:
                if error.qr_url and "pair?code=" in error.qr_url:
                    results.ok("PairingRequiredError includes qrUrl")
                else:
                    results.fail("PairingRequiredError shape", repr(error))
    except Exception as error:
        results.fail("PairingRequiredError shape", str(error))


async def run_live_tests(results: TestResult, require_live: bool) -> None:
    load_adapter_env()
    healthy = await stack_health(results)
    if not healthy:
        if require_live:
            results.fail("live stack", "Adapter or Install Directory not running")
        else:
            results.skip("live integration tests", "stack not running")
        return

    await test_sdk_connect(results)
    await test_payment_missing_params(results)
    await test_invalid_request_id_status(results)
    await test_pairing_required_shape(results)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bridge-sdk tests")
    parser.add_argument("--live", action="store_true", help="Require live stack")
    parser.add_argument("--offline-only", action="store_true")
    args = parser.parse_args()

    results = TestResult()
    print("=== Offline tests ===")
    test_models(results)
    test_directory_store(results)
    test_env_loader(results)

    if not args.offline_only:
        print("\n=== Live integration tests ===")
        asyncio.run(run_live_tests(results, require_live=args.live))

    print("\n=== Summary ===")
    print(f"passed={results.passed} failed={results.failed} skipped={results.skipped}")
    if results.errors:
        print("\nFailures:")
        for line in results.errors:
            print(f"  - {line}")

    return 1 if results.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
