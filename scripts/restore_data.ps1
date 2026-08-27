param(
    [Parameter(Mandatory = $true)][string]$BackupDirectory,
    [string]$DataDirectory = ".\var"
)

$source = [System.IO.Path]::GetFullPath($BackupDirectory)
$sourceDatabase = Join-Path $source "researchflow.db"
if (-not (Test-Path -LiteralPath $sourceDatabase -PathType Leaf)) {
    throw "Backup database not found: $sourceDatabase"
}

$destination = [System.IO.Path]::GetFullPath($DataDirectory)
New-Item -ItemType Directory -Path $destination -Force | Out-Null
$destinationDatabase = Join-Path $destination "researchflow.db"
if (Test-Path -LiteralPath $destinationDatabase) {
    throw "Restore destination is not empty: $destinationDatabase"
}
Copy-Item -LiteralPath $sourceDatabase -Destination $destinationDatabase
$sourceUploads = Join-Path $source "uploads"
if (Test-Path -LiteralPath $sourceUploads -PathType Container) {
    Copy-Item -LiteralPath $sourceUploads -Destination (Join-Path $destination "uploads") -Recurse -Force
}
