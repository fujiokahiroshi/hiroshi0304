param(
    [string]$TunnelId = "tunnel_6a9ce3cefd2c8191ac1728130ba82456",
    [string]$TunnelClient
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not $TunnelClient) {
    $TunnelClient = Join-Path $ProjectRoot "runtime\tunnel-client-v0.0.14\tunnel-client-runtime.exe"
}
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Environment not found. Run .\setup.ps1 first."
}
if (-not (Get-Command $TunnelClient -ErrorAction SilentlyContinue)) {
    throw "Tunnel client not found: $TunnelClient"
}
if ([string]::IsNullOrWhiteSpace($TunnelId)) {
    throw "A TunnelId is required."
}

$EnteredKey = $false
Push-Location $ProjectRoot
try {
    if (-not $env:CONTROL_PLANE_API_KEY) {
        $Secret = Read-Host "Enter tunnel runtime API key (hidden)" -AsSecureString
        $Credential = New-Object System.Net.NetworkCredential("", $Secret)
        $env:CONTROL_PLANE_API_KEY = $Credential.Password
        Remove-Variable Secret, Credential
        $EnteredKey = $true
    }
    if ([string]::IsNullOrWhiteSpace($env:CONTROL_PLANE_API_KEY)) {
        throw "API key is empty."
    }
    # Forward slashes avoid Windows backslash interpretation in command parsing.
    $McpCommand = "command=" + $Python.Replace('\', '/') + " -m cad_workbench.server"
    Write-Host "Keep this terminal running while using CAD from ChatGPT. Press Ctrl+C to stop."
    & $TunnelClient run `
        --control-plane.tunnel-id $TunnelId `
        --control-plane.api-key env:CONTROL_PLANE_API_KEY `
        --mcp.command $McpCommand `
        --mcp.stdio-send-initialized-notification `
        --health.listen-addr 127.0.0.1:0 `
        --health.url-file (Join-Path $ProjectRoot "runtime\chatgpt-tunnel-health-url.txt")
    if ($LASTEXITCODE -ne 0) { throw "Tunnel client exited with code $LASTEXITCODE." }
}
finally {
    if ($EnteredKey) { Remove-Item Env:CONTROL_PLANE_API_KEY -ErrorAction SilentlyContinue }
    Pop-Location
}
