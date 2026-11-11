# Serves <server dir>\update\files over HTTP for the game launcher.
#
#   serve_update.ps1 [-Port 10080]
#
# start_server.ps1 starts this in the background when there is something
# published, and stop_server.ps1 stops it. Launchers are pointed at it with
# set_update_url.ps1. Other PCs need TCP 10080 open (allow_lan_firewall.ps1).
param([int]$Port = 10080)
. "$PSScriptRoot\common.ps1"

$root = [IO.Path]::GetFullPath((Join-Path $ServerDir 'update\files'))
$log  = Join-Path $ServerDir 'logs\update_server.log'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $log) | Out-Null
function Log($t) { "$(Get-Date -Format s) $t" | Out-File -FilePath $log -Append -Encoding utf8 }

$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Any, $Port)
$listener.Start()
Log "serving $root on port $Port"

function Send($stream, [int]$code, [string]$status, [byte[]]$body) {
    $head = "HTTP/1.1 $code $status`r`nContent-Type: application/octet-stream`r`n" +
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
        $rel = [Uri]::UnescapeDataString(($Matches[1] -split '\?')[0]).TrimStart('/') -replace '/+', '\'
        $path = [IO.Path]::GetFullPath((Join-Path $root $rel))
        if (-not $path.StartsWith($root, [StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $path -PathType Leaf)) {
            Send $stream 404 'Not Found' @()
            Log "$peer 404 /$rel"
        } else {
            Send $stream 200 'OK' ([IO.File]::ReadAllBytes($path))
            Log "$peer 200 /$rel"
        }
    } catch {
        Log "error: $_"
    } finally {
        $tcp.Close()
    }
}
