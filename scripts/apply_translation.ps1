# Translates the game client's menus and system text to English, using the
# table in contrib\translation (see contrib\translation\README.md).
#
#   apply_translation.ps1 [-ClientDir "D:/Games/ReIMAGINE"] [-Check]
#
# Needs Python 3 (the "py" launcher) and a build (comp_decrypt, comp_encrypt
# and comp_bdpatch). The client folder defaults to the one start_server.ps1
# remembered. Originals are kept in <client>\BinaryData_jp_backup.
# Afterwards, publish the changed files with publish_update.ps1 so other
# players' launchers download them.
param(
    [string]$ClientDir = '',
    [switch]$Check
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
$script = Join-Path $RepoRoot 'contrib\translation\apply_translation.py'
$pyArgs = @($script, '--client', $ClientDir, '--tools', $tools)
if ($Check) { $pyArgs += '--check' }

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 @pyArgs
} else {
    & python @pyArgs
}
exit $LASTEXITCODE
