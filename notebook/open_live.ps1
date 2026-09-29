param(
    [switch]$NoBrowser,
    [string]$DeviceConfig = (Join-Path $PSScriptRoot 'deployment/targets/current.json'),
    [string]$FallbackDeviceConfig = (Join-Path $PSScriptRoot 'deployment/targets/remote_tailscale.json')
)

$ErrorActionPreference = 'Stop'
$url = 'http://127.0.0.1:18771/auto'
$releaseUrl = 'http://127.0.0.1:18771/api/v1/release'

function Get-Device([string]$configPath) {
    $device = Get-Content -LiteralPath $configPath -Encoding utf8 -Raw | ConvertFrom-Json
    $keyPath = [Environment]::ExpandEnvironmentVariables($device.key_path)
    if ($device.ssh_target -notmatch '^[a-zA-Z0-9_.-]+@[a-zA-Z0-9_.-]+$' -or
        $device.remote_base -notmatch '^/[a-zA-Z0-9_./-]+$' -or $device.remote_base.Contains('..')) {
        throw "Invalid device target or remote path: $configPath"
    }
    if (-not (Test-Path -LiteralPath $keyPath -PathType Leaf)) {
        throw "Existing SSH key is unavailable: $configPath"
    }
    return [pscustomobject]@{
        Target = $device.ssh_target
        Base = $device.remote_base
        KeyPath = $keyPath
    }
}

function Get-RemoteRelease($device) {
    $base = $device.Base
    $remoteCommand = "$base/envs/app_v1/bin/python -B -X utf8 $base/current/manage_live.py start --config $base/config/runtime.json"
    # An unreachable primary is expected when working outside the wired LAN.
    $ErrorActionPreference = 'Continue'
    $output = & ssh.exe -i $device.KeyPath -o BatchMode=yes -o ConnectTimeout=5 `
        -o StrictHostKeyChecking=yes $device.Target $remoteCommand 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    try { return ($output | Select-Object -Last 1 | ConvertFrom-Json).release }
    catch { return $null }
}

function Get-LocalRelease {
    try { return Invoke-RestMethod $releaseUrl -TimeoutSec 2 }
    catch { return $null }
}

function Open-VerifiedScreen {
    Write-Output $url
    if (-not $NoBrowser) { Start-Process $url }
}

$paths = @($DeviceConfig)
if ((Test-Path -LiteralPath $FallbackDeviceConfig -PathType Leaf) -and
    [IO.Path]::GetFullPath($FallbackDeviceConfig) -ne [IO.Path]::GetFullPath($DeviceConfig)) {
    $paths += $FallbackDeviceConfig
}
$selected = $null
$identity = $null
foreach ($path in $paths) {
    $device = Get-Device $path
    $remote = Get-RemoteRelease $device
    if ($remote -and $remote.runtime_path -eq "$($device.Base)/current") {
        $selected = $device
        $identity = $remote
        break
    }
}
if (-not $identity) { throw 'Jetson is not reachable through either configured address.' }

$local = Get-LocalRelease
if ($local.runtime_path -eq $identity.runtime_path -and $local.release_id -eq $identity.release_id) {
    Open-VerifiedScreen
    return
}

$tunnelTask = Get-ScheduledTask -TaskName 'OneDeviceEngineTunnel' -ErrorAction SilentlyContinue
if ($tunnelTask) {
    if ($tunnelTask.State -ne 'Running') { Start-ScheduledTask -TaskName 'OneDeviceEngineTunnel' }
} else {
    $arguments = @('-N', '-L', '18771:127.0.0.1:18771', '-o', 'ExitOnForwardFailure=yes',
        '-o', 'BatchMode=yes', '-o', 'ServerAliveInterval=15',
        '-i', ('"' + $selected.KeyPath + '"'), $selected.Target)
    Start-Process ssh.exe -ArgumentList $arguments -WindowStyle Hidden | Out-Null
}

for ($attempt = 0; $attempt -lt 40; $attempt++) {
    $local = Get-LocalRelease
    if ($local.runtime_path -eq $identity.runtime_path -and $local.release_id -eq $identity.release_id) {
        Open-VerifiedScreen
        return
    }
    Start-Sleep -Milliseconds 500
}
throw 'Local URL did not reach the selected current release.'
