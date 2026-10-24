# ============================================================================
# TIDOS Update Gate (Linux/macOS Bash)
# ============================================================================
# Step 0 of START TIDOS: sync TIDOS with GitHub BEFORE any session work.
# Updates an old or detached TIDOS clone to the latest GitHub version, with
# safety guards (v4.1):
#   - only touches a genuine TIDOS checkout that is its own git top-level
#     (never the project that contains it)
#   - never rewrites a custom/fork 'origin' remote
#   - never discards local edits or unpushed commits to system files
#   - never deletes untracked files (generated personas, new work)
#   - memory/ and evolution/ are backed up and restored; any backup or
#     restore failure aborts loudly and keeps the backup
#
# Usage: ./scripts/update.sh [tidos_dir] [branch]
# Exit codes: 0 = ready (updated / already current / offline-continue)
#             2 = ERROR or refused (nothing was changed)
# ============================================================================

TIDOS_DIR="${1:-}"
BRANCH="${2:-main}"
CANONICAL_URL="${TIDOS_UPDATE_TEST_URL:-https://github.com/Taedj/TIDOS.git}"  # override is for the test harness only
USER_DIRS="memory evolution"

fail() { echo "ERROR: $1" >&2; exit 2; }

is_tidos_checkout() {
  [ -f "$1/TIDSTART.md" ] && [ -f "$1/core/kernel.md" ] && [ -f "$1/config/framework.md" ]
}

normal_url() { printf '%s' "${1%.git}" | sed 's:/*$::' | tr '[:upper:]' '[:lower:]'; }

# Step 1: Locate TIDOS directory ("." is never guessed: it may be a user project)
if [ -z "$TIDOS_DIR" ]; then
  for cand in ".tidos" "TIDOS" "tidos" ".agents/tidos" "../TIDOS" "../.tidos"; do
    if is_tidos_checkout "$cand"; then
      TIDOS_DIR="$cand"
      break
    fi
  done
fi

[ -n "$TIDOS_DIR" ] && is_tidos_checkout "$TIDOS_DIR" || fail "No TIDOS checkout found (needs TIDSTART.md, core/kernel.md, config/framework.md). Pass tidos_dir explicitly."

cd "$TIDOS_DIR" || fail "Cannot enter '$TIDOS_DIR'."
TIDOS_DIR=$(pwd -P)
echo "[1/5] TIDOS directory located: $TIDOS_DIR"

# Step 2: Ensure this directory is its OWN git repository
if [ ! -d ".git" ] && [ ! -f ".git" ]; then
  echo "[2/5] No .git repository in '$TIDOS_DIR' (local copy). Initializing git remote..."
  git init -q || fail "git init failed in '$TIDOS_DIR'."
  git remote add origin "$CANONICAL_URL"
fi

# Guard: git must resolve to THIS directory, never to a parent project repo
# (--show-prefix is empty only at the top-level; avoids symlink / path-form comparisons)
PREFIX=$(git rev-parse --show-prefix 2>/dev/null) && [ -z "$PREFIX" ] \
  || fail "Git top-level is '$(git rev-parse --show-toplevel 2>/dev/null)', not '$TIDOS_DIR'. Refusing to touch another repository."

# Guard: never rewrite a custom origin (forks, mirrors, user projects)
EXISTING_ORIGIN=$(git remote get-url origin 2>/dev/null)
if [ -z "$EXISTING_ORIGIN" ]; then
  git remote add origin "$CANONICAL_URL"
elif [ "$(normal_url "$EXISTING_ORIGIN")" != "$(normal_url "$CANONICAL_URL")" ]; then
  fail "origin is '$EXISTING_ORIGIN', not the TIDOS repository. Refusing to force-sync a fork/custom remote. Update it with 'git pull' instead."
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

# Guard: never discard local work on system files (maintainer / developer mode)
if [ "$OLD_REV" != "(uninitialized)" ]; then
  DIRTY=$(git status --porcelain --untracked-files=no | grep -Ev '^.. "?(memory|evolution)/')
  if [ -n "$DIRTY" ]; then
    echo "Local modifications to TIDOS system files:"
    printf '  %s\n' "$DIRTY"
    echo "  -> WARNING: update skipped to protect your work. Commit/push or stash, then rerun. Continuing on local version ($OLD_REV)."
    exit 0
  fi
  AHEAD=$(git rev-list --count "origin/$BRANCH..HEAD" 2>/dev/null || echo 0)
  if [ "$AHEAD" -gt 0 ]; then
    echo "  -> WARNING: $AHEAD local commit(s) not on origin/$BRANCH. Update skipped - push them first. Continuing on local version ($OLD_REV)."
    exit 0
  fi
fi

echo "[4/5] Update found: $OLD_REV -> $NEW_REV. Force-updating TIDOS..."

# Step 4: Back up user memory before the reset - abort on any failure
TEMP_BACKUP=$(mktemp -d "${TMPDIR:-/tmp}/tidos_mem_backup_XXXXXX") || fail "Cannot create backup directory. Nothing was changed."
BACKED_UP=""
for d in $USER_DIRS; do
  if [ -d "$d" ]; then
    cp -R "$d" "$TEMP_BACKUP/" || fail "Memory backup of '$d' failed. Nothing was changed."
    BACKED_UP="$BACKED_UP $d"
  fi
done

# Step 5: Sync system files to origin/$BRANCH (heals detached HEAD in submodules).
# No 'git clean': untracked files are user work (e.g. generated personas), never upstream files.
git checkout -B "$BRANCH" "origin/$BRANCH" --force 2>/dev/null
git reset --hard "origin/$BRANCH" 2>/dev/null
RESET_RC=$?

# Restore preserved user memory files (also after a failed reset)
for d in $BACKED_UP; do
  mkdir -p "$d" && cp -R "$TEMP_BACKUP/$d/." "$d/" || fail "Memory restore of '$d' failed. Your backup is kept at: $TEMP_BACKUP"
done
rm -rf "$TEMP_BACKUP"

[ "$RESET_RC" -eq 0 ] || fail "git reset --hard origin/$BRANCH failed (memory restored)."

FINAL_REV=$(git rev-parse --short HEAD 2>/dev/null)
echo "[5/5] Force update successful: $OLD_REV -> $FINAL_REV"
exit 0
