$ErrorActionPreference = "Stop"
$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$webDirectory = Join-Path $repositoryRoot "apps\web"

$env:RESEARCHFLOW_DATABASE_URL = "sqlite+aiosqlite:///./var/e2e.db"
$env:RESEARCHFLOW_KNOWLEDGE_UPLOAD_DIRECTORY = "./var/e2e-uploads"
$env:RESEARCHFLOW_SIMULATION_STEP_DELAY = "0.01"
$env:RESEARCHFLOW_WORKFLOW_MODE = "simulation"
$env:RESEARCHFLOW_CORS_ORIGINS = '["http://127.0.0.1:3100"]'
$env:RESEARCHFLOW_DEMO_ACCESS_CODE = "e2e-portfolio-access"
$env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8100"

$api = $null
$web = $null
try {
    Set-Location $repositoryRoot
    $api = Start-Process -FilePath (Join-Path $repositoryRoot ".venv\Scripts\python.exe") `
        -ArgumentList "-m", "uvicorn", "researchflow.main:app", "--app-dir", "apps/api/src", "--host", "127.0.0.1", "--port", "8100" `
        -WorkingDirectory $repositoryRoot -WindowStyle Hidden -PassThru
    $web = Start-Process -FilePath "npm.cmd" `
        -ArgumentList "run", "dev", "--", "--hostname", "127.0.0.1", "--port", "3100" `
        -WorkingDirectory $webDirectory -WindowStyle Hidden -PassThru

    foreach ($url in "http://127.0.0.1:8100/health", "http://127.0.0.1:3100") {
        $ready = $false
        for ($attempt = 0; $attempt -lt 60; $attempt++) {
            try {
                Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 1 | Out-Null
                $ready = $true
                break
            } catch {
                Start-Sleep -Milliseconds 250
            }
        }
        if (-not $ready) { throw "E2E server did not become ready: $url" }
    }

    & npx.cmd --prefix apps/web playwright test --config apps/web/playwright.config.ts
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    foreach ($process in $web, $api) {
        if ($null -ne $process -and -not $process.HasExited) {
            & taskkill.exe /PID $process.Id /T /F | Out-Null
        }
    }
}
