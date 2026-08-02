param(
    [Parameter(Mandatory = $true)]
    [string]$RootDir
)

$ErrorActionPreference = "Stop"

$zipUrl = "https://github.com/AlistairB99124/Gairedzi-Dam/archive/refs/heads/main.zip"
$normalizedRoot = $RootDir.Trim().Trim('"').TrimEnd([char[]]@([char]'\', [char]'/'))
if ([string]::IsNullOrWhiteSpace($normalizedRoot)) {
    throw "RootDir is empty or invalid."
}

$fullRoot = [System.IO.Path]::GetFullPath($normalizedRoot)
if (-not (Test-Path -LiteralPath $fullRoot -PathType Container)) {
    throw "Root directory not found: $fullRoot"
}

$root = (Resolve-Path -LiteralPath $fullRoot).Path

$tmpRoot = Join-Path $env:TEMP ("gairedzi_update_" + [guid]::NewGuid().ToString("N"))
$zipPath = Join-Path $tmpRoot "repo.zip"
$extractDir = Join-Path $tmpRoot "extract"
$backupData = Join-Path $tmpRoot "data_backup"

New-Item -ItemType Directory -Force -Path $tmpRoot | Out-Null
New-Item -ItemType Directory -Force -Path $extractDir | Out-Null

try {
    Write-Host "Downloading latest project ZIP..."
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing

    Write-Host "Extracting ZIP..."
    Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force

    $extractedRoot = Get-ChildItem -Path $extractDir -Directory | Select-Object -First 1
    if (-not $extractedRoot) {
        throw "Could not find extracted repository folder."
    }

    $dataDir = Join-Path $root "Data"
    if (Test-Path $dataDir) {
        Write-Host "Backing up local Data folder..."
        robocopy $dataDir $backupData /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
    }

    Write-Host "Applying update files..."
    robocopy $extractedRoot.FullName $root /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP /XD ".git" | Out-Null

    if (Test-Path $backupData) {
        Write-Host "Restoring local Data folder..."
        robocopy $backupData $dataDir /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
    }

    Write-Host "ZIP update succeeded."
}
finally {
    if (Test-Path $tmpRoot) {
        Remove-Item -Recurse -Force $tmpRoot
    }
}
