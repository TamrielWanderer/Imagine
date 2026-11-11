@echo off
rem Double-click wrapper for set_update_url.ps1 (arguments are passed through).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0set_update_url.ps1" %*
pause
