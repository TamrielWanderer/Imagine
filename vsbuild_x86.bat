@echo off
rem Build files for Visual Studio 2026 (32-bit). Requires CMake 4.2 or newer.
rem Edit the paths below to match your installs.

rem Qt 5 for MSVC 32-bit (any Qt 5.12 - 5.15 MSVC build works).
set QT_DIR=C:\Qt\5.15.2\msvc2019

rem 32-bit OpenSSL install.
set OPENSSL_DIR=C:\Program Files (x86)\OpenSSL-Win32

rem Optional: set to v143 to compile with the VS 2022 toolset installed
rem inside VS 2026 (Visual Studio Installer > "MSVC v143 build tools").
rem Leave empty to use the default VS 2026 compiler.
set TOOLSET=

mkdir build32 > nul 2> nul
cd build32
set SCRIPT_DIR=%~dp0
set CMAKE_PREFIX_PATH=%QT_DIR%
set TOOLSET_ARG=
if not "%TOOLSET%"=="" set TOOLSET_ARG=-T %TOOLSET%
cmake -G"Visual Studio 18 2026" -A "Win32" %TOOLSET_ARG% -DWINDOWS_SERVICE=OFF -DCMAKE_INSTALL_PREFIX="%SCRIPT_DIR%\build32\install" -DCPACK_WIX_ROOT="C:/Program Files (x86)/WiX Toolset v3.11" -DUSE_SYSTEM_OPENSSL=ON -DOPENSSL_ROOT_DIR="%OPENSSL_DIR%" -DBUILD_BINARIES32=ON ..
pause
