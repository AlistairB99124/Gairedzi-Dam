param(
    [Parameter(Mandatory = $true)]
    [string]$RootDir
)

$ErrorActionPreference = "Stop"

$Owner = "AlistairB99124"
$Repo = "Gairedzi-Dam"
$Branch = "main"
$ApiBase = "https://api.github.com/repos/$Owner/$Repo"
$RawBase = "https://raw.githubusercontent.com/$Owner/$Repo/$Branch"
$StateDirName = ".deps"
$StateFileName = "update_state.json"

$requestHeaders = @{ "User-Agent" = "Gairedzi-Updater" }

function Normalize-Root([string]$Value) {
    $normalized = $Value.Trim().Trim('"').TrimEnd([char[]]@([char]'\', [char]'/'))
    if ([string]::IsNullOrWhiteSpace($normalized)) {
        throw "RootDir is empty or invalid."
    }

    $fullRoot = [System.IO.Path]::GetFullPath($normalized)
    if (-not (Test-Path -LiteralPath $fullRoot -PathType Container)) {
        throw "Root directory not found: $fullRoot"
    }

    return (Resolve-Path -LiteralPath $fullRoot).Path
}

function Get-LatestCommitSha {
    $url = "$ApiBase/commits/$Branch"
    $response = Invoke-RestMethod -Uri $url -Headers $requestHeaders -Method Get
    if (-not $response.sha) {
        throw "Could not resolve latest commit SHA from GitHub."
    }
    return [string]$response.sha
}

function Get-StatePath([string]$Root) {
    $stateDir = Join-Path $Root $StateDirName
    New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
    return Join-Path $stateDir $StateFileName
}

function Read-LocalState([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }

    try {
        $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
        if ([string]::IsNullOrWhiteSpace($raw)) {
            return $null
        }
        return $raw | ConvertFrom-Json
    }
    catch {
        Write-Host "State file is unreadable; proceeding without incremental base." -ForegroundColor Yellow
        return $null
    }
}

function Write-LocalState {
    param(
        [string]$Path,
        [string]$Sha
    )

    $state = [ordered]@{
        repo = "$Owner/$Repo"
        branch = $Branch
        lastUpdatedCommit = $Sha
        updatedAtUtc = (Get-Date).ToUniversalTime().ToString("o")
        updater = "incremental"
    }

    $state | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Ensure-ParentDirectory([string]$Path) {
    $parent = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
}

function Download-FileFromRaw {
    param(
        [string]$Path,
        [string]$Destination
    )

    $escapedSegments = ($Path -split '/') | ForEach-Object { [Uri]::EscapeDataString($_) }
    $escapedPath = $escapedSegments -join '/'
    $url = "$RawBase/$escapedPath"

    Ensure-ParentDirectory -Path $Destination
    Invoke-WebRequest -Uri $url -Headers $requestHeaders -OutFile $Destination -UseBasicParsing
}

function Apply-IncrementalUpdate {
    param(
        [string]$Root,
        [string]$BaseSha,
        [string]$HeadSha
    )

    Write-Host "Checking changed files from $BaseSha to $HeadSha..."

    $compareUrl = "$ApiBase/compare/$BaseSha...$HeadSha"
    $compare = Invoke-RestMethod -Uri $compareUrl -Headers $requestHeaders -Method Get

    if (-not $compare.files) {
        throw "Compare API did not return file details."
    }

    if ($compare.files.Count -eq 0) {
        Write-Host "No file changes detected."
        return
    }

    $downloaded = 0
    $deleted = 0
    $skipped = 0

    foreach ($file in $compare.files) {
        $status = [string]$file.status
        $path = [string]$file.filename

        if ([string]::IsNullOrWhiteSpace($path)) {
            continue
        }

        # Preserve user-managed data and runtime outputs.
        if ($path -like "Data/*" -or $path -like "results/*" -or $path -like "Elmer/results/*") {
            $skipped++
            continue
        }

        $target = Join-Path $Root ($path -replace '/', '\\')

        if ($status -eq "removed") {
            if (Test-Path -LiteralPath $target) {
                Remove-Item -LiteralPath $target -Force
                $deleted++
            }
            continue
        }

        if ($status -eq "renamed") {
            $previous = [string]$file.previous_filename
            if (-not [string]::IsNullOrWhiteSpace($previous)) {
                $oldTarget = Join-Path $Root ($previous -replace '/', '\\')
                if (Test-Path -LiteralPath $oldTarget) {
                    Remove-Item -LiteralPath $oldTarget -Force
                }
            }
        }

        Download-FileFromRaw -Path $path -Destination $target
        $downloaded++
    }

    Write-Host "Incremental update applied. Downloaded: $downloaded, Deleted: $deleted, Skipped: $skipped"
}

$root = Normalize-Root -Value $RootDir
$statePath = Get-StatePath -Root $root
$state = Read-LocalState -Path $statePath

Write-Host "Resolving latest version from GitHub..."
$latestSha = Get-LatestCommitSha

if (-not $state -or -not $state.lastUpdatedCommit) {
    Write-Host "No incremental base found. Running one-time baseline ZIP update..."
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "Setup\update_from_zip.ps1") -RootDir $root
    if ($LASTEXITCODE -ne 0) {
        throw "Baseline ZIP update failed."
    }

    Write-LocalState -Path $statePath -Sha $latestSha
    Write-Host "Baseline complete. Future updates will use incremental patch mode."
    exit 0
}

$baseSha = [string]$state.lastUpdatedCommit
if ($baseSha -eq $latestSha) {
    Write-Host "Already up to date."
    exit 0
}

try {
    Apply-IncrementalUpdate -Root $root -BaseSha $baseSha -HeadSha $latestSha
    Write-LocalState -Path $statePath -Sha $latestSha
    Write-Host "Incremental update succeeded."
}
catch {
    Write-Host "Incremental update failed: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "Falling back to full ZIP update..."

    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "Setup\update_from_zip.ps1") -RootDir $root
    if ($LASTEXITCODE -ne 0) {
        throw "Fallback ZIP update failed."
    }

    Write-LocalState -Path $statePath -Sha $latestSha
    Write-Host "Fallback ZIP update succeeded."
}
