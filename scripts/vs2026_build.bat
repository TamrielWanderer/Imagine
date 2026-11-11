@echo off
rem Configures and builds Imagine with Visual Studio 2026 (64-bit, Release).
rem
rem Settings (set them before running to override the defaults):
rem   QT_DIR       Qt 5 MSVC folder        default C:/Qt/5.15.2/msvc2019_64
rem   OPENSSL_DIR  OpenSSL for Windows     default C:/Program Files/OpenSSL-Win64
rem   BUILD_DIR    build folder            default <repo>\build64
rem Use forward slashes in QT_DIR and OPENSSL_DIR.
rem
rem Logs: configure.log, build.log and build_errors.log in the build folder.
rem Do not name a variable RC before running this: Visual Studio treats RC as
rem the resource compiler.
setlocal
set RC=
set SRC=%~dp0..
for %%I in ("%SRC%") do set SRC=%%~fI
if "%QT_DIR%"=="" set QT_DIR=C:/Qt/5.15.2/msvc2019_64
if "%OPENSSL_DIR%"=="" set OPENSSL_DIR=C:/Program Files/OpenSSL-Win64
if "%BUILD_DIR%"=="" set BUILD_DIR=%SRC%\build64

rem Use the CMake bundled with Visual Studio 2026 (4.x); older CMake on PATH
rem does not know the Visual Studio 18 2026 generator.
set VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe
set CMAKE=cmake
for /f "usebackq delims=" %%I in (`"%VSWHERE%" -latest -prerelease -property installationPath`) do (
  if exist "%%I\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" set "CMAKE=%%I\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
)

mkdir "%BUILD_DIR%" > nul 2> nul
echo === configure %DATE% %TIME% > "%BUILD_DIR%\configure.log"
"%CMAKE%" -S "%SRC%" -B "%BUILD_DIR%" -G "Visual Studio 18 2026" -A x64 ^
  -DCMAKE_PREFIX_PATH="%QT_DIR%" ^
  -DUSE_SYSTEM_OPENSSL=ON -DOPENSSL_ROOT_DIR="%OPENSSL_DIR%" ^
  -DWINDOWS_SERVICE=OFF -DNO_WARNINGS=ON -DGENERATE_DOCUMENTATION=OFF ^
  >> "%BUILD_DIR%\configure.log" 2>&1
set CFG_EXIT=%ERRORLEVEL%
echo CONFIGURE_EXIT=%CFG_EXIT% >> "%BUILD_DIR%\configure.log"
if not "%CFG_EXIT%"=="0" (
  echo Configure failed, see %BUILD_DIR%\configure.log
  exit /b 1
)

echo === build %DATE% %TIME% > "%BUILD_DIR%\build.log"
"%CMAKE%" --build "%BUILD_DIR%" --config Release -- /m /v:minimal /nologo "/flp1:errorsonly;logfile=%BUILD_DIR%\build_errors.log" >> "%BUILD_DIR%\build.log" 2>&1
set BUILD_EXIT=%ERRORLEVEL%
echo BUILD_EXIT=%BUILD_EXIT% >> "%BUILD_DIR%\build.log"
if "%BUILD_EXIT%"=="0" (
  echo Build succeeded: %BUILD_DIR%\bin\Release
) else (
  echo Build failed, see %BUILD_DIR%\build_errors.log
)
exit /b %BUILD_EXIT%
