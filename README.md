# COMP\_hack #

[![AGPL License](http://img.shields.io/badge/license-AGPL-brightgreen.svg)](https://opensource.org/licenses/AGPL-3.0)
[![Coverity Scan Build Status](https://scan.coverity.com/projects/9671/badge.svg)](https://scan.coverity.com/projects/comphack-comp_hack)

## Shin Megami Tensei IMAGINE (真・女神転生IMAGINE) Open Source Conservation Effort ##

The aim of the project is to revive an MMO that has been shutdown (SMT: IMAGINE). It's a complete re-implementation of the server from scratch and fully open source.

### Building on Linux ###

You only need to build the project if you are on a Linux system that doesn't have a package (there is a [PPA](https://launchpad.net/~compomega/+archive/ubuntu/comphack) for Ubuntu-based systems) or you want to contribute. That being said, if you wish to contribute, Linux is the preferred build and run environment for the server. Of course you can build and develop with Visual Studio 2015 on Windows if that's your thing.

#### Dependencies ####

First thing you want to do is download some dependencies. Make sure you have GCC 5+ or Clang with C++14 support. Here is a command for Debian/Ubuntu based distros to pull in packages you may need:
```
sudo apt-get install build-essential cmake docbook-xsl doxygen texlive-font-utils xmlto libqt5webkit5-dev
```

#### Building ####

> All dependencies are bundled in this repository (see _deps/SOURCES.md_), so no submodules or downloads are needed.

That should be all you need. Just build the project now:
```
mkdir build
cd build
cmake -DNO_WARNINGS=ON ..
make
```

### Building on Windows ###

#### Required Dependencies ####

* [Visual Studio 2026](https://visualstudio.microsoft.com/) with the "Desktop development with C++" workload
* [CMake 4.2+](https://cmake.org) (needed for the Visual Studio 2026 generator; the copy bundled with Visual Studio 2026 works)
* [Qt 5.12 - 5.15](https://www.qt.io), MSVC build matching your target (64-bit or 32-bit), including the Qt WebEngine module (used by the updater). Without a Qt account you can install it with [aqtinstall](https://github.com/miurahr/aqtinstall): `aqt install-qt windows desktop 5.15.2 win64_msvc2019_64 -m qtwebengine`
* [OpenSSL](https://www.openssl.org) for Windows (the build scripts use the system OpenSSL)

#### Optional Dependencies ####

* [Doxygen](http://www.doxygen.nl)
* [WiX Toolset](http://wixtoolset.org) (only to build the _.msi_ installer)

#### Building ####

> All dependencies are bundled in this repository (see _deps/SOURCES.md_), so no submodules or downloads are needed.

You can build from the Visual Studio IDE or entirely from the command line. Each step below shows the script in _scripts/_ that does it. Every _.bat_ file can also be double-clicked, and arguments are passed through.

1. **Check your tools.** `scripts\check_tools.bat` lists the Git, CMake, Visual Studio, Qt (and whether it has WebEngine), OpenSSL and Python versions it finds, and writes them to _scripts\check_tools.log_.

2. **Install Qt if you don't have it.** `scripts\install_qt.bat [folder]` installs Qt 5.15.2 for 64-bit MSVC with the WebEngine module, using aqtinstall. It needs Python 3 but no Qt account. The default folder is _C:\Qt_, and the log goes to _scripts\install_qt.log_.

3. **Build.**
   * **In the IDE:** edit the paths at the top of _vsbuild_x64.bat_ (or _vsbuild_x86.bat_ for 32-bit) to point to your Qt and OpenSSL installs. Run it and you should see a _build64_ (or _build32_) folder containing a comp_hack.sln solution file. Open the solution in Visual Studio 2026 and build as normal.
   * **From the command line:** run `scripts\vs2026_build.bat`. It configures and builds a 64-bit Release with the CMake bundled with Visual Studio 2026. Set these first if your installs aren't in the default places, using forward slashes:
     ```
     set QT_DIR=C:/Qt/5.15.2/msvc2019_64
     set OPENSSL_DIR=C:/Program Files/OpenSSL-Win64
     scripts\vs2026_build.bat
     ```
     The output goes to _build64\bin\Release_ (set `BUILD_DIR` to change the folder). The logs are _configure.log_, _build.log_ and _build_errors.log_ in the build folder.

   If the newer compiler rejects any of the older bundled code, install the "MSVC v143 - VS 2022 C++ build tools" component from the Visual Studio Installer, set `TOOLSET=v143` at the top of _vsbuild_x64.bat_, and run it again from a clean build folder. Don't set an environment variable named `RC` before building, because Visual Studio treats it as the resource compiler.

4. **Test the build.** `scripts\test_servers.bat` runs all unit tests. It then starts the lobby, world and channel servers against the small test datastore that the build generates, checks that each one starts and opens its port, and stops them. No game client is needed. The result is in `<build folder>\servertest\servertest_summary.log`. If Windows Firewall asks about the servers, you can cancel, because the test only uses this PC.

### Running a local server on Windows ###

These scripts run a lobby, world and channel server on your PC that a game client can log in to. They use SQLite, so no database server is needed. The client must be COMP_hack-patched (it has _comp_client.dll_), and its _ImagineClient.dat_ must contain `-ip 127.0.0.1` and `-port 10666`. The server reads the client's _BinaryData_ and _Map_ folders directly.

1. **Start the servers.** Run `scripts\start_server.bat -ClientDir "D:/Games/ReIMAGINE"`, pointing at your client folder. The folder is remembered, so later runs only need `scripts\start_server.bat`. Startup takes about 30 seconds.
   * Everything goes into _local-server_ in the repository: the config, the SQLite database and the logs. Git ignores this folder, and `IMAGINE_SERVER_DIR` sets a different one.
   * The startup summary is in _local-server\server_start.log_, and each server's output is in _local-server\logs_.
   * On the first start, an admin account (user level 1000) is created with a random password, saved to _local-server\admin_account.txt_.
   * The lobby only accepts one client version, 2.032 (the ReIMAGINE client) by default. For another client, pass its version, e.g. `-ClientVersion 1.666` for the original client.

2. **Create an account.** With the servers running, run `scripts\create_test_account.bat` (optionally `-Username name`). It registers the account through the lobby's web API, and the username and a random password are saved to _local-server\test_account.txt_.

3. **Start the client.** `scripts\start_client.bat` starts _ImagineClient.exe_ from the remembered client folder. Log in with the account from step 2.

4. **Stop the servers.** `scripts\stop_server.bat`.

More details and troubleshooting notes are in [scripts/README.md](scripts/README.md).
