#!/usr/bin/env bash
# TIDOS GPTID control script (Linux/macOS). Mirrors scripts/gptid.ps1.
# Usage: ./scripts/gptid.sh status|start|test|stop|reset|ask|review|audit [--port N] ...
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Kill switch (~/.tidos/control.json, /TIDOSZIT): status/stop always allowed
case "${1:-status}" in
  status|stop) ;;
  *) rc=0; python3 -I "$ROOT/tidos_brain/control.py" get gptid >/dev/null || rc=$?
     if [ "$rc" -eq 1 ]; then echo "GPTID is switched OFF in the TIDOS control center (/TIDOSZIT)." >&2; exit 1; fi ;;
esac
python3 "$ROOT/browser_relay/gptid_cli.py" "$@"
