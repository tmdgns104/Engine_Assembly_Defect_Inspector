param(
    [string]$DeviceConfig = (Join-Path $PSScriptRoot 'targets/current.json')
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $DeviceConfig -PathType Leaf)) {
    throw 'Create the local device configuration first.'
}
$script = (Join-Path $PSScriptRoot 'maintain_tunnel.ps1')
$name = 'OneDeviceEngineTunnel'
$user = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute (Join-Path $PSHOME 'powershell.exe') `
    -Argument ('-NoProfile -WindowStyle Hidden -File "' + $script + '" -DeviceConfig "' + $DeviceConfig + '"')
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -StartWhenAvailable `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $name
Get-ScheduledTask -TaskName $name | Select-Object TaskName, State
