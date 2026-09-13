# ============================================================================
# TIDOS Firebase Auth Helper (Windows PowerShell)
# ============================================================================
# Lightweight REST client for TIDOS framework auth against the Firebase
# project defined in config/firebase.md.
#
# Config: FIREBASE_API_KEY env var (or .env file) - the public web API key.
# Session: persisted in $HOME\.tidos\tidos-session.json (OUTSIDE any repo,
#          never committed). Contains refresh token; idToken is never printed.
#
# Usage:
#   .\scripts\auth_verify.ps1 -Status                       # config + session self-check
#   .\scripts\auth_verify.ps1 -Session                      # validate saved session (remember-me)
#   .\scripts\auth_verify.ps1 -Login -Email <e> -Password <p>    # email/password sign-in
#   .\scripts\auth_verify.ps1 -Register -Email <e> -Password <p> # create account
#   .\scripts\auth_verify.ps1 -Verify <idToken>             # verify an external ID token
#   .\scripts\auth_verify.ps1 -Logout                       # clear saved session (no API key needed)
#
# Exit codes: 0 = ready/valid/authenticated
#             1 = auth failed (bad token / wrong credentials / no session) - re-auth needed
#             2 = configuration error (missing API key / no operation selected)
# ============================================================================

param(
    [string]$Verify,
    [switch]$Login,
    [switch]$Register,
    [switch]$Session,
    [switch]$Logout,
    [string]$Email,
    [string]$Password,
    [switch]$Status
)

function Fail($msg, $code) { Write-Error $msg; exit $code }

# --- Session storage (OS user profile - outside any repository) ---------------
function Get-SessionPath { return Join-Path (Join-Path $HOME ".tidos") "tidos-session.json" }

function Read-Session {
    $p = Get-SessionPath
    if (-not (Test-Path $p)) { return $null }
    try { return (Get-Content $p -Raw | ConvertFrom-Json) } catch { return $null }
}

function Write-Session($s) {
    $dir = Split-Path (Get-SessionPath) -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $s | ConvertTo-Json | Set-Content (Get-SessionPath) -Encoding UTF8
}

# --- Config-independent operations (Logout, Status — run before API key load) --
if ($Logout) {
    $p = Get-SessionPath
    if (Test-Path $p) { Remove-Item $p -Force; Write-Host "Session cleared. Disconnected from the TIDOS account." }
    else { Write-Host "No saved session. Already disconnected." }
    exit 0
}

if ($Status) {
    $envKey = $env:FIREBASE_API_KEY
    if (-not $envKey) {
        $envFile = Join-Path $PSScriptRoot "..\.env"
        if (Test-Path $envFile) { $envKey = Get-Content $envFile | Where-Object { $_ -match '^\s*FIREBASE_API_KEY\s*=' } | Select-Object -First 1 }
    }
    if (-not $envKey) { Write-Host "FIREBASE_API_KEY: NOT SET (set env var or add to .env)" }
    else { Write-Host "FIREBASE_API_KEY: present." }
    Write-Host "Project reference: config/firebase.md (tidos-framework)."
    $s = Read-Session
    if ($s) { Write-Host "Saved session: present ($($s.email)) - use -Session to validate, -Logout to disconnect." }
    else { Write-Host "Saved session: none." }
    exit 0
}

# --- API key required below this line (env var, then .env at repo root) ------
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

# --- REST helper ---------------------------------------------------------------
function Auth-Post($url, $body) {
    try {
        return Invoke-RestMethod -Uri $url -Method Post -ContentType "application/json" -Body $body -ErrorAction Stop
    } catch {
        $msg = "HTTP $([int]$_.Exception.Response.StatusCode)"
        try {
            $sr = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $txt = $sr.ReadToEnd() | ConvertFrom-Json
            if ($txt.error.message) { $msg = $txt.error.message }
        } catch { }
        throw "Auth API error: $msg"
    }
}

# --- Endpoint URLs (require API key) -------------------------------------------
$signInUrl   = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=$apiKey"
$signUpUrl   = "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=$apiKey"
$lookupUrl   = "https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=$apiKey"
$verifyMail  = "https://identitytoolkit.googleapis.com/v1/accounts:sendOAuthVerificationEmail?key=$apiKey"
$refreshUrl  = "https://securetoken.googleapis.com/v1/token?key=$apiKey"

# --- Register (new account) ----------------------------------------------------
if ($Register) {
    if (-not $Email -or -not $Password) { Fail "Register requires -Email and -Password (min 6 chars)." 2 }
    try {
        $r = Auth-Post $signUpUrl (@{ email = $Email; password = $Password } | ConvertTo-Json)
        try { Auth-Post $verifyMail (@{ requestType = "VERIFY_EMAIL"; idToken = $r.idToken } | ConvertTo-Json) | Out-Null } catch { }
        Write-Session @{ refreshToken = $r.refreshToken; idToken = $r.idToken; localId = $r.localId; email = $r.email }
        Write-Host "Account created: $($r.email) (uid $($r.localId)). Verification email sent. Session saved (remember-me)."
        exit 0
    } catch { Fail $_.Exception.Message 1 }
}

# --- Login (email/password) ----------------------------------------------------
if ($Login) {
    if (-not $Email -or -not $Password) { Fail "Login requires -Email and -Password." 2 }
    try {
        $r = Auth-Post $signInUrl (@{ email = $Email; password = $Password; returnSecureToken = $true } | ConvertTo-Json)
        Write-Session @{ refreshToken = $r.refreshToken; idToken = $r.idToken; localId = $r.localId; email = $r.email; emailVerified = $r.emailVerified }
        Write-Host "Authenticated: $($r.email) (uid $($r.localId), email verified: $($r.emailVerified)). Session saved (remember-me)."
        exit 0
    } catch {
        if ($_.Exception.Message -match "INVALID_LOGIN_CREDENTIALS") { Fail "Wrong email/password, or no account under this email. Use -Register to create one." 1 }
        Fail $_.Exception.Message 1
    }
}

# --- Session (remember-me boot check) ------------------------------------------
if ($Session) {
    $s = Read-Session
    if (-not $s) { Fail "No saved session - TIDOS requires authentication (Login or Register)." 1 }
    try {
        $r = Auth-Post $refreshUrl (@{ grant_type = "refresh_token"; refresh_token = $s.refreshToken } | ConvertTo-Json)
        $uid = $r.user_id; $email = $s.email
        try {
            $lk = Auth-Post $lookupUrl (@{ idToken = $r.id_token } | ConvertTo-Json)
            $email = $lk.users[0].email
        } catch { }
        Write-Session @{ refreshToken = $r.refresh_token; idToken = $r.id_token; localId = $uid; email = $email }
        Write-Host "Session validated: $email (uid $uid)."
        exit 0
    } catch {
        $p = Get-SessionPath; if (Test-Path $p) { Remove-Item $p -Force }
        Fail "Saved session expired/revoked - removed. TIDOS requires authentication (Login or Register)." 1
    }
}

# --- Verify (external ID token) ------------------------------------------------
if ($Verify) {
    try {
        $r = Auth-Post $lookupUrl (@{ idToken = $Verify } | ConvertTo-Json)
        $u = $r.users[0]
        Write-Host "Token VALID: $($u.email) (uid $($u.localId), verified: $($u.emailVerified), provider: $($u.providerId -join ','))"
        exit 0
    } catch { Fail $_.Exception.Message 1 }
}

Fail "No operation selected. Use -Status, -Session, -Login, -Register, -Verify, or -Logout." 2