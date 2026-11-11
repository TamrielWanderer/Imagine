# Creates a new account on the running local lobby through its web API
# (POST http://127.0.0.1:10999/api/account/register).
#
#   create_test_account.ps1 [-Username name]
#
# Without -Username a random "testerXXXX" name is used. The password is random.
# The credentials are saved to <server dir>/test_account.txt (not printed).
param([string]$Username = '')
. "$PSScriptRoot\common.ps1"

$chars = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
if (-not $Username) {
    $Username = 'tester' + (-join (1..4 | ForEach-Object { 'abcdefghjkmnpqrstuvwxyz23456789'[(Get-Random -Maximum 31)] }))
}
$Username = $Username.ToLower()   # lobby rule: ^[a-z][a-z0-9]{3,31}$
$password = -join (1..12 | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
$body = @{ username = $Username; email = "$Username@localhost.test"; password = $password } | ConvertTo-Json

try {
    $r = Invoke-RestMethod -Uri 'http://127.0.0.1:10999/api/account/register' -Method Post `
        -Body $body -ContentType 'application/json' -TimeoutSec 20
    $result = $r.error
} catch {
    $result = "request failed: $($_.Exception.Message) (is the server running?)"
}

if ($result -eq 'Success') {
    New-Item -ItemType Directory -Force -Path $ServerDir | Out-Null
    $file = Join-Path $ServerDir 'test_account.txt'
    @("Local test account (created $(Get-Date -Format s))", "Username: $Username", "Password: $password") |
        Set-Content -Path $file -Encoding utf8
    Write-Host "Account '$Username' created. Username and password saved to $file"
} else {
    Write-Host "Account not created: $result"
    exit 1
}
