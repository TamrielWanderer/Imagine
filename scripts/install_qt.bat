@echo off
rem Installs Qt 5.15.2 for 64-bit MSVC, including the WebEngine module, without
rem a Qt account, using aqtinstall (needs Python 3).
rem Usage: install_qt.bat [target folder]   (default C:\Qt)
setlocal
set QT_ROOT=%~1
if "%QT_ROOT%"=="" set QT_ROOT=C:\Qt
set LOG=%~dp0install_qt.log
echo === install Qt into %QT_ROOT% %DATE% %TIME% > "%LOG%"
cd /d "%~dp0"
py -3 -m pip install --user --disable-pip-version-check aqtinstall >> "%LOG%" 2>&1
py -3 -m aqt install-qt windows desktop 5.15.2 win64_msvc2019_64 -O "%QT_ROOT%" -m qtwebengine >> "%LOG%" 2>&1
if exist "%QT_ROOT%\5.15.2\msvc2019_64\lib\cmake\Qt5WebEngine\Qt5WebEngineConfig.cmake" (
  echo QT OK: %QT_ROOT%\5.15.2\msvc2019_64 >> "%LOG%"
  echo Qt installed in %QT_ROOT%\5.15.2\msvc2019_64
) else (
  echo QT INSTALL FAILED, see %LOG% >> "%LOG%"
  echo Qt install failed, see %LOG%
)
