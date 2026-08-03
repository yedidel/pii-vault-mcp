#!/usr/bin/env bash
# Run the Claude Code channel MCP server.
# Claude Code should spawn this via .mcp.json; this script is for local smoke tests.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

export CHANNEL_PORT="${CHANNEL_PORT:-8788}"

exec node --experimental-strip-types "$ROOT/server.ts"
