#!/usr/bin/env bash
# ============================================================================
# TIDOS Firebase Auth Helper (Linux/macOS Bash)
# ============================================================================
# Lightweight REST client for TIDOS framework auth against the Firebase
# project defined in config/firebase.md.
#
# Config: FIREBASE_API_KEY env var (or .env file) - the public web API key.
# Session: persisted in $HOME/.tidos/tidos-session.json (OUTSIDE any repo,
#          never committed, mode 600). Contains refresh token; idToken never printed.
#
# Usage:
#   ./scripts/auth_verify.sh -Status                        # config self-check
#   ./scripts/auth_verify.sh -Session                       # validate saved session (remember-me)
#   ./scripts/auth_verify.sh -Login -Email <e> -Password <p>     # email/password sign-in
#   ./scripts/auth_verify.sh -Register -Email <e> -Password <p>  # create account
#   ./scripts/auth_verify.sh -Verify <idToken>              # verify an external ID token
#   ./scripts/auth_verify.sh -Logout                        # clear saved session
#
# Exit codes: 0 = ready/valid/authenticated
#             1 = auth failed (bad token / wrong credentials / no session) - re-auth needed
#             2 = configuration error (missing API key / no operation selected)
# Requires: curl + jq.
# ============================================================================

API_KEY="${FIREBASE_API_KEY:-}"
if [ -z "$API_KEY" ] && [ -f "$(dirname "$0")/../.env" ]; then
  API_KEY=$(grep -E '^\s*FIREBASE_API_KEY\s*=' "$(dirname "$0")/../.env" | head -n1 | sed 's/^[^=]*=//' | tr -d "'\" ")
fi

SESSION_DIR="${HOME}/.tidos"
SESSION_PATH="${SESSION_DIR}/tidos-session.json"
BASE="https://identitytoolkit.googleapis.com/v1"
REFRESH="https://securetoken.googleapis.com/v1/token"

auth_post() {
  local url="$1" data="$2"
  local resp code body
  resp=$(curl -s -w "\n%{http_code}" -X POST "$url" -H "Content-Type: application/json" -d "$data")
  code=$(echo "$resp" | tail -n1); body=$(echo "$resp" | sed '$ d')
  if [ "$code" != "200" ]; then echo "Auth API error: $(echo "$body" | jq -r .error.message)" >&2; return 1; fi
  echo "$body"
}

save_session() {
  mkdir -p "$SESSION_DIR" || return 1
  echo "$1" > "$SESSION_PATH"
  chmod 600 "$SESSION_PATH" 2>/dev/null || true
}

read_session() { [ -f "$SESSION_PATH" ] && cat "$SESSION_PATH" || echo ""; }

case "$1" in
  -Status|status)
    if [ -z "$API_KEY" ]; then echo "FIREBASE_API_KEY: NOT SET (set env var or add to .env)"; else echo "FIREBASE_API_KEY: present."; fi
    echo "Project reference: config/firebase.md (tidos-framework)."
    S=$(read_session)
    if [ -n "$S" ]; then echo "Saved session: present ($(echo "$S" | jq -r .email)) - use -Session to validate, -Logout to disconnect."; else echo "Saved session: none."; fi
    exit 0
    ;;
  -Logout|logout)
    if [ -f "$SESSION_PATH" ]; then rm -f "$SESSION_PATH"; echo "Session cleared. Disconnected from the TIDOS account."; else echo "No saved session. Already disconnected."; fi
    exit 0
    ;;
esac

[ -n "$API_KEY" ] || { echo "ERROR: FIREBASE_API_KEY not set (env or .env). See docs/firebase_auth.md." >&2; exit 2; }

case "$1" in
  -Register|register)
    EMAIL="" PASSWORD=""
    while [ $# -gt 0 ]; do case "$1" in -Email) EMAIL="$2"; shift 2;; -Password) PASSWORD="$2"; shift 2;; *) shift;; esac; done
    [ -n "$EMAIL" ] && [ -n "$PASSWORD" ] || { echo "ERROR: Register requires -Email and -Password (min 6 chars)." >&2; exit 2; }
    R=$(auth_post "$BASE/accounts:signUp?key=$API_KEY" "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}") || exit 1
    auth_post "$BASE/accounts:sendOAuthVerificationEmail?key=$API_KEY" "{\"requestType\":\"VERIFY_EMAIL\",\"idToken\":$(echo "$R" | jq -r .idToken | jq -Rs .)}" >/dev/null 2>&1
    save_session "$R" || { echo "ERROR: cannot write session to $SESSION_DIR." >&2; exit 2; }
    echo "Account created: $(echo "$R" | jq -r .email) (uid $(echo "$R" | jq -r .localId)). Verification email sent. Session saved (remember-me)."
    exit 0
    ;;
  -Login)
    EMAIL="" PASSWORD=""
    while [ $# -gt 0 ]; do case "$1" in -Email) EMAIL="$2"; shift 2;; -Password) PASSWORD="$2"; shift 2;; *) shift;; esac; done
    [ -n "$EMAIL" ] && [ -n "$PASSWORD" ] || { echo "ERROR: Login requires -Email and -Password." >&2; exit 2; }
    R=$(auth_post "$BASE/accounts:signInWithPassword?key=$API_KEY" "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"returnSecureToken\":true}") || { echo "Login failed. Use -Register if no account exists." >&2; exit 1; }
    save_session "$R" || { echo "ERROR: cannot write session to $SESSION_DIR." >&2; exit 2; }
    echo "Authenticated: $(echo "$R" | jq -r .email) (uid $(echo "$R" | jq -r .localId), email verified: $(echo "$R" | jq -r .emailVerified)). Session saved (remember-me)."
    exit 0
    ;;
  -Session)
    S=$(read_session)
    [ -n "$S" ] || { echo "ERROR: No saved session - TIDOS requires authentication (Login or Register)." >&2; exit 1; }
    R=$(auth_post "$REFRESH?key=$API_KEY" "{\"grant_type\":\"refresh_token\",\"refresh_token\":$(echo "$S" | jq -r .refreshToken | jq -Rs .)}") || { rm -f "$SESSION_PATH"; echo "ERROR: Saved session expired/revoked - removed. TIDOS requires authentication (Login or Register)." >&2; exit 1; }
    save_session "$R" || { echo "ERROR: cannot write session to $SESSION_DIR." >&2; exit 2; }
    echo "Session validated: $(echo "$R" | jq -r .user_id) (email saved)."
    exit 0
    ;;
  -Verify)
    TOKEN="$2"
    [ -n "$TOKEN" ] || { echo "ERROR: -Verify requires an idToken." >&2; exit 2; }
    R=$(auth_post "$BASE/accounts:lookup?key=$API_KEY" "{\"idToken\":\"$TOKEN\"}") || exit 1
    echo "Token VALID: $(echo "$R" | jq -r '.users[0].email') (uid $(echo "$R" | jq -r '.users[0].localId'))"
    exit 0
    ;;
  *)
    echo "ERROR: No operation selected. Use -Status, -Session, -Login, -Register, -Verify, or -Logout." >&2
    exit 2
    ;;
esac