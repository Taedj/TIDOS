# ============================================================================
# START TIDOS - Central Session Entry Script (Windows PowerShell)
# ============================================================================
# Executes Step 0 (Force Update Gate) & Step 0.5 (Google Auth Gate)
# and initializes the TIDOS Operating System session.
# ============================================================================

param(
    [string]$TidosDir = "",
    [switch]$SkipUpdate,
    [string]$Tool = "auto",      # claude-code | opencode | gemini-cli | ... (auto-detected when possible)
    [string]$Model = "auto",     # exact model id if the agent knows it; otherwise TIDOS detects it
    [switch]$ApplyUpdate,        # install the reported update (the user approved it)
    [ValidateSet("release", "main")][string]$Channel = "release"
)

$projectDir = (Get-Location).Path   # the user's project: where START TIDOS was run

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
    Write-Host ">>> [STEP 0] Checking for TIDOS updates on GitHub (installed only when approved)..." -ForegroundColor Yellow
    $updateScript = Join-Path $scriptDir "update.ps1"
    if (Test-Path $updateScript) {
        $updateArgs = @("-TidosDir", $tidosRoot, "-Channel", $Channel)
        if ($ApplyUpdate) { $updateArgs += "-Apply" }
        & powershell -NoProfile -ExecutionPolicy Bypass -File $updateScript @updateArgs
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

# Step 1: version + session mode (LEARN on strong models, GUIDE on weak/free models)
$ver = "unknown"
$vf = Join-Path $tidosRoot "VERSION.md"
if (Test-Path $vf) {
    $line = Get-Content $vf | Select-String "Current Version"
    if ($line) { $ver = ($line -replace '.*:\s*', '').Trim() }
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  TIDOS READY (v$ver)" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
$session = Join-Path $tidosRoot "tidos_session\__main__.py"
& python -I $session start --tool $Tool --model $Model --project $projectDir
Write-Host "Follow the TIDOS brief above for this whole session." -ForegroundColor White
