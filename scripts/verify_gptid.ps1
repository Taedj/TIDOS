#Requires -Version 5.1
# TIDOS GPTID structural + protocol validator.
# Deterministic: file/marker asserts + embedded protocol-mirror checks + python unit tests.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:Total = 0
$script:Fail = 0
$script:Root = Split-Path -Parent $PSScriptRoot

function Assert-G {
  param([string]$Name, [bool]$Cond, [string]$Detail = '')
  $script:Total++
  if ($Cond) { Write-Host "PASS $Name" }
  else { $script:Fail++; Write-Host "FAIL $Name $Detail" }
}
function Read-G { param([string]$Rel) return (Get-Content (Join-Path $script:Root $Rel) -Raw) }
function Has-G {
  param([string]$Text, [string[]]$Needles)
  foreach ($n in $Needles) { if ($Text -notmatch [regex]::Escape($n)) { return $false } }
  return $true
}
function Exists-G { param([string]$Rel) return (Test-Path (Join-Path $script:Root $Rel)) }

# --- files ---------------------------------------------------------------
Assert-G 'file-persona' (Exists-G 'personas/tidosgptid.md')
Assert-G 'file-engine' (Exists-G 'engines/gptid_relay_engine.md')
Assert-G 'file-protocol' (Exists-G 'browser_relay/gptid_protocol.py')
Assert-G 'file-relay' (Exists-G 'browser_relay/relay_server.py')
Assert-G 'file-adapter' (Exists-G 'browser_relay/chatgpt_adapter.py')
Assert-G 'file-selectors' (Exists-G 'browser_relay/selector_registry.json')
Assert-G 'file-cli' (Exists-G 'browser_relay/gptid_cli.py')
Assert-G 'file-tests' (Exists-G 'browser_relay/tests/test_gptid_protocol.py')
Assert-G 'file-doc' (Exists-G 'docs/gptid.md')
Assert-G 'file-cli-ps1' (Exists-G 'scripts/gptid.ps1')
Assert-G 'file-tpl-task' (Exists-G 'templates/gptid_task.md')
Assert-G 'file-tpl-resp' (Exists-G 'templates/gptid_response.md')

# --- persona -------------------------------------------------------------
$p = Read-G 'personas/tidosgptid.md'
Assert-G 'persona-governance' (Has-G $p @('TIDOS Core', 'final decision', 'advisor', 'never a second implementation authority'))
Assert-G 'persona-noapi' (Has-G $p @('never uses the OpenAI API', 'never needs an OpenAI API key'))
Assert-G 'persona-modes' (Has-G $p @('REVIEW', 'AUDIT', 'ARCHITECT', 'DEBUG', 'UIUX', 'TRADING_REVIEW'))
Assert-G 'persona-routing' (Has-G $p @('## Routing Signals', 'Trigger keyword: GPTID'))
Assert-G 'persona-boundary' (Has-G $p @('never modifies it', 'never', 'financial decisions'))

# --- engine --------------------------------------------------------------
$e = Read-G 'engines/gptid_relay_engine.md'
Assert-G 'engine-chain' (Has-G $e @('TIDOS', 'GPTID Persona', 'Browser Relay', 'TIDOS (evaluate'))
Assert-G 'engine-drivers' (Has-G $e @('MANUAL', 'AUTO', 'never', 'READY'))
Assert-G 'engine-states' (Has-G $e @('DISCONNECTED', 'WAITING_RESPONSE', 'CONNECTED', 'ERROR'))
Assert-G 'engine-failures' (Has-G $e @('UNAVAILABLE', 'MALFORMED', 'REJECTED', 'never', 'OK'))
Assert-G 'engine-security' (Has-G $e @('Localhost-only', 'never executed', 'redaction'))

# --- protocol source -----------------------------------------------------
$proto = Read-G 'browser_relay/gptid_protocol.py'
Assert-G 'proto-task-keys' (Has-G $proto @('task_id', 'session_id', 'requested_output_format'))
Assert-G 'proto-resp-keys' (Has-G $proto @('chatgpt_response', 'structured_findings', 'uncertainties', 'timestamp'))
Assert-G 'proto-redact' (Has-G $proto @('redact_secrets', 'SECRET_PATTERNS', 'REDACTED'))
Assert-G 'proto-limits' (Has-G $proto @('max_context_chars', 'max_response_chars', 'max_history'))
Assert-G 'proto-correlation' (Has-G $proto @('task_matches_response'))

# --- relay source --------------------------------------------------------
$relay = Read-G 'browser_relay/relay_server.py'
Assert-G 'relay-endpoints' (Has-G $relay @('/health', '/status', '/send', '/poll', '/reset'))
Assert-G 'relay-localhost' (Has-G $relay @('127.0.0.1', 'GPTID_ALLOW_REMOTE'))
Assert-G 'relay-handshake' (Has-G $relay @('BROWSER_RELAY_CONNECTED', 'READY', 'STATUS=UNAVAILABLE'))
Assert-G 'relay-no-silent' (Has-G $relay @('conversation mismatch', 'MALFORMED'))
Assert-G 'relay-auto' (Has-G $relay @('--headed', '--response-timeout', 'auto_response', 'CHATGPT_AUTHENTICATION_REQUIRED'))
Assert-G 'relay-resume' (Has-G $relay @('QUEUED', '_drain_queue', '_monitor_loop', 'auth detected while browser open'))
Assert-G 'relay-probe' (Has-G $relay @('/dom_probe', '_dom_probe', 'extra_selectors'))

# --- adapter + selectors -------------------------------------------------
$ad = Read-G 'browser_relay/chatgpt_adapter.py'
Assert-G 'adapter-modes' (Has-G $ad @('manual', 'playwright', 'MANUAL bridge'))
Assert-G 'adapter-honest' (Has-G $ad @('NEVER fabricates', 'STATUS=UNAVAILABLE'))
Assert-G 'adapter-auto' (Has-G $ad @('class AutoDriver', 'launch_persistent_context', 'ensure_ready', 'send_prompt', 'wait_completion', 'extract_response', 'USER_ACTION_REQUIRED', 'fallback_to_manual'))
Assert-G 'adapter-navfix' (Has-G $ad @('wait_until="commit"', '_page_alive', '_classify', 'CHATGPT_LOADING', 'PAGE_STATES', '--no-first-run', '_take_page'))
Assert-G 'adapter-firefox' (Has-G $ad @('browser_name', 'firefox', 'chromium', 'launch_persistent_context', 'channel'))
Assert-G 'adapter-nocreds' (Has-G $ad @('NEVER reads, prints, persists, or transmits cookies', 'bypass is out of scope'))
Assert-G 'adapter-resume' (Has-G $ad @('quick_ready', 'AUTHENTICATION_REQUIRED'))
Assert-G 'adapter-exec' (Has-G $ad @('_BrowserExec', '_on_browser_thread', 'greenlet', 'dom_probe', 'count', 'visible'))
$sel = Get-Content (Join-Path $script:Root 'browser_relay/selector_registry.json') -Raw | ConvertFrom-Json
Assert-G 'selector-fallbacks' ($sel.composer.fallback_chain.Count -ge 2 -and $sel.assistant_messages.fallback_chain.Count -ge 2)

# --- registry / commands / config ----------------------------------------
$reg = Read-G 'personas/registry.md'
Assert-G 'registry-row' (Has-G $reg @('GPTID', 'personas/tidosgptid.md'))
$cmd = Read-G 'commands/session_commands.md'
Assert-G 'cmd-gptid' (Has-G $cmd @('TIDOS GPTID', 'gptid'))
$cfg = Read-G 'config/framework.md'
Assert-G 'config-gptid' (Has-G $cfg @('gptid:', 'relay_port', 'dedicated_conversation'))
Assert-G 'config-auto' (Has-G $cfg @('headless', 'auto_fallback_to_manual'))

# --- protocol-mirror checks (independent of python impl) ------------------
function Test-Secret { param([string]$Text) return ($Text -match '(?i)(api[_-]?key\s*=|password\s*=|\bssid\s*=|cookie\s*:|BEGIN .*PRIVATE KEY)') }
Assert-G 'mirror-secret-api' (Test-Secret 'api_key=abc123')
Assert-G 'mirror-secret-pass' (Test-Secret 'password=hunter2')
Assert-G 'mirror-secret-cookie' (Test-Secret 'cookie: yummy')
Assert-G 'mirror-clean' (-not (Test-Secret 'three software-engineering observations'))

# --- readiness remediation (shared detector / budget / state truth) ---------
Assert-G 'readiness-detector' (Has-G $ad @('def find_usable_composer', 'SEMANTIC_COMPOSER_SELECTORS', '_locator_usable', 'aria-disabled', 'is_editable'))
Assert-G 'readiness-unified' (Has-G $ad @('READINESS_BUDGET_MS', 'MONITOR_BUDGET_MS', '_PROBE_SLICE_MS', '_composer_usable(READINESS_BUDGET_MS', '_composer_usable(MONITOR_BUDGET_MS'))
Assert-G 'readiness-liveness' (Has-G $ad @('_live_tab_count', 'DEAD:', '_page_alive', 'zero usable ChatGPT tabs'))
Assert-G 'relay-truth' (Has-G $relay @('sync_relay_state', '_probe_dead', '_adapter_dead', 'DOWNGRADED-ERROR', 'DOWNGRADED-LOADING'))
Assert-G 'relay-dead-send' (Has-G $relay @('_probe_dead(_m)', 'never queue behind a dead page'))
Assert-G 'domprobe-detector' (Has-G $relay @('composer_usable', 'DOM_PROBE_BUDGET_MS', 'composer_usable(semantic-first)'))
Assert-G 'file-readiness-tests' (Exists-G 'browser_relay/tests/test_gptid_readiness.py')
Assert-G 'file-review' (Exists-G 'browser_relay/gptid_review.py')
Assert-G 'file-review-tests' (Exists-G 'browser_relay/tests/test_gptid_review.py')
Assert-G 'file-lifecycle-tests' (Exists-G 'browser_relay/tests/test_gptid_lifecycle.py')

# --- auto-REVIEW policy (decision layer, TIDOS authority preserved) -------
$rev = Read-G 'browser_relay/gptid_review.py'
Assert-G 'review-policy' (Has-G $rev @('def decide_review', 'LOW_VALUE_KINDS', 'SIGNIFICANT_KINDS', 'LARGE_CHANGE_LINES'))
Assert-G 'review-gate' (Has-G $rev @('def readiness_ok', 'page_state', 'tabs'))
Assert-G 'review-bound' (Has-G $rev @('class ReviewLedger', 'already_reviewed', 'gptid-reviews.json'))
Assert-G 'review-untrusted' (Has-G $rev @('chatgpt-untrusted', 'def untrusted_envelope', 'verification_checklist'))
Assert-G 'review-noapply' (Has-G $rev @('NO code-apply path', 'only TIDOS may act'))
$cli = Read-G 'browser_relay/gptid_cli.py'
Assert-G 'review-cli' (Has-G $cli @('review-auto', 'cmd_review_auto', 'no retry'))
Assert-G 'review-ps1' (Has-G (Read-G 'scripts/gptid.ps1') @('review-auto', 'ChangeJson'))

# --- startup/lifecycle (single spawn, bounded polling, PID safety) --------
Assert-G 'lifecycle-spawn' (Has-G $cli @('DEFAULT_STARTUP_TIMEOUT', 'STARTUP_POLL_SECONDS', 'exactly one', '--startup-timeout'))
Assert-G 'lifecycle-pid' (Has-G $cli @('_is_relay_process', '_remove_pidfile_if', '_pid_alive', 'PID reuse', '_stop_owned', '_reap_stale_pidfile'))
Assert-G 'lifecycle-ps1' (Has-G (Read-G 'scripts/gptid.ps1') @('StartupTimeout'))
Assert-G 'lifecycle-stdio' (Has-G $cli @('RELAY_LOG', '_relay_log_handle', '_relay_log_tail', 'unread PIPE'))
Assert-G 'lifecycle-logguard' (Has-G (Read-G 'browser_relay/relay_server.py') @('a logging failure must never kill the HTTP response'))

# --- python unit tests (via cmd so native stderr merges to plain text) --------
$tp = Join-Path $script:Root 'browser_relay/tests/test_gptid_protocol.py'
$pyOut = & cmd /c "python ""$tp"" 2>&1"
$pyExit = $LASTEXITCODE
$pyOut | ForEach-Object { Write-Host $_ }
if ($pyExit -ne 0) { $script:Fail++; Write-Host "FAIL python-tests (exit $pyExit)" }
else { Write-Host "PASS python-tests (deterministic, see Ran count above)" }
$script:Total++

# --- readiness regression tests (shared detector / budget / state truth) ---
$tr = Join-Path $script:Root 'browser_relay/tests/test_gptid_readiness.py'
$rdOut = & cmd /c "python ""$tr"" 2>&1"
$rdExit = $LASTEXITCODE
$rdOut | ForEach-Object { Write-Host $_ }
if ($rdExit -ne 0) { $script:Fail++; Write-Host "FAIL readiness-tests (exit $rdExit)" }
else { Write-Host "PASS readiness-tests (deterministic, see Ran count above)" }
$script:Total++

# --- auto-REVIEW policy tests (decision/bound/provenance, no browser) -----
$rv = Join-Path $script:Root 'browser_relay/tests/test_gptid_review.py'
$rvOut = & cmd /c "python ""$rv"" 2>&1"
$rvExit = $LASTEXITCODE
$rvOut | ForEach-Object { Write-Host $_ }
if ($rvExit -ne 0) { $script:Fail++; Write-Host "FAIL review-tests (exit $rvExit)" }
else { Write-Host "PASS review-tests (deterministic, see Ran count above)" }
$script:Total++

# --- startup/lifecycle tests (spawn/polling/PID safety, no browser) -------
$lc = Join-Path $script:Root 'browser_relay/tests/test_gptid_lifecycle.py'
$lcOut = & cmd /c "python ""$lc"" 2>&1"
$lcExit = $LASTEXITCODE
$lcOut | ForEach-Object { Write-Host $_ }
if ($lcExit -ne 0) { $script:Fail++; Write-Host "FAIL lifecycle-tests (exit $lcExit)" }
else { Write-Host "PASS lifecycle-tests (deterministic, see Ran count above)" }
$script:Total++

Write-Host ""
Write-Host ("GPTID verify: {0} checks, {1} failures" -f $script:Total, $script:Fail)
if ($script:Fail -gt 0) { exit 1 }
exit 0
