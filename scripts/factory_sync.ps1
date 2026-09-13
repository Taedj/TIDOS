# ============================================================================
# TIDOS Persona Factory Sync (Windows PowerShell)
# ============================================================================
# Stages ONLY factory-generated paths (new persona spec + registry + evolution)
# and pushes them to origin/main (the central brain). Never force-pushes.
#
# Usage:
#   .\scripts\factory_sync.ps1                        # commit + push new persona
#   .\scripts\factory_sync.ps1 -Persona <NAME>        # name (default: detected new line)
#   .\scripts\factory_sync.ps1 -Message "<msg>"       # custom commit message
#   .\scripts\factory_sync.ps1 -DryRun                # show what would be staged
#
# Exit: 0 = pushed, 1 = nothing to push / blocked, 2 = error
# ============================================================================

param(
    [string]$Persona,
    [string]$Message,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
function Fail($msg, $code) { Write-Error $msg; exit $code }

$repo = (Resolve-Path (Join-Path $PSScriptRoot ".."))
Set-Location $repo

if (-not (Test-Path ".git")) { Fail "Not a git repo: $repo" 2 }

# --- Detect the new persona file if not supplied -------------------------------
function Find-NewPersona {
    $untracked = git status --porcelain -- personas
    $cand = $untracked | Select-String '^\?\?\s+personas/tidos.+\.md$'
    if ($cand) { return ($cand[0].Line -replace '^\?\?\s+', '').Trim() }
    return $null
}

if (-not $Persona) { $Persona = Find-NewPersona }
if (-not $Persona) { Fail "No new persona detected to sync. Expected new personas/tidos*.md." 1 }

# --- Guard: only factory paths go in -------------------------------------------
$factoryPaths = @($Persona, "personas/registry.md", "evolution/SUGGESTIONS.md")
$allChanges = git status --porcelain
$blocked = $allChanges | Where-Object { $_ -match '^\?\?' -or $_ -match '^ M ' } |
    ForEach-Object { ($_ -replace '^(..) ', '') } |
    Where-Object { $_ -notin $factoryPaths }

if ($blocked.Count -gt 0) {
    Write-Host "BLOCKED: unrelated changes would be included:"
    $blocked | ForEach-Object { Write-Host "  $_" }
    Fail "Stash/commit unrelated changes first; factory_sync commits ONLY the persona trio." 1
}

# --- Message ---------------------------------------------------------------
$name = (Split-Path $Persona -Leaf) -replace '\.md$', ''
if (-not $Message) { $Message = "feat(persona-factory): $name persona auto-generated (discovered domain/stack)" }

# --- Stage & show --------------------------------------------------------------
git add $Persona "personas/registry.md" "evolution/SUGGESTIONS.md"
Write-Host "Staging: $Persona + personas/registry.md + evolution/SUGGESTIONS.md"
Write-Host "Message: $Message"
if ($DryRun) { Write-Host "[dry-run] push skipped. Staged files:"; git diff --cached --name-status; exit 0 }

git commit -m $Message | Out-Null
git push origin main 2>&1 | ForEach-Object { Write-Host $_ }
if (-not $?) { Fail "Push failed (examine remote above). Local commit $name exists." 1 }
Write-Host "Pushed to origin/main. Central brain updated."
exit 0