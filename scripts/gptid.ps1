# ============================================================================
# TIDOS GPTID control script (Windows PowerShell)
# ============================================================================
# Thin wrapper over browser_relay/gptid_cli.py. No credentials, no secrets.
# Usage:
#   .\scripts\gptid.ps1 start [-Port 8765] [-Driver auto|manual] [-Browser chromium|firefox|firefox-nightly] [-Headed] [-ResponseTimeout 180] [-StartupTimeout 120]
#   .\scripts\gptid.ps1 status|test|stop|reset
#   .\scripts\gptid.ps1 ask -Objective "..." [-Mode REVIEW] [-Port 8765]
#   .\scripts\gptid.ps1 review|audit -Objective "..." [-Port 8765]
#   .\scripts\gptid.ps1 review-auto -ChangeJson '{"change_id":"...","kind":"..."}' [-Questions "q1;q2"] [-Context "..."] [-DryRun] [-Ledger PATH]
#   .\scripts\gptid.ps1 connect|reconnect (alias of start)
# ============================================================================

param(
    [string]$Command = "status",
    [int]$Port = 8765,
    [string]$Driver = "auto",
    [string]$Browser = "chromium",
    [switch]$Headed,
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
switch ($Command.ToLower()) {
    "start" {
        $args += @("--driver", $Driver, "--browser", $Browser, "--response-timeout", "$ResponseTimeout", "--startup-timeout", "$StartupTimeout")
        if ($Headed) { $args += "--headed" }
    }
    "test" { $args += @("--response-timeout", "$ResponseTimeout") }
    "ask" { $args += @("--mode", $Mode, "--objective", $Objective, "--context", $Context) }
    "review" { $args += @("--objective", $Objective, "--context", $Context) }
    "audit" { $args += @("--objective", $Objective, "--context", $Context) }
    "review-auto" {
        $args += @("--change-json", $ChangeJson, "--questions", $Questions,
                   "--context", $Context)
        if ($Ledger -ne "") { $args += @("--ledger", $Ledger) }
        if ($DryRun) { $args += "--dry-run" }
    }
    "connect" {
        $args = @($cli, "start", "--port", "$Port", "--driver", $Driver, "--browser", $Browser,
                  "--response-timeout", "$ResponseTimeout", "--startup-timeout", "$StartupTimeout")
        if ($Headed) { $args += "--headed" }
    }
    "reconnect" {
        $args = @($cli, "start", "--port", "$Port", "--driver", $Driver, "--browser", $Browser,
                  "--response-timeout", "$ResponseTimeout", "--startup-timeout", "$StartupTimeout")
        if ($Headed) { $args += "--headed" }
    }
    "new-session" { $args = @($cli, "reset", "--port", "$Port") }
    "reset" { }
    default { }
}
& python $args
exit $LASTEXITCODE
