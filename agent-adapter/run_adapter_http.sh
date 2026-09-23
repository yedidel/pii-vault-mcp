#!/usr/bin/env bash
# Start Adapter HTTP MCP + Bridge webhook on the same process.
# Gemini/OpenAI API keys are optional at startup; they are required only
# when a workflow actually wakes those providers.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi
cd "$ROOT/app"

export MCP_TRANSPORT=http
export ADAPTER_HOST="${ADAPTER_HOST:-0.0.0.0}"
export ADAPTER_PORT="${ADAPTER_PORT:-8000}"
export CONNECTOR_TYPE="${CONNECTOR_TYPE:-WEBHOOK}"
export CONNECTOR_CONTEXT="${CONNECTOR_CONTEXT:-http://localhost:8000/webhook/bridge}"
export GEMINI_MODEL="${GEMINI_MODEL:-gemini-3.6-flash}"

echo "MCP:          http://127.0.0.1:${ADAPTER_PORT}/mcp" >&2
echo "Webhook:      http://127.0.0.1:${ADAPTER_PORT}/webhook/bridge" >&2
echo "Continuation: http://127.0.0.1:${ADAPTER_PORT}/continuation/<session-id>" >&2
echo "Register:     http://127.0.0.1:${ADAPTER_PORT}/continuation/register" >&2
echo "Connector: ${CONNECTOR_TYPE} -> ${CONNECTOR_CONTEXT}" >&2

exec ../.venv/bin/python adapter.py

