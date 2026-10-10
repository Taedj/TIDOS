# Root convenience wrapper for starting TIDOS
param(
    [switch]$SkipUpdate
)

$script = Join-Path $PSScriptRoot "scripts\start_tidos.ps1"
if ($SkipUpdate) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $script -SkipUpdate
} else {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $script
}
