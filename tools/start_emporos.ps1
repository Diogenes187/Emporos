param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$emporosRoot = Split-Path -Parent $PSScriptRoot
$runtimeDirectory = Join-Path $emporosRoot 'var'
$pidPath = Join-Path $runtimeDirectory 'emporos-web.pid'
$outputPath = Join-Path $runtimeDirectory 'emporos-web.log'
$errorPath = Join-Path $runtimeDirectory 'emporos-web-error.log'
$localUrl = 'http://127.0.0.1:8765/'

function Import-EmporosEnvironment {
    $environmentPath = Join-Path $emporosRoot '.env'
    if (-not (Test-Path -LiteralPath $environmentPath)) { return }
    foreach ($line in Get-Content -LiteralPath $environmentPath) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#') -or -not $trimmed.Contains('=')) { continue }
        $name, $value = $trimmed.Split('=', 2)
        $name = $name.Trim()
        $value = $value.Trim().Trim('"').Trim("'")
        if ($name -match '^[A-Za-z_][A-Za-z0-9_]*$') {
            [Environment]::SetEnvironmentVariable($name, $value, 'Process')
        }
    }
}

function Test-EmporosWebServer([int]$ProcessId) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    return $null -ne $process -and $process.Name -match '^python' -and $process.CommandLine -like '*uvicorn*app.main:app*'
}

Set-Location -LiteralPath $emporosRoot
Import-EmporosEnvironment
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python was not found. Install Python 3.11 or newer, then run Start Emporos again.'
}
if (-not $env:EMPOROS_DATABASE_URL -and -not $env:BASE_CEPHEUS_DATABASE_URL -and -not $env:DATABASE_URL) {
    throw 'No database connection is configured. Copy .env.example to .env and set EMPOROS_DATABASE_URL.'
}

New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null
if (Test-Path -LiteralPath $pidPath) {
    $existingText = (Get-Content -LiteralPath $pidPath -Raw).Trim()
    if ($existingText -match '^\d+$' -and (Test-EmporosWebServer ([int]$existingText))) {
        Write-Host "Emporos is already running at $localUrl"
        if (-not $NoBrowser) { Start-Process $localUrl }
        exit 0
    }
    Remove-Item -LiteralPath $pidPath -Force
}

$migrationDsn = if ($env:EMPOROS_DATABASE_URL) { $env:EMPOROS_DATABASE_URL } elseif ($env:BASE_CEPHEUS_DATABASE_URL) { $env:BASE_CEPHEUS_DATABASE_URL } else { $env:DATABASE_URL }
$env:EMPOROS_DATABASE_URL = $migrationDsn
$env:BASE_CEPHEUS_DATABASE_URL = $migrationDsn
Write-Host 'Preparing the Emporos database...'
& python -B tools\deploy_database.py
if ($LASTEXITCODE -ne 0) { throw 'Database preparation failed. Review the message above.' }

Write-Host 'Starting the local game server...'
$server = Start-Process -FilePath 'python' -ArgumentList @('-B','-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8765') -WorkingDirectory $emporosRoot -WindowStyle Hidden -RedirectStandardOutput $outputPath -RedirectStandardError $errorPath -PassThru
Set-Content -LiteralPath $pidPath -Value $server.Id -Encoding ascii

$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Milliseconds 250
    if ($server.HasExited) { break }
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri ($localUrl + 'health') -TimeoutSec 1
        if ($response.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
}
if (-not $ready) {
    if (Test-Path -LiteralPath $pidPath) { Remove-Item -LiteralPath $pidPath -Force }
    $detail = if (Test-Path -LiteralPath $errorPath) { (Get-Content -LiteralPath $errorPath -Tail 12) -join [Environment]::NewLine } else { 'No server error log was produced.' }
    throw "Emporos did not start successfully.`n$detail"
}

Write-Host "Emporos is ready at $localUrl"
Write-Host 'Use Stop Emporos.bat when your playtest is finished.'
if (-not $NoBrowser) { Start-Process $localUrl }
