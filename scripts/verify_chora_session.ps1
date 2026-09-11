#Requires -Version 5.1
# TIDOS CHORA Session structural validator.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:STotal = 0
$script:SFail = 0
$script:SRoot = Split-Path -Parent $PSScriptRoot

function Assert-S {
  param([string]$Name, [bool]$Cond, [string]$Detail = '')
  $script:STotal++
  if ($Cond) { Write-Host "PASS $Name" }
  else { $script:SFail++; Write-Host "FAIL $Name $Detail" }
}
function Read-S { param([string]$Rel) return (Get-Content (Join-Path $script:SRoot $Rel) -Raw) }
function Has-S {
  param([string]$Text, [string[]]$Needles)
  foreach ($n in $Needles) { if ($Text -notmatch [regex]::Escape($n)) { return $false } }
  return $true
}

$eng = Read-S 'engines/chora_session_engine.md'
Assert-S 'engine-chain' (Has-S $eng @('TIDOS -> Trigger Engine -> CHORA Session', 'Human Bridge', 'TIDOS Verification', 'TIDOS Synthesis', 'TIDOS Decision'))
Assert-S 'engine-authority' (Has-S $eng @('Actual repository / code', 'Executed tests', 'advisor statement != verified project fact'))
Assert-S 'engine-states' (Has-S $eng @('SCOPE-LOCK', 'AWAIT-RESPONSES', 'CLAIM-EXTRACT', 'DECIDE', 'VALIDATE', 'CLOSE'))
Assert-S 'engine-round2' (Has-S $eng @('Round 2 is an exception', 'max_rounds'))
Assert-S 'engine-required' (Has-S $eng @('DECIDED + VALIDATED'))
Assert-S 'engine-memory' (Has-S $eng @('session instances stay out of', 'chora_outcome'))
Assert-S 'engine-security' (Has-S $eng @('zero secrets', 'untrusted input'))
Assert-S 'engine-no-vote' (($eng -match 'majority is never a decision') -and ($eng -match 'never means "implement"'))

$base = Read-S 'prompts/chora/advisor_base.md'
Assert-S 'prompt-schema' (Has-S $base @('Falsification mandate', 'Consultation scope', 'Response schema', 'Disproving test', 'No secrets'))
Assert-S 'prompt-falsify' ($base -match 'Try to falsify')
$lens = Read-S 'prompts/chora/perspectives.md'
Assert-S 'prompt-lenses' (Has-S $lens @('Architecture', 'Security', 'Performance', 'Algorithm / Math', 'Quantitative / Risk', 'QA / Validation', 'Adversarial'))

Assert-S 'tpl-session' (Has-S (Read-S 'templates/chora_session.md') @('Locked scope', 'Advisors', 'Fingerprint'))
Assert-S 'tpl-response' (Has-S (Read-S 'templates/chora_response.md') @('verbatim', 'external-untrusted', 'Prompt hash'))
Assert-S 'tpl-claims' ((Has-S (Read-S 'templates/chora_claims.md') @('UNVERIFIABLE', 'SUPERSEDED', 'advisor statement != verified project fact')) -and ((Read-S 'templates/chora_claims.md') -match 'PENDING'))
Assert-S 'tpl-synthesis' (Has-S (Read-S 'templates/chora_synthesis.md') @('verified claims only', 'TIDOS decision', 'chora_outcome'))

$guide = Read-S 'docs/chora_session.md'
Assert-S 'guide-bridge' (Has-S $guide @('human transport', 'verbatim', 'never execute'))
Assert-S 'guide-security' (Has-S $guide @('zero secrets', 'untrusted'))

$cfg = Read-S 'config/framework.md'
Assert-S 'config-session' (Has-S $cfg @('chora:', 'max_rounds', 'human_bridge'))
$cmd = Read-S 'commands/session_commands.md'
Assert-S 'cmd-sub' (Has-S $cmd @('TIDOSCHORA', 'start', 'scope', 'status', 'close'))

# Dry-run: fake local decision through every stage, no external AI.
$dry = @{}
$dry['Trigger'] = 'MANUAL TIDOSCHORA handoff with MANUAL_REQUEST'
$dry['Session'] = 'chora-dryrun-001 OPEN'
$dry['Scope'] = 'Q: keep trigger threshold at 3? Decision: keep vs raise to 5'
$dry['Advisors'] = 'A1 Architecture + A2 Adversarial (local simulated replies)'
$dry['Prompts'] = 'rendered from advisor_base with falsification mandate'
$dry['Responses'] = '2 verbatim local envelopes, provenance external-untrusted'
$dry['Claims'] = 'C1 testability, C2 threshold evidence, C3 opinion (kept opinion)'
$dry['Verification'] = 'repo-code + config read: threshold=3 present; change needs evidence'
$dry['Comparison'] = 'agree on evidence rule; disagree on default value'
$dry['Synthesis'] = 'verified claims only; no majority vote'
$dry['Decision'] = 'keep 3 until repo evidence justifies change'
$dry['Validation'] = 'verify_chora_session + verify_chora_trigger green'
$dry['ADR'] = 'draft ADR ref linked to session record'
$stages = @('Trigger','Session','Scope','Advisors','Prompts','Responses','Claims','Verification','Comparison','Synthesis','Decision','Validation','ADR')
foreach ($k in $stages) { Assert-S "dryrun-$($k.ToLower())" ($dry.ContainsKey($k) -and $dry[$k].Length -gt 0) }

Write-Host "CHORA session verification: $($script:STotal - $script:SFail)/$script:STotal passed"
if ($script:SFail -gt 0) { exit 1 }
exit 0


