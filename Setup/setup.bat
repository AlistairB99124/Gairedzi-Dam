@echo off
setlocal

set ROOT_DIR=%~dp0..
echo Running Gairedzi prerequisite setup...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%\Setup\run_client_pipeline_windows.ps1" -Mode setup
if errorlevel 1 (
  echo.
  echo Setup failed. Check results\logs for details.
) else (
  echo.
  echo Setup complete.
)

echo.
pause
