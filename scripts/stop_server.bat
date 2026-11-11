@echo off
rem Double-click wrapper for stop_server.ps1 (arguments are passed through).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_server.ps1" %*
pause
