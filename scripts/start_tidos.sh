#!/usr/bin/env bash
# ============================================================================
# START TIDOS - Central Session Entry Script (Linux/macOS Bash)
# ============================================================================
# Executes Step 0 (Force Update Gate) & Step 0.5 (Google Auth Gate)
# and initializes the TIDOS Operating System session.
# ============================================================================

set -e

PROJECT_DIR="$(pwd)"   # the user's project: where START TIDOS was run
TOOL="auto"; MODEL="auto"; SKIP_ARG=""; UPDATE_ARGS=""
for arg in "$@"; do
    case "$arg" in
        --tool=*) TOOL="${arg#--tool=}" ;;
        --model=*) MODEL="${arg#--model=}" ;;
        --skip-update) SKIP_ARG="--skip-update" ;;
        --apply-update) UPDATE_ARGS="$UPDATE_ARGS --apply" ;;
        --channel=*) UPDATE_ARGS="$UPDATE_ARGS --channel ${arg#--channel=}" ;;
    esac
done
set -- $SKIP_ARG
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIDOS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================================="
echo "  TIDOS (Tidjani Development Operating System) v3.0"
echo "=========================================================="
echo ""

# Kill switch (~/.tidos/control.json, /TIDOSZIT): auto_update off -> skip Step 0
SKIP_UPDATE=0
[ "${1:-}" = "--skip-update" ] && SKIP_UPDATE=1
if [ "$SKIP_UPDATE" = 0 ]; then
    rc=0; python3 -I "$TIDOS_ROOT/tidos_brain/control.py" get auto_update >/dev/null 2>&1 || rc=$?
    if [ "$rc" -eq 1 ]; then
        echo ">>> [STEP 0] Auto-update is switched OFF in the control center (/TIDOSZIT). Skipping."
        SKIP_UPDATE=1
    fi
fi

# Step 0: Force-Update Gate against GitHub origin/main
if [ "$SKIP_UPDATE" = 0 ]; then
    echo ">>> [STEP 0] Checking for TIDOS updates on GitHub..."
    if [ -f "$SCRIPT_DIR/update.sh" ]; then
        bash "$SCRIPT_DIR/update.sh" "$TIDOS_ROOT" $UPDATE_ARGS || echo "WARNING: Update check completed with non-zero exit. Continuing."
    fi
fi

# Step 0.5: Firebase Google Authentication Gate
echo ""
echo ">>> [STEP 0.5] Verifying Google Authentication (Firebase)..."
if [ -f "$SCRIPT_DIR/auth_verify.sh" ]; then
    if ! bash "$SCRIPT_DIR/auth_verify.sh" -Session; then
        echo ""
        echo "TIDOS is LOCKED. You must sign in with Google to use TIDOS."
        echo "Opening browser for Google Authentication..."
        bash "$SCRIPT_DIR/auth_verify.sh" -GoogleLogin || {
            echo "Authentication failed or was cancelled. TIDOS remains locked."
            exit 1
        }
    fi
fi

VER="unknown"
if [ -f "$TIDOS_ROOT/VERSION.md" ]; then
    VER=$(grep "Current Version" "$TIDOS_ROOT/VERSION.md" | awk -F: '{print $2}' | xargs)
fi

echo ""
echo "=========================================================="
echo "  TIDOS READY (v$VER)"
echo "=========================================================="
# Session mode: LEARN on strong models, GUIDE on weak/free models
"$(command -v python3 || command -v python)" -I "$TIDOS_ROOT/tidos_session/__main__.py" start     --tool "$TOOL" --model "$MODEL" --project "$PROJECT_DIR"
echo "Follow the TIDOS brief above for this whole session."
