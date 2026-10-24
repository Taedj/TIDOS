param([string]$Path)

$rows = Import-Csv $Path
$groups = $rows | Group-Object group
foreach ($g in $groups) {
    $avg = ($g.Group | Measure-Object -Property grade -Average).Average
    Write-Output "$($g.Name): $avg ($($g.Count) students)"
}
