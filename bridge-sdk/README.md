# bridge-sdk

Python client library for **The Bridge** via the **Agent Adapter MCP** server.

This SDK does **not** call REST endpoints like `/action/send`. It uses the same
interface as Gemini/OpenAI clients:

| What | URL / tool |
|------|------------|
| Send action | MCP tool `send_action` at `{adapter}/mcp` |
| Poll status | MCP tool `get_action_status` |
| Live updates | `POST /sessions/register` + `GET /events` (SSE) |

## Install (local, no publish)

```powershell
cd C:\pii-vault-mcp
pip install -e ./bridge-sdk
```

Optional: load Adapter env vars

```powershell
pip install -e "./bridge-sdk[dev]"
# set BRIDGE_MCP_URL, ADAPTER_AUTH_TOKEN if used
```

## Quick start

```python
import asyncio
from bridge_sdk import BridgeClient, PairingRequiredError

async def main():
    async with BridgeClient() as client:
        try:
            result = await client.send_payment(amount="100", currency="ILS")
        except PairingRequiredError as e:
            print("Open:", e.qr_url)
            result = await client.wait_for_pairing_and_retry(
                lambda: client.send_payment(amount="100", currency="ILS"),
            )

        status = await client.wait_for_completion(result.request_id)
        print(status.status)

asyncio.run(main())
```

Run the included demo (full stack must be running):

```powershell
python bridge-sdk/examples/payment_demo.py
```

## Architecture

```
Your script / app
       │
       ▼
  BridgeClient  (bridge-sdk)
       │  MCP Streamable HTTP
       ▼
  Agent Adapter  :8000/mcp
       │  gRPC
       ▼
  Bridge Server  :50051
       │
       ▼
  Mock Vault (y/n)
```

### Why `platform=sdk`?

Each `send_action` includes `platform` + `sessionId`. The Adapter uses them for
workflow wake + SSE routing. SDK uses `platform="sdk"` and a generated
`sessionId` like `sdk-<uuid>`.

A small **SdkProvider** (noop wake) was added to the Adapter so SSE notifications
work for SDK sessions without calling an LLM.

## API reference

### `BridgeClient`

| Method | Description |
|--------|-------------|
| `send_action(...)` | Generic action (PAYMENT, FILL_FORM, …) |
| `send_payment(amount, currency)` | PAYMENT helper |
| `get_action_status(request_id)` | One status read (Adapter may poll Bridge briefly) |
| `wait_for_completion(request_id)` | Poll until terminal status |
| `wait_for_completion(..., use_sse=True)` | Wait via SSE instead of polling |
| `send_payment_and_wait(...)` | Send + wait in one call |
| `wait_for_pairing_and_retry(callable)` | Retry after QR pairing |

### Exceptions

| Exception | When |
|-----------|------|
| `PairingRequiredError` | Vault not paired; `.qr_url` has the link |
| `BridgeTimeoutError` | Timeout waiting for completion or pairing |
| `BridgeError` | Other Adapter/Bridge errors |

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `BRIDGE_MCP_URL` | `http://127.0.0.1:8000/mcp` | Adapter MCP endpoint |
| `BRIDGE_EVENTS_URL` | derived from MCP URL | Override SSE URL |
| `ADAPTER_AUTH_TOKEN` | (empty) | Bearer token if Adapter auth enabled |
| `BRIDGE_AGENT_ID` | `agent-123` | Default `agentId` |

## What this SDK does **not** replace

- **AI agents** (Gemini/OpenAI/Claude) still use MCP via their own clients or Cursor `.mcp.json`.
- **Direct gRPC** to Bridge is still available via `bridge.proto` for Kotlin/Java services.

## Files

```
bridge-sdk/
  pyproject.toml          # pip install -e .
  bridge_sdk/
    client.py             # BridgeClient (main API)
    mcp_client.py         # MCP transport
    events.py             # SSE + session register
    models.py             # ActionResult, ActionStatus
    exceptions.py
  examples/
    payment_demo.py
```
