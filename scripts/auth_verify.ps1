# ============================================================================
# TIDOS Firebase Auth Helper (Windows PowerShell)
# ============================================================================
# Lightweight REST client for TIDOS framework auth against the Firebase
# project defined in config/firebase.md. Verifies settled ID tokens and
# performs email/password sign-in. NEVER prints or logs tokens.
#
# Config: FIREBASE_API_KEY env var (or .env file) - the public web API key.
#
# Usage:
#   .\scripts\auth_verify.ps1 -Verify <idToken>            # verify an ID token
#   .\scripts\auth_verify.ps1 -Login -Email <e> -Password <p>   # email/pass sign-in
#   .\scripts\auth_verify.ps1 -Status                        # env/config self-check
#
# Exit codes: 0 = verified/authenticated/ok
#             1 = auth failed (bad token / wrong credentials / not enabled)
#             2 = configuration error
# ============================================================================

param(
    [string]$Verify,
    [switch]$Login,
    [string]$Email,
    [string]$Password,
    [switch]$Status
)

function Fail($msg, $code) { Write-Error $msg; exit $code }

# Load FIREBASE_API_KEY from env or .env (never committed)
$apiKey = $env:FIREBASE_API_KEY
if (-not $apiKey) {
    $envFile = Join-Path $PSScriptRoot "..\.env"
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            if ($_ -match '^\s*FIREBASE_API_KEY\s*=\s*(.+?)\s*$') { $apiKey = $Matches[1].Trim("'", '"') }
        }
    }
}
if (-not $apiKey) { Fail "FIREBASE_API_KEY not set (env or .env). See docs/firebase_auth.md." 2 }

if ($Status) {
    Write-Host "Firebase Auth Helper: OK (API key present)."
    Write-Host "Project reference: config/firebase.md (tidos-framework)."
    exit 0
}

if ($Login) {
    if (-not $Email -or -not $Password) { Fail "Login requires -Email and -Password." 2 }
    $body = @{ email = $Email; password = $Password; returnSecureToken = $true } | ConvertTo-Json
    try {
        $r = Invoke-RestMethod -Uri "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=$apiKey" `
            -Method Post -ContentType "application/json" -Body $body -ErrorAction Stop
    } catch { Fail "Sign-in failed: $($_.Exception.Message)" 1 }
    Write-Host "Signed in as: $($r.email) (uid $($r.localId), verified: $($r.emailVerified))"
    Write-Host "Do NOT print idToken. Session token stored in this shell scope only."
    exit 0
}

if ($Verify) {
    $body = @{ idToken = $Verify } | ConvertTo-Json
    try {
        $r = Invoke-RestMethod -Uri "https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=$apiKey" `
            -Method Post -ContentType "application/json" -Body $body -ErrorAction Stop
    } catch { Fail "Token verification failed: $($_.Exception.Message)" 1 }
    $u = $r.users[0]
    Write-Host "Token VALID: $($u.email) (uid $($u.localId), verified: $($u.emailVerified), provider: $($u.providerId -join ','))"
    exit 0
}

Fail "No operation selected. Use -Verify, -Login, or -Status." 2