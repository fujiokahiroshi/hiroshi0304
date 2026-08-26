$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$ViewerUrl = "http://127.0.0.1:3939"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Environment not found. Run .\setup.ps1 first."
}
$viewer = Start-Process -FilePath $Python `
    -ArgumentList @("-m", "ocp_vscode", "--port", "3939", "--theme", "dark", "--axes", "--grid_xy") `
    -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru
try {
    $viewerReady = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        try {
            $client = New-Object System.Net.Sockets.TcpClient
            $client.Connect("127.0.0.1", 3939)
            $client.Close()
            $viewerReady = $true
            break
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if (-not $viewerReady) {
        throw "OCP CAD Viewer did not start on port 3939 within 30 seconds."
    }
    Start-Process $ViewerUrl
    & $Python -m cad_workbench.dashboard
}
finally {
    if (-not $viewer.HasExited) { Stop-Process -Id $viewer.Id }
}
