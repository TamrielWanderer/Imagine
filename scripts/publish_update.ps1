# Publishes changed client files so game launchers (ImagineUpdate.exe) download
# them on their next start.
#
#   publish_update.ps1 -Add BinaryData\Shield\CHelpData.sbin, BinaryData\Client
#   publish_update.ps1            # just rebuild the file list from update\patch
#   publish_update.ps1 -Clear     # empty the patch folder first
#
# -Add takes paths relative to the client folder (files or whole folders) and
# copies them from the client folder (client_dir.txt) into
# <server dir>\update\patch. You can also drop files into that folder by hand,
# laid out like the client folder. Everything in it is published: comp_rehash
# writes compressed copies and the file list (hashlist.dat/.ver) to
# <server dir>\update\files, which serve_update.ps1 serves over HTTP.
#
# Launchers only download files whose checksum differs from their copy, so
# publishing a whole folder costs players nothing for files they already have.
param(
    [string[]]$Add = @(),
    [switch]$Clear
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"

$srv   = $ServerDir
$upd   = Join-Path $srv 'update'
$patch = Join-Path $upd 'patch'
$files = Join-Path $upd 'files'
$base  = Join-Path $upd 'base'
$rehash = Join-Path (Get-BuildDir) 'bin\Release\comp_rehash.exe'
if (-not (Test-Path $rehash)) { Write-Host "comp_rehash.exe not found ($rehash). Build first."; exit 1 }

New-Item -ItemType Directory -Force -Path $patch, $base | Out-Null
if ($Clear) { Get-ChildItem $patch | Remove-Item -Recurse -Force }

if ($Add.Count) {
    $clientFile = Join-Path $srv 'client_dir.txt'
    if (-not (Test-Path $clientFile)) { Write-Host 'Unknown client folder: run start_server.ps1 -ClientDir <folder> once.'; exit 1 }
    $client = (Get-Content $clientFile -First 1).Trim()
    foreach ($rel in $Add) {
        $src = Join-Path $client $rel
        if (-not (Test-Path $src)) { Write-Host "Not found in the client folder: $rel"; exit 1 }
        $dst = Join-Path $patch $rel
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
        Copy-Item -Recurse -Force $src $dst
        Write-Host "added $rel"
    }
}

# ImagineClient.exe and comp_client.dll must always be published together:
# comp_client.dll holds a checksum of the exe's code (the client AI patch
# updates both), and a launcher that gets only one of them ends up with a
# client that closes on start.
$clientFile = Join-Path $srv 'client_dir.txt'
if ((Test-Path (Join-Path $patch 'ImagineClient.exe')) -and (Test-Path $clientFile)) {
    $client = (Get-Content $clientFile -First 1).Trim()
    foreach ($pair in 'ImagineClient.exe', 'comp_client.dll') {
        $src = Join-Path $client $pair
        if (Test-Path $src) {
            Copy-Item -Force $src (Join-Path $patch $pair)
            Write-Host "included $pair (published as a pair)"
        }
    }
}

$list = @(Get-ChildItem -Recurse -File $patch)
if (-not $list.Count) { Write-Host "Nothing to publish: $patch is empty."; exit 1 }

# Fresh copy of the patch, then let comp_rehash compress it and write the list.
if (Test-Path $files) { Remove-Item -Recurse -Force $files }
Copy-Item -Recurse -Force $patch $files
Set-Content -Path (Join-Path $base 'hashlist.dat') -Value 'VERSION : 0' -Encoding ascii
& $rehash --base $base --overlay $files
if ($LASTEXITCODE -ne 0) { Write-Host 'comp_rehash failed.'; exit 1 }

$ver = (Get-Content (Join-Path $files 'hashlist.ver') -First 1).Trim()
Write-Host "Published $($list.Count) file(s), $ver"
Write-Host 'Players get them the next time they open ImagineUpdate.exe (serve_update must be running).'
