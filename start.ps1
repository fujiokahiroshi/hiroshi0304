$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$ViewerUrl = "http://127.0.0.1:3939"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Environment not found. Run .\setup.ps1 first."
}

function Test-ViewerAlive {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $client.Connect("127.0.0.1", 3939)
        $client.Close()
        return $true
    }
    catch {
        return $false
    }
}

function Find-AppModeBrowser {
    $candidates = @(
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path -LiteralPath $path) { return $path }
    }
    throw "No Chromium-based browser (Chrome/Edge) found for --app mode."
}

# --- Windows Job Object: kills a process unconditionally the moment the job
# handle is closed (process exit, crash, or this script being killed all
# close the handle via normal OS handle teardown -- no polling, no timeout). ---
Add-Type -Namespace V8Cad -Name JobObject -MemberDefinition @"
    [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
    public struct JOBOBJECT_BASIC_LIMIT_INFORMATION {
        public long PerProcessUserTimeLimit;
        public long PerJobUserTimeLimit;
        public uint LimitFlags;
        public UIntPtr MinimumWorkingSetSize;
        public UIntPtr MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public long Affinity;
        public uint PriorityClass;
        public uint SchedulingClass;
    }

    [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
    public struct IO_COUNTERS {
        public ulong ReadOperationCount;
        public ulong WriteOperationCount;
        public ulong OtherOperationCount;
        public ulong ReadTransferCount;
        public ulong WriteTransferCount;
        public ulong OtherTransferCount;
    }

    [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
    public struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION {
        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
        public IO_COUNTERS IoInfo;
        public UIntPtr ProcessMemoryLimit;
        public UIntPtr JobMemoryLimit;
        public UIntPtr PeakProcessMemoryUsed;
        public UIntPtr PeakJobMemoryUsed;
    }

    [System.Runtime.InteropServices.DllImport("kernel32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
    public static extern System.IntPtr CreateJobObject(System.IntPtr lpJobAttributes, string lpName);

    [System.Runtime.InteropServices.DllImport("kernel32.dll")]
    public static extern bool SetInformationJobObject(System.IntPtr hJob, int JobObjectInfoClass, System.IntPtr lpJobObjectInfo, uint cbJobObjectInfoLength);

    [System.Runtime.InteropServices.DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool AssignProcessToJobObject(System.IntPtr hJob, System.IntPtr hProcess);

    [System.Runtime.InteropServices.DllImport("kernel32.dll")]
    public static extern bool CloseHandle(System.IntPtr hObject);

    public const int JobObjectExtendedLimitInformation = 9;
    public const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000;

    public static System.IntPtr CreateKillOnCloseJob() {
        System.IntPtr job = CreateJobObject(System.IntPtr.Zero, null);
        var info = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        int length = System.Runtime.InteropServices.Marshal.SizeOf(typeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION));
        System.IntPtr infoPtr = System.Runtime.InteropServices.Marshal.AllocHGlobal(length);
        System.Runtime.InteropServices.Marshal.StructureToPtr(info, infoPtr, false);
        SetInformationJobObject(job, JobObjectExtendedLimitInformation, infoPtr, (uint)length);
        System.Runtime.InteropServices.Marshal.FreeHGlobal(infoPtr);
        return job;
    }
"@

# cad_workbench never touches the browser/viewer lifecycle itself; a Windows
# Job Object does. As long as this script (the only sanctioned launcher) is
# the one starting things, "already alive" always means "the supervised
# browser window is still open" -- reuse it instead of spawning a second one.
if (Test-ViewerAlive) {
    Write-Host "OCP CAD Viewer is already running on port 3939 - reusing it."
    return
}

$viewer = Start-Process -FilePath $Python `
    -ArgumentList @("-m", "ocp_vscode", "--port", "3939", "--theme", "dark", "--axes", "--grid_xy") `
    -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru

$job = [V8Cad.JobObject]::CreateKillOnCloseJob()
[V8Cad.JobObject]::AssignProcessToJobObject($job, $viewer.Handle) | Out-Null

try {
    $viewerReady = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if (Test-ViewerAlive) { $viewerReady = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $viewerReady) {
        throw "OCP CAD Viewer did not start on port 3939 within 30 seconds."
    }

    $browserProfile = Join-Path $ProjectRoot "runtime\viewer-profile"
    $browser = Find-AppModeBrowser
    $browserProcess = Start-Process -FilePath $browser `
        -ArgumentList @("--app=$ViewerUrl", "--user-data-dir=$browserProfile") -PassThru

    $dashboard = Start-Process -FilePath $Python -ArgumentList @("-m", "cad_workbench.dashboard") `
        -WorkingDirectory $ProjectRoot -PassThru

    Write-Host "Viewer window open. Close it to stop the CAD Viewer. Press Ctrl+C here to stop early."
    $browserProcess.WaitForExit()
}
finally {
    # Closing the job handle unconditionally kills the viewer process, however
    # this script itself ends (normal exit, Ctrl+C, or a crash tearing down
    # its handles) -- no timeout, no polling, no reliance on browser JS.
    [V8Cad.JobObject]::CloseHandle($job) | Out-Null
    if ($dashboard -and -not $dashboard.HasExited) { Stop-Process -Id $dashboard.Id -ErrorAction SilentlyContinue }
}
