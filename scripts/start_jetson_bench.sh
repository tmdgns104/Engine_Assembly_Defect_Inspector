#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p runs/bench_live
if [[ -f runs/bench_live/service.pid ]] && kill -0 "$(cat runs/bench_live/service.pid)" 2>/dev/null; then
  echo 'Existing recorded process is alive; inspect it before restarting.'
  exit 1
fi
stamp="$(date -u +%Y%m%dT%H%M%S%N)"
if [[ -f runs/bench_live/service.pid ]]; then
  cp runs/bench_live/service.pid "runs/bench_live/service.$stamp.previous.pid"
fi
nohup python3 -B -u -m apps.edge_service.bench --model best.pt --config config/earbud_bench.json --output runs/bench_live/inspections --port 8767 > "runs/bench_live/service.$stamp.log" 2>&1 < /dev/null &
echo "$!" > runs/bench_live/service.pid
echo "Started PID $!; readiness must be checked at http://127.0.0.1:8767/api/status"
