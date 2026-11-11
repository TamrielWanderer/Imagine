@echo off
rem Double-click wrapper for test_servers.ps1 (arguments are passed through).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0test_servers.ps1" %*
pause
