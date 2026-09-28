param(
    [switch]$NoBrowser,
    [string]$DeviceConfig = (Join-Path $PSScriptRoot 'deployment/targets/current.json')
)
$ErrorActionPreference = 'Stop'
# 장치 주소와 키는 Git 밖의 로컬 설정으로 받는다.
$device = Get-Content -LiteralPath $DeviceConfig -Encoding utf8 -Raw | ConvertFrom-Json
$target = $device.ssh_target
$remoteBase = $device.remote_base
$keyPath = [Environment]::ExpandEnvironmentVariables($device.key_path)
if ($target -notmatch '^[a-zA-Z0-9_.-]+@[a-zA-Z0-9_.-]+$' -or
    $remoteBase -notmatch '^/[a-zA-Z0-9_./-]+$' -or $remoteBase.Contains('..')) {
    throw 'Invalid device target or remote path.'
}
if (-not (Test-Path -LiteralPath $keyPath -PathType Leaf)) { throw 'Existing SSH key is unavailable.' }
$remoteCommand = "$remoteBase/envs/app_v1/bin/python -B -X utf8 $remoteBase/current/manage_live.py start --config $remoteBase/config/runtime.json"
$remoteOutput = & ssh -i $keyPath -o BatchMode=yes $target $remoteCommand
if ($LASTEXITCODE -ne 0) { throw 'Jetson startup failed. Inspect the configured data_root/live_server.log.' }
$remote = $remoteOutput | Select-Object -Last 1 | ConvertFrom-Json
$identity = $remote.release
if ($identity.runtime_path -ne "$remoteBase/current") { throw 'Unexpected remote Runtime path.' }
$localRelease = $null
try { $localRelease = Invoke-RestMethod 'http://127.0.0.1:18771/api/v1/release' -TimeoutSec 3 } catch {}
if ($null -eq $localRelease) {
    $tunnelArgs = @('-N','-L','18771:127.0.0.1:18771','-o','ExitOnForwardFailure=yes','-o','BatchMode=yes',
              '-o','ServerAliveInterval=15','-i',('"'+$keyPath+'"'),$target)
    $tunnel = Start-Process ssh -ArgumentList $tunnelArgs -WindowStyle Hidden -PassThru
    $tunnel.Id | Set-Content -Encoding utf8 (Join-Path (Split-Path $DeviceConfig) 'live_tunnel.pid')
    for ($attempt=0; $attempt -lt 20; $attempt++) {
        try { $localRelease = Invoke-RestMethod 'http://127.0.0.1:18771/api/v1/release' -TimeoutSec 2; break }
        catch { Start-Sleep -Milliseconds 500 }
    }
}
if ($localRelease.runtime_path -ne $identity.runtime_path -or $localRelease.release_id -ne $identity.release_id) {
    throw 'Local URL does not match the selected current release.'
}
Write-Output 'http://127.0.0.1:18771/auto'
if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:18771/auto' }
