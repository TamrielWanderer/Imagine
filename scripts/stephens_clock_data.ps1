# Adds the Stephen's Clock items and countdown to the client data, see
# contrib\roguelike\stephens_clock_data.py and docs\stephens-clock.md.
#
#   stephens_clock_data.ps1 [-Check] [-Remove] [-ClientDir "D:/Games/ReIMAGINE"]
#
# Edits ItemData.sbin, CItemData.sbin and TimeLimitData.sbin in
# <client>\BinaryData\Shield, which both the server and the client read.
# Restart the server afterwards, and publish the files with
#   publish_update.bat -Add BinaryData\Shield\ItemData.sbin,BinaryData\Shield\CItemData.sbin,BinaryData\Shield\TimeLimitData.sbin
# Run it again after apply_translation or stack_sizes (they rebuild the
# item files and drop the clock items).
param(
    [switch]$Check,
    [switch]$Remove,
    [string]$ClientDir = ''
)
. "$PSScriptRoot\common.ps1"

if (-not $ClientDir) {
    $clientFile = Join-Path $ServerDir 'client_dir.txt'
    if (Test-Path $clientFile) { $ClientDir = (Get-Content $clientFile -First 1).Trim() }
}
if (-not $ClientDir -or -not (Test-Path (Join-Path $ClientDir 'BinaryData'))) {
    Write-Host 'Client folder not found. Pass -ClientDir <folder that contains BinaryData>.'
    exit 1
}

$tools = Join-Path (Get-BuildDir) 'bin\Release'
$script = Join-Path $RepoRoot 'contrib\roguelike\stephens_clock_data.py'
$pyArgs = @($script, '--client', $ClientDir, '--tools', $tools)
if ($Check) { $pyArgs += '--check' }
if ($Remove) { $pyArgs += '--remove' }

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 @pyArgs
} else {
    & python @pyArgs
}
exit $LASTEXITCODE
