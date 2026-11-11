@echo off
rem Double-click wrapper for serve_update.ps1 (arguments are passed through).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0serve_update.ps1" %*
pause
