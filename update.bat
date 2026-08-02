@echo off
setlocal

set ROOT_DIR=%~dp0
cd /d "%ROOT_DIR%"

echo Updating Gairedzi-Dam from GitHub...
echo.

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo This folder is not a git repository.
  echo Please run this file from the root of a cloned repository.
  echo.
  pause
  exit /b 1
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
