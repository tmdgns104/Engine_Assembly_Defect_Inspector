"""Replay saved Journal evidence through frozen assembly models, never field I/O.

Requires private row JSON and original assets supplied explicitly. Outputs are
offline evidence only; this tool neither loads a Journal DB nor publishes PLC data.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time
import traceback


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--row', type=Path, required=True)
    parser.add_argument('--assets-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    # Supported by the installed Ultralytics runtime. Only this replay process
    # is offline; no service environment or model setting is changed.
    os.environ['YOLO_OFFLINE'] = 'true'
    blocked = []

    def forbid_field_io(event, values):
        if event in ('socket.connect', 'socket.bind', 'socket.sendto'):
            if values[0].family in (socket.AF_INET, socket.AF_INET6):
                blocked.append(dict(event=event, destination=str(values[1]),
                    stack=[dict(file=f.filename, line=f.lineno, function=f.name)
                           for f in traceback.extract_stack(limit=60)]))
                raise RuntimeError('OFFLINE_REPLAY_NETWORK_FORBIDDEN')
        if event == 'open' and isinstance(values[0], (str, bytes)):
            path = str(values[0])
            if path.startswith('/dev/video') or path.endswith(('.sqlite3', '.sqlite3-wal')):
                blocked.append('open_protected_device_or_db')
                raise RuntimeError('OFFLINE_REPLAY_DEVICE_OR_DB_FORBIDDEN')

    sys.addaudithook(forbid_field_io)
    sys.path.insert(0, str(args.runtime_root.resolve()))
    from src.vision.assembly_inspection import AssemblyInspector
    from src.vision.integrated_decision import combine_decisions
    from src.vision.misassembly_shadow import verify_assets
    row_bytes = args.row.read_bytes()
    row = json.loads(row_bytes)
    result = dict(scope='OFFLINE_SAVED_FRAME_REPLAY_NOT_FIELD_CYCLE',
        inspection_id=row['inspection_id'], row_sha256=hashlib.sha256(row_bytes).hexdigest(),
        plc_output=False, camera_opened=False, operating_db_opened=False)
    started = time.monotonic()
    try:
        manifest = verify_assets(args.assets_root)
        observer = AssemblyInspector(args.data_root, args.output/'assembly',
            assets_root=args.assets_root, start=False)
        assembly = observer.process_one(row)
        import torch
        assert torch.cuda.is_available(), 'NATIVE_CUDA_REQUIRED'
        original = row['result']['observations']
        assert len(assembly['frames']) == len(original) == 3
        for observation, frame in zip(original, assembly['frames']):
            fresh = observation['freshness']
            assert frame['frame_id'] == fresh['frame_id']
            assert frame['source_pts_ns'] == fresh['source_pts_ns']
            assert frame['camera_epoch'] == fresh['camera_epoch']
            assert frame['raw_pixel_sha256'] == observation['input_pixel_sha256']
        for asset in row['result']['assets']:
            if asset['kind'] == 'raw':
                assert hashlib.sha256((args.data_root/asset['relative_path']).read_bytes()).hexdigest() == asset['sha256']
        assert args.row.read_bytes() == row_bytes
        result.update(validation='PASS', frozen_manifest_files=len(manifest['files']),
            cuda_device=torch.cuda.get_device_name(0), assembly_state=assembly['state'],
            three_frames=assembly['three_frames'],
            integrated=combine_decisions(row['decision'], assembly),
            frames=[dict(frame_id=f['frame_id'], source_pts_ns=f['source_pts_ns'],
                camera_epoch=f['camera_epoch'], raw_pixel_sha256=f['raw_pixel_sha256'],
                raw_sha256=f['raw_sha256'], evidence_validation=f['evidence_validation'],
                model_state=f['shadow_state'], preprocessing=f.get('preprocessing'),
                parts=f['parts'], timings_ms=f.get('timings_ms')) for f in assembly['frames']])
    except Exception as error:
        result.update(validation='FAIL', error=f'{type(error).__name__}:{error}', traceback=traceback.format_exc())
    result.update(elapsed_seconds=time.monotonic()-started, blocked_access=blocked)
    (args.output/'REPLAY_VERIFICATION.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('frames','three_frames','traceback')}, ensure_ascii=False))
    return 0 if result['validation'] == 'PASS' and not blocked else 1


if __name__ == '__main__':
    raise SystemExit(main())
