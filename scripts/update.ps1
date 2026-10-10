# ============================================================================
# TIDOS Update Gate (Windows PowerShell)
# ============================================================================
# Step 0 of START TIDOS: force-sync TIDOS with GitHub BEFORE any session work.
# Automatically updates any old or detached TIDOS clone to the latest GitHub version.
# Non-destructive memory safety: user profile and memory/ are preserved while
# OS and system files are force-updated to origin/main.
#
# Usage: .\scripts\update.ps1 [[-TidosDir] <string>] [-Branch <string>]
# Exit codes: 0 = ready (updated / already current / offline-continue)
#             2 = ERROR (not a TIDOS checkout)
# ============================================================================

param(
    [string]$TidosDir = "",
    [string]$Branch = "main"
)

$CanonicalUrl = "https://github.com/Taedj/TIDOS.git"

function Fail($msg) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 2
}

# Step 1: Locate TIDOS directory
$candidatePaths = @($TidosDir, ".tidos", "TIDOS", "tidos", ".", ".agents/tidos", "../TIDOS", "../.tidos")
$resolvedDir = ""
foreach ($cand in $candidatePaths) {
    if (-not [string]::IsNullOrWhiteSpace($cand)) {
        $checkPath = Join-Path $cand "TIDSTART.md"
        if (Test-Path $checkPath) {
            $resolvedDir = $cand
            break
        }
    }
}

if ([string]::IsNullOrWhiteSpace($resolvedDir)) {
    Fail "No TIDOS checkout found. Pass -TidosDir explicitly or ensure TIDSTART.md exists."
}

Write-Host "[1/5] TIDOS directory located: $resolvedDir" -ForegroundColor Cyan

# Step 2: Ensure Git environment & remote origin
$gitPath = Join-Path $resolvedDir ".git"
if (-not (Test-Path $gitPath)) {
    Write-Host "[2/5] No .git repository in '$resolvedDir' (local copy). Initializing git remote..." -ForegroundColor Yellow
    Push-Location $resolvedDir
    try {
        git init -q 2>$null
        git remote add origin $CanonicalUrl 2>$null
    } finally {
        Pop-Location
    }
}

Push-Location $resolvedDir
try {
    # Verify or configure remote origin
    $existingOrigin = (git remote get-url origin 2>$null)
    if (-not $existingOrigin) {
        git remote add origin $CanonicalUrl 2>$null
    } elseif ($existingOrigin -ne $CanonicalUrl -and $existingOrigin -ne ($CanonicalUrl -replace '\.git$', '')) {
        # Ensure origin points to canonical TIDOS repository
        git remote set-url origin $CanonicalUrl 2>$null
    }

    $oldRev = (git rev-parse --short HEAD 2>$null)
    if (-not $oldRev) { $oldRev = "(uninitialized)" }

    # Step 3: Fetch latest from GitHub
    Write-Host "[3/5] Fetching origin/$Branch from GitHub... (current: $oldRev)"
    git fetch origin $Branch --prune --tags 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  -> WARNING: GitHub unreachable or offline. Continuing on local version ($oldRev)." -ForegroundColor Yellow
        exit 0
    }

    $newRev = (git rev-parse --short "origin/$Branch" 2>$null)
    if (-not $newRev) {
        Fail "Remote branch 'origin/$Branch' could not be resolved from $CanonicalUrl."
    }

    if ($oldRev -eq $newRev) {
        Write-Host "[4/5] Already up-to-date with GitHub ($newRev). No update needed." -ForegroundColor Green
        Write-Host "[5/5] TIDOS is ready." -ForegroundColor Green
        exit 0
    }

    Write-Host "[4/5] Update found: $oldRev -> $newRev. Force-updating TIDOS..." -ForegroundColor Yellow

    # Step 4: Memory preservation backup before force reset
    $tempBackup = Join-Path ([System.IO.Path]::GetTempPath()) ("tidos_mem_backup_" + [System.Guid]::NewGuid().ToString("N"))
    $memoryDir = Join-Path "." "memory"
    $evolutionDir = Join-Path "." "evolution"
    $hasMem = Test-Path $memoryDir
    $hasEvo = Test-Path $evolutionDir

    if ($hasMem -or $hasEvo) {
        New-Item -ItemType Directory -Path $tempBackup -Force | Out-Null
        if ($hasMem) { Copy-Item -Path $memoryDir -Destination (Join-Path $tempBackup "memory") -Recurse -Force 2>$null }
        if ($hasEvo) { Copy-Item -Path $evolutionDir -Destination (Join-Path $tempBackup "evolution") -Recurse -Force 2>$null }
    }

    # Step 5: Force sync - reset hard to origin/$Branch & clean untracked deprecated files
    # Force checkout branch to heal any detached HEAD states (e.g. submodules)
    git checkout -B $Branch "origin/$Branch" --force 2>$null
    git reset --hard "origin/$Branch" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Fail "git reset --hard origin/$Branch failed."
    }

    # Clean obsolete / untracked files while protecting memory & evolution
    git clean -fd -e memory/ -e evolution/ -e .tidos/ 2>$null

    # Restore preserved user memory files
    if (Test-Path $tempBackup) {
        if (Test-Path (Join-Path $tempBackup "memory")) {
            Copy-Item -Path (Join-Path $tempBackup "memory\*") -Destination $memoryDir -Recurse -Force 2>$null
        }
        if (Test-Path (Join-Path $tempBackup "evolution")) {
            Copy-Item -Path (Join-Path $tempBackup "evolution\*") -Destination $evolutionDir -Recurse -Force 2>$null
        }
        Remove-Item -Path $tempBackup -Recurse -Force -ErrorAction SilentlyContinue 2>$null
    }

    $finalRev = (git rev-parse --short HEAD 2>$null)
    Write-Host "[5/5] Force update successful: $oldRev -> $finalRev" -ForegroundColor Green
    exit 0
} finally {
    Pop-Location
}

