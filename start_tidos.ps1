# Root convenience wrapper for starting TIDOS
param(
    [switch]$SkipUpdate,
    [string]$Tool = "auto",
    [string]$Model = "auto"
)

$script = Join-Path $PSScriptRoot "scripts\start_tidos.ps1"
$extra = @("-Tool", $Tool, "-Model", $Model)
if ($SkipUpdate) { $extra += "-SkipUpdate" }
& powershell -NoProfile -ExecutionPolicy Bypass -File $script @extra
