#!/usr/bin/env bash
# Launch bridge-wake for Claude Code.
# Loads agent-adapter/.env so ADAPTER_AUTH_TOKEN is available, then execs tsx.
# Never print environment values.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
ADAPTER_ROOT="$(cd "$ROOT/.." && pwd)"
ENV_FILE="$ADAPTER_ROOT/.env"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ENV_FILE"
  set +a
fi

cd "$ROOT"

if [[ -x "$ROOT/node_modules/.bin/tsx" ]]; then
  exec "$ROOT/node_modules/.bin/tsx" "$ROOT/server.ts"
fi

exec npx tsx "$ROOT/server.ts"
