# ============================================================================
# TIDOS Community Contribution Sync (Windows PowerShell)
# ============================================================================
# Allows cloned TIDOS users to safely contribute newly learned expert personas
# and architectural patterns back to the central repository (Taedj/TIDOS).
#
# Automatically runs the Privacy & Sanitization Firewall (sanitizer.py) before
# staging, guaranteeing ZERO leakage of user code, personal data, or credentials.
#
# Usage:
#   .\scripts\community_sync.ps1
#   .\scripts\community_sync.ps1 -Persona <path_to_persona>
#   .\scripts\community_sync.ps1 -DryRun
#
# Exit: 0 = PR opened or patch exported, 1 = blocked, 2 = error
# ============================================================================

param(
    [string]$Persona,
    [string]$Message,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
function Fail($msg, $code = 2) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit $code
}

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..'))
Set-Location $repo

if (-not (Test-Path '.git')) {
    Fail "Not a git repo: $repo" 2
}

$CanonicalRepo = 'Taedj/TIDOS'

# --- 1. Detect candidate persona if not specified -----------------------------
function Find-CandidatePersona {
    $untracked = git status --porcelain -- personas
    $cand = $untracked | Select-String '^\?\?\s+personas/tidos.+\.md$'
    if ($cand) {
        return ($cand[0].Line -replace '^\?\?\s+', '').Trim()
    }
    $modified = $untracked | Select-String '^ M\s+personas/tidos.+\.md$'
    if ($modified) {
        return ($modified[0].Line -replace '^ M\s+', '').Trim()
    }
    return $null
}

if (-not $Persona) {
    $Persona = Find-CandidatePersona
}
if (-not $Persona) {
    Fail 'No new or modified persona detected. Expected personas/tidos*.md to contribute.' 1
}

if (-not (Test-Path $Persona)) {
    Fail "Persona file not found: $Persona" 2
}

# --- 2. Privacy & Sanitization Firewall Audit ---------------------------------
Write-Host "[1/4] Running TIDOS Privacy Firewall audit on $Persona..." -ForegroundColor Cyan
$sanitizerPath = Join-Path $repo 'scripts/sanitizer.py'
& python $sanitizerPath --check $Persona
if ($LASTEXITCODE -ne 0) {
    Fail "Privacy Firewall REJECTED contribution: Secrets or prohibited patterns found in $Persona. Aborting." 2
}
Write-Host '[✓] Privacy Firewall PASSED: Zero secrets, PII, or forbidden code found.' -ForegroundColor Green

# --- 3. Prepare Contribution Metadata -----------------------------------------
$personaName = (Split-Path $Persona -Leaf) -replace '\.md$', ''
$branchName = "contrib/$personaName-" + (Get-Date -Format 'yyyyMMdd-HHmmss')
if (-not $Message) {
    $Message = "feat(community): contribute $personaName expert persona to central brain"
}

Write-Host "[2/4] Target Persona: $Persona" -ForegroundColor Cyan
Write-Host "      Commit Message: $Message" -ForegroundColor DarkGray
Write-Host "      Upstream Target: $CanonicalRepo" -ForegroundColor DarkGray

if ($DryRun) {
    Write-Host '[dry-run] Dry run complete. Zero git mutations performed.' -ForegroundColor Yellow
    exit 0
}

# --- 4. Submit via GitHub CLI (gh) or Export Patch ----------------------------
$hasGh = (Get-Command gh -ErrorAction SilentlyContinue)

if ($hasGh) {
    Write-Host "[3/4] GitHub CLI detected. Preparing Pull Request to $CanonicalRepo..." -ForegroundColor Cyan
    $ghAuth = & gh auth status 2>&1
    if ($LASTEXITCODE -eq 0) {
        $currentBranch = (git branch --show-current).Trim()
        try {
            git checkout -b $branchName | Out-Null
            git add $Persona
            git commit -m $Message | Out-Null
            Write-Host '[4/4] Submitting Pull Request upstream...' -ForegroundColor Cyan
            $prBody = 'Auto-generated expert persona contributed from field usage via TIDOS Community Sync. Audited and sanitized by TIDOS Privacy Firewall.'
            $prUrl = & gh pr create --repo $CanonicalRepo --title $Message --body $prBody
            if ($LASTEXITCODE -eq 0) {
                Write-Host "SUCCESS! Pull Request submitted: $prUrl" -ForegroundColor Green
                git checkout $currentBranch | Out-Null
                exit 0
            } else {
                Write-Host 'Notice: Direct upstream PR creation failed (fork may be required). Exporting patch bundle.' -ForegroundColor Yellow
            }
        } finally {
            git checkout $currentBranch 2>$null | Out-Null
        }
    }
}

# Fallback: Export Sanitized Contribution Bundle
Write-Host '[3/4] Packaging Sanitized Contribution Bundle...' -ForegroundColor Cyan
$contribDir = Join-Path $repo 'evolution/contributions'
if (-not (Test-Path $contribDir)) {
    New-Item -ItemType Directory -Path $contribDir | Out-Null
}

$bundlePath = Join-Path $contribDir "$personaName.bundle.md"
$personaContent = Get-Content $Persona -Raw
$dateStr = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$bundleLines = @(
    "# TIDOS Community Contribution: $personaName",
    "Date: $dateStr",
    "Source File: $Persona",
    '',
    '---',
    '',
    $personaContent
)
[System.IO.File]::WriteAllLines($bundlePath, $bundleLines, [System.Text.Encoding]::UTF8)

Write-Host "[4/4] Contribution bundle exported to: $bundlePath" -ForegroundColor Green
Write-Host "You can share this bundle or submit an Issue/Discussion at https://github.com/$CanonicalRepo" -ForegroundColor Green
exit 0
