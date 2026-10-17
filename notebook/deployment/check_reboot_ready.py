"""Check stopped restart readiness, including persisted product-context closure.

Run on Jetson with its standard-library Python. Read-only by default; --reboot
requires the operator's normal sudo authentication. Never closes product context,
creates an inspection, changes a result, or commands conveyor motion.
"""
import argparse
import json
from pathlib import Path
import subprocess
import urllib.request


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def validate_ready(status, view):
    try:
        plc = status['plc']['snapshot']
        service = status['inspection_service']
        assembly = status['assembly_component']
        cycle = status['plc_cycle']
        require(cycle['product_identity_reason'] is None
                and cycle['request_identity_block'] is None, 'PRODUCT_CONTEXT_NOT_SETTLED')
        require(all(plc[k] is True for k in ('connected', 'fresh', 'bool_valid', 'run_idle'))
                and plc['raw100'] == '00000000'
                and plc['phase'] in ('SYNC_LOW', 'DISARMED')
                and plc['controls'] == dict(Inspection_Request=False, Mc_Run=False,
                    EStop_OK=True, Stop_PB=True), 'FRESH_STOPPED_NO_OUTPUT_REQUIRED')
        require(service['state'] == 'IDLE' and service['worker_alive'] is True
                and service['camera_ready'] is True and service['error'] is None
                and service['active_inspection_id'] is None and service['storage_pending'] is False
                and status['final_commit_pending'] is False, 'IDLE_CAMERA_AND_STORAGE_REQUIRED')
        require(assembly['ready'] is True and assembly['error'] is None
                and assembly['outstanding'] == 0 and assembly['active_identifier'] is None,
                'IDLE_MODEL_REQUIRED')
        require(status['runtime_loop_alive'] is True and status['error'] is None
                and status['runtime_issue'] is None and status['aborted_inspection'] is None
                and status['ipc_health']['latest']['IPC_HEALTH_SENT']['ready'] is True,
                'RUNTIME_HEALTH_REQUIRED')
        require(cycle['reason'] == 'WAIT_NEW_PHYSICAL_START' and view['phase'] == 'WAIT_START'
                and view['camera']['fresh'] is True, 'START_READY_SCREEN_REQUIRED')
    except (KeyError, TypeError) as exc:
        raise ValueError('INCOMPLETE_READINESS_EVIDENCE') from exc


def observe():
    def get(path):
        with urllib.request.urlopen('http://127.0.0.1:18771' + path, timeout=8) as response:
            return json.load(response)
    status = get('/api/v1/runtime/status')
    view = get('/api/v1/line/view')
    validate_ready(status, view)
    return status, view


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reboot', action='store_true')
    parser.add_argument('--evidence', required=True, type=Path)
    args = parser.parse_args()
    require(Path('/proc/sys/kernel/random/boot_id').is_file(), 'JETSON_LINUX_REQUIRED')
    require(not args.evidence.exists(), 'EVIDENCE_MUST_NOT_BE_OVERWRITTEN')
    if args.reboot:
        subprocess.run(['sudo', '-n', '-v'], check=True)
    status, view = observe()
    record = dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  status=status, view=view, reboot_requested=args.reboot)
    with args.evidence.open('x', encoding='utf-8') as output:
        json.dump(record, output, ensure_ascii=False, indent=2)
    print(json.dumps(dict(ready=True, boot_id=record['boot_id'], title=view['title'],
                          product_identity_reason=None)), flush=True)
    if args.reboot:
        observe()  # Recheck immediately before the privileged command.
        subprocess.run(['sudo', '-n', 'systemctl', 'reboot'], check=True)


if __name__ == '__main__':
    main()
