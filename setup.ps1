$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot
uv python install 3.12
uv sync --python 3.12
Write-Host ""
Write-Host "Setup complete" -ForegroundColor Green
Write-Host "1. Add MCP to Claude Desktop: .\configure-claude.ps1"
Write-Host "2. Start viewer and dashboard: .\start.ps1"
