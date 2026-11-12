# COMP\_hack #

[![AGPL License](http://img.shields.io/badge/license-AGPL-brightgreen.svg)](https://opensource.org/licenses/AGPL-3.0)
[![Coverity Scan Build Status](https://scan.coverity.com/projects/9671/badge.svg)](https://scan.coverity.com/projects/comphack-comp_hack)

## Shin Megami Tensei IMAGINE (真・女神転生IMAGINE) Open Source Conservation Effort ##

The aim of the project is to revive an MMO that has been shutdown (SMT: IMAGINE). It's a complete re-implementation of the server from scratch and fully open source.

## Experimental branch ##

This is the `experimental` branch. It holds changes that differ from the original release of the game. Use `main` if you want the original behavior.

### List of changes ###

**Client partner demon AI** (`contrib/client-patches/partner_ai_patch.py`)

The partner demon AI runs in the game client, so these changes are a patch to `ImagineClient.exe`. The patcher changes:

- **Shorter pauses.** The demon waits less time between actions (1.5 s → 0.5 s between actions, and shorter waits after skills and movement).
- **Better skill choice.** Healing and recovery come first when an ally is hurt. Then attack skills, and buffs and debuffs last.
- **Guard and counter only when attacked.** The demon no longer uses guard or counter skills when nothing is attacking it.
- **Learning enemy resistances.** When a skill is drained, nulled or reflected by an enemy type, the demon remembers it and stops using that element on that enemy type. The memory resets when the client closes.
- **Aggressive mode.** The old "Defense" option in the demon's behavior settings now switches modes. Enabled means normal mode. Disabled means aggressive mode: the demon attacks any hostile enemy in medium range, even when no one is fighting.
- **Area skills only in range.** Skills that hit an area around the demon (for example Absolute Zero) are only chosen when the target is inside the area. Otherwise the demon picks another suitable skill.

The game checks the client's code, so the patcher also updates the matching hash in `comp_client.dll`. It keeps `.orig` backups of both files.

```
python partner_ai_patch.py "<client folder>"            # apply the patch
python partner_ai_patch.py "<client folder>" --check    # show what is applied
python partner_ai_patch.py "<client folder>" --revert   # restore the original files
python partner_ai_patch.py "<client folder>" --debug    # also write a debug log
```

The patch checks the original bytes before it writes anything, and it can upgrade a client patched with an older version. The reverse engineering notes are in `docs/client-partner-ai-notes.md`. The scripts `build_learning_cave.py`, `build_aggressive_cave.py` and `build_skill_filter.py` rebuild the added code.

**Server partner assist (off by default)**

An earlier server-side try at the same goal. The channel server can make the partner demon use skills on its own. It is turned off by default and is not needed with the client patch. Options in `channelconfig.xml`: `PartnerCombatAssist`, `PartnerAssistInterval`, `PartnerAssistHealPercent`, `PartnerAssistBuffInterval`, `PartnerAssistChase` and `PartnerAssistOwnSkills`. `scripts/start_server.ps1 -PartnerAssist on|off` switches it.

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

### Playing over the LAN or the Internet ###

By default the servers only accept the client on the same PC. The channel server tells clients which address to connect to, so it has to advertise an address the other players can reach.

**LAN (other PCs on your network)**

1. Start the servers with `scripts\start_server.bat -LanIP auto`. It detects this PC's LAN address (or pass one, e.g. `-LanIP 192.168.1.20`). The address is remembered in _local-server\lan_ip.txt_, and `-LanIP off` goes back to this PC only. _local-server\server_start.log_ shows the address in use.
2. Open the firewall once, from an administrator PowerShell: `powershell -ExecutionPolicy Bypass -File scripts\allow_lan_firewall.ps1`. It allows TCP 10666 (lobby), 14666 (channel), 10999 (lobby web API) and 10080 (launcher updates) on Private networks, and removes Block rules Windows saved for the server programs if a firewall prompt was cancelled. Your network must be set to Private in Windows settings. `-Remove` undoes it.
3. On each other PC, set `-ip <server address>` in the client's _ImagineClient.dat_ (keep `-port 10666`).
4. Accounts: run `scripts\create_test_account.bat` on the server PC, or register through `http://<server address>:10999/api/account/register`.

**Internet**

1. Give the server PC a fixed LAN address, then forward TCP 10666, 14666, 10999 and 10080 from your router to it. Port 18666 (world) stays internal.
2. Start the servers with `-LanIP <your public IP address>`. The channel server then advertises the public address. If your public address changes, start again with the new one (or use a static address).
3. Open the firewall as for the LAN (step 2 above). If Windows classifies the connection as Public, add the same ports for the Public profile.
4. Players set `-ip <your public IP address>` in _ImagineClient.dat_.
5. Players on your own network may not be able to use the public address (many routers don't support NAT loopback). They can keep using the LAN address with `-ip`, but the channel address is the public one, so test from outside your network too.

Opening ports exposes the servers to anyone. Account registration through the web API is open, and the admin account from _local-server\admin_account.txt_ has full rights, so keep that file private.

### Client updates through the launcher ###

The game launcher (_ImagineUpdate.exe_) downloads changed client files from an update server before starting the game. The server PC can be that update server, so players get new translations and other client fixes automatically.

1. **Publish files.** `scripts\publish_update.bat -Add BinaryData\Shield\CHelpData.sbin,BinaryData\Client` takes paths relative to the client folder (files or whole folders) and copies them from the client folder into _local-server\update\patch_. You can also drop files there by hand, in the same layout as the client folder. Everything in that folder is published: `comp_rehash` writes compressed copies and the file list (_hashlist.dat_, _hashlist.ver_) to _local-server\update\files_. `-Clear` empties the patch folder first.
2. **Serve them.** `scripts\start_server.bat` also starts the update server (HTTP on TCP 10080) whenever something is published, and `scripts\stop_server.bat` stops it. You can also run `scripts\serve_update.bat` on its own. Requests are logged to _local-server\logs\update_server.log_.
3. **Point launchers at it.** `scripts\set_update_url.bat` sets `BaseURL1` in this PC's _ImagineUpdate.dat_ to `http://<LAN address>:10080/`. On other PCs, edit `BaseURL1` in _ImagineUpdate.dat_ to `http://<server address>:10080/` (the LAN or public address, as for `-ip`). `set_update_url.bat -Restore` goes back to the original file, which is kept as _ImagineUpdate.dat.reimagine_.

Launchers download a file only if its checksum differs from the player's copy, so publishing a whole folder costs nothing for files players already have. Files you don't publish are never touched. Pointing a launcher at your server replaces the official update server, so the official ReIMAGINE updates stop reaching that client. For a public release, any web server can host the _local-server\update\files_ folder instead.

### English translation of the client ###

`scripts\apply_translation.bat` translates the menus and system text that the client still shows in Japanese (about 2,400 strings). It patches your client's _BinaryData_ files and keeps the originals in _BinaryData_jp_backup_. Publish the changed files with the updater to give them to other players. Details and the table format are in [contrib/translation/README.md](contrib/translation/README.md).

More details and troubleshooting notes are in [scripts/README.md](scripts/README.md).
