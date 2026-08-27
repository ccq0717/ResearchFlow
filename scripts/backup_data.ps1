param(
    [string]$DataDirectory = ".\var",
    [string]$BackupRoot = ".\backups"
)

$dataPath = [System.IO.Path]::GetFullPath($DataDirectory)
$databasePath = Join-Path $dataPath "researchflow.db"
if (-not (Test-Path -LiteralPath $databasePath -PathType Leaf)) {
    throw "Database not found: $databasePath"
}

$destination = Join-Path ([System.IO.Path]::GetFullPath($BackupRoot)) (Get-Date -Format "yyyyMMdd-HHmmss")
New-Item -ItemType Directory -Path $destination | Out-Null
Copy-Item -LiteralPath $databasePath -Destination (Join-Path $destination "researchflow.db")
$uploadsPath = Join-Path $dataPath "uploads"
if (Test-Path -LiteralPath $uploadsPath -PathType Container) {
    Copy-Item -LiteralPath $uploadsPath -Destination (Join-Path $destination "uploads") -Recurse
}
Write-Output $destination
