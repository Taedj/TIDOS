# ============================================================================
# TIDOS GPTID control script (Windows PowerShell)
# ============================================================================
# Thin wrapper over browser_relay/gptid_cli.py. No credentials, no secrets.
# Usage:
#   .\scripts\gptid.ps1 enhance|correct|develop|design|review|audit -Objective "..."
#   .\scripts\gptid.ps1 chat [-Objective "..."]             # interactive partnership conversation
#   .\scripts\gptid.ps1 start [-Port 8765] [-Browser chrome|chromium|firefox] [-Headed]
#   .\scripts\gptid.ps1 status|test|stop|reset
# ============================================================================

param(
    [string]$Command = "status",
    [int]$Port = 8765,
    [string]$Driver = "auto",
    [string]$Browser = "chrome",
    [switch]$Headed,
    [switch]$Headless,
    [int]$ResponseTimeout = 180,
    [string]$Mode = "REVIEW",
    [string]$Objective = "",
    [string]$Context = "",
    [string]$ChangeJson = "{}",
    [string]$Questions = "",
    [string]$Ledger = "",
    [switch]$DryRun,
    [int]$StartupTimeout = 120
)

$ErrorActionPreference = 'Stop'
$cli = Join-Path (Join-Path $PSScriptRoot "..\browser_relay") "gptid_cli.py"
if (-not (Test-Path $cli)) { Write-Error "GPTID relay not found: $cli"; exit 2 }

$args = @($cli, $Command.ToLower(), "--port", "$Port")

# Pass browser and headless/headed preferences
$args += @("--browser", $Browser, "--driver", $Driver)
if ($Headless) { $args += "--headless" }
elseif ($Headed) { $args += "--headed" }

switch ($Command.ToLower()) {
    "start" {
        $args += @("--response-timeout", "$ResponseTimeout", "--startup-timeout", "$StartupTimeout")
    }
    "test" { $args += @("--response-timeout", "$ResponseTimeout") }
    "ask" { $args += @("--mode", $Mode, "--objective", $Objective, "--context", $Context, "--response-timeout", "$ResponseTimeout") }
    "enhance" { $args += @("--objective", $Objective, "--context", $Context, "--response-timeout", "$ResponseTimeout") }
    "correct" { $args += @("--objective", $Objective, "--context", $Context, "--response-timeout", "$ResponseTimeout") }
    "develop" { $args += @("--objective", $Objective, "--context", $Context, "--response-timeout", "$ResponseTimeout") }
    "design" { $args += @("--objective", $Objective, "--context", $Context, "--response-timeout", "$ResponseTimeout") }
    "review" { $args += @("--objective", $Objective, "--context", $Context, "--response-timeout", "$ResponseTimeout") }
    "audit" { $args += @("--objective", $Objective, "--context", $Context, "--response-timeout", "$ResponseTimeout") }
    "chat" { $args += @("--objective", $Objective, "--context", $Context, "--response-timeout", "$ResponseTimeout") }
    "partner" { $args += @("--objective", $Objective, "--context", $Context, "--response-timeout", "$ResponseTimeout") }
    "review-auto" {
        $args += @("--change-json", $ChangeJson, "--questions", $Questions,
                   "--context", $Context)
        if ($Ledger -ne "") { $args += @("--ledger", $Ledger) }
        if ($DryRun) { $args += "--dry-run" }
    }
    "connect" {
        $args = @($cli, "start", "--port", "$Port", "--driver", $Driver, "--browser", $Browser,
                  "--response-timeout", "$ResponseTimeout", "--startup-timeout", "$StartupTimeout")
        if (-not $Headless) { $args += "--headed" }
    }
    "reconnect" {
        $args = @($cli, "start", "--port", "$Port", "--driver", $Driver, "--browser", $Browser,
                  "--response-timeout", "$ResponseTimeout", "--startup-timeout", "$StartupTimeout")
        if (-not $Headless) { $args += "--headed" }
    }
    "new-session" { $args = @($cli, "reset", "--port", "$Port") }
    "reset" { }
    default { }
}
& python $args
exit $LASTEXITCODE
