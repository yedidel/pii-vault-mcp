#!/usr/bin/env bash
# Local smoke test for the Claude channel. Claude Code uses launch.sh via .mcp.json.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
export CHANNEL_PORT="${CHANNEL_PORT:-8788}"

exec "$ROOT/launch.sh"
