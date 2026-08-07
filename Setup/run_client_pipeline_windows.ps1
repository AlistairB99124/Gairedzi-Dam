param(
    [ValidateSet("setup", "run")]
    [string]$Mode = "run"
)

$ErrorActionPreference = "Stop"

$SetupDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $SetupDir
$ElmerDir = Join-Path $RootDir "Elmer"
$LogDir = Join-Path $RootDir "results\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$SetupStateDir = Join-Path $RootDir ".deps"
$SetupStatePath = Join-Path $SetupStateDir "setup_state.json"
$SetupFlagPath = Join-Path $SetupStateDir "setup_complete.flag"

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path $LogDir ("run_windows_" + $Timestamp + ".log")

function Write-Section([string]$Message) {
    Write-Host ""
    Write-Host "==== $Message ===="
}

function Save-SetupState {
    param(
        [string]$VenvPython,
        [hashtable]$ElmerInfo
    )

    New-Item -ItemType Directory -Force -Path $SetupStateDir | Out-Null
    $state = [ordered]@{
        mode = "setup"
        timestamp = (Get-Date).ToString("o")
        rootDir = $RootDir
        venvPython = $VenvPython
        elmerGrid = $ElmerInfo.Grid
        elmerSolver = $ElmerInfo.Solver
    }
    $state | ConvertTo-Json -Depth 4 | Set-Content -Path $SetupStatePath -Encoding UTF8
    Set-Content -Path $SetupFlagPath -Value "ok" -Encoding ASCII
}

function Invoke-CommandChecked {
    param(
        [string]$Exe,
        [string[]]$Args,
        [string]$StepName
    )

    & $Exe @Args
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "$StepName failed with exit code $exitCode"
    }
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
        "$RootDir\.deps\elmer\*\bin",
        "$RootDir\.deps\elmer\bin",
        "$env:SystemDrive\CSC\elmerfem\bin",
        "$env:SystemDrive\Elmer\bin",
        "$env:ProgramFiles\Elmer*\bin",
        "$env:ProgramFiles\Elmer\bin",
        "$env:ProgramFiles\elmer\bin",
        "$env:ProgramFiles(x86)\Elmer*\bin",
        "$env:ProgramFiles(x86)\Elmer\bin",
        "$env:ProgramFiles(x86)\elmer\bin",
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

function Resolve-ElmerInRoot {
    param([string]$Root)

    if (-not (Test-Path $Root)) {
        return $null
    }

    $gridHit = Get-ChildItem -Path $Root -Filter "ElmerGrid.exe" -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $gridHit) {
        return $null
    }

    $binDir = Split-Path -Parent $gridHit.FullName
    $solver = Join-Path $binDir "ElmerSolver.exe"
    if (Test-Path $solver) {
        return @{ Grid = $gridHit.FullName; Solver = $solver; Home = $null; Modules = $null }
    }

    return $null
}

function Resolve-ElmerByRecursiveSearch {
    $roots = @(
        "$env:SystemDrive\CSC",
        "$env:SystemDrive\Elmer",
        "$env:ProgramFiles",
        "$env:ProgramFiles(x86)",
        "$env:LOCALAPPDATA\Programs"
    )

    foreach ($root in $roots) {
        $resolved = Resolve-ElmerInRoot -Root $root
        if ($resolved) {
            return $resolved
        }
    }

    return $null
}

function Install-ElmerFromOfficialZip {
    $depsDir = Join-Path $RootDir ".deps\elmer"
    $resolved = Resolve-ElmerInRoot -Root $depsDir
    if ($resolved) {
        return $resolved
    }

    New-Item -ItemType Directory -Force -Path $depsDir | Out-Null

    $zipUrl = "https://www.nic.funet.fi/pub/sci/physics/elmer/bin/windows/ElmerFEM-nogui-nompi-Windows-AMD64.zip"
    $zipPath = Join-Path $env:TEMP "ElmerFEM-nogui-nompi-Windows-AMD64.zip"

    Write-Host "Downloading Elmer fallback package from official mirror..."
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing

    if (-not (Test-Path $zipPath)) {
        throw "Elmer fallback download failed: $zipPath was not created."
    }

    Write-Host "Extracting Elmer fallback package..."
    Remove-Item -Recurse -Force $depsDir
    New-Item -ItemType Directory -Force -Path $depsDir | Out-Null
    Expand-Archive -Path $zipPath -DestinationPath $depsDir -Force

    $resolved = Resolve-ElmerInRoot -Root $depsDir
    if ($resolved) {
        return $resolved
    }

    throw "Downloaded Elmer package but did not find ElmerGrid.exe and ElmerSolver.exe after extraction."
}

function Try-WingetInstallPackage {
    param([string]$PackageId)

    Write-Host "Trying winget package: $PackageId"
    $null = & winget install --id $PackageId --exact --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -eq 0) {
        return $true
    }

    Write-Host "winget install for $PackageId returned exit code $LASTEXITCODE"
    return $false
}

function Get-ElmerWingetPackageIds {
    $ids = New-Object System.Collections.Generic.List[string]
    $ids.Add("CSC.Elmer")
    $ids.Add("ElmerFEM.Elmer")
    $ids.Add("Elmer.Elmer")

    $null = & winget source update

    $searchOutput = & winget search --query Elmer --source winget --accept-source-agreements 2>&1
    $lines = ($searchOutput | Out-String).Split([Environment]::NewLine)
    foreach ($line in $lines) {
        if ($line -match "\s([A-Za-z0-9][A-Za-z0-9\._\-]+)\s+[0-9A-Za-z\.-]+\s+winget\s*$") {
            $candidate = $Matches[1]
            if ($candidate -match "(?i)elmer") {
                if (-not $ids.Contains($candidate)) {
                    $ids.Add($candidate)
                }
            }
        }
    }

    return $ids.ToArray()
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
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "Python command failed with exit code $exitCode"
    }
}

function Ensure-Python {
    param([bool]$InstallIfMissing = $true)

    $pythonCmd = Resolve-PythonCommand
    if ($pythonCmd) {
        return $pythonCmd
    }

    if (-not $InstallIfMissing) {
        throw "Python is not available. Run Setup\\setup.bat first."
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
    param([bool]$InstallIfMissing = $true)

    $grid = Find-Exe "ElmerGrid"
    $solver = Find-Exe "ElmerSolver"

    if ($grid -and $solver) {
        return @{ Grid = $grid; Solver = $solver; Home = $null; Modules = $null }
    }

    $resolved = Resolve-ElmerFromCommonPaths
    if ($resolved) {
        return $resolved
    }

    $resolved = Resolve-ElmerByRecursiveSearch
    if ($resolved) {
        return $resolved
    }

    if (-not $InstallIfMissing) {
        throw "Elmer is not available. Run Setup\\setup.bat first."
    }

    Write-Host "Elmer not found in PATH. Attempting install with winget..."
    $winget = Find-Exe "winget"
    if (-not $winget) {
        throw "Elmer is missing and winget is not available. Install Elmer manually and rerun."
    }

    $packageIds = Get-ElmerWingetPackageIds
    if (-not $packageIds -or $packageIds.Count -eq 0) {
        throw "No Elmer package candidates were found via winget search."
    }

    $installed = $false
    foreach ($pkg in $packageIds) {
        try {
            if (Try-WingetInstallPackage -PackageId $pkg) {
                $installed = $true
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

            $resolved = Resolve-ElmerByRecursiveSearch
            if ($resolved) {
                return $resolved
            }
        }
        catch {
            Write-Host "winget package $pkg not available or install failed, trying next option..."
        }
    }

    if (-not $installed) {
        Write-Host "winget could not install Elmer. Trying official Elmer binary package fallback..."
        return Install-ElmerFromOfficialZip
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

    $resolved = Resolve-ElmerByRecursiveSearch
    if ($resolved) {
        return $resolved
    }

    Write-Host "winget install completed but binaries were not found. Trying official Elmer binary package fallback..."
    return Install-ElmerFromOfficialZip
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

    $installIfMissing = $Mode -eq "setup"

    Write-Section "1/6 Preparing Python"
    $pythonCmd = Ensure-Python -InstallIfMissing:$installIfMissing

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

    Invoke-CommandChecked -Exe $VenvPython -Args @("-m", "pip", "install", "--upgrade", "pip") -StepName "pip upgrade"
    Invoke-CommandChecked -Exe $VenvPython -Args @("-m", "pip", "install", "-r", (Join-Path $RootDir "client_requirements.txt")) -StepName "dependency install"

    Write-Section "2/6 Detecting Elmer"
    $elmer = Ensure-Elmer -InstallIfMissing:$installIfMissing
    Write-Host "Using ElmerGrid: $($elmer.Grid)"
    Write-Host "Using ElmerSolver: $($elmer.Solver)"

    if ($Mode -eq "setup") {
        Save-SetupState -VenvPython $VenvPython -ElmerInfo $elmer
        Write-Host ""
        Write-Host "Setup complete."
        Write-Host "Setup state file: $SetupStatePath"
        Write-Host "Run flag file: $SetupFlagPath"
        return
    }

    Write-Section "3/6 Rebuilding geometry and mesh from Data"
    Invoke-CommandChecked -Exe $VenvPython -Args @((Join-Path $ElmerDir "build_curved_dam_geometry.py")) -StepName "geometry build"

    Write-Section "4/6 Running ElmerGrid"
    $MeshDir = Join-Path $ElmerDir "mesh"
    $ResultsDir = Join-Path $ElmerDir "results"
    if (Test-Path $MeshDir) { Remove-Item -Recurse -Force $MeshDir }
    if (Test-Path $ResultsDir) { Remove-Item -Recurse -Force $ResultsDir }
    New-Item -ItemType Directory -Force -Path $MeshDir | Out-Null
    New-Item -ItemType Directory -Force -Path $ResultsDir | Out-Null

    Push-Location $ElmerDir
    try {
        Invoke-CommandChecked -Exe $elmer.Grid -Args @("14", "2", "curved_dam_mesh.msh", "-autoclean", "-out", "mesh") -StepName "ElmerGrid"
    }
    finally {
        Pop-Location
    }

    Write-Section "5/6 Running ElmerSolver"
    Push-Location $ElmerDir
    try {
        Invoke-CommandChecked -Exe $elmer.Solver -Args @("dam_model.sif") -StepName "ElmerSolver"
    }
    finally {
        Pop-Location
    }

    Write-Section "6/6 Running stress post-processing"
    Invoke-CommandChecked -Exe $VenvPython -Args @((Join-Path $ElmerDir "analyze_stress.py")) -StepName "stress post-processing"

    $Report = Join-Path $ElmerDir "results\client_stress_report.png"
    $Summary = Join-Path $ElmerDir "results\stress_summary.json"

    if (-not (Test-Path $Summary)) {
        throw "Expected summary output missing: $Summary"
    }
    if (-not (Test-Path $Report)) {
        throw "Expected report output missing: $Report"
    }

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
