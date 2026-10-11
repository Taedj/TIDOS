#!/usr/bin/env bash
# ============================================================================
# TIDOS Community Contribution Sync (Linux / macOS)
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CANONICAL_REPO="Taedj/TIDOS"
PERSONA="${1:-}"

if [[ -z "$PERSONA" ]]; then
    PERSONA=$(git status --porcelain personas | grep -E '^(\?\?| M)  personas/tidos.+\.md$' | head -n 1 | awk '{print $2}' || true)
fi

if [[ -z "$PERSONA" || ! -f "$PERSONA" ]]; then
    echo "ERROR: No candidate persona found in personas/tidos*.md to contribute." >&2
    exit 1
fi

echo "[1/4] Running Privacy Firewall audit on $PERSONA..."
python3 "$ROOT/scripts/sanitizer.py" --check "$PERSONA"
echo "[✓] Privacy Firewall PASSED: Zero secrets or prohibited code found."

PERSONA_NAME=$(basename "$PERSONA" .md)
MSG="feat(community): contribute $PERSONA_NAME expert persona to central brain"

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    echo "[2/4] Submitting Pull Request via GitHub CLI..."
    BRANCH="contrib/$PERSONA_NAME-$(date +%s)"
    git checkout -b "$BRANCH"
    git add "$PERSONA"
    git commit -m "$MSG"
    gh pr create --repo "$CANONICAL_REPO" --title "$MSG" --body "Contributed from field use via TIDOS Community Sync."
    echo "SUCCESS! Pull Request submitted."
    exit 0
fi

echo "[3/4] Packaging Sanitized Contribution Bundle..."
mkdir -p "$ROOT/evolution/contributions"
BUNDLE="$ROOT/evolution/contributions/$PERSONA_NAME.bundle.md"
cat <<EOF > "$BUNDLE"
# TIDOS Community Contribution: $PERSONA_NAME
Date: $(date -u +"%Y-%m-%d %H:%M:%SZ")
Source File: $PERSONA

---

$(cat "$PERSONA")
EOF

echo "[4/4] Contribution bundle exported to: $BUNDLE"
echo "Submit as an Issue or PR at https://github.com/$CANONICAL_REPO"
exit 0
