$ErrorActionPreference = "Stop"

Write-Host "setup.ps1 is disabled to prevent accidental CAD environment rebuilds." -ForegroundColor Yellow
Write-Host "Use .\start.ps1 to start OCP CAD Viewer and the dashboard." -ForegroundColor Cyan
throw "setup.ps1 is intentionally disabled."
