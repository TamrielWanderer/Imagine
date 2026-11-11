# Starts the game client from the folder start_server.ps1 remembered
# (<server dir>/client_dir.txt), or from -ClientDir.
# The client must be COMP_hack-patched (comp_client.dll) and its
# ImagineClient.dat must contain "-ip 127.0.0.1" and "-port 10666".
param([string]$ClientDir = '')
. "$PSScriptRoot\common.ps1"

$clientFile = Join-Path $ServerDir 'client_dir.txt'
if (-not $ClientDir -and (Test-Path $clientFile)) { $ClientDir = (Get-Content $clientFile -First 1).Trim() }
$exe = Join-Path $ClientDir 'ImagineClient.exe'
if (-not (Test-Path $exe)) {
    Write-Host 'ImagineClient.exe not found. Run: start_client.ps1 -ClientDir <client folder>'
    exit 1
}
Start-Process -FilePath $exe -WorkingDirectory $ClientDir
