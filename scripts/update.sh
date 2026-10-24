#!/usr/bin/env bash
# ============================================================================
# TIDOS Update Gate (Linux/macOS Bash)
# ============================================================================
# Step 0 of START TIDOS. Checks GitHub for a newer TIDOS and installs it ONLY when
# approved (--apply). Default channel "release" follows the newest vX.Y.Z tag;
# "main" follows the main branch (maintainers). TIDOS_REQUIRE_SIGNED=1 refuses
# tags that are unsigned or fail `git verify-tag`.
#
# Safety guards (v4.1):
#   - only touches a genuine TIDOS checkout that is its own git top-level
#   - never rewrites a custom/fork 'origin' remote
#   - never discards local edits or commits that are not in the target version
#   - never deletes untracked files (generated personas, new work)
#   - memory/ and evolution/ are backed up and restored; failures abort loudly
#
# Usage: ./scripts/update.sh [tidos_dir] [--channel release|main] [--apply]
# Exit codes: 0 = ready (up to date / update reported / applied / offline)
#             2 = ERROR or refused (nothing was changed)
# ============================================================================

TIDOS_DIR=""
CHANNEL="release"
APPLY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --channel) CHANNEL="$2"; shift 2 ;;
    --channel=*) CHANNEL="${1#--channel=}"; shift ;;
    --apply) APPLY=1; shift ;;
    *) [ -z "$TIDOS_DIR" ] && TIDOS_DIR="$1"; shift ;;
  esac
done
CANONICAL_URL="${TIDOS_UPDATE_TEST_URL:-https://github.com/Taedj/TIDOS.git}"  # override is for the test harness only
USER_DIRS="memory evolution"

fail() { echo "ERROR: $1" >&2; exit 2; }
case "$CHANNEL" in release|main) ;; *) fail "channel must be release or main" ;; esac

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
# (--show-prefix is empty only at the top-level; avoids symlink / path-form comparisons)
PREFIX=$(git rev-parse --show-prefix 2>/dev/null) && [ -z "$PREFIX" ] \
  || fail "Git top-level is '$(git rev-parse --show-toplevel 2>/dev/null)', not '$TIDOS_DIR'. Refusing to touch another repository."
EXISTING_ORIGIN=$(git remote get-url origin 2>/dev/null)
if [ -z "$EXISTING_ORIGIN" ]; then
  git remote add origin "$CANONICAL_URL"
elif [ "$(normal_url "$EXISTING_ORIGIN")" != "$(normal_url "$CANONICAL_URL")" ]; then
  fail "origin is '$EXISTING_ORIGIN', not the TIDOS repository. Refusing to force-sync a fork/custom remote. Update it with 'git pull' instead."
fi

OLD_REV=$(git rev-parse --short HEAD 2>/dev/null || echo "(uninitialized)")

# Step 3: Fetch and pick the target version
echo "[3/5] Checking GitHub ($CHANNEL channel, current: $OLD_REV)..."
if ! git fetch origin main --prune --tags --force 2>/dev/null; then
  echo "  -> WARNING: GitHub unreachable or offline. Continuing on local version ($OLD_REV)."
  exit 0
fi
if [ "$CHANNEL" = "release" ]; then
  TARGET=$(git tag -l 'v*' --sort=-v:refname | head -n 1)
  if [ -z "$TARGET" ]; then
    echo "  -> No release tag published yet. Staying on $OLD_REV (use --channel main to follow main)."
    exit 0
  fi
else
  TARGET="origin/main"
fi
TARGET_FULL=$(git rev-parse "$TARGET^{commit}" 2>/dev/null) || fail "Cannot resolve '$TARGET'."
NEW_REV=$(git rev-parse --short "$TARGET_FULL")
if [ "$(git rev-parse HEAD 2>/dev/null)" = "$TARGET_FULL" ]; then
  echo "[4/5] Already on $TARGET ($NEW_REV). No update needed."
  echo "[5/5] TIDOS is ready."
  exit 0
fi
if git merge-base --is-ancestor "$TARGET_FULL" HEAD 2>/dev/null; then
  echo "[4/5] Local version ($OLD_REV) already contains $TARGET. No update needed."
  exit 0
fi

SIGNATURE="not a tag"
if [ "$CHANNEL" = "release" ]; then
  if git verify-tag "$TARGET" >/dev/null 2>&1; then
    SIGNATURE="valid signature"
  elif [ "$(git cat-file -t "$TARGET" 2>/dev/null)" = "tag" ] && git cat-file -p "$TARGET" | grep -qE "BEGIN (PGP|SSH) SIGNATURE"; then
    SIGNATURE="INVALID or untrusted signature"
  else
    SIGNATURE="unsigned"
  fi
  if [ "${TIDOS_REQUIRE_SIGNED:-0}" = "1" ] && [ "$SIGNATURE" != "valid signature" ]; then
    fail "Release $TARGET is $SIGNATURE and TIDOS_REQUIRE_SIGNED=1. Not updating."
  fi
fi

# Step 4: Report the update (always) and stop unless approved
COUNT=$(git rev-list --count "HEAD..$TARGET_FULL" 2>/dev/null || echo "?")
echo "[4/5] Update available: $OLD_REV -> $TARGET ($NEW_REV), tag: $SIGNATURE"
echo "      $COUNT commit(s);$(git diff --shortstat HEAD "$TARGET_FULL" 2>/dev/null)"
git log --oneline "HEAD..$TARGET_FULL" 2>/dev/null | head -n 15 | sed 's/^/        /'
if [ "$APPLY" != 1 ]; then
  echo "  -> NOT installed. Review the changes above, then approve with: START TIDOS --apply-update (or scripts/update.sh --apply)."
  exit 0
fi

# Guard: never discard local work that is not part of the target version
if [ "$OLD_REV" != "(uninitialized)" ]; then
  DIRTY=$(git status --porcelain --untracked-files=no | grep -Ev '^.. "?(memory|evolution)/')
  if [ -n "$DIRTY" ]; then
    echo "Local modifications to TIDOS system files:"
    printf '  %s\n' "$DIRTY"
    echo "  -> WARNING: update skipped to protect your work. Commit/push or stash, then rerun. Continuing on local version ($OLD_REV)."
    exit 0
  fi
  AHEAD=$(git rev-list --count "$TARGET_FULL..HEAD" 2>/dev/null || echo 0)
  if [ "$AHEAD" -gt 0 ]; then
    echo "  -> WARNING: $AHEAD local commit(s) are not in $TARGET. Update skipped - push or merge them first. Continuing on local version ($OLD_REV)."
    exit 0
  fi
fi

# Step 5: Back up user memory, move to the target, restore memory
TEMP_BACKUP=$(mktemp -d "${TMPDIR:-/tmp}/tidos_mem_backup_XXXXXX") || fail "Cannot create backup directory. Nothing was changed."
BACKED_UP=""
for d in $USER_DIRS; do
  if [ -d "$d" ]; then
    cp -R "$d" "$TEMP_BACKUP/" || fail "Memory backup of '$d' failed. Nothing was changed."
    BACKED_UP="$BACKED_UP $d"
  fi
done

# No 'git clean': untracked files are user work (e.g. generated personas), never upstream files.
if [ "$CHANNEL" = "main" ]; then
  git checkout -B main "$TARGET_FULL" --force 2>/dev/null
else
  git checkout --detach "$TARGET_FULL" --force 2>/dev/null
fi
git reset --hard "$TARGET_FULL" 2>/dev/null
RESET_RC=$?

for d in $BACKED_UP; do
  mkdir -p "$d" && cp -R "$TEMP_BACKUP/$d/." "$d/" || fail "Memory restore of '$d' failed. Your backup is kept at: $TEMP_BACKUP"
done
rm -rf "$TEMP_BACKUP"
[ "$RESET_RC" -eq 0 ] || fail "git reset --hard $TARGET failed (memory restored)."

echo "[5/5] Updated: $OLD_REV -> $TARGET ($(git rev-parse --short HEAD 2>/dev/null))"
exit 0
