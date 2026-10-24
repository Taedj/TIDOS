# Root convenience wrapper for starting TIDOS
param(
    [switch]$SkipUpdate,
    [switch]$ApplyUpdate,
    [ValidateSet("release", "main")][string]$Channel = "release",
    [string]$Tool = "auto",
    [string]$Model = "auto"
)

$script = Join-Path $PSScriptRoot "scripts\start_tidos.ps1"
$extra = @("-Tool", $Tool, "-Model", $Model, "-Channel", $Channel)
if ($SkipUpdate) { $extra += "-SkipUpdate" }
if ($ApplyUpdate) { $extra += "-ApplyUpdate" }
& powershell -NoProfile -ExecutionPolicy Bypass -File $script @extra
