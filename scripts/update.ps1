# ============================================================================
# TIDOS Update Gate (Windows PowerShell)
# ============================================================================
# Step 0 of START TIDOS: sync TIDOS with GitHub BEFORE any session work.
# Updates an old or detached TIDOS clone to the latest GitHub version, with
# safety guards (v4.1):
#   - only touches a genuine TIDOS checkout that is its own git top-level
#     (never the project that contains it)
#   - never rewrites a custom/fork 'origin' remote
#   - never discards local edits or unpushed commits to system files
#   - never deletes untracked files (generated personas, new work)
#   - memory/ and evolution/ are backed up and restored; any backup or
#     restore failure aborts loudly and keeps the backup
#
# Usage: .\scripts\update.ps1 [[-TidosDir] <string>] [-Branch <string>]
# Exit codes: 0 = ready (updated / already current / offline-continue)
#             2 = ERROR or refused (nothing was changed)
# ============================================================================

param(
    [string]$TidosDir = "",
    [string]$Branch = "main"
)

$CanonicalUrl = "https://github.com/Taedj/TIDOS.git"
if ($env:TIDOS_UPDATE_TEST_URL) { $CanonicalUrl = $env:TIDOS_UPDATE_TEST_URL }  # test harness only
$UserDirs = @("memory", "evolution")

function Fail($msg) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 2
}

function Test-TidosCheckout($dir) {
    foreach ($marker in @("TIDSTART.md", "core/kernel.md", "config/framework.md")) {
        if (-not (Test-Path (Join-Path $dir $marker))) { return $false }
    }
    return $true
}

function Get-NormalUrl($url) {
    return ($url -replace '\.git$', '').TrimEnd('/').ToLowerInvariant()
}

# Step 1: Locate TIDOS directory ("." is never guessed: it may be a user project)
$candidatePaths = @($TidosDir, ".tidos", "TIDOS", "tidos", ".agents/tidos", "../TIDOS", "../.tidos")
$resolvedDir = ""
foreach ($cand in $candidatePaths) {
    if (-not [string]::IsNullOrWhiteSpace($cand) -and (Test-TidosCheckout $cand)) {
        $resolvedDir = (Resolve-Path $cand).Path
        break
    }
}

if ([string]::IsNullOrWhiteSpace($resolvedDir)) {
    Fail "No TIDOS checkout found (needs TIDSTART.md, core/kernel.md, config/framework.md). Pass -TidosDir explicitly."
}

Write-Host "[1/5] TIDOS directory located: $resolvedDir" -ForegroundColor Cyan

Push-Location $resolvedDir
try {
    # Step 2: Ensure this directory is its OWN git repository
    if (-not (Test-Path ".git")) {
        Write-Host "[2/5] No .git repository in '$resolvedDir' (local copy). Initializing git remote..." -ForegroundColor Yellow
        git init -q
        if ($LASTEXITCODE -ne 0) { Fail "git init failed in '$resolvedDir'." }
        git remote add origin $CanonicalUrl
    }

    # Guard: git must resolve to THIS directory, never to a parent project repo
    # (--show-prefix is empty only at the top-level; avoids 8.3 / slash path comparisons)
    $prefix = (git rev-parse --show-prefix 2>$null)
    if ($LASTEXITCODE -ne 0 -or $prefix) {
        $topLevel = (git rev-parse --show-toplevel 2>$null)
        Fail "Git top-level is '$topLevel', not '$resolvedDir'. Refusing to touch another repository."
    }

    # Guard: never rewrite a custom origin (forks, mirrors, user projects)
    $existingOrigin = (git remote get-url origin 2>$null)
    if (-not $existingOrigin) {
        git remote add origin $CanonicalUrl
    } elseif ((Get-NormalUrl $existingOrigin) -ne (Get-NormalUrl $CanonicalUrl)) {
        Fail "origin is '$existingOrigin', not the TIDOS repository. Refusing to force-sync a fork/custom remote. Update it with 'git pull' instead."
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

    # Guard: never discard local work on system files (maintainer / developer mode)
    if ($oldRev -ne "(uninitialized)") {
        $dirty = git status --porcelain --untracked-files=no | Where-Object { $_ -notmatch '^.. "?(memory|evolution)/' }
        if ($dirty) {
            Write-Host "Local modifications to TIDOS system files:" -ForegroundColor Yellow
            $dirty | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
            Write-Host "  -> WARNING: update skipped to protect your work. Commit/push or stash, then rerun. Continuing on local version ($oldRev)." -ForegroundColor Yellow
            exit 0
        }
        $ahead = (git rev-list --count "origin/$Branch..HEAD" 2>$null)
        if ($ahead -and [int]$ahead -gt 0) {
            Write-Host "  -> WARNING: $ahead local commit(s) not on origin/$Branch. Update skipped - push them first. Continuing on local version ($oldRev)." -ForegroundColor Yellow
            exit 0
        }
    }

    Write-Host "[4/5] Update found: $oldRev -> $newRev. Force-updating TIDOS..." -ForegroundColor Yellow

    # Step 4: Back up user memory before the reset - abort on any failure
    $tempBackup = Join-Path ([System.IO.Path]::GetTempPath()) ("tidos_mem_backup_" + [System.Guid]::NewGuid().ToString("N"))
    $backedUp = @()
    try {
        foreach ($d in $UserDirs) {
            if (Test-Path $d) {
                New-Item -ItemType Directory -Path $tempBackup -Force -ErrorAction Stop | Out-Null
                Copy-Item -Path $d -Destination (Join-Path $tempBackup $d) -Recurse -Force -ErrorAction Stop
                $backedUp += $d
            }
        }
    } catch {
        Fail "Memory backup failed ($($_.Exception.Message)). Nothing was changed."
    }

    # Step 5: Sync system files to origin/$Branch (heals detached HEAD in submodules).
    # No 'git clean': untracked files are user work (e.g. generated personas), never upstream files.
    git checkout -B $Branch "origin/$Branch" --force 2>$null
    git reset --hard "origin/$Branch" 2>$null
    $resetOk = ($LASTEXITCODE -eq 0)

    # Restore preserved user memory files (also after a failed reset)
    try {
        foreach ($d in $backedUp) {
            if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force -ErrorAction Stop | Out-Null }
            Copy-Item -Path (Join-Path (Join-Path $tempBackup $d) "*") -Destination $d -Recurse -Force -ErrorAction Stop
        }
    } catch {
        Fail "Memory restore failed ($($_.Exception.Message)). Your backup is kept at: $tempBackup"
    }
    if (Test-Path $tempBackup) { Remove-Item -Path $tempBackup -Recurse -Force -ErrorAction SilentlyContinue }

    if (-not $resetOk) { Fail "git reset --hard origin/$Branch failed (memory restored)." }

    $finalRev = (git rev-parse --short HEAD 2>$null)
    Write-Host "[5/5] Force update successful: $oldRev -> $finalRev" -ForegroundColor Green
    exit 0
} finally {
    Pop-Location
}
