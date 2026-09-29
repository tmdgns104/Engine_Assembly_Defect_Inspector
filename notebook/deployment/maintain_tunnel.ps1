param(
    [string]$DeviceConfig = (Join-Path $PSScriptRoot 'targets/current.json'),
    [string]$FallbackDeviceConfig = (Join-Path $PSScriptRoot 'targets/remote_tailscale.json'),
    [int]$LocalPort = 18771
)

$ErrorActionPreference = 'Stop'
$localPort = $LocalPort
$remotePort = 18771
$localReleaseUrl = "http://127.0.0.1:$localPort/api/v1/release"

function Read-Target([string]$configPath) {
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
        Address = $device.ssh_target
        KeyPath = $keyPath
        RuntimePath = "$($device.remote_base)/current"
    }
}

function Test-LocalRelease($target) {
    try {
        $release = Invoke-RestMethod $localReleaseUrl -TimeoutSec 2
        return $release.runtime_path -eq $target.RuntimePath -and [bool]$release.release_id
    } catch {
        return $false
    }
}

function Test-PrimarySsh($target) {
    # Windows PowerShell can promote native stderr to an exception under Stop.
    $ErrorActionPreference = 'Continue'
    & ssh.exe -i $target.KeyPath -o BatchMode=yes -o ConnectTimeout=3 `
        -o StrictHostKeyChecking=yes $target.Address 'true' 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
}

function Stop-OwnedTunnel($tunnel) {
    if ($null -ne $tunnel) {
        $tunnel.Refresh()
        if (-not $tunnel.HasExited) {
            Stop-Process -Id $tunnel.Id
            $tunnel.WaitForExit()
        }
        $tunnel.Dispose()
    }
}

$targets = @((Read-Target $DeviceConfig))
if ((Test-Path -LiteralPath $FallbackDeviceConfig -PathType Leaf) -and
    [IO.Path]::GetFullPath($FallbackDeviceConfig) -ne [IO.Path]::GetFullPath($DeviceConfig)) {
    $fallback = Read-Target $FallbackDeviceConfig
    if ($fallback.Address -ne $targets[0].Address) { $targets += $fallback }
}

# One loopback port has one owner. Try wired LAN first, then Tailscale.
# Never stop a listener that this script did not start.
while ($true) {
    if (Get-NetTCPConnection -LocalPort $localPort -State Listen -ErrorAction SilentlyContinue) {
        Start-Sleep -Seconds 3
        continue
    }

    foreach ($target in $targets) {
        if (Get-NetTCPConnection -LocalPort $localPort -State Listen -ErrorAction SilentlyContinue) { break }
        $arguments = @(
            '-N', '-L', "${localPort}:127.0.0.1:${remotePort}",
            '-o', 'ExitOnForwardFailure=yes', '-o', 'BatchMode=yes',
            '-o', 'ConnectTimeout=5', '-o', 'ServerAliveInterval=10',
            '-o', 'ServerAliveCountMax=2', '-i', ('"' + $target.KeyPath + '"'),
            $target.Address
        )
        $tunnel = $null
        try {
            $tunnel = Start-Process ssh.exe -ArgumentList $arguments -WindowStyle Hidden -PassThru
            $ready = $false
            for ($attempt = 0; $attempt -lt 12; $attempt++) {
                $tunnel.Refresh()
                if ($tunnel.HasExited) { break }
                if (Test-LocalRelease $target) { $ready = $true; break }
                Start-Sleep -Milliseconds 500
            }
            if (-not $ready) { continue }

            $failedHealthChecks = 0
            $primaryChecks = 0
            $lastPrimaryCheck = [datetime]::MinValue
            while ($true) {
                Start-Sleep -Seconds 3
                $tunnel.Refresh()
                if ($tunnel.HasExited) { break }
                if (Test-LocalRelease $target) { $failedHealthChecks = 0 }
                else { $failedHealthChecks++ }
                if ($failedHealthChecks -ge 3) { break }

                if ($target.Address -ne $targets[0].Address -and
                    ((Get-Date) - $lastPrimaryCheck).TotalSeconds -ge 15) {
                    $lastPrimaryCheck = Get-Date
                    if (Test-PrimarySsh $targets[0]) { $primaryChecks++ }
                    else { $primaryChecks = 0 }
                    if ($primaryChecks -ge 2) { break }
                }
            }
        } finally {
            Stop-OwnedTunnel $tunnel
        }
        # A failed path does not block the other one.
    }
    Start-Sleep -Seconds 3
}
