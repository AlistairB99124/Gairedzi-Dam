@echo off
setlocal

set ROOT_DIR=%~dp0
echo Launching Gairedzi dam pipeline for Windows...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%run_client_pipeline_windows.ps1"
if errorlevel 1 (
  echo.
  echo Pipeline failed. Please check the log in results\logs.
) else (
  echo.
  echo Pipeline finished successfully.
)

echo.
pause
