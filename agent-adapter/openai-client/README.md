# OpenAI Bridge Client

Minimal OpenAI client that mirrors Claude `bridge-wake` and Gemini hooks.

It owns conversation bootstrap. The Adapter only stores `sessionId` and later
wakes via `OpenAIProvider`.

## What each file does

| File | Responsibility |
|---|---|
| `conversation_store.py` | Load/create/persist `conversation.id` under `~/.openai-bridge/conversation.json` |
| `bridge_mcp.py` | Connect to Adapter MCP over Streamable HTTP; map tools to Responses functions; inject `platform=openai` + `sessionId=conversation.id` on `send_action` |
| `bridge_events.py` | Re-export of shared Adapter SSE subscriber (`../shared_client/bridge_events.py`) |
| `conversation_updates.py` | Fetch + format new Conversations API items after a notify |
| `client.py` | Interactive chat loop using Responses API + Conversations API + SSE notify |
| `requirements.txt` | Client-only dependencies |

## Prerequisites

1. Adapter running with HTTP MCP:

```bash
cd agent-adapter/app
export MCP_TRANSPORT=http
export ADAPTER_PORT=8000
export OPENAI_API_KEY=...   # required by OpenAIProvider wake
python adapter.py
```

2. Bridge configured to webhook the Adapter:

```text
POST http://127.0.0.1:8000/webhook/bridge
```

3. Client env:

```bash
cd agent-adapter/openai-client
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=...
# optional:
# export OPENAI_MODEL=gpt-5.6
# export BRIDGE_MCP_URL=http://127.0.0.1:8000/mcp
# export BRIDGE_EVENTS_URL=http://127.0.0.1:8000/events
```

## Run

```bash
python client.py
```

Reset the stored conversation:

```bash
python client.py --reset-conversation
```

## End-to-end flow

```text
User types a prompt
        ↓
client.py → Responses API (conversation=conv_…)
        ↓
GPT decides to call send_action
        ↓
bridge_mcp.py injects:
  platform=openai
  sessionId=conv_…   (never typed by the user)
        ↓
Adapter stores continuationContext=conv_…
        ↓
client also: GET /events?platform=openai&sessionId=conv_…
        ↓
Bridge runs async workflow
        ↓
POST /webhook/bridge
        ↓
WakeDispatcher → OpenAIProvider.wake()
        ↓
responses.create(conversation=conv_…, input="Bridge workflow update…")
        ↓
WakeDispatcher → ClientNotifier.notify(platform, sessionId)
        ↓
SSE event → client fetches new conversation items → prints
```

## Notes

- Uses **Conversations + Responses** only. No Assistants / Threads.
- OpenAI’s hosted remote MCP tool cannot reach `127.0.0.1`, so this client
  uses a **local MCP client** and exposes Adapter tools as Responses
  function tools. Semantically identical for Bridge continuation.
- The user never pastes a conversation id; `conversation_store.py` handles it.
- MCP exposes `parameters: dict[str, str]` as a free-form object schema
  (`additionalProperties` only). Responses function-calling often emits
  `parameters: {}` for that shape. `bridge_mcp.py` enriches the schema with
  explicit keys (`amount`, `currency`, …) and recovers flattened top-level
  keys before calling the Adapter.
- Client notification is session-routed SSE (`platform` + `sessionId`).
  The Adapter never pushes message bodies; the client fetches from OpenAI.
