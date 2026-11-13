# Builds KeyConfigTool.exe (the keys / extra bars / macros editor,
# contrib\tools\key_config_tool.py) as one stand-alone program, so players
# don't need Python, puts it in the client folder and publishes it with the
# updater so every player's launcher downloads it.
#
#   build_key_config_tool.ps1 [-NoPublish]
#
# Needs Python 3 on this PC (only here, not on the players' PCs); PyInstaller
# is installed for the current user the first time.
param([switch]$NoPublish)
. "$PSScriptRoot\common.ps1"

$clientFile = Join-Path $ServerDir 'client_dir.txt'
if (-not (Test-Path $clientFile)) { Write-Host 'Unknown client folder: run start_server.ps1 -ClientDir <folder> once.'; exit 1 }
$client = (Get-Content $clientFile -First 1).Trim()

$py = $null
if (Get-Command py -ErrorAction SilentlyContinue) { $py = @('py', '-3') }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $py = @('python') }
if (-not $py) { Write-Host 'Python 3 was not found (https://www.python.org/downloads/).'; exit 1 }
$pyExe = $py[0]; $pyArgs = @($py | Select-Object -Skip 1)

Write-Host 'Installing/updating PyInstaller...'
& $pyExe @pyArgs -m pip install --user --disable-pip-version-check --quiet pyinstaller
if ($LASTEXITCODE) { Write-Host 'pip failed.'; exit 1 }

$work = Join-Path $ServerDir 'key_config_tool_build'
New-Item -ItemType Directory -Force -Path $work | Out-Null
$src = Join-Path $RepoRoot 'contrib\tools\key_config_tool.py'
Write-Host 'Building KeyConfigTool.exe...'
& $pyExe @pyArgs -m PyInstaller --noconfirm --onefile --windowed --name KeyConfigTool `
    --distpath (Join-Path $work 'dist') --workpath (Join-Path $work 'build') `
    --specpath $work $src
if ($LASTEXITCODE) { Write-Host 'PyInstaller failed.'; exit 1 }

$exe = Join-Path $work 'dist\KeyConfigTool.exe'
Copy-Item $exe (Join-Path $client 'KeyConfigTool.exe') -Force
Write-Host "Copied to $client\KeyConfigTool.exe"

if (-not $NoPublish) {
    & (Join-Path $PSScriptRoot 'publish_update.ps1') -Add KeyConfigTool.exe
}
