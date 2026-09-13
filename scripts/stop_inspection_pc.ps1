$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$dataRoot = Join-Path $projectRoot 'runs/inspection_app_v1/pc'
foreach ($name in @('collector','tunnel')) {
    $pidPath = Join-Path $dataRoot "$name.pid"
    if (!(Test-Path -LiteralPath $pidPath)) { continue }
    $recordedPid = [int](Get-Content -LiteralPath $pidPath -Encoding UTF8)
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$recordedPid"
    if (!$process) { continue }
    $expected = if ($name -eq 'collector') { 'apps.pc_service.collector_api' } else { '127.0.0.1:18769:127.0.0.1:8769' }
    if (!$process.CommandLine.Contains($expected)) { throw "$name PID ownership mismatch" }
    Stop-Process -Id $recordedPid
    Write-Output "$name stopped: $recordedPid"
}
