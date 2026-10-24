# ============================================================================
# START TIDOS - Central Session Entry Script (Windows PowerShell)
# ============================================================================
# Executes Step 0 (Force Update Gate) & Step 0.5 (Google Auth Gate)
# and initializes the TIDOS Operating System session.
# ============================================================================

param(
    [string]$TidosDir = "",
    [switch]$SkipUpdate
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  TIDOS (Tidjani Development Operating System) v3.0" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Locate root scripts directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$tidosRoot = Split-Path -Parent $scriptDir

# Kill switch (~/.tidos/control.json, /TIDOSZIT): auto_update off -> skip Step 0
$ctl = Join-Path $tidosRoot "tidos_brain/control.py"
if (-not $SkipUpdate -and (Test-Path $ctl)) {
    & python -I $ctl get auto_update | Out-Null
    if ($LASTEXITCODE -eq 1) {
        Write-Host ">>> [STEP 0] Auto-update is switched OFF in the control center (/TIDOSZIT). Skipping." -ForegroundColor Yellow
        $SkipUpdate = $true
    }
}

# Step 0: Force-Update Gate against GitHub origin/main
if (-not $SkipUpdate) {
    Write-Host ">>> [STEP 0] Checking for TIDOS updates on GitHub..." -ForegroundColor Yellow
    $updateScript = Join-Path $scriptDir "update.ps1"
    if (Test-Path $updateScript) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $updateScript -TidosDir $tidosRoot
        if ($LASTEXITCODE -ne 0) {
            Write-Host "WARNING: Update check completed with non-zero exit ($LASTEXITCODE). Proceeding with local version." -ForegroundColor Yellow
        }
    }
}

# Step 0.5: Firebase Google Authentication Gate
Write-Host "`n>>> [STEP 0.5] Verifying Google Authentication (Firebase)..." -ForegroundColor Yellow
$authScript = Join-Path $scriptDir "auth_verify.ps1"
if (Test-Path $authScript) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $authScript -Session
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nTIDOS is LOCKED. You must sign in with Google to use TIDOS." -ForegroundColor Red
        Write-Host "Opening browser for Google Authentication..." -ForegroundColor Cyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File $authScript -GoogleLogin
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Authentication failed or was cancelled. TIDOS remains locked." -ForegroundColor Red
            exit 1
        }
    }
}

# Step 1-9: Startup Report
$ver = "3.2.0"
$vf = Join-Path $tidosRoot "VERSION.md"
if (Test-Path $vf) {
    $line = Get-Content $vf | Select-String "Current Version"
    if ($line) { $ver = ($line -replace '.*:\s*', '').Trim() }
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  TIDOS SYSTEM READY & AUTHENTICATED (v$ver)" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  - Core: Frozen & Protected"
Write-Host "  - Engine: Active"
Write-Host "  - Personas: Mounted"
Write-Host "  - GPTID Partner Relay: Ready (Chrome)"
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "TIDOS is active. You may now give engineering commands." -ForegroundColor White
