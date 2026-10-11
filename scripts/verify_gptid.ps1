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
function Test-GHas {
  param([string]$Text, [string[]]$Needles)
  foreach ($n in $Needles) { if ($Text -notmatch [regex]::Escape($n)) { return $false } }
  return $true
}
function Test-GExists { param([string]$Rel) return (Test-Path (Join-Path $script:Root $Rel)) }

# --- files ---------------------------------------------------------------
Assert-G 'file-persona' (Test-GExists 'personas/tidosgptid.md')
Assert-G 'file-engine' (Test-GExists 'engines/gptid_relay_engine.md')
Assert-G 'file-protocol' (Test-GExists 'browser_relay/gptid_protocol.py')
Assert-G 'file-relay' (Test-GExists 'browser_relay/relay_server.py')
Assert-G 'file-adapter' (Test-GExists 'browser_relay/chatgpt_adapter.py')
Assert-G 'file-selectors' (Test-GExists 'browser_relay/selector_registry.json')
Assert-G 'file-cli' (Test-GExists 'browser_relay/gptid_cli.py')
Assert-G 'file-ui' (Test-GExists 'browser_relay/terminal_ui.py')
Assert-G 'file-tests' (Test-GExists 'browser_relay/tests/test_gptid_protocol.py')
Assert-G 'file-doc' (Test-GExists 'docs/gptid.md')
Assert-G 'file-cli-ps1' (Test-GExists 'scripts/gptid.ps1')
Assert-G 'file-tpl-task' (Test-GExists 'templates/gptid_task.md')
Assert-G 'file-tpl-resp' (Test-GExists 'templates/gptid_response.md')

# --- persona -------------------------------------------------------------
$p = Read-G 'personas/tidosgptid.md'
Assert-G 'persona-governance' (Test-GHas $p @('TIDOS Core', 'final decision', 'advisor', 'never a second implementation authority'))
Assert-G 'persona-noapi' (Test-GHas $p @('never uses the OpenAI API', 'never needs an OpenAI API key'))
Assert-G 'persona-modes' (Test-GHas $p @('REVIEW', 'AUDIT', 'ARCHITECT', 'DEBUG', 'UIUX', 'TRADING_REVIEW'))
Assert-G 'persona-routing' (Test-GHas $p @('## Routing Signals', 'Trigger keyword: GPTID'))
Assert-G 'persona-boundary' (Test-GHas $p @('never modifies it', 'never', 'financial decisions'))

# --- engine --------------------------------------------------------------
$e = Read-G 'engines/gptid_relay_engine.md'
Assert-G 'engine-chain' (Test-GHas $e @('TIDOS', 'GPTID Persona', 'Browser Relay', 'TIDOS (evaluate'))
Assert-G 'engine-drivers' (Test-GHas $e @('MANUAL', 'AUTO', 'never', 'READY'))
Assert-G 'engine-states' (Test-GHas $e @('DISCONNECTED', 'WAITING_RESPONSE', 'CONNECTED', 'ERROR'))
Assert-G 'engine-failures' (Test-GHas $e @('UNAVAILABLE', 'MALFORMED', 'REJECTED', 'never', 'OK'))
Assert-G 'engine-security' (Test-GHas $e @('Localhost-only', 'never executed', 'redaction'))

# --- protocol source -----------------------------------------------------
$proto = Read-G 'browser_relay/gptid_protocol.py'
Assert-G 'proto-task-keys' (Test-GHas $proto @('task_id', 'session_id', 'requested_output_format'))
Assert-G 'proto-resp-keys' (Test-GHas $proto @('chatgpt_response', 'structured_findings', 'uncertainties', 'timestamp'))
Assert-G 'proto-redact' (Test-GHas $proto @('redact_secrets', 'SECRET_PATTERNS', 'REDACTED'))
Assert-G 'proto-limits' (Test-GHas $proto @('max_context_chars', 'max_response_chars', 'max_history'))
Assert-G 'proto-correlation' (Test-GHas $proto @('task_matches_response'))

# --- relay source --------------------------------------------------------
$relay = Read-G 'browser_relay/relay_server.py'
Assert-G 'relay-endpoints' (Test-GHas $relay @('/health', '/status', '/send', '/poll', '/reset'))
Assert-G 'relay-localhost' (Test-GHas $relay @('127.0.0.1', 'GPTID_ALLOW_REMOTE'))
Assert-G 'relay-handshake' (Test-GHas $relay @('BROWSER_RELAY_CONNECTED', 'READY', 'STATUS=UNAVAILABLE'))
Assert-G 'relay-no-silent' (Test-GHas $relay @('conversation mismatch', 'MALFORMED'))
Assert-G 'relay-auto' (Test-GHas $relay @('--headed', '--response-timeout', 'auto_response', 'CHATGPT_AUTHENTICATION_REQUIRED'))
Assert-G 'relay-resume' (Test-GHas $relay @('QUEUED', '_drain_queue', '_monitor_loop', 'auth detected while browser open'))
Assert-G 'relay-probe' (Test-GHas $relay @('/dom_probe', '_dom_probe', 'extra_selectors'))

# --- adapter + selectors -------------------------------------------------
$ad = Read-G 'browser_relay/chatgpt_adapter.py'
Assert-G 'adapter-modes' (Test-GHas $ad @('manual', 'playwright', 'MANUAL bridge'))
Assert-G 'adapter-honest' (Test-GHas $ad @('NEVER fabricates', 'STATUS=UNAVAILABLE'))
Assert-G 'adapter-auto' (Test-GHas $ad @('class AutoDriver', 'launch_persistent_context', 'ensure_ready', 'send_prompt', 'wait_completion', 'extract_response', 'USER_ACTION_REQUIRED', 'fallback_to_manual'))
Assert-G 'adapter-navfix' (Test-GHas $ad @('wait_until="commit"', '_page_alive', '_classify', 'CHATGPT_LOADING', 'PAGE_STATES', '--no-first-run', '_take_page'))
Assert-G 'adapter-firefox' (Test-GHas $ad @('browser_name', 'firefox', 'chromium', 'launch_persistent_context', 'channel'))
Assert-G 'adapter-nocreds' (Test-GHas $ad @('NEVER reads, prints, persists, or transmits cookies', 'bypass is out of scope'))
Assert-G 'adapter-resume' (Test-GHas $ad @('quick_ready', 'AUTHENTICATION_REQUIRED'))
Assert-G 'adapter-exec' (Test-GHas $ad @('_BrowserExec', '_on_browser_thread', 'greenlet', 'dom_probe', 'count', 'visible'))
$sel = Get-Content (Join-Path $script:Root 'browser_relay/selector_registry.json') -Raw | ConvertFrom-Json
Assert-G 'selector-fallbacks' ($sel.composer.fallback_chain.Count -ge 2 -and $sel.assistant_messages.fallback_chain.Count -ge 2)

# --- registry / commands / config ----------------------------------------
$reg = Read-G 'personas/registry.md'
Assert-G 'registry-row' (Test-GHas $reg @('GPTID', 'personas/tidosgptid.md'))
$cmd = Read-G 'commands/session_commands.md'
Assert-G 'cmd-gptid' (Test-GHas $cmd @('TIDOS GPTID', 'gptid'))
$cfg = Read-G 'config/framework.md'
Assert-G 'config-gptid' (Test-GHas $cfg @('gptid:', 'relay_port', 'dedicated_conversation'))
Assert-G 'config-auto' (Test-GHas $cfg @('headless', 'auto_fallback_to_manual'))

# --- protocol-mirror checks (independent of python impl) ------------------
function Test-Secret { param([string]$Text) return ($Text -match '(?i)(api[_-]?key\s*=|password\s*=|\bssid\s*=|cookie\s*:|BEGIN .*PRIVATE KEY)') }
Assert-G 'mirror-secret-api' (Test-Secret 'api_key=abc123')
Assert-G 'mirror-secret-pass' (Test-Secret 'password=hunter2')
Assert-G 'mirror-secret-cookie' (Test-Secret 'cookie: yummy')
Assert-G 'mirror-clean' (-not (Test-Secret 'three software-engineering observations'))

# --- readiness remediation (shared detector / budget / state truth) ---------
Assert-G 'readiness-detector' (Test-GHas $ad @('def find_usable_composer', 'SEMANTIC_COMPOSER_SELECTORS', '_locator_usable', 'aria-disabled', 'is_editable'))
Assert-G 'readiness-unified' (Test-GHas $ad @('READINESS_BUDGET_MS', 'MONITOR_BUDGET_MS', '_PROBE_SLICE_MS', '_composer_usable(READINESS_BUDGET_MS', '_composer_usable(MONITOR_BUDGET_MS'))
Assert-G 'readiness-liveness' (Test-GHas $ad @('_live_tab_count', 'DEAD:', '_page_alive', 'zero usable ChatGPT tabs'))
Assert-G 'relay-truth' (Test-GHas $relay @('sync_relay_state', '_probe_dead', '_adapter_dead', 'DOWNGRADED-ERROR', 'DOWNGRADED-LOADING'))
Assert-G 'relay-dead-send' (Test-GHas $relay @('_probe_dead(_m)', 'never queue behind a dead page'))
Assert-G 'domprobe-detector' (Test-GHas $relay @('composer_usable', 'DOM_PROBE_BUDGET_MS', 'composer_usable(semantic-first)'))
Assert-G 'file-readiness-tests' (Test-GExists 'browser_relay/tests/test_gptid_readiness.py')
Assert-G 'file-review' (Test-GExists 'browser_relay/gptid_review.py')
Assert-G 'file-review-tests' (Test-GExists 'browser_relay/tests/test_gptid_review.py')
Assert-G 'file-lifecycle-tests' (Test-GExists 'browser_relay/tests/test_gptid_lifecycle.py')

# --- auto-REVIEW policy (decision layer, TIDOS authority preserved) -------
$rev = Read-G 'browser_relay/gptid_review.py'
Assert-G 'review-policy' (Test-GHas $rev @('def decide_review', 'LOW_VALUE_KINDS', 'SIGNIFICANT_KINDS', 'LARGE_CHANGE_LINES'))
Assert-G 'review-gate' (Test-GHas $rev @('def readiness_ok', 'page_state', 'tabs'))
Assert-G 'review-bound' (Test-GHas $rev @('class ReviewLedger', 'already_reviewed', 'gptid-reviews.json'))
Assert-G 'review-untrusted' (Test-GHas $rev @('chatgpt-untrusted', 'def untrusted_envelope', 'verification_checklist'))
Assert-G 'review-noapply' (Test-GHas $rev @('NO code-apply path', 'only TIDOS may act'))
$cli = Read-G 'browser_relay/gptid_cli.py'
Assert-G 'review-cli' (Test-GHas $cli @('review-auto', 'cmd_review_auto', 'no retry'))
Assert-G 'review-ps1' (Test-GHas (Read-G 'scripts/gptid.ps1') @('review-auto', 'ChangeJson'))
Assert-G 'ask-auto-capture' (Test-GHas $cli @('def cmd_ask', 'auto_response', 'correlation=True', 'no retry loop'))
Assert-G 'ask-auto-timeout' (Test-GHas $cli @('response_timeout=args.response_timeout + 60'))
Assert-G 'ask-ps1-timeout' (Test-GHas (Read-G 'scripts/gptid.ps1') @('--response-timeout'))

# --- startup/lifecycle (single spawn, bounded polling, PID safety) --------
Assert-G 'lifecycle-spawn' (Test-GHas $cli @('DEFAULT_STARTUP_TIMEOUT', 'STARTUP_POLL_SECONDS', 'exactly one', '--startup-timeout'))
Assert-G 'lifecycle-pid' (Test-GHas $cli @('_is_relay_process', '_remove_pidfile_if', '_pid_alive', 'PID reuse', '_stop_owned', '_reap_stale_pidfile'))
Assert-G 'lifecycle-ps1' (Test-GHas (Read-G 'scripts/gptid.ps1') @('StartupTimeout'))
Assert-G 'lifecycle-stdio' (Test-GHas $cli @('RELAY_LOG', '_relay_log_handle', '_relay_log_tail', 'unread PIPE'))
Assert-G 'lifecycle-logguard' (Test-GHas (Read-G 'browser_relay/relay_server.py') @('a logging failure must never kill the HTTP response'))

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
