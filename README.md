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

Edit the paths at the top of _vsbuild_x64.bat_ (or _vsbuild_x86.bat_ for 32-bit) to point to your Qt and OpenSSL installs. Run the script and you should see a _build64_ (or _build32_) folder containing a comp_hack.sln solution file. Open the solution in Visual Studio 2026 and build as normal.

To build from the command line instead, and to run a local server that the game client can log in to, see [scripts/README.md](scripts/README.md).

If the newer compiler rejects any of the older bundled code, install the "MSVC v143 - VS 2022 C++ build tools" component from the Visual Studio Installer, set `TOOLSET=v143` at the top of the batch file, and run it again from a clean build folder.
