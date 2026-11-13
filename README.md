# COMP\_hack #

[![AGPL License](http://img.shields.io/badge/license-AGPL-brightgreen.svg)](https://opensource.org/licenses/AGPL-3.0)
[![Coverity Scan Build Status](https://scan.coverity.com/projects/9671/badge.svg)](https://scan.coverity.com/projects/comphack-comp_hack)

## Shin Megami Tensei IMAGINE (真・女神転生IMAGINE) Open Source Conservation Effort ##

The aim of the project is to revive an MMO that has been shutdown (SMT: IMAGINE). It's a complete re-implementation of the server from scratch and fully open source.

## Experimental branch ##

This is the `experimental` branch. It holds changes that differ from the original release of the game. Use `main` if you want the original behavior.

### Overview ###

| Area | What changed | Where |
| --- | --- | --- |
| Partner demon | Faster, smarter client AI (skill order, learned resistances, aggressive mode) | [Client partner demon AI](#list-of-changes) |
| Hotbars | Up to 6 extra shortcut bars, a key for every slot, macros | [Extra shortcut bars](#list-of-changes) |
| Settings | Window editor for keys, bars and macros, shipped to players as _KeyConfigTool.exe_ | [Editor for keys, bars and macros](#list-of-changes) |
| Combat | Stagger rework: affinity-based stagger, recovery window, Smirk | [Stagger rework](#list-of-changes) |
| Inventory | `@sort`, `@deposit`, bigger item stacks | [Inventory QoL](#list-of-changes) |
| Language | The client is translated to English: menus, items, skills, compendium, story and NPC dialogue | [English translation](#english-translation-of-the-client) |
| Accounts | Player portal web page: create an account, see characters, stats, alignment and demons | [Player portal](#player-portal-accounts-and-characters) |
| Hosting | Windows build and server scripts, LAN/Internet play, client updates through the launcher | [Running a local server](#running-a-local-server-on-windows) |
| Admin | GM command reference | [docs/GM_commands.txt](docs/GM_commands.txt) |

**Publishing to players.** Everything a player needs on their PC goes through the launcher ([Client updates](#client-updates-through-the-launcher)): the patched _ImagineClient.exe_ and _comp_client.dll_ (client patches), _KeyConfigTool.exe_, the translated _BinaryData_ files and _BinaryData/Shield/ItemData.sbin_ (stack sizes). Personal settings (_KeyConfigOption.txt_, _ShortcutBars.txt_, _Macros.txt_, _InsideOption.txt_) are never published.

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

**Extra shortcut bars, keys and macros** (`contrib/client-patches/shortcut_bars_patch.py`)

A second client patch (it works with or without the partner AI patch):

- **Up to 6 more shortcut bars on screen.** Each bar shows its own page and keeps its own arrows, so pages 1, 2 and 3 can all be visible at once. Clicking, dragging skills or items onto them and rearranging slots work like on the main bar.
- **A key for every slot.** The new key actions `ShortCutBar1_00` to `ShortCutBar6_15` (bar 1-6, slot 00-15) go in `KeyConfigOption.txt`, for example `-ShortCutBar1_00 SHIFT+1`. Modifiers work like the game's own keys.
- **Macros.** `ShortCutMacro01` to `ShortCutMacro10` run up to 8 slots from a list in `Macros.txt`: either one step per key press (like a cast sequence, starting over after a few seconds) or all at once.

The bars are set in `ShortcutBars.txt` in the client folder: one line per bar, `page layout x y` (page 1-10, layout 0-3 like `ShortcutWindowType`, position or `-1 -1` for above the main bar). The game writes the file with two bars (pages 2 and 3) and an explanation the first time it starts, and saves pages and positions there when a bar moves. `Macros.txt` is written the same way with an explanation and an example.

Close the game, then:

```
scripts\shortcut_bars_patch.bat                      # apply to the client folder start_server.ps1 remembers
scripts\shortcut_bars_patch.bat "<client folder>" --check    # show what is applied
scripts\shortcut_bars_patch.bat "<client folder>" --revert   # remove it
```

(Or `py -3 contrib\client-patches\shortcut_bars_patch.py "<client folder>\ImagineClient.exe"`.) Running it again on a client patched with an older build upgrades it. Like the partner AI patch it updates the hash in `comp_client.dll`; publish both with `scripts\publish_update.bat -Add ImagineClient.exe` (the dll is added automatically). The key of `ShortCutBarN_SS` is the same slot position as the main bar's `ShortCutPlayerSS` key.

**Editor for keys, bars and macros.** The game has no menu for these, so `scripts\key_config_tool.bat` opens a small window (Python 3 with tkinter, part of the python.org installer) with three tabs:

- **Keys:** every action in `KeyConfigOption.txt`, grouped (main bar, extra bars, macros, demon bar, movement, windows...). Double-click an action and press the key combination, or pick it from a list. It warns when the key is already used and can move it.
- **Extra bars:** add or remove bars and set their page, layout and position.
- **Macros:** up to 10 macros of up to 8 steps (page and slot), one step per press or all at once, and their keys.

Close the game before saving, because the game rewrites `KeyConfigOption.txt` and `ShortcutBars.txt` when it exits. The first save keeps the old files as `.bak`. These three files are personal settings, so they are not published with the updater.

To give the editor to every player, run `scripts\build_key_config_tool.bat` once on the server PC (it needs Python there, players don't). It builds the stand-alone `KeyConfigTool.exe` with PyInstaller, copies it into the client folder and publishes it with the updater, so every launcher downloads it next to `ImagineClient.exe`. Players double-click `KeyConfigTool.exe` in their game folder; it edits the files of the folder it is in. Run the script again after the editor changes (`-NoPublish` only builds and copies). Notes: `docs/client-shortcut-bars-notes.md`; the code is `shortcut_bars.asm` (rebuild with `build_shortcut_bars.py`, needs nasm).

**Stagger rework** (channel server, `StaggerRework` in `channelconfig.xml`)

In the original game, hits stop the target (knockback and hit stun) and nothing limits how long a target can be kept stunned. Enemy groups and players could chain hits so the target never acted. The rework keeps hits feeling strong but makes stagger something you earn, in the spirit of the Press Turn system:

- **Affinity decides the stagger.** A hit on a weakness, a critical or a limit break drains the knockback gauge 3× faster. A normal hit drains it as before. A resisted hit does not drain it and does not cause hit stun.
- **Blocked attacks stagger the attacker.** If an attack is nulled, absorbed (drained) or reflected, the attacker is stunned for 1 s, the "lost turn" of Press Turn.
- **Recovery after a knockback.** After getting up from a knockback, the target cannot be knocked back, hit stunned or have a charge interrupted for 2.5 s.
- **Diminishing hit stun.** Within 5 s, the second hit stun on a target lasts half as long and later ones do not apply. Knockbacks count toward this.
- **Smirk.** A successful dodge or counter grants Smirk for 8 s. While it lasts the entity cannot be staggered, and its next damaging skill deals 150% damage, which uses up Smirk. A chat message tells the player when they or their demon smirk.
- **Guard is unchanged.** It still reduces damage and prevents stagger.

The rules apply the same way to players, demons and enemies. Settings (all in `channelconfig.xml`):

| Setting | Default | Meaning |
| --- | --- | --- |
| `StaggerRework` | `false` | Turns the rework on |
| `StaggerWeakPercent` | `300` | Gauge drain on a weakness, critical or limit break, in % |
| `StaggerNormalPercent` | `100` | Gauge drain on a normal hit, in % |
| `StaggerResistPercent` | `0` | Gauge drain on a resisted hit, in % |
| `StaggerResistHitStun` | `false` | Whether resisted hits still cause hit stun |
| `StaggerBlockedTime` | `1000` | Attacker stun when its attack is nulled, absorbed or reflected, in ms (0 = off) |
| `StaggerDownImmunity` | `2500` | Recovery window after a knockback, in ms |
| `StaggerStunWindow` | `5000` | Window for diminishing hit stun, in ms |
| `StaggerStunDecay` | `50` | Hit stun length for each repeat in the window, in % of the previous one |
| `StaggerStunMax` | `2` | Hit stuns allowed in the window (0 = no limit) |
| `SmirkOnDodge` / `SmirkOnCounter` | `true` | What grants Smirk |
| `SmirkOnGetUp` | `false` | Also grant Smirk when getting up from a knockback |
| `SmirkDuration` | `8000` | How long Smirk lasts, in ms |
| `SmirkDamagePercent` | `150` | Damage of the attack that uses Smirk, in % |
| `SmirkMessage` | `true` | Chat message when Smirk starts |

`scripts/start_server.ps1 -StaggerRework on|off` switches it (on by default in this branch, remembered in `stagger_rework.txt`).

**Inventory QoL** (channel server and `contrib/qol/stack_sizes.py`)

The client has no buttons for these, so they are chat commands any player can use (not only GMs):

| Command | What it does |
| --- | --- |
| `@sort` | Merges partial stacks of the same item and sorts the inventory by category and item. Equipped items keep their slots. |
| `@sort depo [N]` | The same for item depository box N (1 is the main box). |
| `@deposit` | Quick stack: moves inventory items into the item depository, but only items the depository already holds. Existing stacks are topped up first, then empty slots are used (a box already holding that item first). |
| `@deposit all` | Stores every storable item. |
| `@qol` | Lists these commands. |

Equipped items, Macca and Magnetite never move, and items that can't be stored stay in the inventory. Settings in `channelconfig.xml`: `QoLCommands` (default `true`) turns the commands on, and `QuickDepositAnywhere` (default `true`) lets `@deposit` work anywhere. Set it to `false` to require the depository window to be open.

**Bigger item stacks.** `scripts/stack_sizes.bat` raises the stack limit of stackable items in `BinaryData/Shield/ItemData.sbin`, which the server and the client both read. By default every limit from 10 up is multiplied by 10, capped at 9999 (10 → 100, 100 → 1000, 1000 → 9999). Limits under 10 (items you're only meant to hold a few of) and limits already above 9999 don't change. The numbers can be changed (`-Multiplier`, `-Min`, `-Max`), `-Check` shows the changes without writing, and `-Restore` puts the original file back. Running it again always starts from the original, so limits are never multiplied twice. Restart the server afterwards and publish the file with `publish_update.bat -Add BinaryData\Shield\ItemData.sbin` so every player's client has the same limits.

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
4. Accounts: players create their own on the [player portal](#player-portal-accounts-and-characters), `http://<server address>:10999/portal/`. On the server PC `scripts\create_test_account.bat` also works.

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

**Launcher banner and news.** The launcher shows a web page next to the Start button (`Information =` in _ImagineUpdate.dat_). The update server serves one at `http://<server address>:10080/updatebanner/`: the first steps for new players (create an account on the portal, set keys with _KeyConfigTool.exe_, the `@sort`/`@deposit` commands) and a news list with a server online/offline light. `set_update_url.bat` points the launcher at it together with `BaseURL1` (`-NoBanner` leaves the page alone); on other PCs set `Information = http://<server address>:10080/updatebanner/` by hand. The page is copied the first time from _contrib/updatebanner_ to _local-server\updatebanner_; post news by editing _local-server\updatebanner\news.json_ (date, title, text; newest first). It updates for everyone right away, nothing needs publishing. `start_server.bat` now always starts the update server so the banner is available.

Launchers download a file only if its checksum differs from the player's copy, so publishing a whole folder costs nothing for files players already have. Files you don't publish are never touched. Pointing a launcher at your server replaces the official update server, so the official ReIMAGINE updates stop reaching that client. For a public release, any web server can host the _local-server\update\files_ folder instead.

### Player portal (accounts and characters) ###

The lobby's web server (TCP 10999, already opened by `allow_lan_firewall.ps1`) serves a player portal at `http://<server address>:10999/portal/`. (The address without _/portal/_ is the game client's own login page, which is not meant for a browser.)

- **Create an account** with a username, email and password; it works for the game right away.
- **Sign in** to see the account (character tickets, CP, last login) and every character: level, experience, HP/MP, base stats, Law/Neutral/Chaos alignment with the LNC value, clan, and the demons in the COMP with their level, stats and familiarity (the partner demon is marked).

The page is _contrib/webroot/portal/index.html_. Its data comes from the new `/api/account/get_characters` call of the lobby (signed in with the same challenge login as the old account manager, so passwords are never sent after registration). The old admin account manager is still at _/accountmanager/_ and now also works from other PCs.

### English translation of the client ###

`scripts\apply_translation.bat` translates the Japanese text left in the client to English. It applies every table in _contrib/translation_ and keeps the originals in _BinaryData_jp_backup_:

| Table | Content |
| --- | --- |
| `menus_system.json` | Menus, buttons, system and shop messages, help, status effects, titles, NPC, map and demon names (about 2,400 strings) |
| `gameplay.json` | Every item and skill name and description, barter lines, demon compendium (about 17,000 strings) |
| `story.json` | Event, NPC and story dialogue, the Hourai club conversations, character messages (about 50,000 strings) |

Publish the changed files with the updater (`publish_update.bat -Add BinaryData\Shield\<file>,...`) to give them to other players. The Aeria English client is lost, so the text was translated from the Japanese client; details, the glossary and the table format are in [contrib/translation/README.md](contrib/translation/README.md).

More details and troubleshooting notes are in [scripts/README.md](scripts/README.md).
