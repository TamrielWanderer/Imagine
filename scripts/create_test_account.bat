@echo off
rem Double-click wrapper for create_test_account.ps1 (arguments are passed through).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_test_account.ps1" %*
pause
