#!/usr/bin/env python3
"""
Bridge SDK demo: send a PAYMENT and wait for completion.

Requires (running):
  - Docker (PostgreSQL + Kafka)
  - Bridge (gradlew run)
  - Agent Adapter (python adapter.py, MCP_TRANSPORT=http)
  - Install Directory (python install-directory/server.py)
  - Mock Vault (python mock-vault/vault_sim.py)

Install SDK:
  pip install -e ./bridge-sdk

Run:
  python bridge-sdk/examples/payment_demo.py
"""

from __future__ import annotations

import asyncio
import sys

from bridge_sdk import BridgeClient
from bridge_sdk.env import load_adapter_env

load_adapter_env()


async def main() -> int:
    async with BridgeClient() as client:
        print(f"sessionId = {client.session_id}")
        print(f"mcp       = {client.mcp_url}")
        print("Waiting for Vault approval (y/n in Mock Vault terminal)...")

        final = await client.send_payment_and_wait(amount="42", currency="ILS")
        print(f"done status={final.status} resultData={final.result_data or '(empty)'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        print()
        raise SystemExit(130) from None
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
