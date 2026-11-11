@echo off
rem Double-click wrapper for start_client.ps1 (arguments are passed through).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_client.ps1" %*
pause
