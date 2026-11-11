# Windows scripts: build, test and run a local server

These scripts build Imagine with Visual Studio 2026 and run a complete local
server (lobby, world, channel) that a COMP_hack-patched game client can log
in to. Tested on Windows 10 with VS 2026 Community, Qt 5.15.2, OpenSSL 3.0
and the ReIMAGINE client (version 2.032): character creation and the
tutorial work.

Every `.bat` file can be double-clicked. The `.ps1` files hold the logic;
the `.bat` files run them with PowerShell.

## 1. Install the tools

| Tool | Notes |
|---|---|
| Visual Studio 2026 | "Desktop development with C++" workload. Its bundled CMake (4.x) is used automatically. |
| Git | |
| Qt 5.15.2, MSVC 64-bit, **with Qt WebEngine** | `install_qt.bat [folder]` installs it without a Qt account (needs Python 3). Default folder `C:\Qt`. |
| OpenSSL for Windows | e.g. the Shining Light "Win64 OpenSSL" installer (3.0.x works). |

`check_tools.bat` lists what it finds and writes `check_tools.log`.

## 2. Build

```bat
set QT_DIR=C:/Qt/5.15.2/msvc2019_64
set OPENSSL_DIR=C:/Program Files/OpenSSL-Win64
scripts\vs2026_build.bat
```

Use forward slashes in both paths. The defaults are the values above, so
you can skip the `set` lines if your tools are there. The build goes to
`build64` (override with `BUILD_DIR`) and takes about 20 minutes. Logs:
`build64\configure.log`, `build64\build.log`, `build64\build_errors.log`.

## 3. Test the build (no game client needed)

`test_servers.bat` runs all unit tests, then starts the three servers
against the small test datastore the build generates, checks that each one
starts and listens on its port, and stops them. The result is in
`<build>\servertest\servertest_summary.log`. Windows Firewall may ask to
allow the servers; the test only uses localhost, so you can cancel.

## 4. Run a local server and play

You need the game client: a COMP_hack-patched client (it has
`comp_client.dll`) whose `ImagineClient.dat` contains:

```
-ip 127.0.0.1
-port 10666
```

The server reads the client's `BinaryData` and `Map` folders directly.

1. **Start the servers** (only the first time needs the client folder):

   ```bat
   scripts\start_server.bat -ClientDir "D:/Games/ReIMAGINE"
   ```

   Later runs: just `start_server.bat`. Startup takes about 30 seconds. The
   summary is in `local-server\server_start.log`, server output in
   `local-server\logs`. Everything (config, SQLite database, logs) lives in
   `local-server` (override with `IMAGINE_SERVER_DIR`); it is git-ignored.

   On the first start an admin account (user level 1000) with a random
   password is created and saved to `local-server\admin_account.txt`.

   For a client other than ReIMAGINE 2.032, pass its version, e.g.
   `-ClientVersion 1.666` for the original client. The lobby rejects other
   versions.

2. **Create an account:** `create_test_account.bat` (optionally
   `-Username name`). The username and a random password are saved to
   `local-server\test_account.txt`.

3. **Start the client:** `start_client.bat`, then log in with that account.

4. **Stop the servers:** `stop_server.bat`.

## 5. Play over the LAN (other PCs)

1. Start the servers in LAN mode once: `start_server.bat -LanIP auto` (or
   `-LanIP 192.168.1.20` to pick the address yourself). The address is
   remembered in `local-server\lan_ip.txt`; `-LanIP off` goes back to
   this-PC-only. `local-server\server_start.log` shows the address used.
2. Open the firewall: in an administrator PowerShell, run
   `powershell -ExecutionPolicy Bypass -File scripts\allow_lan_firewall.ps1`.
   It removes Block rules Windows saved for the server programs (from a
   cancelled firewall prompt) and allows TCP 10666, 14666, 10999 and 10080
   on Private networks. Your network must be set to Private. `-Remove` undoes it.
3. On the other PC, set `-ip <server address>` in the client's
   `ImagineClient.dat` (keep `-port 10666`) and start the client.
4. Accounts: run `create_test_account.bat` on the server PC, or call
   `http://<server address>:10999/api/account/register` from the other PC.

## Notes

- The lobby waits at an interactive `Username:` prompt if its database has
  no accounts and there is no `setup.xml`. `start_server.ps1` writes
  `setup.xml` on the first run to avoid this.
- Expected startup warnings with the ReIMAGINE client data: "Invalid spot
  file listed in DynamicMapData" for some maps, and a missing
  `MD01_002_02t.qmp` zone geometry file.
- Do not set an environment variable named `RC` before building; Visual
  Studio treats it as the resource compiler.

## Partner demon combat assist (experimental)

`start_server.ps1 -PartnerAssist on|off` (default on, remembered in
`local-server/partner_assist.txt`). When on, the channel server makes your
summoned demon heal you (or itself) below 50% HP, cast its buffs/debuffs about
once a minute each, and use its attack skills on whatever you or it are
fighting, roughly every 1.5 seconds. It never interrupts a skill the client
already started for the demon. Tune it in `channel.xml` with
`PartnerAssistInterval` (ms), `PartnerAssistHealPercent` and
`PartnerAssistBuffInterval` (seconds).

## 6. Client updates through the launcher

Players' launchers (`ImagineUpdate.exe`) can download changed client files
from your server before the game starts.

1. Publish: `publish_update.ps1 -Add BinaryData\Shield\CHelpData.sbin, ...`
   (paths relative to the client folder; folders work too). Files collect in
   `local-server\update\patch`; `-Clear` empties it first. It runs
   `comp_rehash` and writes the downloadable set to `local-server\update\files`.
2. Serve: `start_server.ps1` starts `serve_update.ps1` (HTTP, TCP 10080) in the
   background whenever something is published; `stop_server.ps1` stops it.
   Other PCs need 10080 open: re-run `allow_lan_firewall.ps1` as admin.
3. Point launchers at it: `set_update_url.ps1` on this PC (uses `lan_ip.txt`),
   or on another PC set `BaseURL1 = http://<server LAN IP>:10080/` in its
   `ImagineUpdate.dat`. `set_update_url.ps1 -Restore` goes back to the official
   ReIMAGINE update server (the original is kept as `ImagineUpdate.dat.reimagine`).

Launchers only download files whose checksum differs from their own copy.
Only the files you publish are managed; nothing else in the client is touched.

## 7. English translation

`apply_translation.bat` (needs Python 3) translates the client's menus and
system text using `contrib\translation\menus_system.json`. It uses the
remembered client folder (or `-ClientDir <folder>`), keeps the originals in
`<client>\BinaryData_jp_backup`, and `-Check` only counts what would change.
Then publish the changed files (step 6) so other players get them.

For Internet play, see "Playing over the LAN or the Internet" in the main
README: forward TCP 10666, 14666, 10999 and 10080 and start with
`-LanIP <public IP address>`.
