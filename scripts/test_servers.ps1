# Runs the unit tests, then starts the lobby, world and channel servers against
# the generated test datastore (<build>/testing, no game client needed) with
# SQLite, checks they come up and listen, and stops them again.
# Everything is written to <build>/servertest; summary in servertest_summary.log.
$ErrorActionPreference = 'Continue'
. "$PSScriptRoot\common.ps1"

$build = Get-BuildDir
$bin   = Join-Path $build 'bin\Release'
$run   = Join-Path $build 'servertest'
$sum   = Join-Path $run 'servertest_summary.log'

if (Test-Path $run) { Remove-Item -Recurse -Force $run }
New-Item -ItemType Directory -Path $run, "$run\config", "$run\unittests" | Out-Null
function Say($t) { $t | Out-File -FilePath $sum -Append -Encoding utf8; Write-Host $t }
"=== servertest $(Get-Date -Format s) ($build)" | Out-File -FilePath $sum -Encoding utf8

# ---------- 1. unit tests ----------
# (ctest cannot find them with the Visual Studio generator, so run them directly.)
Say '--- unit tests'
$pass = 0; $fail = 0
foreach ($t in (Get-ChildItem -Path $bin -Filter 'Test*.exe' | Sort-Object Name)) {
    $out = Join-Path $run ("unittests\" + $t.BaseName + '.log')
    $p = Start-Process -FilePath $t.FullName -WorkingDirectory $build -NoNewWindow -PassThru `
        -RedirectStandardOutput $out -RedirectStandardError ($out + '.err')
    $null = $p.Handle
    if (-not $p.WaitForExit(120000)) { $p.Kill(); Say ('TIMEOUT ' + $t.Name); $fail++; continue }
    $line = (Select-String -Path $out -Pattern '\[  PASSED  \]|\[  FAILED  \]' | ForEach-Object { $_.Line }) -join ' | '
    Say ('{0,-28} exit={1}  {2}' -f $t.Name, $p.ExitCode, $line)
    if ($p.ExitCode -eq 0) { $pass++ } else { $fail++ }
}
Say "unit tests: $pass passed, $fail failed"

# ---------- 2. server smoke test ----------
# The build converts contrib/testing XML into encrypted .sbin files under
# <build>/testing; the servers cannot use the raw XML copy in contrib/testing.
Say '--- servers'
Copy-Item -Recurse (Join-Path $build 'testing\datastore') "$run\datastore"
$webroot = To-ForwardSlashes (Join-Path $RepoRoot 'contrib\webroot')
foreach ($f in 'lobby.xml', 'world.xml', 'channel.xml', 'constants.xml', 'test_lobby_setup.xml', 'test_world_setup.xml', 'newcharacter.xml') {
    $text = Get-Content -Raw (Join-Path $RepoRoot "contrib\testing\config\$f")
    $text = $text -replace '<member name="DatabaseType">MARIADB</member>', '<member name="DatabaseType">SQLITE3</member>'
    $text = $text -replace '<member name="WebRoot">[^<]*</member>', "<member name=`"WebRoot`">$webroot</member>"
    Set-Content -Path "$run\config\$f" -Value $text -Encoding utf8
}

Get-Process comp_lobby, comp_world, comp_channel -ErrorAction SilentlyContinue | Stop-Process -Force
$servers = @(
    @{ name = 'lobby';   exe = 'comp_lobby.exe';   port = 10666; wait = 20 },
    @{ name = 'world';   exe = 'comp_world.exe';   port = 18666; wait = 20 },
    @{ name = 'channel'; exe = 'comp_channel.exe'; port = 14666; wait = 60 }
)
$procs = @{}
foreach ($s in $servers) {
    $out = "$run\$($s.name).out.log"
    $procs[$s.name] = Start-Process -FilePath (Join-Path $bin $s.exe) `
        -ArgumentList ('"' + "$run\config\$($s.name).xml" + '"') `
        -WorkingDirectory $run -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $out -RedirectStandardError ($out + '.err')
    $null = $procs[$s.name].Handle
    Start-Sleep -Seconds $s.wait
}

$listen = netstat -ano | Select-String 'LISTENING'
$ok = $true
foreach ($s in $servers + @(@{ name = 'lobby-web'; port = 10999 })) {
    $p = $procs[($s.name -split '-')[0]]
    $alive = -not $p.HasExited
    $open = [bool]($listen | Select-String (':' + $s.port + '\s'))
    if (-not ($alive -and $open)) { $ok = $false }
    Say ('{0,-10} running={1,-5} port {2} listening={3}' -f $s.name, $alive, $s.port, $open)
}
foreach ($n in 'channel', 'world', 'lobby') {
    if (-not $procs[$n].HasExited) { Stop-Process -Id $procs[$n].Id -Force }
}
Say ("=== result: unit tests {0}/{1} passed, servers {2}" -f $pass, ($pass + $fail), $(if ($ok) { 'OK' } else { 'FAILED' }))
