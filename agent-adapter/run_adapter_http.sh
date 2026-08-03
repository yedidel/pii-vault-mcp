#!/usr/bin/env bash
# Start Adapter for Gemini CLI (MCP over HTTP) + Bridge webhook on the same process.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/app"

export MCP_TRANSPORT=http
export ADAPTER_HOST="${ADAPTER_HOST:-0.0.0.0}"
export ADAPTER_PORT="${ADAPTER_PORT:-8000}"
export CONNECTOR_TYPE="${CONNECTOR_TYPE:-WEBHOOK}"
export CONNECTOR_CONTEXT="${CONNECTOR_CONTEXT:-http://localhost:8000/webhook/bridge}"
export GEMINI_MODEL="${GEMINI_MODEL:-gemini-3.6-flash}"

if [[ \
  -z "${GEMINI_API_KEY:-}" && \
  -z "${GOOGLE_API_KEY:-}" && \
  -z "${OPENAI_API_KEY:-}" \
]]; then
  echo "Set one of the following before starting the Adapter:" >&2
  echo "  GEMINI_API_KEY or GOOGLE_API_KEY" >&2
  echo "  OPENAI_API_KEY" >&2
  exit 1
fi

echo "MCP:          http://127.0.0.1:${ADAPTER_PORT}/mcp" >&2
echo "Webhook:      http://127.0.0.1:${ADAPTER_PORT}/webhook/bridge" >&2
echo "Continuation: http://127.0.0.1:${ADAPTER_PORT}/continuation/<session-id>" >&2
echo "Register:     http://127.0.0.1:${ADAPTER_PORT}/continuation/register" >&2
echo "Connector: ${CONNECTOR_TYPE} -> ${CONNECTOR_CONTEXT}" >&2

exec ../.venv/bin/python adapter.py

