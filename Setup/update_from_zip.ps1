param(
    [Parameter(Mandatory = $true)]
    [string]$RootDir,

    [string]$GithubToken = $env:GAIREDZI_GITHUB_TOKEN
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($GithubToken) -and -not [string]::IsNullOrWhiteSpace($env:GITHUB_TOKEN)) {
    $GithubToken = $env:GITHUB_TOKEN
}

$zipUrls = @(
    "https://api.github.com/repos/AlistairB99124/Gairedzi-Dam/zipball/main",
    "https://github.com/AlistairB99124/Gairedzi-Dam/archive/refs/heads/main.zip",
    "https://codeload.github.com/AlistairB99124/Gairedzi-Dam/zip/refs/heads/main",
    "https://api.github.com/repos/AlistairB99124/Gairedzi/zipball/main",
    "https://github.com/AlistairB99124/Gairedzi/archive/refs/heads/main.zip",
    "https://codeload.github.com/AlistairB99124/Gairedzi/zip/refs/heads/main"
)

$requestHeaders = @{ "User-Agent" = "Gairedzi-Updater" }
if (-not [string]::IsNullOrWhiteSpace($GithubToken)) {
    $requestHeaders["Authorization"] = "Bearer $GithubToken"
}
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
    $downloaded = $false
    $statusCodes = @()
    foreach ($url in $zipUrls) {
        try {
            Write-Host "Trying: $url"
            Invoke-WebRequest -Uri $url -OutFile $zipPath -Headers $requestHeaders -UseBasicParsing
            $downloaded = $true
            break
        }
        catch {
            $code = $null
            if ($_.Exception -and $_.Exception.Response -and $_.Exception.Response.StatusCode) {
                $code = [int]$_.Exception.Response.StatusCode
                $statusCodes += $code
            }

            Write-Host "Download failed from this URL, trying next..."
        }
    }

    if (-not $downloaded) {
        if (($statusCodes -contains 401) -or ($statusCodes -contains 403) -or ($statusCodes -contains 404)) {
            throw @"
Could not download update ZIP.
If this repository is private, set a GitHub token first and retry.

PowerShell (current session):
  `$env:GAIREDZI_GITHUB_TOKEN = "<your_token>"

Then run update.bat again.
"@
        }

        throw "Could not download update ZIP from any known URL. Check repository visibility, branch name, or network access."
    }

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
