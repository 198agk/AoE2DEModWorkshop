@echo off
rem ===========================================================================
rem  Double-click this file to open the mod workshop.
rem
rem  Why a .cmd exists at all: the README says "run tools\run_ui.py with the
rem  absolute python path", but the python on PATH may be the Microsoft Store
rem  stub (it opens the Store instead of running).  Double-clicking is the
rem  shortest path for a newcomer, so this shim does the one thing the README
rem  cannot: find a real interpreter before anything else runs.
rem
rem  IMPORTANT: this file is deliberately ASCII-ONLY.
rem  Measured 2026-10-24: a .cmd whose own text contained Chinese, saved as
rem  UTF-8 and started under "chcp 65001", had cmd.exe split three comment
rem  lines in half and try to EXECUTE the fragments
rem  ("'--' is not recognized as an internal or external command").
rem  The launch itself worked, so the damage was three scary lines of stderr
rem  on a brand-new user's very first run.  All Chinese wording lives in
rem  tools\run_ui.py, where UTF-8 is safe.
rem ===========================================================================
setlocal
cd /d "%~dp0"

set "PY="
set "KNOWN=%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
if exist "%KNOWN%" set "PY=%KNOWN%"
if not defined PY (
  where py >nul 2>nul
  if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
  where python >nul 2>nul
  if not errorlevel 1 set "PY=python"
)

if not defined PY (
  echo.
  echo Python was not found on this machine.
  echo Install Python 3.10 or newer from https://www.python.org/downloads/
  echo Tick "Add python.exe to PATH" during setup, then double-click again.
  echo.
  pause
  exit /b 1
)

rem Keep the console open after a crash: the reason is printed by run_ui.py,
rem and a window that vanishes takes the reason with it.
%PY% -X utf8 -u "tools\run_ui.py" %*
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" echo The workshop stopped with code %RC% - the lines above say why.
pause
endlocal
