# ============================================================================
# TIDOS Update Gate (Linux/macOS Bash)
# ============================================================================
# Step 0 of START TIDOS: force-sync TIDOS with GitHub BEFORE any session work.
# Automatically updates any old or detached TIDOS clone to the latest GitHub version.
# Non-destructive memory safety: user profile and memory/ are preserved while
# OS and system files are force-updated to origin/main.
#
# Usage: ./scripts/update.sh [tidos_dir] [branch]
# Exit codes: 0 = ready (updated / already current / offline-continue)
#             2 = ERROR (not a TIDOS checkout)
# ============================================================================

TIDOS_DIR="${1:-}"
BRANCH="${2:-main}"
CANONICAL_URL="https://github.com/Taedj/TIDOS.git"

fail() { echo "ERROR: $1" >&2; exit 2; }

# Step 1: Locate TIDOS directory
if [ -z "$TIDOS_DIR" ]; then
  for cand in ".tidos" "TIDOS" "tidos" "." ".agents/tidos" "../TIDOS" "../.tidos"; do
    if [ -f "$cand/TIDSTART.md" ]; then
      TIDOS_DIR="$cand"
      break
    fi
  done
fi

[ -n "$TIDOS_DIR" ] && [ -f "$TIDOS_DIR/TIDSTART.md" ] || fail "No TIDOS checkout found. Pass tidos_dir explicitly or ensure TIDSTART.md exists."

echo "[1/5] TIDOS directory located: $TIDOS_DIR"

# Step 2: Ensure Git environment & remote origin
if [ ! -d "$TIDOS_DIR/.git" ] && [ ! -f "$TIDOS_DIR/.git" ]; then
  echo "[2/5] No .git repository in '$TIDOS_DIR' (local copy). Initializing git remote..."
  (cd "$TIDOS_DIR" && git init -q 2>/dev/null && git remote add origin "$CANONICAL_URL" 2>/dev/null)
fi

cd "$TIDOS_DIR" || fail "Cannot enter '$TIDOS_DIR'."

EXISTING_ORIGIN=$(git remote get-url origin 2>/dev/null)
if [ -z "$EXISTING_ORIGIN" ]; then
  git remote add origin "$CANONICAL_URL" 2>/dev/null
elif [ "$EXISTING_ORIGIN" != "$CANONICAL_URL" ] && [ "$EXISTING_ORIGIN" != "${CANONICAL_URL%.git}" ]; then
  git remote set-url origin "$CANONICAL_URL" 2>/dev/null
fi

OLD_REV=$(git rev-parse --short HEAD 2>/dev/null || echo "(uninitialized)")

# Step 3: Fetch latest from GitHub
echo "[3/5] Fetching origin/$BRANCH from GitHub... (current: $OLD_REV)"
if ! git fetch origin "$BRANCH" --prune --tags 2>/dev/null; then
  echo "  -> WARNING: GitHub unreachable or offline. Continuing on local version ($OLD_REV)."
  exit 0
fi

NEW_REV=$(git rev-parse --short "origin/$BRANCH" 2>/dev/null) || fail "Remote branch 'origin/$BRANCH' could not be resolved from $CANONICAL_URL."

if [ "$OLD_REV" = "$NEW_REV" ]; then
  echo "[4/5] Already up-to-date with GitHub ($NEW_REV). No update needed."
  echo "[5/5] TIDOS is ready."
  exit 0
fi

echo "[4/5] Update found: $OLD_REV -> $NEW_REV. Force-updating TIDOS..."

# Step 4: Memory preservation backup before force reset
TEMP_BACKUP="/tmp/tidos_mem_backup_$$"
mkdir -p "$TEMP_BACKUP" 2>/dev/null
[ -d "memory" ] && cp -r memory "$TEMP_BACKUP/" 2>/dev/null
[ -d "evolution" ] && cp -r evolution "$TEMP_BACKUP/" 2>/dev/null

# Step 5: Force sync - reset hard to origin/$BRANCH & clean untracked deprecated files
git checkout -B "$BRANCH" "origin/$BRANCH" --force 2>/dev/null
git reset --hard "origin/$BRANCH" 2>/dev/null || fail "git reset --hard origin/$BRANCH failed."
git clean -fd -e memory/ -e evolution/ -e .tidos/ 2>/dev/null

# Restore preserved user memory files
if [ -d "$TEMP_BACKUP" ]; then
  [ -d "$TEMP_BACKUP/memory" ] && cp -r "$TEMP_BACKUP/memory/"* memory/ 2>/dev/null
  [ -d "$TEMP_BACKUP/evolution" ] && cp -r "$TEMP_BACKUP/evolution/"* evolution/ 2>/dev/null
  rm -rf "$TEMP_BACKUP" 2>/dev/null
fi

FINAL_REV=$(git rev-parse --short HEAD 2>/dev/null)
echo "[5/5] Force update successful: $OLD_REV -> $FINAL_REV"
exit 0

