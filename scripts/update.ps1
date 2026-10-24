# ============================================================================
# TIDOS Update Gate (Windows PowerShell)
# ============================================================================
# Step 0 of START TIDOS. Checks GitHub for a newer TIDOS and installs it ONLY when
# approved (-Apply). Default channel "release" follows the newest vX.Y.Z tag;
# "main" follows the main branch (maintainers). TIDOS_REQUIRE_SIGNED=1 refuses
# tags that are unsigned or fail `git verify-tag`.
#
# Safety guards (v4.1):
#   - only touches a genuine TIDOS checkout that is its own git top-level
#   - never rewrites a custom/fork 'origin' remote
#   - never discards local edits or commits that are not in the target version
#   - never deletes untracked files (generated personas, new work)
#   - memory/ and evolution/ are backed up and restored; failures abort loudly
#
# Usage: .\scripts\update.ps1 [[-TidosDir] <dir>] [-Channel release|main] [-Apply]
# Exit codes: 0 = ready (up to date / update reported / applied / offline)
#             2 = ERROR or refused (nothing was changed)
# ============================================================================

param(
    [string]$TidosDir = "",
    [ValidateSet("release", "main")][string]$Channel = "release",
    [switch]$Apply
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
    # (--show-prefix is empty only at the top-level; avoids 8.3 / slash path comparisons)
    $prefix = (git rev-parse --show-prefix 2>$null)
    if ($LASTEXITCODE -ne 0 -or $prefix) {
        $topLevel = (git rev-parse --show-toplevel 2>$null)
        Fail "Git top-level is '$topLevel', not '$resolvedDir'. Refusing to touch another repository."
    }
    $existingOrigin = (git remote get-url origin 2>$null)
    if (-not $existingOrigin) {
        git remote add origin $CanonicalUrl
    } elseif ((Get-NormalUrl $existingOrigin) -ne (Get-NormalUrl $CanonicalUrl)) {
        Fail "origin is '$existingOrigin', not the TIDOS repository. Refusing to force-sync a fork/custom remote. Update it with 'git pull' instead."
    }

    $oldRev = (git rev-parse --short HEAD 2>$null)
    if (-not $oldRev) { $oldRev = "(uninitialized)" }

    # Step 3: Fetch and pick the target version
    Write-Host "[3/5] Checking GitHub ($Channel channel, current: $oldRev)..."
    git fetch origin main --prune --tags --force 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  -> WARNING: GitHub unreachable or offline. Continuing on local version ($oldRev)." -ForegroundColor Yellow
        exit 0
    }
    if ($Channel -eq "release") {
        $target = (git tag -l "v*" --sort=-v:refname | Select-Object -First 1)
        if (-not $target) {
            Write-Host "  -> No release tag published yet. Staying on $oldRev (use -Channel main to follow main)." -ForegroundColor Yellow
            exit 0
        }
    } else {
        $target = "origin/main"
    }
    $newRev = (git rev-parse --short "$target^{commit}" 2>$null)
    if (-not $newRev) { Fail "Cannot resolve '$target'." }
    $headFull = (git rev-parse HEAD 2>$null)
    $targetFull = (git rev-parse "$target^{commit}")
    if ($headFull -eq $targetFull) {
        Write-Host "[4/5] Already on $target ($newRev). No update needed." -ForegroundColor Green
        Write-Host "[5/5] TIDOS is ready." -ForegroundColor Green
        exit 0
    }
    git merge-base --is-ancestor $targetFull HEAD 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[4/5] Local version ($oldRev) already contains $target. No update needed." -ForegroundColor Green
        exit 0
    }

    # Signature check (release tags)
    $signature = "not a tag"
    if ($Channel -eq "release") {
        git verify-tag $target 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { $signature = "valid signature" }
        elseif ((git cat-file -t $target 2>$null) -eq "tag" -and (git cat-file -p $target | Select-String "BEGIN (PGP|SSH) SIGNATURE")) { $signature = "INVALID or untrusted signature" }
        else { $signature = "unsigned" }
        if ($env:TIDOS_REQUIRE_SIGNED -eq "1" -and $signature -ne "valid signature") {
            Fail "Release $target is $signature and TIDOS_REQUIRE_SIGNED=1. Not updating."
        }
    }

    # Step 4: Report the update (always) and stop unless approved
    $commits = @(git log --oneline "HEAD..$targetFull" 2>$null)
    $stat = (git diff --shortstat HEAD $targetFull 2>$null)
    Write-Host "[4/5] Update available: $oldRev -> $target ($newRev), tag: $signature" -ForegroundColor Yellow
    Write-Host "      $($commits.Count) commit(s);$stat"
    $commits | Select-Object -First 15 | ForEach-Object { Write-Host "        $_" }
    if (-not $Apply) {
        Write-Host "  -> NOT installed. Review the changes above, then approve with: START TIDOS -ApplyUpdate (or scripts/update.ps1 -Apply)." -ForegroundColor Yellow
        exit 0
    }

    # Guard: never discard local work that is not part of the target version
    if ($oldRev -ne "(uninitialized)") {
        $dirty = git status --porcelain --untracked-files=no | Where-Object { $_ -notmatch '^.. "?(memory|evolution)/' }
        if ($dirty) {
            Write-Host "Local modifications to TIDOS system files:" -ForegroundColor Yellow
            $dirty | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
            Write-Host "  -> WARNING: update skipped to protect your work. Commit/push or stash, then rerun. Continuing on local version ($oldRev)." -ForegroundColor Yellow
            exit 0
        }
        $ahead = (git rev-list --count "$targetFull..HEAD" 2>$null)
        if ($ahead -and [int]$ahead -gt 0) {
            Write-Host "  -> WARNING: $ahead local commit(s) are not in $target. Update skipped - push or merge them first. Continuing on local version ($oldRev)." -ForegroundColor Yellow
            exit 0
        }
    }

    # Step 5: Back up user memory, move to the target, restore memory
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

    # No 'git clean': untracked files are user work (e.g. generated personas), never upstream files.
    if ($Channel -eq "main") {
        git checkout -B main $targetFull --force 2>$null
    } else {
        git checkout --detach $targetFull --force 2>$null
    }
    git reset --hard $targetFull 2>$null
    $resetOk = ($LASTEXITCODE -eq 0)

    try {
        foreach ($d in $backedUp) {
            if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force -ErrorAction Stop | Out-Null }
            Copy-Item -Path (Join-Path (Join-Path $tempBackup $d) "*") -Destination $d -Recurse -Force -ErrorAction Stop
        }
    } catch {
        Fail "Memory restore failed ($($_.Exception.Message)). Your backup is kept at: $tempBackup"
    }
    if (Test-Path $tempBackup) { Remove-Item -Path $tempBackup -Recurse -Force -ErrorAction SilentlyContinue }
    if (-not $resetOk) { Fail "git reset --hard $target failed (memory restored)." }

    $finalRev = (git rev-parse --short HEAD 2>$null)
    Write-Host "[5/5] Updated: $oldRev -> $target ($finalRev)" -ForegroundColor Green
    exit 0
} finally {
    Pop-Location
}
