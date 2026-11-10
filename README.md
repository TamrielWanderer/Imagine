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

* [Visual Studio 2015](https://visualstudio.microsoft.com/vs/older-downloads/)
* [CMake](https://cmake.org)
* [Qt 5.7+](https://www.qt.io)

#### Optional Dependencies ####

* [Doxygen](http://www.doxygen.nl)
* [WiX Toolset](http://wixtoolset.org)

#### Building ####

> All dependencies are bundled in this repository (see _deps/SOURCES.md_), so no submodules or downloads are needed.

Edit the _vsbuild_x86.bat_ and _vsbuild_x64.bat_ batch files to point to your install of Qt. Run the desired script and you should see a _build32_ or _build64_ folder. Inside the folder should be a comp_hack.sln solution file. Open the solution and build as normal.
