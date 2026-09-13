#!/usr/bin/env bash
# ============================================================================
# TIDOS Update Gate (Linux/macOS Bash)
# ============================================================================
# Step 0 of START TIDOS: force-sync TIDOS with GitHub BEFORE any session work.
# Memory-safe force: OS files are reset to the remote, but the gate ABORTS
# (instead of wiping) when uncommitted memory/ or evolution/ changes exist.
# Never blocks boot when the network or remote is unreachable.
#
# Usage: ./scripts/update.sh [tidos_dir] [branch]
# Exit codes: 0 = ready (updated / already current / offline-continue)
#             1 = BLOCKED (uncommitted memory/evolution changes - commit first)
#             2 = ERROR (not a TIDOS checkout)
# ============================================================================

TIDOS_DIR="${1:-}"
BRANCH="${2:-main}"

fail() { echo "ERROR: $1" >&2; exit 2; }

# Step 1: Locate the TIDOS checkout (.tidos submodule -> explicit dir -> current dir)
if [ -z "$TIDOS_DIR" ]; then
  if [ -f ".tidos/TIDSTART.md" ]; then TIDOS_DIR=".tidos"
  elif [ -f "TIDSTART.md" ]; then TIDOS_DIR="."
  else fail "No TIDOS checkout found. Pass tidos_dir explicitly."; fi
fi
[ -f "$TIDOS_DIR/TIDSTART.md" ] || fail "'$TIDOS_DIR' is not a TIDOS checkout (TIDSTART.md missing)."

echo "[0/4] TIDOS directory: $TIDOS_DIR"

# Step 2: Local-copy mode (no .git) cannot pull - warn and continue on local version
if [ ! -d "$TIDOS_DIR/.git" ]; then
  echo "[1/4] No .git in '$TIDOS_DIR' (local-copy mode). Skipping remote sync."
  VER="(unknown)"; [ -f "$TIDOS_DIR/VERSION.md" ] && VER=$(grep "Current Version" "$TIDOS_DIR/VERSION.md")
  echo "  -> Continuing on local version: $VER"
  exit 0
fi

cd "$TIDOS_DIR" || fail "Cannot enter '$TIDOS_DIR'."
OLD_REV=$(git rev-parse --short HEAD 2>/dev/null) || fail "git is unavailable or repository is corrupt."

# Step 3: Fetch - network failure must never block boot
echo "[1/4] Fetching origin... (local: $OLD_REV)"
if ! git fetch origin 2>/dev/null; then
  echo "  -> WARNING: GitHub unreachable. Continuing on local version ($OLD_REV)."
  exit 0
fi
NEW_REV=$(git rev-parse --short "origin/$BRANCH" 2>/dev/null) || fail "Remote branch 'origin/$BRANCH' not found."

if [ "$OLD_REV" = "$NEW_REV" ]; then
  echo "[2/4] Already current ($OLD_REV). No sync needed."
  exit 0
fi
echo "[2/4] Update available: $OLD_REV -> $NEW_REV"

# Step 4a: Unpushed-commit check - reset would orphan local commits
AHEAD=$(git rev-list --count "origin/$BRANCH..HEAD" 2>/dev/null)
if [ "${AHEAD:-0}" -gt 0 ]; then
  echo "  -> BLOCKED: $AHEAD unpushed local commit(s) would be orphaned by force sync."
  echo "  -> Push them first (git push), then re-run START TIDOS."
  exit 1
fi

# Step 4: Memory-safety check - abort instead of wiping institutional memory
DIRTY=$(git status --porcelain -- memory evolution 2>/dev/null)
if [ -n "$DIRTY" ]; then
  echo "  -> BLOCKED: uncommitted memory/evolution changes would be wiped:"
  echo "$DIRTY" | sed 's/^/     /'
  echo "  -> Commit or stash them first, then re-run START TIDOS."
  exit 1
fi

# Step 5: Memory-safe force sync
echo "[3/4] Force-syncing OS files to origin/$BRANCH..."
git reset --hard "origin/$BRANCH" || fail "Force sync failed."
echo "[4/4] Updated: $OLD_REV -> $NEW_REV"
exit 0
