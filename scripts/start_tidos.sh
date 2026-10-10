#!/usr/bin/env bash
# ============================================================================
# START TIDOS - Central Session Entry Script (Linux/macOS Bash)
# ============================================================================
# Executes Step 0 (Force Update Gate) & Step 0.5 (Google Auth Gate)
# and initializes the TIDOS Operating System session.
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIDOS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================================="
echo "  TIDOS (Tidjani Development Operating System) v3.0"
echo "=========================================================="
echo ""

# Step 0: Force-Update Gate against GitHub origin/main
if [ "$1" != "--skip-update" ]; then
    echo ">>> [STEP 0] Checking for TIDOS updates on GitHub..."
    if [ -f "$SCRIPT_DIR/update.sh" ]; then
        bash "$SCRIPT_DIR/update.sh" "$TIDOS_ROOT" || echo "WARNING: Update check completed with non-zero exit. Continuing."
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

VER="3.2.0"
if [ -f "$TIDOS_ROOT/VERSION.md" ]; then
    VER=$(grep "Current Version" "$TIDOS_ROOT/VERSION.md" | awk -F: '{print $2}' | xargs)
fi

echo ""
echo "=========================================================="
echo "  TIDOS SYSTEM READY & AUTHENTICATED (v$VER)"
echo "=========================================================="
echo "  - Core: Frozen & Protected"
echo "  - Engine: Active"
echo "  - Personas: Mounted"
echo "  - GPTID Partner Relay: Ready (Chrome)"
echo "=========================================================="
echo "TIDOS is active. You may now give engineering commands."
