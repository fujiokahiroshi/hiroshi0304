$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Compiler = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
& $Compiler /nologo /target:winexe /reference:System.Windows.Forms.dll /out:"$ProjectRoot\V8_CAD.exe" "$ProjectRoot\packaging\Launcher.cs"
if ($LASTEXITCODE -ne 0) { throw "Build failed." }
Write-Host "Built $ProjectRoot\V8_CAD.exe"
