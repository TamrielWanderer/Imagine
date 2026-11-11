@echo off
rem Double-click wrapper for apply_translation.ps1 (arguments are passed through).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply_translation.ps1" %*
pause
