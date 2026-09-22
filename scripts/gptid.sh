#!/usr/bin/env bash
# TIDOS GPTID control script (Linux/macOS). Mirrors scripts/gptid.ps1.
# Usage: ./scripts/gptid.sh status|start|test|stop|reset|ask|review|audit [--port N] ...
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$ROOT/browser_relay/gptid_cli.py" "$@"
