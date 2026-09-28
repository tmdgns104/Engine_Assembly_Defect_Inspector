param(
    [string]$DeviceConfig = (Join-Path $PSScriptRoot 'targets/current.json')
)

$ErrorActionPreference = 'Stop'
$device = Get-Content -LiteralPath $DeviceConfig -Encoding utf8 -Raw | ConvertFrom-Json
$target = $device.ssh_target
$keyPath = [Environment]::ExpandEnvironmentVariables($device.key_path)
if ($target -notmatch '^[a-zA-Z0-9_.-]+@[a-zA-Z0-9_.-]+$') {
    throw 'Invalid SSH target.'
}
if (-not (Test-Path -LiteralPath $keyPath -PathType Leaf)) {
    throw 'Existing SSH key is unavailable.'
}

# Only this local forward is maintained. A user-owned listener is never killed.
while ($true) {
    $listener = Get-NetTCPConnection -LocalPort 18771 -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        Start-Sleep -Seconds 3
        continue
    }
    $arguments = @(
        '-N', '-L', '18771:127.0.0.1:18771',
        '-o', 'ExitOnForwardFailure=yes', '-o', 'BatchMode=yes',
        '-o', 'ConnectTimeout=5', '-o', 'ServerAliveInterval=10',
        '-o', 'ServerAliveCountMax=2', '-i', ('"' + $keyPath + '"'), $target
    )
    $tunnel = Start-Process ssh.exe -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $tunnel.WaitForExit()
    Start-Sleep -Seconds 3
}
