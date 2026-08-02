@echo off
setlocal

set ROOT_DIR=%~dp0
set SETUP_FLAG=%ROOT_DIR%\.deps\setup_complete.flag
set VENV_PY=%ROOT_DIR%\.venv\Scripts\python.exe

if not exist "%SETUP_FLAG%" goto do_setup
if not exist "%VENV_PY%" goto do_setup
goto do_run

:do_setup
echo Prerequisites missing. Running setup first...
call "%ROOT_DIR%\Setup\setup.bat"
if errorlevel 1 (
  echo.
  echo Setup did not complete successfully.
  exit /b 1
)

:do_run
echo Running Gairedzi analysis...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%\Setup\run_client_pipeline_windows.ps1" -Mode run
if errorlevel 1 (
  echo.
  echo Analysis failed. Check results\logs for details.
) else (
  echo.
  echo Analysis finished successfully.
)

echo.
pause
