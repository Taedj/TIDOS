param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Destination
)

if (-not (Test-Path -LiteralPath $Destination)) {
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
}
$files = @(Get-ChildItem -LiteralPath $Source -File | Where-Object { $_.Extension -eq ".txt" })
foreach ($f in $files) {
    Copy-Item -LiteralPath $f.FullName -Destination (Join-Path $Destination $f.Name)
}
Write-Output "Copied $($files.Count) files"
