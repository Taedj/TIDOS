# ============================================================================
# TIDOS v3.0 Installation Script (Windows PowerShell)
# ============================================================================
# Installs TIDOS as a Git submodule in the current project.
# Usage: .\scripts\install.ps1 [[-TargetDir] <string>]
# ============================================================================

param(
    [string]$TargetDir = ".tidos"
)

$TidosUrl = "https://github.com/tidjani/TIDOS.git"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  TIDOS v3.0 Installation Script" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check prerequisites
$gitVersion = git --version 2>$null
if (-not $gitVersion) {
    Write-Host "ERROR: Git is not installed. Please install Git first." -ForegroundColor Red
    exit 1
}
Write-Host "[0/4] Git detected: $gitVersion"

# Step 2: Initialize Git if needed
if (-not (Test-Path ".git")) {
    Write-Host "[1/4] Initializing Git repository..."
    git init
    Write-Host "  -> Git repository initialized." -ForegroundColor Green
} else {
    Write-Host "[1/4] Git repository already initialized."
}

# Step 3: Install TIDOS as a submodule
if (Test-Path $TargetDir) {
    Write-Host "[2/4] TIDOS directory '$TargetDir' already exists." -ForegroundColor Yellow
    Write-Host "  -> Skipping submodule addition."
    Write-Host "  -> Run 'git submodule update --remote' to update."
} else {
    Write-Host "[2/4] Installing TIDOS as a Git submodule..."
    git submodule add $TidosUrl $TargetDir
    git submodule init
    git submodule update
    Write-Host "  -> TIDOS installed at '$TargetDir/'." -ForegroundColor Green
}

# Step 4: Verify installation
Write-Host "[3/4] Verifying installation..."
$versionFile = Join-Path $TargetDir "VERSION.md"
if (Test-Path $versionFile) {
    $tidosVersion = (Get-Content $versionFile)[2]
    Write-Host "  -> TIDOS version: $tidosVersion" -ForegroundColor Green
    Write-Host "  -> Installation verified successfully." -ForegroundColor Green
} else {
    Write-Host "  -> WARNING: VERSION.md not found. Installation may be incomplete." -ForegroundColor Yellow
}

# Step 5: Display next steps
Write-Host "[4/4] Installation complete." -ForegroundColor Green
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Next Steps" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Read the startup protocol:"
Write-Host "     Get-Content $TargetDir\TIDSTART.md"
Write-Host ""
Write-Host "  2. Start your session by loading TIDOS:"
Write-Host "     - Open $TargetDir\TIDSTART.md"
Write-Host "     - Follow the 9-step startup sequence"
Write-Host ""
Write-Host "  3. For AI agent integration guides:"
Write-Host "     Get-ChildItem $TargetDir\docs\tools\"
Write-Host ""
Write-Host "  4. Commit the submodule:"
Write-Host "     git add .gitmodules $TargetDir"
Write-Host '     git commit -m "chore: add TIDOS v3.0 submodule"'
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
