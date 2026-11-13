@echo off
rem Opens the keys, extra shortcut bars and macros editor
rem (contrib\tools\key_config_tool.py). Close the game first.
setlocal
set PY=
where pyw >nul 2>nul && set PY=pyw -3
if "%PY%"=="" where pythonw >nul 2>nul && set PY=pythonw
if "%PY%"=="" where py >nul 2>nul && set PY=py -3
if "%PY%"=="" where python >nul 2>nul && set PY=python
if "%PY%"=="" (
  echo Python 3 was not found. Install it from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" in the installer.
  pause
  exit /b 1
)
start "" %PY% "%~dp0..\contrib\tools\key_config_tool.py" %*
