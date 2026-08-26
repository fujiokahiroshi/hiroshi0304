$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$ConfigDir = Join-Path $env:APPDATA "Claude"
$ConfigFile = Join-Path $ConfigDir "claude_desktop_config.json"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Environment not found. Run .\setup.ps1 first."
}
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
if (Test-Path -LiteralPath $ConfigFile) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    Copy-Item -LiteralPath $ConfigFile -Destination "$ConfigFile.backup-$stamp"
}
$config = if (Test-Path -LiteralPath $ConfigFile) {
    Get-Content -LiteralPath $ConfigFile -Raw | ConvertFrom-Json
} else { [PSCustomObject]@{} }
if (-not $config.PSObject.Properties["mcpServers"]) {
    $config | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue ([PSCustomObject]@{})
}
$serverConfig = [PSCustomObject]@{
    command = $Python
    args = @("-m", "cad_workbench.server")
}
if ($config.mcpServers.PSObject.Properties["cad-workbench"]) {
    $config.mcpServers."cad-workbench" = $serverConfig
} else {
    $config.mcpServers | Add-Member -NotePropertyName "cad-workbench" -NotePropertyValue $serverConfig
}
$json = $config | ConvertTo-Json -Depth 20
[System.IO.File]::WriteAllText($ConfigFile, $json, [System.Text.UTF8Encoding]::new($false))
Write-Host "Updated Claude Desktop config: $ConfigFile" -ForegroundColor Green
Write-Host "Quit Claude Desktop completely, then restart it."
