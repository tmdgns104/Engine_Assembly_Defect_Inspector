#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
app_root="$PWD"
package_root="${INSPECTION_PACKAGE_ROOT:-$app_root/deployment/products/earbud_case_v0/app_v001}"
data_root="${INSPECTION_DATA_ROOT:-$HOME/oned_device_bench/data/app_v1}"
python_path="${INSPECTION_PYTHON:-$HOME/oned_device_bench/envs/app_v1/bin/python}"
mkdir -p "$data_root/logs"
if [[ -f "$data_root/service.pid" ]] && kill -0 "$(cat "$data_root/service.pid")" 2>/dev/null; then
  echo 'Recorded process is still alive. Verify its state before restart.'; exit 1
fi
stamp="$(date -u +%Y%m%dT%H%M%S%N)"
if [[ -f "$data_root/service.pid" ]]; then cp "$data_root/service.pid" "$data_root/logs/service.$stamp.previous.pid"; fi
collector_args=()
if [[ -f "$data_root/collector.token" ]]; then
  collector_args=(--collector-url http://127.0.0.1:18769 --collector-token-file "$data_root/collector.token")
fi
nohup "$python_path" -B -u -m apps.edge_service.inspection_api --package "$package_root" --station "$app_root/config/inspection_station.json" --data-root "$data_root" --port 8768 "${collector_args[@]}" > "$data_root/logs/service.$stamp.log" 2>&1 < /dev/null &
echo "$!" > "$data_root/service.pid"
echo "Started Service PID $!; verify /api/v1/health before use."
