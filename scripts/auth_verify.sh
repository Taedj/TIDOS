#!/usr/bin/env bash
# ============================================================================
# TIDOS Firebase Auth Helper (Linux/macOS Bash)
# ============================================================================
# Lightweight REST client for TIDOS framework auth against the Firebase
# project defined in config/firebase.md. Verifies settled ID tokens and
# performs email/password sign-in. NEVER prints or logs tokens.
#
# Config: FIREBASE_API_KEY env var (or .env file) - the public web API key.
#
# Usage:
#   ./scripts/auth_verify.sh -Verify <idToken>                 # verify an ID token
#   ./scripts/auth_verify.sh -Login -Email <e> -Password <p>   # email/pass sign-in
#   ./scripts/auth_verify.sh -Status                           # env/config self-check
#
# Exit codes: 0 = verified/authenticated/ok
#             1 = auth failed (bad token / wrong credentials / not enabled)
#             2 = configuration error
# ============================================================================

API_KEY="${FIREBASE_API_KEY:-}"
if [ -z "$API_KEY" ] && [ -f "$(dirname "$0")/../.env" ]; then
  API_KEY=$(grep -E '^\s*FIREBASE_API_KEY\s*=' "$(dirname "$0")/../.env" | head -n1 | sed 's/^[^=]*=//' | tr -d "'\" " )
fi
[ -n "$API_KEY" ] || { echo "ERROR: FIREBASE_API_KEY not set (env or .env). See docs/firebase_auth.md." >&2; exit 2; }

if [ "$1" = "-Status" ]; then
  echo "Firebase Auth Helper: OK (API key present)."
  echo "Project reference: config/firebase.md (tidos-framework)."
  exit 0
fi

BASE="https://identitytoolkit.googleapis.com/v1"

if [ "$1" = "-Login" ]; then
  while [ $# -gt 0 ]; do
    case "$1" in
      -Email) EMAIL="$2"; shift 2 ;;
      -Password) PASSWORD="$2"; shift 2 ;;
      *) shift ;;
    esac
  done
  [ -n "$EMAIL" ] && [ -n "$PASSWORD" ] || { echo "ERROR: Login requires -Email and -Password." >&2; exit 2; }
  RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/accounts:signInWithPassword?key=$API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"returnSecureToken\":true}")
  CODE=$(echo "$RESP" | tail -n1); BODY=$(echo "$RESP" | sed '$ d')
  [ "$CODE" = "200" ] || { echo "Sign-in failed (HTTP $CODE): $BODY" >&2; exit 1; }
  echo "Signed in as: $(echo "$BODY" | jq -r .email) (uid $(echo "$BODY" | jq -r .localId))"
  echo "Do NOT print idToken. Session token stays in this shell scope only."
  exit 0
fi

if [ "$1" = "-Verify" ]; then
  TOKEN="$2"
  [ -n "$TOKEN" ] || { echo "ERROR: -Verify requires an idToken." >&2; exit 2; }
  RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/accounts:lookup?key=$API_KEY" \
    -H "Content-Type: application/json" -d "{\"idToken\":\"$TOKEN\"}")
  CODE=$(echo "$RESP" | tail -n1); BODY=$(echo "$RESP" | sed '$ d')
  [ "$CODE" = "200" ] || { echo "Token verification failed (HTTP $CODE): $BODY" >&2; exit 1; }
  echo "Token VALID: $(echo "$BODY" | jq -r '.users[0].email') (uid $(echo "$BODY" | jq -r '.users[0].localId'))"
  exit 0
fi

echo "ERROR: No operation selected. Use -Verify, -Login, or -Status." >&2
exit 2