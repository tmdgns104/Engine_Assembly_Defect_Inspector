#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
pid="$(cat runs/bench_live/service.pid)"
[[ "$pid" =~ ^[0-9]+$ ]] || exit 1
if ! kill -0 "$pid" 2>/dev/null; then echo 'Recorded process is not running'; exit 0; fi
[[ "$(readlink /proc/"$pid"/cwd)" == "$PWD" ]] || { echo 'PID working directory mismatch'; exit 1; }
tr '\0' ' ' < /proc/"$pid"/cmdline | grep -q 'apps.edge_service.bench' || { echo 'PID command mismatch'; exit 1; }
kill -TERM "$pid"
for i in {1..20}; do
  if ! kill -0 "$pid" 2>/dev/null; then echo 'BENCH stopped'; exit 0; fi
  if [[ "$(awk '{print $3}' /proc/"$pid"/stat 2>/dev/null)" == Z ]]; then echo 'BENCH exited'; exit 0; fi
  sleep 0.5
done
echo 'Stop pending; process did not exit within 10 seconds. Do not launch another owner.'
exit 1
