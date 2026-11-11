# Opens the local server to other PCs on your network (Windows Firewall).
# Run it yourself as administrator (right-click PowerShell > Run as administrator):
#
#   powershell -ExecutionPolicy Bypass -File scripts\allow_lan_firewall.ps1          # allow
#   powershell -ExecutionPolicy Bypass -File scripts\allow_lan_firewall.ps1 -Remove  # undo
#
# What it does:
#  - removes Block rules Windows created for comp_lobby/comp_world/comp_channel
#    (made when a firewall prompt for them was cancelled; Block beats Allow)
#  - adds one Allow rule "Imagine local server" for TCP 10666 (lobby),
#    14666 (channel), 10999 (lobby web API) and 10080 (launcher updates,
#    serve_update.ps1), for Private networks only.
#    Your network must be set to Private in Windows settings for it to apply.
param([switch]$Remove)

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { Write-Host 'Run this from an administrator PowerShell.'; exit 1 }

$ruleName = 'Imagine local server'
Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
if ($Remove) { Write-Host "Removed '$ruleName'."; exit 0 }

# Block rules for the server programs (from a cancelled firewall prompt).
$blocks = Get-NetFirewallRule -Direction Inbound -Action Block -ErrorAction SilentlyContinue | Where-Object {
    $app = ($_ | Get-NetFirewallApplicationFilter).Program
    $app -match 'comp_(lobby|world|channel)\.exe$'
}
foreach ($r in $blocks) {
    Write-Host "Removing block rule: $($r.DisplayName) ($(($r | Get-NetFirewallApplicationFilter).Program))"
    $r | Remove-NetFirewallRule
}

New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP `
    -LocalPort 10666, 14666, 10999, 10080 -Profile Private | Out-Null
Write-Host "Added '$ruleName' (TCP 10666, 14666, 10999, 10080, Private networks)."

$profiles = Get-NetConnectionProfile | ForEach-Object { "$($_.InterfaceAlias): $($_.NetworkCategory)" }
Write-Host "Network profile(s): $($profiles -join ', ')"
if (Get-NetConnectionProfile | Where-Object { $_.NetworkCategory -eq 'Public' }) {
    Write-Host 'Your network is set to Public; switch it to Private in Settings > Network for the rule to apply.'
}
