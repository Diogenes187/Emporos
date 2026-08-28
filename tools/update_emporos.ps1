param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$emporosRoot = Split-Path -Parent $PSScriptRoot

Set-Location -LiteralPath $emporosRoot
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git was not found. Install GitHub Desktop or Git for Windows, then try again.'
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python was not found. Install Python 3.11 or newer, then try again.'
}

$branch = (& git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $branch -ne 'main') {
    throw "Updates require the main branch. The current branch is '$branch'."
}
$changes = & git status --porcelain
if ($LASTEXITCODE -ne 0) { throw 'Git could not inspect the Emporos folder.' }
if ($changes) {
    throw 'Emporos has local file changes. Preserve or discard them in GitHub Desktop before updating.'
}

& (Join-Path $PSScriptRoot 'stop_emporos.ps1')
Write-Host 'Downloading the latest Emporos release from GitHub...'
& git pull --ff-only origin main
if ($LASTEXITCODE -ne 0) { throw 'Git could not update Emporos. Review the message above.' }

Write-Host 'Checking Python dependencies...'
& python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }

Write-Host 'Starting the updated game...'
if ($NoBrowser) {
    & (Join-Path $PSScriptRoot 'start_emporos.ps1') -NoBrowser
} else {
    & (Join-Path $PSScriptRoot 'start_emporos.ps1')
}
