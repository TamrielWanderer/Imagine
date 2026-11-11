# Points a game client's launcher (ImagineUpdate.exe) at your update server.
#
#   set_update_url.ps1                          # this PC's client, this PC's server
#   set_update_url.ps1 -ClientDir D:\Games\ReIMAGINE -Url http://192.168.0.149:10080/
#   set_update_url.ps1 -Restore                 # back to the official ReIMAGINE updates
#
# The original ImagineUpdate.dat is saved once as ImagineUpdate.dat.reimagine.
# On another PC, copy this script there (or edit BaseURL1 in ImagineUpdate.dat
# by hand to the same address).
param(
    [string]$ClientDir = '',
    [string]$Url = '',
    [switch]$Restore
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"

if (-not $ClientDir) {
    $clientFile = Join-Path $ServerDir 'client_dir.txt'
    if (Test-Path $clientFile) { $ClientDir = (Get-Content $clientFile -First 1).Trim() }
}
$dat = Join-Path $ClientDir 'ImagineUpdate.dat'
if (-not (Test-Path $dat)) { Write-Host "ImagineUpdate.dat not found in '$ClientDir'. Pass -ClientDir."; exit 1 }
$orig = "$dat.reimagine"
if (-not (Test-Path $orig)) { Copy-Item $dat $orig }

if ($Restore) {
    Copy-Item -Force $orig $dat
    Write-Host 'Restored the original ImagineUpdate.dat.'
    exit 0
}

if (-not $Url) {
    $ip = '127.0.0.1'
    $lanFile = Join-Path $ServerDir 'lan_ip.txt'
    if (Test-Path $lanFile) { $ip = (Get-Content $lanFile -First 1).Trim() }
    $Url = "http://${ip}:10080/"
}

$text = Get-Content -Raw $dat
$text = $text -replace '(?m)^BaseURL1\s*=.*$', "BaseURL1 = $Url"
Set-Content -Path $dat -Value $text.TrimEnd() -Encoding ascii -NoNewline
Write-Host "ImagineUpdate.exe in $ClientDir now updates from $Url"
