"""Candidate-only entry point; a failed Runtime Gate prevents app/DB startup.

Deploy under candidates/app_v008_dev_p0_002/runtime and invoke with app_v1's
Python -B. This selects the existing overlay only for this process and children.
"""

import json
import os
from pathlib import Path
import sys


def main():
    base = Path('/home/jetson/oned_device_bench')
    candidate = base/'candidates/app_v008_dev_p0_002'
    root = Path(__file__).resolve().parents[1]
    if root != candidate/'runtime':
        raise RuntimeError('CANDIDATE_LOCATION_REQUIRED')
    gate = json.loads((candidate/'logs/runtime_gate.json').read_text(encoding='utf-8'))
    if any(gate.get(key) != 'PASS' for key in ('gate_A','gate_B','gate_C')):
        raise RuntimeError('CANDIDATE_RUNTIME_GATE_BLOCKED: no app or database startup')
    overlay = base/'env_candidates/numpy_compat_001/overlay'
    sys.path[:0] = [str(overlay),str(root)]
    os.environ.update(PYTHONDONTWRITEBYTECODE='1',YOLO_AUTOINSTALL='false',
                      YOLO_CONFIG_DIR=str(candidate/'config/ultralytics'),
                      MPLCONFIGDIR=str(candidate/'config/matplotlib'),
                      XDG_CACHE_HOME=str(candidate/'cache'),TORCH_HOME=str(candidate/'cache/torch'),
                      TMPDIR=str(candidate/'tmp'))
    os.chdir(root)
    from apps.edge_service.inspection_api import main as run_api
    sys.argv = [sys.argv[0], '--package',str(base/'releases/app_v007/deployment/products/earbud_case_v0/app_v001'),
                '--station',str(root/'config/inspection_station_candidate_p0_002.json'),
                '--data-root',str(base/'data/candidate_p0_002'), '--port','18768']
    run_api()


if __name__ == '__main__':
    main()
