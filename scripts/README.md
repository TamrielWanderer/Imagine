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

## Notes

- The lobby waits at an interactive `Username:` prompt if its database has
  no accounts and there is no `setup.xml`. `start_server.ps1` writes
  `setup.xml` on the first run to avoid this.
- Expected startup warnings with the ReIMAGINE client data: "Invalid spot
  file listed in DynamicMapData" for some maps, and a missing
  `MD01_002_02t.qmp` zone geometry file.
- Do not set an environment variable named `RC` before building; Visual
  Studio treats it as the resource compiler.
