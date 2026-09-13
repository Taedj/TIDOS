#!/usr/bin/env bash
# ============================================================================
# TIDOS Persona Factory Sync (Linux/macOS Bash)
# ============================================================================
# Stages ONLY factory-generated paths (new persona spec + registry + evolution)
# and pushes them to origin/main (the central brain). Never force-pushes.
#
# Usage:
#   ./scripts/factory_sync.ps1                      # detect + commit + push
#   ./scripts/factory_sync.ps1 -Persona <NAME>      # explicitly name path
#   ./scripts/factory_sync.ps1 -Message "<msg>"     # custom commit message
#   ./scripts/factory_sync.ps1 -DryRun              # show what would be staged
#
# Exit: 0 = pushed, 1 = nothing to push / blocked, 2 = error
# ============================================================================

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || { echo "ERROR: Not a git repo: $REPO" >&2; exit 2; }

PERSONA=""
MESSAGE=""
DRYRUN=0

while [ $# -gt 0 ]; do
  case "$1" in
    -Persona) PERSONA="$2"; shift 2 ;;
    -Message) MESSAGE="$2"; shift 2 ;;
    -DryRun)  DRYRUN=1; shift ;;
    *) shift ;;
  esac
done

# --- detect untracked persona file if not given --------------------------------
if [ -z "$PERSONA" ]; then
  PERSONA=$(git status --porcelain -- personas | grep -E '^\?\? personas/tidos[^ ]+\.md$' | head -n1 | sed 's/^\?\? //')
fi
[ -n "$PERSONA" ] || { echo "ERROR: No new persona detected to sync. Expected new personas/tidos*.md." >&2; exit 1; }

# --- guard: only factory paths -----------------------------------------------
FACTORY_PATHS="$PERSONA
personas/registry.md
evolution/SUGGESTIONS.md"
UNRELATED=$(git status --porcelain | awk '{print $2}' | grep -vFf <(echo "$FACTORY_PATHS") | head -n5)
if [ -n "$UNRELATED" ]; then
  echo "BLOCKED: unrelated changes would be included:" >&2
  echo "$UNRELATED" >&2
  echo "Stash/commit unrelated changes first; factory_sync commits ONLY the persona trio." >&2
  exit 1
fi

# --- message ------------------------------------------------------------------
NAME=$(basename "$PERSONA" .md)
[ -z "$MESSAGE" ] && MESSAGE="feat(persona-factory): $NAME persona auto-generated (discovered domain/stack)"

# --- stage & commit -----------------------------------------------------------
git add "$PERSONA" personas/registry.md evolution/SUGGESTIONS.md
echo "Staging: $PERSONA + personas/registry.md + evolution/SUGGESTIONS.md"
echo "Message: $MESSAGE"
if [ "$DRYRUN" = "1" ]; then echo "[dry-run] push skipped. Staged:"; git diff --cached --name-status; exit 0; fi

git commit -m "$MESSAGE" >/dev/null 2>&1
git push origin main 2>&1
[ $? -eq 0 ] || { echo "ERROR: push failed. Local commit exists." >&2; exit 1; }
echo "Pushed to origin/main. Central brain updated."
exit 0