"""기존 managed start/stop의 단일 Runtime 버전. 다른 Python은 종료하지 않는다."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent


def read_settings(path):
    settings = json.loads(path.read_text(encoding='utf-8'))
    for name in ('package', 'station', 'data_root', 'pythonpath'):
        settings[name] = str((path.parent / settings[name]).resolve())
    if not Path(settings['pythonpath']).is_dir():
        raise ValueError('EXISTING_PYTHON_OVERLAY_REQUIRED')
    return settings


def api(port, endpoint):
    with urlopen(f'http://127.0.0.1:{port}/api/v1/{endpoint}', timeout=3) as response:
        return json.load(response)


def process_identity(pid):
    process = Path('/proc') / str(pid)
    command = (process / 'cmdline').read_bytes().split(b'\0')
    if str(ROOT / 'launch_live.py').encode() not in command:
        raise RuntimeError('PID_IDENTITY_MISMATCH')
    # PID가 재사용된 다른 세대를 종료하지 않도록 Linux 시작 tick도 기록한다.
    return (process / 'stat').read_text().rsplit(')', 1)[1].split()[19]


def assert_idle(value):
    service = value['inspection_service']
    if (value['operating'] or value['active_cycle'] is not None
            or service.get('active_inspection_id') is not None
            or service.get('diagnostic_capture', {}).get('state') in ('STARTING', 'RECORDING', 'SAVING')
            or value.get('plc', {}).get('Inspection_Request') is not False):
        raise RuntimeError('STOP_AUTO_AND_FINISH_REQUEST_INSPECTION_STORAGE_FIRST')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'stop', 'status'])
    parser.add_argument('--config', type=Path, required=True, help='코드 밖의 장치별 runtime.json')
    args = parser.parse_args()
    settings = read_settings(args.config.resolve())
    port = settings.get('port', 18771)
    data = Path(settings['data_root'])
    pid_file = data / 'managed_runtime.json'
    try:
        health = api(port, 'health')
    except URLError:
        health = None
    if health is not None:
        identity = api(port, 'release')
        if identity['runtime_path'] != str(ROOT):
            raise RuntimeError('PORT_BELONGS_TO_ANOTHER_RUNTIME')
    if args.action == 'status':
        print(json.dumps({'running': health is not None,
                          'release': identity if health else None,
                          'camera_ready': health.get('camera_ready') if health else False}))
        return
    if args.action == 'stop':
        if not pid_file.exists():
            raise RuntimeError('NO_MANAGED_PID_RECEIPT')
        record = json.loads(pid_file.read_text(encoding='utf-8'))
        try:
            start = process_identity(record['pid'])
        except FileNotFoundError:
            print('Managed process already stopped')
            return
        if start != record['start_ticks']:
            raise RuntimeError('PID_GENERATION_MISMATCH')
        if health is None:
            raise RuntimeError('STATUS_UNAVAILABLE_USE_DOCUMENTED_RECOVERY')
        assert_idle(api(port, 'runtime/status'))
        os.kill(record['pid'], signal.SIGTERM)
        print('Clean shutdown requested; wait for the Worker to release the camera')
        return
    if health is not None:
        print(json.dumps({'running': True, 'release': identity, 'camera_ready': health['camera_ready']}))
        return
    if pid_file.exists():
        previous = json.loads(pid_file.read_text(encoding='utf-8'))
        if (Path('/proc') / str(previous['pid']) / 'cmdline').exists():
            raise RuntimeError('PREVIOUS_MANAGED_PID_STILL_EXISTS')
    data.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-B', '-X', 'utf8', str(ROOT / 'launch_live.py'),
               '--package', settings['package'], '--station', settings['station'],
               '--data-root', str(data), '--port', str(port)]
    env = dict(os.environ, PYTHONPATH=settings['pythonpath'])
    subprocess.run(command + ['--check-only'], env=env, cwd=ROOT, check=True)
    with (data / 'live_server.log').open('ab') as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=log, start_new_session=True)
    pid_file.write_text(json.dumps({'pid': process.pid, 'start_ticks': process_identity(process.pid)}), encoding='utf-8')
    deadline = time.monotonic() + 100
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('RUNTIME_EXITED: inspect data_root/live_server.log')
        try:
            health = api(port, 'health')
            if health.get('error'):
                raise RuntimeError('RUNTIME_START_FAILED: ' + str(health['error']))
            if health.get('camera_ready'):
                print(json.dumps({'url': f'http://127.0.0.1:{port}/auto', 'release': api(port, 'release'),
                                  'camera_ready': True, 'auto_started': False}))
                return
        except URLError:
            pass
        time.sleep(.5)
    raise RuntimeError('START_TIMEOUT: process retained for diagnosis; inspect data_root/live_server.log')


if __name__ == '__main__':
    main()
