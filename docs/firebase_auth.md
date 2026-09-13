# TIDOS Firebase Authentication Integration

Firebase-based authentication for the TIDOS framework: users authenticate with **Google Sign-In** or
**email/password**, and TIDOS agents verify sessions before privileged operations.

**Canonical config**: `config/firebase.md` (project `tidos-framework`).
**Helpers**: `scripts/auth_verify.ps1` (Windows), `scripts/auth_verify.sh` (Linux/macOS, requires `jq` + `curl`).
**Boot gate**: mandatory Step 0.5 — see `TIDSTART.md`.

---

## 1. Current Setup Status (2026-09-13)

| Item | Status |
|---|---|
| Firebase project `tidos-framework` | DONE |
| Web app registered (SDK config captured) | DONE |
| Auth backend provisioned (console Get Started) | DONE |
| Email/Password provider enabled | DONE (verified: `INVALID_LOGIN_CREDENTIALS`, not 404) |
| Google Sign-In provider enabled | DONE (per console; client-side verify needs a real Google token) |

## 2. One-Time Console Setup (can't be automated — no CLI/API for fresh projects)

Firebase only provisions a new project's Authentication service when its console tab is first opened.
Complete these steps in the browser:

1. Open <https://console.firebase.google.com/project/tidos-framework/authentication> → **Get Started**
   (auto-provisions the Auth backend).
2. **Sign-in method** tab → **Email/Password** → **Enable** → **Save**. Set the following toggles as desired:
   - *Allow users to sign in with verified email addresses only* (recommended ON for the framework).
   - *Password reset* — enabled by default once Email/Password is on.
3. **Sign-in method** tab → **Google** → **Enable**.
   - This creates/links a Google Cloud OAuth consent screen. On first activation Firebase
     auto-creates a web client for the given authorized domains (add `tidos-framework.firebaseapp.com`
     and any custom domain).
4. (Optional but recommended) **Users** tab → manually create your first admin test user
   (email/password) to validate the helpers.

After step 1, run `.\scripts\auth_verify.ps1 -Status` (or `./scripts/auth_verify.sh -Status`) — it should
report OK. Then test email/password with a real user; a settled ID token is required to test `-Verify`.

## 3. Environment (never commit secrets)

```bash
# .env at TIDOS root (gitignored) — the web API key is public but kept out of git by convention
FIREBASE_API_KEY=AIzaSyDzbyda_7ygLaWtqjLZtiHrqSd0b_CYBQk
```

- The **web** `apiKey`/`authDomain`/`appId` (in `config/firebase.md`) are public by design.
- **Service-account keys** and **OAuth client secrets** must NEVER be committed — `.env` or a vault only.
- `config/firebase.md` contains no secrets; update it only for non-secret metadata.

## 4. Usage

### Mandatory Auth Gate (START TIDOS Step 0.5)

Signature desired. On every boot, `auth_verify.ps1/.sh -Session` restores the saved session (remember-me,
refresh token from `~/.tidos`, validated against Firebase). exit 0 = authenticated, boot proceeds; exit 1 =
**block boot** and ask the user to **Login** (existing account) or **Register** (new account + verification
email); exit 2 or network failure = warn and continue (auth never hard-blocks when Firebase is unreachable
or `FIREBASE_API_KEY` is unset).

### Sign in / create account

```powershell
.\scripts\auth_verify.ps1 -Login -Email user@example.com -Password '****'
.\scripts\auth_verify.ps1 -Register -Email user@example.com -Password '****'
```

### Validate saved session / clear it

```powershell
.\scripts\auth_verify.ps1 -Session     # remember-me check (used by boot gate)
.\scripts\auth_verify.ps1 -Logout      # delete ~\.tidos\tidos-session.json
```

### Verify a settled (foreign) ID token

```powershell
.\scripts\auth_verify.ps1 -Verify $env:TIDOS_ID_TOKEN
```

### In AI-agent workflows (TIDOS gateway pattern)

1. The user signs in via FirebaseUI (web/mobile) or the helpers above and supplies an **ID token**.
2. The TIDOS agent verifies the token (`auth_verify -Verify` → exit 0 + uid/email) **before**
   privileged operations (`TIDOS AUTH` directive — see `commands/session_commands.md`).
3. The token is treated as untrusted, never logged, and its `uid`/`email` is attributed to session state.
4. Sessions can additionally be gated locally (offline) — the framework NEVER requires Firebase reachability at boot.

## 4b. Session Storage & Security

## 4b. Session Storage & Security

- The refresh token lives in `~/.tidos/tidos-session.json` (OS user profile — **outside any repository**, chmod 600 on Unix, never committed; there is no `.gitignore` needed and the repo never contains it).
- `idToken` is refreshed and re-persisted on each `-Session`; tokens are never printed by helpers.
- `scripts/auth_verify.ps1` stores the session in `$HOME\.tidos\tidos-session.json`; the bash variant in `$HOME/.tidos/tidos-session.json`.
- Clear any machine-level session with `auth_verify -Logout` or `TIDOS AUTH logout`.

## 5. Security Rules

- Zero-trust: every ID token verified against Firebase on use; never trust a locally cached "logged in" flag.
- Never write tokens, passwords, or PII to logs (`rules/security_rules.md` Gate 3/4).
- Email/password: enforce email verification for privileged scope; rate-limit sign-in attempts.
- Google Sign-In: keep the OAuth client's authorized domains minimal.
- Rotate/revoke the API key or a user in the Firebase console at any time.

## 6. Troubleshooting

| Symptom | Cause / Fix |
|---|---|
| `accounts:lookup` 400 `EMAIL_NOT_FOUND` / 401 | Provider disabled or user doesn't exist — check console Sign-in method |
| `-Status` fails (exit 2) | `FIREBASE_API_KEY` missing in env/.env |
| Admin API 404 during setup | Auth backend not provisioned — complete console Step 1 |
| Bash helper fails on `jq` | `sudo apt install jq` (Debian) / `brew install jq` (macOS) |