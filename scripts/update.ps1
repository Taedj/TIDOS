# ============================================================================
# TIDOS Update Gate (Windows PowerShell)
# ============================================================================
# Step 0 of START TIDOS: force-sync TIDOS with GitHub BEFORE any session work.
# Memory-safe force: OS files are reset to the remote, but the gate ABORTS
# (instead of wiping) when uncommitted memory/ or evolution/ changes exist.
# Never blocks boot when the network or remote is unreachable.
#
# Usage: .\scripts\update.ps1 [[-TidosDir] <string>] [-Branch <string>]
# Exit codes: 0 = ready (updated / already current / offline-continue)
#             1 = BLOCKED (uncommitted memory/evolution changes - commit first)
#             2 = ERROR (not a TIDOS checkout)
# ============================================================================

param(
    [string]$TidosDir = "",
    [string]$Branch = "main"
)

function Fail($msg) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 2
}

# Step 1: Locate the TIDOS checkout (.tidos submodule -> explicit dir -> current dir)
if ([string]::IsNullOrWhiteSpace($TidosDir)) {
    if (Test-Path (Join-Path ".tidos" "TIDSTART.md")) {
        $TidosDir = ".tidos"
    } elseif (Test-Path "TIDSTART.md") {
        $TidosDir = "."
    } else {
        Fail "No TIDOS checkout found. Pass -TidosDir explicitly."
    }
}
if (-not (Test-Path (Join-Path $TidosDir "TIDSTART.md"))) {
    Fail "'$TidosDir' is not a TIDOS checkout (TIDSTART.md missing)."
}

Write-Host "[0/4] TIDOS directory: $TidosDir"

# Step 2: Local-copy mode (no .git) cannot pull - warn and continue on local version
if (-not (Test-Path (Join-Path $TidosDir ".git"))) {
    Write-Host "[1/4] No .git in '$TidosDir' (local-copy mode). Skipping remote sync." -ForegroundColor Yellow
    $ver = "(unknown)"; $vf = Join-Path $TidosDir "VERSION.md"
    if (Test-Path $vf) { $ver = (Get-Content $vf | Select-String "Current Version").ToString() }
    Write-Host "  -> Continuing on local version: $ver" -ForegroundColor Yellow
    exit 0
}

Push-Location $TidosDir
try {
    $oldRev = (git rev-parse --short HEAD) 2>$null
    if (-not $oldRev) { Fail "git is unavailable or repository is corrupt." }

    # Step 3: Fetch - network failure must never block boot
    Write-Host "[1/4] Fetching origin... (local: $oldRev)"
    git fetch origin 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  -> WARNING: GitHub unreachable. Continuing on local version ($oldRev)." -ForegroundColor Yellow
        exit 0
    }
    $newRev = (git rev-parse --short "origin/$Branch") 2>$null
    if (-not $newRev) { Fail "Remote branch 'origin/$Branch' not found." }

    if ($oldRev -eq $newRev) {
        Write-Host "[2/4] Already current ($oldRev). No sync needed." -ForegroundColor Green
        exit 0
    }
    Write-Host "[2/4] Update available: $oldRev -> $newRev"

    # Step 4a: Unpushed-commit check - reset would orphan local commits
    $ahead = (git rev-list --count "origin/$Branch..HEAD") 2>$null
    if ([int]$ahead -gt 0) {
        Write-Host "  -> BLOCKED: $ahead unpushed local commit(s) would be orphaned by force sync." -ForegroundColor Red
        Write-Host "  -> Push them first (git push), then re-run START TIDOS." -ForegroundColor Red
        exit 1
    }

    # Step 4: Memory-safety check - abort instead of wiping institutional memory
    $dirty = git status --porcelain -- memory evolution 2>$null
    if ($dirty) {
        Write-Host "  -> BLOCKED: uncommitted memory/evolution changes would be wiped:" -ForegroundColor Red
        $dirty | ForEach-Object { Write-Host "     $_" -ForegroundColor Red }
        Write-Host "  -> Commit or stash them first, then re-run START TIDOS." -ForegroundColor Red
        exit 1
    }

    # Step 5: Memory-safe force sync
    Write-Host "[3/4] Force-syncing OS files to origin/$Branch..."
    git reset --hard "origin/$Branch"
    if ($LASTEXITCODE -ne 0) { Fail "Force sync failed." }
    Write-Host "[4/4] Updated: $oldRev -> $newRev" -ForegroundColor Green
    exit 0
} finally {
    Pop-Location
}
