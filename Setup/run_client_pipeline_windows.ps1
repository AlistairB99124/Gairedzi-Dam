$ErrorActionPreference = "Stop"

$SetupDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $SetupDir
$ElmerDir = Join-Path $RootDir "Elmer"
$LogDir = Join-Path $RootDir "results\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path $LogDir ("run_windows_" + $Timestamp + ".log")

function Write-Section([string]$Message) {
    Write-Host ""
    Write-Host "==== $Message ===="
}

function Find-Exe([string]$Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    return $null
}

function Test-PythonCommand {
    param(
        [string]$Exe,
        [string[]]$PrefixArgs = @()
    )

    if (-not $Exe) {
        return $false
    }
    if (-not (Test-Path $Exe)) {
        return $false
    }

    $allArgs = @()
    if ($PrefixArgs) {
        $allArgs += $PrefixArgs
    }
    $allArgs += "--version"

    $previousErrorAction = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = & $Exe @allArgs 2>&1
        $exitCode = $LASTEXITCODE
        $text = ($output | Out-String).Trim()
    }
    catch {
        return $false
    }
    finally {
        $ErrorActionPreference = $previousErrorAction
    }

    if ($exitCode -ne 0) {
        return $false
    }
    if ($text -notmatch "^Python\s+\d+\.\d+") {
        return $false
    }
    return $true
}

function Refresh-PathFromSystem {
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    if ($machinePath -and $userPath) {
        $env:Path = "$machinePath;$userPath"
    }
    elseif ($machinePath) {
        $env:Path = $machinePath
    }
    elseif ($userPath) {
        $env:Path = $userPath
    }
}

function Resolve-PythonCommand {
    $pyLauncher = Find-Exe "py"
    if (Test-PythonCommand -Exe $pyLauncher -PrefixArgs @("-3")) {
        return @{ Exe = $pyLauncher; PrefixArgs = @("-3") }
    }

    $pythonExe = Find-Exe "python"
    if (Test-PythonCommand -Exe $pythonExe) {
        return @{ Exe = $pythonExe; PrefixArgs = @() }
    }

    $commonInstalls = @(
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:ProgramFiles\Python313\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "$env:ProgramFiles\Python311\python.exe"
    )
    foreach ($candidate in $commonInstalls) {
        if (Test-PythonCommand -Exe $candidate) {
            return @{ Exe = $candidate; PrefixArgs = @() }
        }
    }

    return $null
}

function Resolve-ElmerFromCommonPaths {
    $candidates = @(
        "$env:ProgramFiles\Elmer*\bin",
        "$env:ProgramFiles\Elmer\bin",
        "$env:ProgramFiles\elmer\bin",
        "$env:LOCALAPPDATA\Programs\Elmer*\bin",
        "$env:LOCALAPPDATA\Programs\Elmer\bin",
        "$env:LOCALAPPDATA\Programs\elmer\bin"
    )

    foreach ($pattern in $candidates) {
        foreach ($dir in (Get-ChildItem -Path $pattern -Directory -ErrorAction SilentlyContinue)) {
            $grid = Join-Path $dir.FullName "ElmerGrid.exe"
            $solver = Join-Path $dir.FullName "ElmerSolver.exe"
            if ((Test-Path $grid) -and (Test-Path $solver)) {
                return @{ Grid = $grid; Solver = $solver; Home = $null; Modules = $null }
            }
        }
    }

    return $null
}

function Invoke-Python {
    param(
        [hashtable]$PythonCmd,
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Args
    )

    $allArgs = @()
    if ($PythonCmd.PrefixArgs) {
        $allArgs += $PythonCmd.PrefixArgs
    }
    $allArgs += $Args
    & $PythonCmd.Exe @allArgs
}

function Ensure-Python {
    $pythonCmd = Resolve-PythonCommand
    if ($pythonCmd) {
        return $pythonCmd
    }

    Write-Host "Python not found. Attempting install with winget..."
    $winget = Find-Exe "winget"
    if (-not $winget) {
        throw "Python is missing and winget is not available. Install Python 3 manually and rerun."
    }

    $null = & winget install --id Python.Python.3.11 --exact --accept-package-agreements --accept-source-agreements
    Refresh-PathFromSystem
    $pythonCmd = Resolve-PythonCommand
    if (-not $pythonCmd) {
        throw "Python installation did not complete correctly. Open a new terminal and rerun. If it still fails, disable the Microsoft Store python app-execution alias and install Python 3.11+ manually."
    }
    return $pythonCmd
}

function Ensure-Elmer {
    $grid = Find-Exe "ElmerGrid"
    $solver = Find-Exe "ElmerSolver"

    if ($grid -and $solver) {
        return @{ Grid = $grid; Solver = $solver; Home = $null; Modules = $null }
    }

    $resolved = Resolve-ElmerFromCommonPaths
    if ($resolved) {
        return $resolved
    }

    Write-Host "Elmer not found in PATH. Attempting install with winget..."
    $winget = Find-Exe "winget"
    if (-not $winget) {
        throw "Elmer is missing and winget is not available. Install Elmer manually and rerun."
    }

    $installed = $false
    $packageIds = @("CSC.Elmer", "ElmerFEM.Elmer")
    foreach ($pkg in $packageIds) {
        try {
            $null = & winget install --id $pkg --exact --accept-package-agreements --accept-source-agreements
            $installed = $true
            break
        }
        catch {
            Write-Host "winget package $pkg not available or install failed, trying next option..."
        }
    }

    if (-not $installed) {
        throw "Unable to install Elmer automatically. Please install Elmer manually and ensure ElmerGrid and ElmerSolver are in PATH."
    }

    Refresh-PathFromSystem
    $grid = Find-Exe "ElmerGrid"
    $solver = Find-Exe "ElmerSolver"
    if ($grid -and $solver) {
        return @{ Grid = $grid; Solver = $solver; Home = $null; Modules = $null }
    }

    $resolved = Resolve-ElmerFromCommonPaths
    if ($resolved) {
        return $resolved
    }

    throw "Elmer install completed but binaries were not found. Open a new terminal session and retry. If still failing, install Elmer manually and add its bin folder (containing ElmerGrid.exe and ElmerSolver.exe) to PATH."
}

if (-not (Test-Path $ElmerDir)) {
    throw "Missing Elmer folder: $ElmerDir"
}

Start-Transcript -Path $LogFile -Append
try {
    Write-Host "============================================================"
    Write-Host "Gairedzi Dam one-click pipeline (Windows)"
    Write-Host "Start time: $(Get-Date)"
    Write-Host "Log file: $LogFile"
    Write-Host "============================================================"

    Write-Section "1/6 Preparing Python"
    $pythonCmd = Ensure-Python

    $VenvDir = Join-Path $RootDir ".venv"
    $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
    if ((Test-Path $VenvDir) -and (-not (Test-Path $VenvPython))) {
        Remove-Item -Recurse -Force $VenvDir
    }
    if (-not (Test-Path $VenvDir)) {
        Invoke-Python $pythonCmd -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create virtual environment at $VenvDir"
        }
    }

    if (-not (Test-Path $VenvPython)) {
        throw "Virtual environment python not found at $VenvPython"
    }

    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r (Join-Path $RootDir "client_requirements.txt")

    Write-Section "2/6 Detecting Elmer"
    $elmer = Ensure-Elmer
    Write-Host "Using ElmerGrid: $($elmer.Grid)"
    Write-Host "Using ElmerSolver: $($elmer.Solver)"

    Write-Section "3/6 Rebuilding geometry and mesh from Data"
    & $VenvPython (Join-Path $ElmerDir "build_curved_dam_geometry.py")

    Write-Section "4/6 Running ElmerGrid"
    $MeshDir = Join-Path $ElmerDir "mesh"
    $ResultsDir = Join-Path $ElmerDir "results"
    if (Test-Path $MeshDir) { Remove-Item -Recurse -Force $MeshDir }
    if (Test-Path $ResultsDir) { Remove-Item -Recurse -Force $ResultsDir }
    New-Item -ItemType Directory -Force -Path $MeshDir | Out-Null
    New-Item -ItemType Directory -Force -Path $ResultsDir | Out-Null

    Push-Location $ElmerDir
    try {
        & $elmer.Grid 14 2 "curved_dam_mesh.msh" -autoclean -out "mesh"
    }
    finally {
        Pop-Location
    }

    Write-Section "5/6 Running ElmerSolver"
    Push-Location $ElmerDir
    try {
        & $elmer.Solver "dam_model.sif"
    }
    finally {
        Pop-Location
    }

    Write-Section "6/6 Running stress post-processing"
    & $VenvPython (Join-Path $ElmerDir "analyze_stress.py")

    $Report = Join-Path $ElmerDir "results\client_stress_report.png"
    $Summary = Join-Path $ElmerDir "results\stress_summary.json"

    Write-Host ""
    Write-Host "Pipeline complete."
    Write-Host "Summary file: $Summary"
    Write-Host "Report image: $Report"
    Write-Host "Log file: $LogFile"

    if (Test-Path $Report) {
        Start-Process $Report
    }
}
finally {
    Stop-Transcript | Out-Null
}
