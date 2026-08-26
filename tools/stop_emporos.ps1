$ErrorActionPreference = 'Stop'
$emporosRoot = Split-Path -Parent $PSScriptRoot
$pidPath = Join-Path $emporosRoot 'var\emporos-web.pid'

if (-not (Test-Path -LiteralPath $pidPath)) {
    Write-Host 'Emporos is not recorded as running.'
    exit 0
}
$pidText = (Get-Content -LiteralPath $pidPath -Raw).Trim()
if ($pidText -notmatch '^\d+$') {
    throw 'The Emporos process record is invalid. No process was stopped.'
}
$processId = [int]$pidText
$process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
if ($null -eq $process) {
    Remove-Item -LiteralPath $pidPath -Force
    Write-Host 'Emporos was already stopped.'
    exit 0
}
if ($process.Name -notmatch '^python' -or $process.CommandLine -notlike '*uvicorn*app.main:app*') {
    throw "Process $processId is not an Emporos web server. No process was stopped."
}
Stop-Process -Id $processId
Remove-Item -LiteralPath $pidPath -Force
Write-Host 'Emporos stopped.'
