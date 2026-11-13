@echo off
rem Double-click wrapper for build_key_config_tool.ps1 (arguments are passed through).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_key_config_tool.ps1" %*
pause
