# Starts the Imagine lobby, world and channel servers on this PC for local play.
#
#   start_server.ps1 -ClientDir "D:/Games/ReIMAGINE" [-ClientVersion 2.032]
#
# Data:      <repo>/datastore + the game client folder (BinaryData and Map QMP files).
# Database:  SQLite in <server dir>/database.
# Server dir defaults to <repo>/local-server (override with IMAGINE_SERVER_DIR).
# The client folder is remembered in <server dir>/client_dir.txt, so later runs
# need no arguments.
#
# On the first run (empty database) an admin account (UserLevel 1000) with a
# random password is created and saved to <server dir>/admin_account.txt.
# Summary: <server dir>/server_start.log. Server output: <server dir>/logs.
param(
    [string]$ClientDir = '',
    [string]$ClientVersion = '2.032'   # ReIMAGINE client; the original client is 1.666
)
$ErrorActionPreference = 'Continue'
. "$PSScriptRoot\common.ps1"

$build = Get-BuildDir
$bin   = Join-Path $build 'bin\Release'
$srv   = $ServerDir
$sum   = Join-Path $srv 'server_start.log'

New-Item -ItemType Directory -Force -Path $srv, "$srv\config", "$srv\logs", "$srv\database" | Out-Null
function Say($t) { $t | Out-File -FilePath $sum -Append -Encoding utf8; Write-Host $t }
"=== start $(Get-Date -Format s)" | Out-File -FilePath $sum -Encoding utf8

$clientFile = Join-Path $srv 'client_dir.txt'
if (-not $ClientDir -and (Test-Path $clientFile)) { $ClientDir = (Get-Content $clientFile -First 1).Trim() }
if (-not $ClientDir -or -not (Test-Path (Join-Path $ClientDir 'BinaryData'))) {
    Say "Client folder not found. Run: start_server.ps1 -ClientDir <folder that contains BinaryData and Map>"
    exit 1
}
Set-Content -Path $clientFile -Value $ClientDir -Encoding utf8
if (-not (Test-Path (Join-Path $bin 'comp_lobby.exe'))) {
    Say "No Release build found in $build. Build first (vs2026_build.bat) or set IMAGINE_BUILD_DIR."
    exit 1
}

# Stop an earlier run of this script and any servers it left running.
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
    Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -like '*start_server.ps1*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Get-Process comp_lobby, comp_world, comp_channel -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

$ds     = (To-ForwardSlashes $RepoRoot) + '/datastore'
$web    = (To-ForwardSlashes $RepoRoot) + '/contrib/webroot'
$client = To-ForwardSlashes $ClientDir

# Windows config templates, pointed at the real data folders.
foreach ($f in 'lobby.xml', 'world.xml', 'channel.xml', 'newcharacter.xml') {
    $text = Get-Content -Raw (Join-Path $RepoRoot "contrib\winconfig\$f")
    $text = $text -replace '<element>datastore</element>', "<element>$ds</element>"
    $text = $text -replace '<element>C:/path/to/client/files</element>', "<element>$client</element>"
    $text = $text -replace '<member name="WebRoot">webroot</member>', "<member name=`"WebRoot`">$web</member>"
    $text = $text -replace '<member name="Name">Some Server</member>', '<member name="Name">Local World</member>'
    $text = $text -replace '<member name="Name">Some Channel</member>', '<member name="Name">Local Channel</member>'
    if ($f -eq 'lobby.xml') {
        $text = $text -replace '(<member name="DatabaseType">SQLITE3</member>)', "`$1`r`n        <member name=`"ClientVersion`">$ClientVersion</member>"
    }
    Set-Content -Path "$srv\config\$f" -Value $text -Encoding utf8
}
Copy-Item -Force (Join-Path $RepoRoot 'contrib\testing\config\constants.xml') "$srv\config\constants.xml"

# First-run admin account. Without setup.xml the lobby waits at an interactive
# "Username:" prompt when the database has no accounts.
if (-not (Test-Path "$srv\admin_account.txt")) {
    $chars = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    $pw = -join (1..14 | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
    $setup = (Get-Content -Raw (Join-Path $RepoRoot 'contrib\winconfig\setup.xml')) `
        -replace '<member name="Password">[^<]*</member>', "<member name=`"Password`">$pw</member>" `
        -replace '<member name="Email">[^<]*</member>', '<member name="Email">admin@localhost.test</member>'
    Set-Content -Path "$srv\config\setup.xml" -Value $setup -Encoding utf8
    @("Local admin account (UserLevel 1000), created $(Get-Date -Format s)", 'Username: admin', "Password: $pw") |
        Set-Content -Path "$srv\admin_account.txt" -Encoding utf8
    # Start from an empty database so setup.xml is applied.
    Get-ChildItem "$srv\database" -ErrorAction SilentlyContinue | Remove-Item -Force -Recurse
    Say 'Created an admin account (see admin_account.txt)'
}
Say "build: $build"
Say "data:  $ds | $client"

$servers = @(
    @{ name = 'lobby';   exe = 'comp_lobby.exe';   timeout = 120 },
    @{ name = 'world';   exe = 'comp_world.exe';   timeout = 180 },
    @{ name = 'channel'; exe = 'comp_channel.exe'; timeout = 600 }
)
foreach ($s in $servers) {
    $out = "$srv\logs\$($s.name).out.log"
    if (Test-Path $out) { Remove-Item -Force $out }
    $p = Start-Process -FilePath (Join-Path $bin $s.exe) `
        -ArgumentList ('"' + "$srv\config\$($s.name).xml" + '"') `
        -WorkingDirectory $srv -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $out -RedirectStandardError ($out + '.err')
    $null = $p.Handle
    Say ("started {0} (pid {1})" -f $s.name, $p.Id)

    # Wait for "Server ready!" (or exit / timeout) before starting the next one.
    $t0 = Get-Date
    while ($true) {
        Start-Sleep -Seconds 2
        if ((Test-Path $out) -and (Select-String -Path $out -Pattern 'Server ready!' -Quiet)) {
            Say ("{0} ready after {1:N0}s" -f $s.name, ((Get-Date) - $t0).TotalSeconds); break
        }
        if ($p.HasExited) { Say ("{0} EXITED with code {1}, see logs\{0}.out.log" -f $s.name, $p.ExitCode); exit 1 }
        if (((Get-Date) - $t0).TotalSeconds -gt $s.timeout) { Say "$($s.name) not ready after $($s.timeout)s"; break }
    }
}

Start-Sleep -Seconds 3
$listen = netstat -ano | Select-String 'LISTENING'
foreach ($port in 10666, 10999, 18666, 14666) {
    Say ("port {0} listening: {1}" -f $port, [bool]($listen | Select-String (":" + $port + "\s")))
}
Select-String -Path "$srv\logs\*.out.log" -Pattern 'ERROR|CRITICAL' |
    ForEach-Object { Say ("[{0}] {1}" -f $_.Filename, $_.Line) }
Say 'Servers are running. Stop them with stop_server.bat.'
