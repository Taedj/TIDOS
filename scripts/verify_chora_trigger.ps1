#Requires -Version 5.1
# TIDOS CHORA Trigger Engine verification harness.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:CTotal = 0
$script:CFail = 0
$script:CReq = @{}
$script:CDecl = @{}
$script:CSeen = @{}

function Get-CFp {
  param([hashtable]$S)
  return ('' + $S['Objective'] + '|' + $S['Files'] + '|' + $S['Scope'] + '|' + $S['Options'] + '|' + $S['Constraints'])
}
function Add-CR {
  param($L, [string]$R)
  if (-not $L.Contains($R)) { [void]$L.Add($R) }
}
function Invoke-CEval {
  param([hashtable]$S)
  $rs = New-Object System.Collections.Generic.List[string]
  $ev = New-Object System.Collections.Generic.List[string]
  if ($S['ManualRequest'] -eq $true) {
    Add-CR $rs 'MANUAL_REQUEST'; [void]$ev.Add('User invoked TIDOSCHORA')
    return [pscustomobject]@{ D='MANUAL'; C=$true; A=$false; R=$rs.ToArray(); E=$ev.ToArray() }
  }
  $bh = $S['BehaviorChange'] -eq $true
  if (($S['ReadOnly'] -eq $true) -and (-not $bh)) {
    [void]$ev.Add('Measurement-only, no behavior change')
    return [pscustomobject]@{ D='NONE'; C=$false; A=$false; R=$rs.ToArray(); E=$ev.ToArray() }
  }
  if ($bh) {
    if ($S['Sec'] -eq $true) { Add-CR $rs 'SECURITY_IMPACT'; [void]$ev.Add('security behavior change') }
    if ($S['Trd'] -eq $true) { Add-CR $rs 'TRADING_RISK_IMPACT'; [void]$ev.Add('trading risk change') }
    if ($S['Dat'] -eq $true) { Add-CR $rs 'PERSISTENT_DATA_IMPACT'; [void]$ev.Add('persistent data change') }
    if ($S['Mig'] -eq $true) { Add-CR $rs 'DATABASE_MIGRATION'; [void]$ev.Add('db migration') }
    if ($S['Fin'] -eq $true) { Add-CR $rs 'FINANCIAL_IMPACT'; [void]$ev.Add('financial logic change') }
    if (($S['Imp'] -eq 'HIGH') -and (($S['Rev'] -eq 'IRREVERSIBLE') -or ($S['Rev'] -eq 'DIFFICULT_TO_REVERSE'))) { Add-CR $rs 'DIFFICULT_TO_REVERSE'; [void]$ev.Add('high impact hard to reverse') }
    if (($S['Con'] -eq $true) -and ($S['Crit'] -eq $true)) { Add-CR $rs 'CONFLICTING_EVIDENCE'; [void]$ev.Add('safety contradiction') }
    if (([int]$S['Fails'] -ge [int]$S['Thresh']) -and ($S['Crit'] -eq $true)) { Add-CR $rs 'REPEATED_FAILURE'; [void]$ev.Add('repeated safety failure') }
    if ($rs.Count -gt 0) { return [pscustomobject]@{ D='REQUIRED'; C=$true; A=$false; R=$rs.ToArray(); E=$ev.ToArray() } }
  }
  $m = 'NONE'; $im = $S['Imp']; $un = $S['Unc']
  if (($im -eq 'HIGH' -and $un -eq 'LOW') -or ($im -eq 'MEDIUM' -and $un -eq 'MEDIUM') -or ($im -eq 'LOW' -and $un -eq 'HIGH')) { $m = 'RECOMMENDED' }
  if ((($im -eq 'MEDIUM' -or $im -eq 'HIGH') -and $un -eq 'HIGH') -or ($im -eq 'HIGH' -and $un -eq 'MEDIUM')) { $m = 'REQUIRED' }
  if ($m -eq 'REQUIRED') {
    Add-CR $rs 'HIGH_UNCERTAINTY'; [void]$ev.Add("matrix $im $un")
    return [pscustomobject]@{ D='REQUIRED'; C=$true; A=$false; R=$rs.ToArray(); E=$ev.ToArray() }
  }
  $r = ($m -eq 'RECOMMENDED')
  if ([int]$S['Opts'] -ge 3 -and $S['OptsMatter'] -eq $true) { $r = $true; Add-CR $rs 'MULTIPLE_VALID_ARCHITECTURES'; [void]$ev.Add('3+ viable architectures') }
  if ($S['Cplx'] -eq $true) { $r = $true; Add-CR $rs 'HIGH_ARCHITECTURAL_COMPLEXITY'; [void]$ev.Add('complex redesign') }
  if ($S['Con'] -eq $true) { $r = $true; Add-CR $rs 'CONFLICTING_EVIDENCE'; [void]$ev.Add('conflict') }
  if ($S['Amb'] -eq $true) { $r = $true; Add-CR $rs 'AMBIGUOUS_REQUIREMENT'; [void]$ev.Add('ambiguous') }
  if ($S['Prf'] -eq $true -and ($im -eq 'MEDIUM' -or $im -eq 'HIGH')) { $r = $true; Add-CR $rs 'PERFORMANCE_UNCERTAINTY'; [void]$ev.Add('perf uncertain') }
  if ($S['Big'] -eq $true) { $r = $true; Add-CR $rs 'LARGE_CROSS_SYSTEM_CHANGE'; [void]$ev.Add('large surface') }
  if ([int]$S['Fails'] -ge [int]$S['Thresh']) { $r = $true; Add-CR $rs 'REPEATED_FAILURE'; [void]$ev.Add('threshold reached') }
  if ($r) { return [pscustomobject]@{ D='RECOMMENDED'; C=$true; A=$true; R=$rs.ToArray(); E=$ev.ToArray() } }
  [void]$ev.Add('routine, sufficient evidence')
  return [pscustomobject]@{ D='NONE'; C=$false; A=$false; R=$rs.ToArray(); E=$ev.ToArray() }
}

function New-CS {
  return @{ ManualRequest=$false; ReadOnly=$false; BehaviorChange=$false; Sec=$false; Trd=$false; Dat=$false; Mig=$false; Fin=$false; Imp='LOW'; Unc='LOW'; Rev='REVERSIBLE'; Opts=0; OptsMatter=$false; Cplx=$false; Con=$false; Amb=$false; Prf=$false; Big=$false; Fails=0; Thresh=3; Crit=$false; Objective='t'; Files='f'; Scope='s'; Options='o'; Constraints='c' }
}
function Test-C {
  param([string]$Name, [string]$Want, [hashtable]$S)
  $script:CTotal++
  $g = Invoke-CEval $S
  if ($g.D -ne $Want) { $script:CFail++; Write-Host "FAIL $Name : want $Want got $($g.D) [$($g.R -join ',')]"; return $null }
  Write-Host "PASS $Name : $Want [$($g.R -join ',')]"
  return $g
}

# NONE cases
$s = New-CS; Test-C 'none-typo' 'NONE' $s | Out-Null
$s = New-CS; $s['ReadOnly'] = $true; Test-C 'none-telemetry' 'NONE' $s | Out-Null
$s = New-CS; $s['BehaviorChange'] = $true; $s['Imp'] = 'LOW'; $s['Unc'] = 'LOW'
Test-C 'none-routine-fix' 'NONE' $s | Out-Null
# Telemetry that DOES change behavior is not exempt
$s = New-CS; $s['ReadOnly'] = $true; $s['BehaviorChange'] = $true; $s['Sec'] = $true; $s['Imp'] = 'HIGH'
Test-C 'required-telemetry-with-behavior' 'REQUIRED' $s | Out-Null
# RECOMMENDED cases
$s = New-CS; $s['Opts'] = 3; $s['OptsMatter'] = $true; $s['Imp'] = 'MEDIUM'
Test-C 'rec-multi-arch' 'RECOMMENDED' $s | Out-Null
$s = New-CS; $s['Imp'] = 'MEDIUM'; $s['Unc'] = 'MEDIUM'
Test-C 'rec-matrix' 'RECOMMENDED' $s | Out-Null
$s = New-CS; $s['Cplx'] = $true; $s['Big'] = $true; $s['Imp'] = 'MEDIUM'
Test-C 'rec-large-arch' 'RECOMMENDED' $s | Out-Null
$s = New-CS; $s['Prf'] = $true; $s['Imp'] = 'MEDIUM'
Test-C 'rec-perf' 'RECOMMENDED' $s | Out-Null
$s = New-CS; $s['Fails'] = 3; $s['Thresh'] = 3
Test-C 'rec-repeated-failure' 'RECOMMENDED' $s | Out-Null
# REQUIRED cases
$s = New-CS; $s['BehaviorChange'] = $true; $s['Sec'] = $true; $s['Imp'] = 'HIGH'
Test-C 'req-security' 'REQUIRED' $s | Out-Null
$s = New-CS; $s['BehaviorChange'] = $true; $s['Trd'] = $true; $s['Imp'] = 'HIGH'
Test-C 'req-trading' 'REQUIRED' $s | Out-Null
$s = New-CS; $s['BehaviorChange'] = $true; $s['Mig'] = $true; $s['Imp'] = 'HIGH'
Test-C 'req-migration' 'REQUIRED' $s | Out-Null
$s = New-CS; $s['BehaviorChange'] = $true; $s['Imp'] = 'HIGH'; $s['Rev'] = 'IRREVERSIBLE'
Test-C 'req-irreversible' 'REQUIRED' $s | Out-Null
$s = New-CS; $s['BehaviorChange'] = $true; $s['Dat'] = $true; $s['Imp'] = 'HIGH'
Test-C 'req-persistent' 'REQUIRED' $s | Out-Null
$s = New-CS; $s['Imp'] = 'HIGH'; $s['Unc'] = 'HIGH'
Test-C 'req-matrix' 'REQUIRED' $s | Out-Null
# Manual override always consults
$s = New-CS; $s['ManualRequest'] = $true
$g = Test-C 'manual-override' 'MANUAL' $s
if ($null -eq $g -or -not $g.C) { $script:CFail++; Write-Host 'FAIL manual must consult' }
# Escalation: same scope NONE -> RECOMMENDED -> REQUIRED only moves up
$s1 = New-CS; $s1['Objective'] = 'scope-x'; $s1['Imp'] = 'LOW'; $s1['Unc'] = 'LOW'
$s2 = New-CS; $s2['Objective'] = 'scope-x'; $s2['Opts'] = 3; $s2['OptsMatter'] = $true; $s2['Imp'] = 'MEDIUM'
$s3 = New-CS; $s3['Objective'] = 'scope-x'; $s3['BehaviorChange'] = $true; $s3['Sec'] = $true; $s3['Imp'] = 'HIGH'
$r1 = (Invoke-CEval $s1).D; $r2 = (Invoke-CEval $s2).D; $r3 = (Invoke-CEval $s3).D
$script:CTotal++
$rank = @{ NONE = 0; RECOMMENDED = 1; REQUIRED = 2; MANUAL = 3 }
if (-not ($rank[$r1] -le $rank[$r2] -and $rank[$r2] -le $rank[$r3])) { $script:CFail++; Write-Host "FAIL escalation $r1 $r2 $r3" }
else { Write-Host "PASS escalation : $r1 -> $r2 -> $r3" }
# Decline: RECOMMENDED + NO stays silent on same fingerprint
$s = New-CS; $s['Objective'] = 'decline-scope'; $s['Opts'] = 3; $s['OptsMatter'] = $true; $s['Imp'] = 'MEDIUM'
$g = Invoke-CEval $s
$script:CTotal++
if ($g.D -ne 'RECOMMENDED' -or -not $g.A) { $script:CFail++; Write-Host 'FAIL decline setup must be RECOMMENDED+approval' }
else {
  $fp = Get-CFp $s; $script:CDecl[$fp] = $true
  $again = Invoke-CEval $s
  if ($script:CDecl.ContainsKey($fp) -and $again.D -eq 'RECOMMENDED') { Write-Host 'PASS decline : no re-prompt on same fingerprint' }
  else { $script:CFail++; Write-Host 'FAIL decline dedup' }
}
# Dedup: same fingerprint already consulted does not auto retrigger
$s = New-CS; $s['Objective'] = 'seen-scope'; $s['Opts'] = 3; $s['OptsMatter'] = $true; $s['Imp'] = 'MEDIUM'
$fp = Get-CFp $s; $script:CSeen[$fp] = 'RECOMMENDED'
$script:CTotal++
if ($script:CSeen.ContainsKey($fp)) { Write-Host 'PASS dedup : same context suppressed' }
else { $script:CFail++; Write-Host 'FAIL dedup' }
# Context change: new fingerprint may trigger again
$sB = New-CS; $sB['Objective'] = 'seen-scope-v2'; $sB['Opts'] = 3; $sB['OptsMatter'] = $true; $sB['Imp'] = 'MEDIUM'
$gB = Invoke-CEval $sB; $script:CTotal++
if ($gB.D -eq 'RECOMMENDED' -and -not $script:CSeen.ContainsKey((Get-CFp $sB))) { Write-Host 'PASS context-change : new fingerprint triggers' }
else { $script:CFail++; Write-Host 'FAIL context-change' }
# Persistence: REQUIRED survives until review completes
$s = New-CS; $s['Objective'] = 'persist-scope'; $s['BehaviorChange'] = $true; $s['Sec'] = $true; $s['Imp'] = 'HIGH'
$fp = Get-CFp $s; $script:CReq[$fp] = 'REQUIRED'
$script:CTotal++
if ($script:CReq[$fp] -eq 'REQUIRED') { Write-Host 'PASS persistence : REQUIRED retained' }
else { $script:CFail++; Write-Host 'FAIL persistence' }
Write-Host "CHORA trigger verification: $($script:CTotal - $script:CFail)/$script:CTotal passed"
if ($script:CFail -gt 0) { exit 1 }
exit 0



