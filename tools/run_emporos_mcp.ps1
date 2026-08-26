$ErrorActionPreference = 'Stop'
$emporosRoot = Split-Path -Parent $PSScriptRoot
$environmentPath = Join-Path $emporosRoot '.env'

if (Test-Path -LiteralPath $environmentPath) {
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
if (-not $env:EMPOROS_DATABASE_URL -and -not $env:BASE_CEPHEUS_DATABASE_URL -and -not $env:DATABASE_URL) {
    throw 'No Emporos database connection is configured.'
}
Set-Location -LiteralPath $emporosRoot
& python -B mcp_server.py
exit $LASTEXITCODE
