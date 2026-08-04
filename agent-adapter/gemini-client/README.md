# Gemini Bridge Client

Minimal Gemini client parallel to `openai-client`.

It owns Interaction bootstrap. The Adapter stores `sessionId` and later wakes
via `GeminiProvider`. Client notification uses the shared Adapter SSE layer.

## What each file does

| File | Responsibility |
|---|---|
| `interaction_store.py` | Load/create/persist `interaction.id` under `~/.gemini-bridge/interaction.json` |
| `bridge_mcp.py` | Adapter MCP over Streamable HTTP; inject `platform=gemini` + `sessionId=interaction.id` |
| `bridge_events.py` | Re-export of shared `shared_client/bridge_events.py` SSE subscriber |
| `interaction_updates.py` | Fetch + format a Gemini Interaction after notify |
| `client.py` | Interactive chat + SSE notify + auto-render |
| `requirements.txt` | Client-only dependencies |

## Prerequisites

1. Adapter running with HTTP MCP + `/events`
2. Bridge webhook → `POST http://127.0.0.1:8000/webhook/bridge`
3. Client env:

```bash
cd agent-adapter/gemini-client
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=...   # or GOOGLE_API_KEY
# optional:
# export GEMINI_MODEL=gemini-3.6-flash
# export BRIDGE_MCP_URL=http://127.0.0.1:8000/mcp
# export BRIDGE_EVENTS_URL=http://127.0.0.1:8000/events
```

## Run

```bash
python client.py
```

Reset the stored interaction:

```bash
python client.py --reset-interaction
```

## End-to-end flow

```text
User types a prompt
        ↓
client.py → Interactions API (previous_interaction_id=…)
        ↓
Gemini decides to call send_action
        ↓
bridge_mcp.py injects:
  platform=gemini
  sessionId=interaction_…   (never typed by the user)
        ↓
client also: GET /events?platform=gemini&sessionId=interaction_…
        ↓
Bridge runs async workflow
        ↓
POST /webhook/bridge
        ↓
WakeDispatcher → GeminiProvider.wake()
        ↓
interactions.create(previous_interaction_id=…)
        ↓
WakeDispatcher → ClientNotifier.notify(sessionId=subscribed, resumeSessionId=new)
        ↓
SSE event → client fetches new Interaction → prints → re-subscribes to tip
```

## Notes

- Gemini Interactions **rotate** `interaction.id` on each wake. The Adapter
  routes SSE to the pre-wake session id (`sessionId`) and includes
  `resumeSessionId` for the successor created by `GeminiProvider`.
- After `send_action`, the client **locks SSE** to that injected sessionId
  until the wake arrives. It must not re-subscribe to later chat tips from
  the same tool loop — that was the bug that dropped continuation events.
- On `workflow.updated`, the client fetches `resumeSessionId` only (never
  creates a new Interaction), persists that id, and re-subscribes to it.
- Shared SSE helper lives in `../shared_client/bridge_events.py`.
- The notifier stays platform-agnostic; only this client knows Interactions.
