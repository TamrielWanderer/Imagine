@echo off
rem Double-click wrapper for stephens_clock_data.ps1 (arguments are passed through).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stephens_clock_data.ps1" %*
pause
