param([Parameter(Mandatory = $true)][string]$Path)

$inv = [System.Globalization.CultureInfo]::InvariantCulture
$lines = Get-Content -LiteralPath $Path -Encoding UTF8 | Where-Object { $_.Trim() -ne '' }
$rows = $lines | ConvertFrom-Csv -Delimiter ';'
$groups = $rows | Group-Object -Property group | Sort-Object -Property Name
foreach ($g in $groups) {
    $values = @($g.Group | ForEach-Object { [double]::Parse(($_.grade.Trim() -replace ',', '.'), $inv) })
    $avg = ($values | Measure-Object -Average).Average
    Write-Output ("{0}: {1} ({2} students)" -f $g.Name, $avg.ToString('0.00', $inv), $values.Count)
}
