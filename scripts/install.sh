#!/usr/bin/env bash
# ============================================================================
# TIDOS v3.0 Installation Script (Linux/macOS)
# ============================================================================
# Installs TIDOS as a Git submodule in the current project.
# Usage: ./scripts/install.sh [target-directory]
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIDOS_URL="https://github.com/tidjani/TIDOS.git"
TARGET_DIR="${1:-.tidos}"

echo "============================================"
echo "  TIDOS v3.0 Installation Script"
echo "============================================"
echo ""

# Step 1: Check prerequisites
if ! command -v git &> /dev/null; then
    echo "ERROR: Git is not installed. Please install Git first."
    exit 1
fi

# Step 2: Initialize Git if needed
if [ ! -d ".git" ]; then
    echo "[1/4] Initializing Git repository..."
    git init
    echo "  -> Git repository initialized."
else
    echo "[1/4] Git repository already initialized."
fi

# Step 3: Install TIDOS as a submodule
if [ -d "$TARGET_DIR" ]; then
    echo "[2/4] TIDOS directory '$TARGET_DIR' already exists."
    echo "  -> Skipping submodule addition."
    echo "  -> Run 'git submodule update --remote' to update."
else
    echo "[2/4] Installing TIDOS as a Git submodule..."
    git submodule add "$TIDOS_URL" "$TARGET_DIR"
    git submodule init
    git submodule update
    echo "  -> TIDOS installed at '$TARGET_DIR/'."
fi

# Step 4: Verify installation
echo "[3/4] Verifying installation..."
if [ -f "$TARGET_DIR/VERSION.md" ]; then
    TIDOS_VERSION=$(cat "$TARGET_DIR/VERSION.md" | head -n 3 | tail -n 1)
    echo "  -> TIDOS version: $TIDOS_VERSION"
    echo "  -> Installation verified successfully."
else
    echo "  -> WARNING: VERSION.md not found. Installation may be incomplete."
fi

# Step 5: Display next steps
echo "[4/4] Installation complete."
echo ""
echo "============================================"
echo "  Next Steps"
echo "============================================"
echo ""
echo "  1. Read the startup protocol:"
echo "     cat $TARGET_DIR/TIDSTART.md"
echo ""
echo "  2. Start your session by loading TIDOS:"
echo "     - Open $TARGET_DIR/TIDSTART.md"
echo "     - Follow the 9-step startup sequence"
echo ""
echo "  3. For AI agent integration guides:"
echo "     ls $TARGET_DIR/docs/tools/"
echo ""
echo "  4. Commit the submodule:"
echo "     git add .gitmodules $TARGET_DIR"
echo "     git commit -m \"chore: add TIDOS v3.0 submodule\""
echo ""
echo "============================================"
