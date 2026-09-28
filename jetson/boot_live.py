"""Arm the managed PLC bench runtime after a safe, empty boot scene.

Run once at OS boot through the jetson user's crontab. This process exits after
AUTO starts; it never owns the camera or writes PLC result tags.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import manage_live


def start_allowed(status):
    """Only an idle, healthy, clearly empty bench may be armed automatically."""
    service = status.get('inspection_service') or {}
    plc = status.get('plc') or {}
    area = status.get('area_occupancy') or {}
    if status.get('error') or status.get('active_cycle') is not None:
        return False, 'RUNTIME_RECOVERY_REQUIRED'
    if status.get('auto_stop_requested'):
        return False, 'OPERATOR_STOP'
    if status.get('operating'):
        return True, 'ALREADY_AUTO'
    if status.get('phase') != 'STOPPED' or service.get('active_inspection_id') is not None:
        return False, 'RUNTIME_NOT_IDLE'
    if not service.get('ready') or not service.get('camera_ready'):
        return False, 'CAMERA_OR_MODEL_NOT_READY'
    if (plc.get('backend') != 'OMRON_CIP_BENCH' or plc.get('physical_output_enabled') is not False
            or plc.get('available') is not True or plc.get('Inspection_Request') is not False
            or plc.get('state') not in ('SYNC_LOW', 'ARMED')):
        return False, 'PLC_NOT_READY_WITH_REQUEST_LOW'
    if (not status.get('area_observation_valid') or area.get('state') != 'CLEAR'
            or not area.get('reference_valid') or not (status.get('inspection_zone') or {}).get('confirmed')):
        return False, 'CURRENT_EMPTY_SCENE_REQUIRED'
    return True, 'READY'


def post_auto(port):
    token = manage_live.api(port, 'session')['token']
    request = Request(f'http://127.0.0.1:{port}/api/v1/runtime/auto/start',
                      data=b'{}', method='POST', headers={
                          'Content-Type': 'application/json',
                          'x-inspection-token': token})
    with urlopen(request, timeout=8) as response:
        return json.load(response)


def run(config, interval=10):
    import fcntl  # Linux-only boot lock; pure gate tests also run on Windows.

    settings = manage_live.read_settings(config)
    data_root = Path(settings['data_root'])
    data_root.mkdir(parents=True, exist_ok=True)
    with (data_root / 'boot_live.lock').open('a+b') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Boot arming already in progress', flush=True)
            return 0
        port = settings.get('port', 18771)
        expected = json.loads((manage_live.ROOT / 'release.json').read_text(encoding='utf-8'))['release_id']
        last_reason = None
        while True:
            try:
                release = manage_live.api(port, 'release')
            except (URLError, TimeoutError):
                try:
                    result = subprocess.run(
                        [sys.executable, '-B', '-X', 'utf8', str(manage_live.ROOT / 'manage_live.py'),
                         'start', '--config', str(config)], cwd=manage_live.ROOT,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=130,
                        check=False)
                    reason = 'WAITING_FOR_CAMERA_OR_RUNTIME' if result.returncode else 'RUNTIME_STARTED'
                except subprocess.TimeoutExpired:
                    reason = 'MANAGED_START_TIMEOUT'
            else:
                if (release.get('release_id') != expected
                        or release.get('runtime_path') != str(manage_live.ROOT)
                        or release.get('backend') != 'OMRON_CIP_BENCH'
                        or release.get('physical_output_enabled') is not False):
                    raise RuntimeError('WRONG_RUNTIME_RELEASE_OR_GATEWAY_ON_PORT')
                try:
                    status = manage_live.api(port, 'runtime/status')
                except (HTTPError, URLError, TimeoutError):
                    reason = 'WAITING_FOR_RUNTIME_STATUS'
                else:
                    allowed, reason = start_allowed(status)
                    if reason == 'OPERATOR_STOP':
                        print('Automatic arming cancelled by operator STOP', flush=True)
                        return 0
                    if reason == 'ALREADY_AUTO':
                        print(f'AUTO already active: {expected}', flush=True)
                        return 0
                    if allowed:
                        try:
                            result = post_auto(port)
                        except (HTTPError, URLError, TimeoutError):
                            reason = 'AUTO_START_REJECTED_BY_RUNTIME'
                        else:
                            if result.get('operating') is True:
                                print(f'AUTO armed after boot: {expected}', flush=True)
                                return 0
                            reason = 'AUTO_START_NOT_ACTIVE'
            if reason != last_reason:
                print(reason, flush=True)
                last_reason = reason
            time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    return run(args.config.resolve())


if __name__ == '__main__':
    raise SystemExit(main())
