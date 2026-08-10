@echo off
setlocal

set ROOT_DIR=%~dp0
set SETUP_FLAG=%ROOT_DIR%\.deps\setup_complete.flag
set VENV_PY=%ROOT_DIR%\.venv\Scripts\python.exe
set APP_VERSION=unknown
set RESULT_VTU=
set PARAVIEW_EXE=

if exist "%ROOT_DIR%\VERSION" (
  set /p APP_VERSION=<"%ROOT_DIR%\VERSION"
)

echo Gairedzi Dam Analysis - Version %APP_VERSION%
echo.

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

  rem Find the newest VTU output in Elmer\results
  if exist "%ROOT_DIR%\Elmer\results\dam_results_t0001.vtu" (
    set "RESULT_VTU=%ROOT_DIR%\Elmer\results\dam_results_t0001.vtu"
  ) else (
    for /f "delims=" %%F in ('dir /b /a-d /o-d "%ROOT_DIR%\Elmer\results\*.vtu" 2^>nul') do (
      if not defined RESULT_VTU set "RESULT_VTU=%ROOT_DIR%\Elmer\results\%%F"
    )
  )

  if defined RESULT_VTU (
    rem Prefer concrete install paths, then PATH lookup.
    if exist "C:\Program Files\ParaView 6.2.0\bin\paraview.exe" (
      set "PARAVIEW_EXE=C:\Program Files\ParaView 6.2.0\bin\paraview.exe"
    )

    if not defined PARAVIEW_EXE (
      for /f "delims=" %%P in ('dir /b /s "C:\Program Files\ParaView*\bin\paraview.exe" 2^>nul') do (
        if not defined PARAVIEW_EXE set "PARAVIEW_EXE=%%P"
      )
    )

    if not defined PARAVIEW_EXE (
      for /f "delims=" %%P in ('dir /b /s "C:\Program Files (x86)\ParaView*\bin\paraview.exe" 2^>nul') do (
        if not defined PARAVIEW_EXE set "PARAVIEW_EXE=%%P"
      )
    )

    if not defined PARAVIEW_EXE (
      for /f "delims=" %%P in ('where paraview 2^>nul') do (
        if not defined PARAVIEW_EXE set "PARAVIEW_EXE=%%P"
      )
    )

    if defined PARAVIEW_EXE (
      echo.
      echo Opening result in ParaView...
      start "" "%PARAVIEW_EXE%" "%RESULT_VTU%"
    ) else (
      echo.
      echo ParaView was not found. Install ParaView to open:
      echo %RESULT_VTU%
    )
  ) else (
    echo.
    echo No VTU result file was found under Elmer\results.
  )
)

echo.
pause
