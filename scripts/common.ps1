# Shared helpers for the Windows scripts in this folder. Dot-source it:
#   . "$PSScriptRoot\common.ps1"

$RepoRoot = Split-Path -Parent $PSScriptRoot

# Folder the local server runs in: config, SQLite database, logs, account files.
# Override with IMAGINE_SERVER_DIR.
$ServerDir = if ($env:IMAGINE_SERVER_DIR) { $env:IMAGINE_SERVER_DIR } else { Join-Path $RepoRoot 'local-server' }

# Build folder: IMAGINE_BUILD_DIR, else build64, else the first build* folder
# that has a Release build of the lobby server in it.
function Get-BuildDir {
    if ($env:IMAGINE_BUILD_DIR) { return $env:IMAGINE_BUILD_DIR }
    $default = Join-Path $RepoRoot 'build64'
    if (Test-Path (Join-Path $default 'bin\Release\comp_lobby.exe')) { return $default }
    $found = Get-ChildItem -Path $RepoRoot -Directory -Filter 'build*' |
        Where-Object { Test-Path (Join-Path $_.FullName 'bin\Release\comp_lobby.exe') } |
        Select-Object -First 1
    if ($found) { return $found.FullName }
    return $default
}

function To-ForwardSlashes([string]$path) { return ($path -replace '\\', '/') }
