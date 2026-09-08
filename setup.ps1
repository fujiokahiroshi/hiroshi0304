$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv was not found on PATH. Install it first: https://docs.astral.sh/uv/getting-started/installation/"
}

Write-Host "Syncing Python environment with uv (creates/updates .venv from uv.lock)..." -ForegroundColor Cyan
uv sync

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "uv sync finished but .venv\Scripts\python.exe was not found. Check the uv output above for errors."
}

Write-Host "Environment ready at $Python" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "  .\configure-claude.ps1   # register the cad-workbench MCP server with Claude Desktop"
Write-Host "  .\start.ps1              # start OCP CAD Viewer and the dashboard"
