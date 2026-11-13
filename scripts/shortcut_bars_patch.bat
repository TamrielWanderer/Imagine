@echo off
rem Applies (or with --check / --revert, checks or removes) the extra shortcut
rem bars client patch. Uses the client folder start_server.ps1 remembered,
rem or the folder given as the first argument. Close the game first.
setlocal
set CLIENT=%~1
if "%CLIENT%"=="" if exist "%~dp0..\local-server\client_dir.txt" set /p CLIENT=<"%~dp0..\local-server\client_dir.txt"
if "%CLIENT%"=="" (
  echo Usage: shortcut_bars_patch.bat "client folder" [--check^|--revert]
  pause
  exit /b 1
)
set PY=
where py >nul 2>nul && set PY=py -3
if "%PY%"=="" where python >nul 2>nul && set PY=python
if "%PY%"=="" (
  echo Python 3 was not found. Install it from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" in the installer.
  pause
  exit /b 1
)
%PY% "%~dp0..\contrib\client-patches\shortcut_bars_patch.py" "%CLIENT%\ImagineClient.exe" %2
pause
