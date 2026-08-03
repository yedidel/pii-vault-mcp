#!/usr/bin/env bash
# Minimal proof: Gemini CLI BeforeTool rewrites send_action.sessionId to HOOK_TEST.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOKS_DIR="$ROOT/agent-adapter/gemini-bridge-hooks"
VENV_PY="$ROOT/agent-adapter/.venv/bin/python"
LOG_HOOK="$HOOKS_DIR/.poc-hook.log"
LOG_SEND="$HOOKS_DIR/.poc-send-action.log"
LOG_MCP="$HOOKS_DIR/.poc-mcp-server.log"
LOG_GEMINI_OUT="$HOOKS_DIR/.poc-gemini-out.log"
LOG_GEMINI_ERR="$HOOKS_DIR/.poc-gemini-err.log"
POC_PORT="${POC_MCP_PORT:-8010}"

cd "$ROOT"

: > "$LOG_HOOK"
: > "$LOG_SEND"
: > "$LOG_MCP"
: > "$LOG_GEMINI_OUT"
: > "$LOG_GEMINI_ERR"

# Temporary project settings: POC MCP on 8010 + rewrite hook only.
mkdir -p .gemini
cat > .gemini/settings.json <<EOF
{
  "mcpServers": {
    "bridge-adapter": {
      "httpUrl": "http://127.0.0.1:${POC_PORT}/mcp"
    }
  },
  "hooks": {
    "BeforeTool": [
      {
        "matcher": "mcp_bridge-adapter_send_action",
        "hooks": [
          {
            "name": "poc-rewrite-sessionId",
            "type": "command",
            "command": "node \"\$GEMINI_PROJECT_DIR/agent-adapter/gemini-bridge-hooks/scripts/poc-before-send-action.js\"",
            "description": "POC: force sessionId=HOOK_TEST before send_action."
          }
        ]
      }
    ]
  }
}
EOF

cleanup() {
  if [[ -n "${MCP_PID:-}" ]]; then
    kill "$MCP_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "Starting POC MCP on :${POC_PORT} ..."
POC_SEND_ACTION_LOG="$LOG_SEND" \
POC_MCP_PORT="$POC_PORT" \
PYTHONPATH="$ROOT/agent-adapter/app" \
"$VENV_PY" -u "$HOOKS_DIR/scripts/poc-mcp-server.py" > "$LOG_MCP" 2>&1 &
MCP_PID=$!

# Cold imports can take several seconds before the port listens.
ready=0
for _ in $(seq 1 30); do
  if ! kill -0 "$MCP_PID" 2>/dev/null; then
    break
  fi
  if lsof -nP -iTCP:"$POC_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done

if [[ "$ready" -ne 1 ]]; then
  echo "POC MCP failed to start. See $LOG_MCP" >&2
  exit 1
fi

echo "Running Gemini CLI headless (yolo) ..."
HOOK_POC_LOG="$LOG_HOOK" \
gemini -y -o json \
  -m "${POC_GEMINI_MODEL:-gemini-1.5-flash}" \
  -p 'Call the send_action tool exactly once with: agentId="poc-agent", actionType="PAYMENT", parameters={"amount":"1"}, platform="gemini", sessionId="ORIGINAL". Then print the tool result JSON, especially pocReceivedSessionId.' \
  > "$LOG_GEMINI_OUT" 2> "$LOG_GEMINI_ERR" || true

echo
echo "======== HOOK LOG ========"
cat "$LOG_HOOK" || true
echo
echo "======== SEND_ACTION LOG ========"
cat "$LOG_SEND" || true
echo
echo "======== GEMINI OUT (tail) ========"
tail -n 60 "$LOG_GEMINI_OUT" || true
echo
echo "======== GEMINI ERR (tail) ========"
tail -n 40 "$LOG_GEMINI_ERR" || true
echo

if rg -q 'sessionId=.HOOK_TEST.' "$LOG_SEND" \
  || rg -q '"pocReceivedSessionId"\s*:\s*"HOOK_TEST"' "$LOG_GEMINI_OUT" \
  || rg -q 'rewriting sessionId' "$LOG_HOOK"; then
  if rg -q 'sessionId=.HOOK_TEST.' "$LOG_SEND" \
    || rg -q '"pocReceivedSessionId"\s*:\s*"HOOK_TEST"' "$LOG_GEMINI_OUT"; then
    echo "RESULT: PASS — Adapter/POC MCP received sessionId=HOOK_TEST"
    exit 0
  fi
  echo "RESULT: PARTIAL — hook ran, but MCP did not log HOOK_TEST. Inspect logs above."
  exit 2
fi

echo "RESULT: FAIL — no rewrite evidence. Inspect logs above."
exit 1
