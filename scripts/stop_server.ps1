# Stops the local lobby, world and channel servers.
Get-Process comp_channel, comp_world, comp_lobby -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host 'Servers stopped.'
