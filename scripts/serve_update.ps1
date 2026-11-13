# Serves <server dir>\update\files over HTTP for the game launcher, and the
# launcher banner page (/updatebanner/, from <server dir>\updatebanner, which
# is copied from contrib\updatebanner the first time; edit news.json there).
#
#   serve_update.ps1 [-Port 10080]
#
# start_server.ps1 starts this in the background when there is something
# published, and stop_server.ps1 stops it. Launchers are pointed at it with
# set_update_url.ps1. Other PCs need TCP 10080 open (allow_lan_firewall.ps1).
param([int]$Port = 10080)
. "$PSScriptRoot\common.ps1"

$root = [IO.Path]::GetFullPath((Join-Path $ServerDir 'update\files'))
New-Item -ItemType Directory -Force -Path $root | Out-Null
$banner = [IO.Path]::GetFullPath((Join-Path $ServerDir 'updatebanner'))
if (-not (Test-Path $banner)) {
    Copy-Item -Recurse (Join-Path $RepoRoot 'contrib\updatebanner') $banner
}
$types = @{ '.html' = 'text/html; charset=utf-8'; '.htm' = 'text/html; charset=utf-8';
            '.css' = 'text/css'; '.js' = 'application/javascript'; '.json' = 'application/json; charset=utf-8';
            '.png' = 'image/png'; '.jpg' = 'image/jpeg'; '.jpeg' = 'image/jpeg'; '.gif' = 'image/gif';
            '.svg' = 'image/svg+xml'; '.ico' = 'image/x-icon' }
$log  = Join-Path $ServerDir 'logs\update_server.log'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $log) | Out-Null
function Log($t) { "$(Get-Date -Format s) $t" | Out-File -FilePath $log -Append -Encoding utf8 }

$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Any, $Port)
$listener.Start()
Log "serving $root on port $Port"

function Send($stream, [int]$code, [string]$status, [byte[]]$body, [string]$type = 'application/octet-stream') {
    $head = "HTTP/1.1 $code $status`r`nContent-Type: $type`r`nCache-Control: no-cache`r`n" +
            "Content-Length: $($body.Length)`r`nConnection: close`r`n`r`n"
    $h = [Text.Encoding]::ASCII.GetBytes($head)
    $stream.Write($h, 0, $h.Length)
    if ($body.Length) { $stream.Write($body, 0, $body.Length) }
}

while ($true) {
    $tcp = $listener.AcceptTcpClient()
    try {
        $tcp.ReceiveTimeout = 10000
        $stream = $tcp.GetStream()
        $reader = [IO.StreamReader]::new($stream, [Text.Encoding]::ASCII, $false, 4096, $true)
        $request = $reader.ReadLine()
        while ($true) { $l = $reader.ReadLine(); if ($null -eq $l -or $l -eq '') { break } }
        $peer = $tcp.Client.RemoteEndPoint
        if ($request -notmatch '^GET (\S+) HTTP') { Send $stream 405 'Method Not Allowed' @(); continue }
        $url = [Uri]::UnescapeDataString(($Matches[1] -split '\?')[0])
        if ($url -eq '/updatebanner') {
            $h = [Text.Encoding]::ASCII.GetBytes("HTTP/1.1 302 Found`r`nLocation: /updatebanner/`r`nContent-Length: 0`r`nConnection: close`r`n`r`n")
            $stream.Write($h, 0, $h.Length)
            continue
        }
        if ($url.EndsWith('/')) { $url += 'index.html' }
        $rel = $url.TrimStart('/') -replace '/+', '\'
        $base = $root
        if ($rel -like 'updatebanner\*') { $base = $banner; $rel = $rel.Substring('updatebanner\'.Length) }
        $path = [IO.Path]::GetFullPath((Join-Path $base $rel))
        if (-not $path.StartsWith($base, [StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $path -PathType Leaf)) {
            Send $stream 404 'Not Found' @()
            Log "$peer 404 $url"
        } else {
            $type = $types[[IO.Path]::GetExtension($path).ToLower()]
            if (-not $type) { $type = 'application/octet-stream' }
            Send $stream 200 'OK' ([IO.File]::ReadAllBytes($path)) $type
            Log "$peer 200 $url"
        }
    } catch {
        Log "error: $_"
    } finally {
        $tcp.Close()
    }
}
