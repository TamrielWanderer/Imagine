@echo off
rem Double-click wrapper for stack_sizes.ps1 (arguments are passed through).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stack_sizes.ps1" %*
pause
