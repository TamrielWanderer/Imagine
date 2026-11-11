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
# LAN play: -LanIP auto (or an address like 192.168.1.20) makes the channel
# server advertise that address instead of 127.0.0.1, so clients on other PCs
# can connect. Remembered in <server dir>/lan_ip.txt; -LanIP off turns it off.
# Partner demon combat assist (experimental): -PartnerAssist on|off, remembered
# in <server dir>/partner_assist.txt. Default on.
param(
    [string]$ClientDir = '',
    [string]$ClientVersion = '2.032',  # ReIMAGINE client; the original client is 1.666
    [string]$LanIP = '',
    [string]$PartnerAssist = ''
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

# LAN address to advertise for the channel server (empty = this PC only).
$lanFile = Join-Path $srv 'lan_ip.txt'
if (-not $LanIP -and (Test-Path $lanFile)) { $LanIP = (Get-Content $lanFile -First 1).Trim() }
if ($LanIP -eq 'off') {
    Remove-Item -Force -ErrorAction SilentlyContinue $lanFile
    $LanIP = ''
} elseif ($LanIP -eq 'auto') {
    # IPv4 address of the adapter that has the default gateway (the LAN one).
    $LanIP = @((Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } |
        Select-Object -First 1).IPv4Address.IPAddress)[0]
    if (-not $LanIP) { Say 'Could not detect the LAN address; pass it with -LanIP <address>.'; exit 1 }
}
if ($LanIP) { Set-Content -Path $lanFile -Value $LanIP -Encoding utf8 }

# Partner demon combat assist switch (channel server).
$assistFile = Join-Path $srv 'partner_assist.txt'
if (-not $PartnerAssist -and (Test-Path $assistFile)) { $PartnerAssist = (Get-Content $assistFile -First 1).Trim() }
if ($PartnerAssist -ne 'off') { $PartnerAssist = 'on' }
Set-Content -Path $assistFile -Value $PartnerAssist -Encoding utf8
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
    if ($f -eq 'channel.xml' -and $LanIP) {
        $text = $text -replace '(<member name="DatabaseType">SQLITE3</member>)', "`$1`r`n        <member name=`"ExternalIP`">$LanIP</member>"
    }
    if ($f -eq 'channel.xml' -and $PartnerAssist -eq 'on') {
        $text = $text -replace '(<member name="DatabaseType">SQLITE3</member>)', "`$1`r`n        <member name=`"PartnerCombatAssist`">true</member>"
    }
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
if ($LanIP) {
    Say "LAN:   channel advertised as $LanIP (other PCs: set -ip $LanIP in ImagineClient.dat)"
} else {
    Say 'LAN:   off (this PC only; use -LanIP auto for LAN play)'
}

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
# Update server for the game launcher, when something has been published.
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
    Where-Object { $_.CommandLine -like '*serve_update.ps1*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
if (Test-Path (Join-Path $srv 'update\files\hashlist.ver')) {
    Start-Process powershell -WindowStyle Hidden -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', "`"$PSScriptRoot\serve_update.ps1`"")
    Start-Sleep -Seconds 2
    $updHost = if ($LanIP) { $LanIP } else { '127.0.0.1' }
    Say "update server: http://${updHost}:10080/ (listening: $([bool](Get-NetTCPConnection -LocalPort 10080 -State Listen -ErrorAction SilentlyContinue)))"
}
Say 'Servers are running. Stop them with stop_server.bat.'
