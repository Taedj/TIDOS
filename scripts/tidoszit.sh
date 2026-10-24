#!/usr/bin/env bash
# ============================================================================
# TIDOSZIT - open the TIDOS Control Center (Linux/macOS/Git Bash)
# ============================================================================
# Starts the local dashboard server in the background (127.0.0.1 only) if it is
# not already running, then opens it in the browser. Login happens IN THE
# BROWSER (Google owner account + control password) - never in a chat/terminal.
#
# Usage: ./scripts/tidoszit.sh [--port 8767] [--stop]
# ============================================================================
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT=8767
STOP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --stop) STOP=1; shift ;;
    *) shift ;;
  esac
done
URL="http://localhost:$PORT/"
PIDFILE="$HOME/.tidos/tidoszit.pid"
PY="$(command -v python3 || command -v python)"

running() { "$PY" -c "import urllib.request,sys; urllib.request.urlopen(sys.argv[1]+'api/boot', timeout=2)" "$URL" 2>/dev/null; }

if [ "$STOP" = 1 ]; then
  if [ -f "$PIDFILE" ]; then kill "$(cat "$PIDFILE")" 2>/dev/null; rm -f "$PIDFILE"; echo "[TIDOSZIT] Control center stopped."
  else echo "[TIDOSZIT] Not running (no pid file)."; fi
  exit 0
fi

if ! running; then
  mkdir -p "$HOME/.tidos"
  nohup "$PY" -I "$ROOT/tidos_dashboard/__main__.py" --port "$PORT" --no-browser >/dev/null 2>&1 &
  echo $! > "$PIDFILE"
  for _ in $(seq 1 50); do running && break; sleep 0.3; done
  running || { echo "ERROR: control center did not start (port $PORT busy?)." >&2; exit 2; }
fi

( command -v xdg-open >/dev/null && xdg-open "$URL" ) || ( command -v open >/dev/null && open "$URL" ) || \
  "$PY" -m webbrowser "$URL" >/dev/null 2>&1
echo "[TIDOSZIT] Control center open at $URL"
echo "[TIDOSZIT] Log in in the browser. Never type the control password in a chat or terminal."
echo "[TIDOSZIT] Stop it with: ./scripts/tidoszit.sh --stop"
