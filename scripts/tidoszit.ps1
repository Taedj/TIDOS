# ============================================================================
# TIDOSZIT - open the TIDOS Control Center (Windows PowerShell)
# ============================================================================
# Starts the local dashboard server in the background (127.0.0.1 only) if it is
# not already running, then opens it in the browser. Login happens IN THE
# BROWSER (Google owner account + control password) - never in a chat/terminal.
#
# Usage: .\scripts\tidoszit.ps1 [-Port 8767] [-Stop]
# ============================================================================

param(
    [int]$Port = 8767,
    [switch]$Stop
)

$root = Split-Path -Parent $PSScriptRoot
$main = Join-Path $root "tidos_dashboard\__main__.py"
$url = "http://localhost:$Port/"
$pidFile = Join-Path (Join-Path $HOME ".tidos") "tidoszit.pid"

function Test-Running {
    try { Invoke-RestMethod -Uri "$($url)api/boot" -TimeoutSec 2 | Out-Null; return $true } catch { return $false }
}

if ($Stop) {
    if (Test-Path $pidFile) {
        $procId = [int](Get-Content $pidFile)
        Stop-Process -Id $procId -ErrorAction SilentlyContinue
        Remove-Item $pidFile -ErrorAction SilentlyContinue
        Write-Host "[TIDOSZIT] Control center stopped." -ForegroundColor Yellow
    } else {
        Write-Host "[TIDOSZIT] Not running (no pid file)."
    }
    exit 0
}

if (-not (Test-Running)) {
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python) { Write-Host "ERROR: python not found on PATH." -ForegroundColor Red; exit 2 }
    $proc = Start-Process -FilePath $python -ArgumentList @("-I", "`"$main`"", "--port", $Port, "--no-browser") `
        -WindowStyle Hidden -PassThru
    New-Item -ItemType Directory -Force -Path (Split-Path $pidFile) | Out-Null
    Set-Content -Path $pidFile -Value $proc.Id -Encoding ascii
    $deadline = (Get-Date).AddSeconds(15)
    while (-not (Test-Running)) {
        if ((Get-Date) -gt $deadline -or $proc.HasExited) {
            Write-Host "ERROR: control center did not start (port $Port busy?)." -ForegroundColor Red
            exit 2
        }
        Start-Sleep -Milliseconds 300
    }
}

Start-Process $url
Write-Host "[TIDOSZIT] Control center open at $url" -ForegroundColor Cyan
Write-Host "[TIDOSZIT] Log in in the browser. Never type the control password in a chat or terminal." -ForegroundColor Cyan
Write-Host "[TIDOSZIT] Stop it with: .\scripts\tidoszit.ps1 -Stop"
exit 0
