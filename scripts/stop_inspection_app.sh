#!/usr/bin/env bash
set -euo pipefail
cd "${1:-$(dirname "$0")/..}"
data_root="${INSPECTION_DATA_ROOT:-$HOME/oned_device_bench/data/app_v1}"
pid="$(cat "$data_root/service.pid")"
[[ "$pid" =~ ^[0-9]+$ ]] || exit 1
if ! kill -0 "$pid" 2>/dev/null; then echo 'Recorded process is stopped'; exit 0; fi
[[ "$(readlink /proc/"$pid"/cwd)" == "$PWD" ]] || { echo 'PID working directory mismatch'; exit 1; }
tr '\0' ' ' < /proc/"$pid"/cmdline | grep -q 'apps.edge_service.inspection_api' || { echo 'PID command mismatch'; exit 1; }
children="$(ps -o pid= --ppid "$pid" || true)"
kill -TERM "$pid"
for i in {1..30}; do
  alive=0
  for owned_pid in $pid $children; do
    if kill -0 "$owned_pid" 2>/dev/null && [[ "$(awk '{print $3}' /proc/"$owned_pid"/stat 2>/dev/null)" != Z ]]; then alive=1; fi
  done
  if [[ "$alive" == 0 ]]; then echo 'Service and recorded child processes stopped'; exit 0; fi
  sleep 0.5
done
echo 'Stop not confirmed. Do not launch another camera owner.'; exit 1
