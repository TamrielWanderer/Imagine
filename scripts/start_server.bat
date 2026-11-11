@echo off
rem Double-click wrapper for start_server.ps1 (arguments are passed through).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_server.ps1" %*
pause
