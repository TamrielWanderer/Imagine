@echo off
rem Double-click wrapper for publish_update.ps1 (arguments are passed through).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0publish_update.ps1" %*
pause
