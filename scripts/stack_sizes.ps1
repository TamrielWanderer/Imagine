# Raises the stack limit of stackable items (QoL), see contrib\qol\stack_sizes.py.
#
#   stack_sizes.ps1 [-Multiplier 10] [-Min 10] [-Max 9999] [-Check] [-Restore]
#                   [-ClientDir "D:/Games/ReIMAGINE"]
#
# Edits <client>\BinaryData\Shield\ItemData.sbin, which both the server and
# the client read. Restart the server afterwards, and publish the file with
#   publish_update.bat -Add BinaryData\Shield\ItemData.sbin
# so other players' launchers download the same limits.
param(
    [int]$Multiplier = 10,
    [int]$Min = 10,
    [int]$Max = 9999,
    [switch]$Check,
    [switch]$Restore,
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
$script = Join-Path $RepoRoot 'contrib\qol\stack_sizes.py'
$pyArgs = @($script, '--client', $ClientDir, '--tools', $tools,
            '--multiplier', $Multiplier, '--min', $Min, '--max', $Max)
if ($Check) { $pyArgs += '--check' }
if ($Restore) { $pyArgs += '--restore' }

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 @pyArgs
} else {
    & python @pyArgs
}
exit $LASTEXITCODE
