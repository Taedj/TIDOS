param($Source, $Destination)

$files = Get-ChildItem $Source -Filter *.txt
foreach ($f in $files) {
    $cmd = "Copy-Item " + $f.FullName + " " + $Destination
    Invoke-Expression $cmd
}
Write-Host "Copied $($files.Count) files"
