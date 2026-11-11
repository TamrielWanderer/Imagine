@echo off
rem Lists the build tools found on this PC (Git, CMake, Visual Studio, Qt,
rem OpenSSL, Python). Writes check_tools.log next to this file.
setlocal
set LOG=%~dp0check_tools.log
echo === check %DATE% %TIME% > "%LOG%"

echo --- git >> "%LOG%"
git --version >> "%LOG%" 2>&1

echo --- cmake on PATH (needs 4.2+ for VS 2026) >> "%LOG%"
cmake --version >> "%LOG%" 2>&1

echo --- Visual Studio >> "%LOG%"
set VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe
if exist "%VSWHERE%" (
  "%VSWHERE%" -all -prerelease -format text -property displayName >> "%LOG%" 2>&1
  for /f "usebackq delims=" %%I in (`"%VSWHERE%" -latest -prerelease -property installationPath`) do (
    echo installationPath: %%I >> "%LOG%"
    if exist "%%I\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" (
      echo --- cmake bundled with Visual Studio >> "%LOG%"
      "%%I\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" --version >> "%LOG%" 2>&1
    )
  )
) else (
  echo Visual Studio Installer not found >> "%LOG%"
)

echo --- Qt (needs 5.12-5.15 MSVC build with the WebEngine module) >> "%LOG%"
for /d %%V in ("C:\Qt\5.*" "D:\Qt\5.*") do for /d %%D in ("%%V\msvc*") do (
  echo %%D >> "%LOG%"
  if exist "%%D\lib\cmake\Qt5WebEngine" (echo   WebEngine: yes >> "%LOG%") else (echo   WebEngine: NO >> "%LOG%")
)

echo --- OpenSSL >> "%LOG%"
for /d %%D in ("C:\Program Files\OpenSSL*" "C:\OpenSSL*" "D:\OpenSSL*") do echo %%D >> "%LOG%"

echo --- Python (only needed to install Qt with aqtinstall) >> "%LOG%"
py -3 --version >> "%LOG%" 2>&1

echo === done >> "%LOG%"
echo Results written to %LOG%
