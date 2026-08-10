@echo off
setlocal

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set APP_VERSION=unknown

if exist "%ROOT_DIR%\VERSION" (
  set /p APP_VERSION=<"%ROOT_DIR%\VERSION"
)

cd /d "%ROOT_DIR%"

echo Gairedzi Dam Updater - Version %APP_VERSION%
echo.
echo Updating Gairedzi-Dam from GitHub...
echo.

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo No git repository detected.
  echo Updating from public patch feed...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%\Setup\update_incremental.ps1" -RootDir "%ROOT_DIR%"
  if errorlevel 1 (
    echo.
    echo Update failed.
    echo.
    pause
    exit /b 1
  )

  echo.
  echo Update complete.
  echo.
  pause
  exit /b 0
)

git fetch origin
if errorlevel 1 (
  echo.
  echo Fetch failed. Check your internet connection and Git credentials.
  echo.
  pause
  exit /b 1
)

git pull --ff-only origin main
if errorlevel 1 (
  echo.
  echo Update failed. Local changes may be present, or fast-forward was not possible.
  echo Please commit/stash local work and retry.
  echo.
  pause
  exit /b 1
)

echo.
echo Update complete.
echo.
pause
