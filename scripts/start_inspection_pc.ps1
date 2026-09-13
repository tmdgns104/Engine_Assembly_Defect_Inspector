param([string]$Target = 'jetson@192.168.50.2')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$dataRoot = Join-Path $projectRoot 'runs/inspection_app_v1/pc'
$keyPath = Join-Path $env:USERPROFILE '.ssh/oned_device_jetson_bench_ed25519'
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
$tokenPath = Join-Path $dataRoot 'collector.token'
New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null
if (!(Test-Path -LiteralPath $tokenPath)) { throw 'Collector token is not provisioned. Follow INSPECTION_APP.md.' }
if (Get-NetTCPConnection -LocalPort 8769 -State Listen -ErrorAction SilentlyContinue) { throw 'Port 8769 already has a listener; verify the existing collector.' }
$stamp = Get-Date -Format 'yyyyMMddTHHmmssfff'
$process = Start-Process $pythonPath -WindowStyle Hidden -WorkingDirectory $projectRoot -ArgumentList @('-B','-X','utf8','-u','-m','apps.pc_service.collector_api','--data-root',$dataRoot,'--token-file',$tokenPath) -RedirectStandardOutput (Join-Path $dataRoot "collector.$stamp.out.log") -RedirectStandardError (Join-Path $dataRoot "collector.$stamp.err.log") -PassThru
$process.Id | Set-Content (Join-Path $dataRoot 'collector.pid') -Encoding UTF8
$tunnel = Start-Process ssh.exe -WindowStyle Hidden -ArgumentList @('-N','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','ExitOnForwardFailure=yes','-i',$keyPath,'-R','127.0.0.1:18769:127.0.0.1:8769',$Target) -RedirectStandardError (Join-Path $dataRoot "tunnel.$stamp.err.log") -PassThru
$tunnel.Id | Set-Content (Join-Path $dataRoot 'tunnel.pid') -Encoding UTF8
Write-Output "PC collector PID $($process.Id), reverse tunnel PID $($tunnel.Id). Check http://127.0.0.1:8769/api/v1/status."
