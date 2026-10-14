"""Local maintenance entrypoint; never stops/restarts services or connects to PLC.

Run only after separately approved service stop. Reuses inspection_worker and its
camera pipeline; no web mutation endpoint, Runtime, Journal or gateway is created.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parent
DEVICE=Path('/home/jetson/oned_device_bench')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_approval(value, now=None):
    now=now or datetime.now(timezone.utc)
    for key in ('approved','service_transition_approved','field_stopped','no_motion'):
        if value.get(key) is not True:raise ValueError('CAPTURE_APPROVAL_REQUIRED:'+key)
    if value.get('mode')!='FIELD_RAW_CAPTURE_ONLY':raise ValueError('CAPTURE_MODE_INVALID')
    if not isinstance(value.get('human_state'),str) or not value['human_state'].strip():
        raise ValueError('HUMAN_SCENE_DECLARATION_REQUIRED')
    expires=datetime.fromisoformat(value['expires_utc'])
    if expires.tzinfo is None or not 0<(expires-now).total_seconds()<=3600:
        raise ValueError('CAPTURE_APPROVAL_EXPIRED_OR_OVERLONG')
    from src.vision.field_raw_capture import validate_field_request
    return validate_field_request(dict(value['request'],condition=value['human_state']))


def check_state(service, listeners, camera_users, publication_enabled):
    if service.get('ActiveState')!='inactive' or service.get('MainPID')!='0':
        raise RuntimeError('OPERATING_SERVICE_MUST_BE_NORMALLY_STOPPED')
    if publication_enabled is not False:raise RuntimeError('EXPLICIT_PUBLICATION_MUST_BE_DISABLED')
    if camera_users.strip():raise RuntimeError('CAMERA_ALREADY_OWNED')
    for line in listeners.splitlines():
        columns=line.split()
        if len(columns)>=5 and columns[4].rsplit(':',1)[-1] in ('2222','44818'):
            raise RuntimeError('OPENER_OR_CIP_LISTENER_PRESENT')


def verify_sources(manifest_path):
    value=json.loads(manifest_path.read_text(encoding='utf-8'))
    for row in value['candidate_files']:
        path=(ROOT/row['path']).resolve()
        if not path.is_relative_to(ROOT) or sha(path)!=row['sha256']:
            raise RuntimeError('CANDIDATE_HASH_MISMATCH:'+row['path'])
    return sha(manifest_path)


def verify_operating_baseline(manifest_path):
    value=json.loads(manifest_path.read_text(encoding='utf-8'))
    for row in value['operating_baseline_files']:
        path=(DEVICE/'current'/row['path']).resolve()
        if not path.is_relative_to(DEVICE) or sha(path)!=row['sha256']:
            raise RuntimeError('OPERATING_SOURCE_CHANGED:'+row['path'])


def preflight(config, approval):
    service_text=subprocess.check_output(['systemctl','show','engine-inspector.service',
        '-p','ActiveState','-p','MainPID'],text=True)
    service=dict(line.split('=',1) for line in service_text.splitlines() if '=' in line)
    listeners=subprocess.check_output(['ss','-lntu'],text=True)
    station_path=(DEVICE/'config'/config['station']).resolve()
    station=json.loads(station_path.read_text(encoding='utf-8'))
    camera=station['camera_device']
    # fuser return 1 means no user. Unknown errors fail closed; never kill owners.
    users=subprocess.run(['fuser',camera],text=True,capture_output=True)
    if users.returncode not in (0,1) or (users.returncode==1 and users.stderr.strip()):
        raise RuntimeError('CAMERA_OWNERSHIP_QUERY_FAILED')
    check_state(service,listeners,users.stdout,config.get('legacy_publication_enabled'))
    processes=subprocess.check_output(['ps','-eo','comm='],text=True)
    if any(name.strip().lower()=='opener' for name in processes.splitlines()):
        raise RuntimeError('OPENER_PROCESS_PRESENT')
    from src.vision.field_raw_capture import MAX_METADATA_BYTES
    from src.vision.diagnostic_capture import RESERVE_BYTES
    required_free=RESERVE_BYTES+approval['request']['max_bytes']+2*MAX_METADATA_BYTES+2*1024*1024
    if shutil.disk_usage(DEVICE/'tmp/verify').free<required_free:
        raise OSError('MAINTENANCE_DISK_RESERVE_REQUIRED')
    if approval['station_sha256']!=sha(station_path):raise RuntimeError('STATION_CHANGED')
    if station.get('auto_profile'):raise RuntimeError('CURRENT_ENGINE_WORKER_REQUIRED')
    return station,dict(service=service,camera_device=camera,station_sha256=sha(station_path),
                        no_cip_listener=True,no_camera_owner=True,no_opener_process=True,required_free_bytes=required_free)


def supervise(package, station, folder, request, context, *, worker_target=None, startup_timeout=90):
    """One child; command channel contains exactly one capture command, never inspect."""
    if worker_target is None:
        from src.vision.inspection_worker import worker_main
        worker_target=worker_main
    ctx=mp.get_context('spawn')
    commands,results,previews,products=(ctx.Queue(maxsize=n) for n in (1,8,1,2))
    stopping,cancellation,tracking=ctx.Event(),ctx.Event(),ctx.Event()
    tracking.set()  # Existing envelope observation path; no inspection is submitted.
    heartbeat=ctx.RawValue('d',time.monotonic())
    generation=uuid.uuid4().hex
    process=ctx.Process(target=worker_target,args=(str(package),station,generation,commands,
        results,previews,stopping,cancellation,heartbeat,products,tracking),daemon=True)
    events=[];baseline=[];ready_at=None;sent=False;capturing=False;terminal=None;failure=None
    started=time.monotonic()
    process.start()
    try:
        while True:
            now=time.monotonic()
            if not process.is_alive():raise RuntimeError('MAINTENANCE_WORKER_EXITED')
            if ready_at is None and now-started>startup_timeout:raise TimeoutError('WORKER_READY_TIMEOUT')
            if ready_at is not None and now-ready_at>45:raise TimeoutError('CAPTURE_SAVE_TIMEOUT')
            for channel in (results,previews,products):
                while True:
                    try:value=channel.get_nowait()
                    except queue.Empty:break
                    if value.get('type')=='fault':raise RuntimeError(value['error'])
                    if value.get('type')=='ready':
                        ready_at=now;events.append(dict(event='WORKER_READY',monotonic_s=now,generation=generation,backend=value['backend']))
                    if not sent and 'product_detection_ms' in value:baseline.append(value['product_detection_ms'])
                    status=value.get('status') if value.get('type')=='diagnostic_capture' else value.get('diagnostic_capture')
                    if status:
                        capturing=capturing or status.get('state')=='RECORDING'
                        if status.get('state') in ('SAVED','SAVED_WITH_DROPS','ERROR'):terminal=status
            if ready_at is not None and not sent and now-ready_at>=2:
                commands.put_nowait(dict(type='field_raw_capture',action='start',folder=str(folder),
                    request=request,context=dict(context,field_raw_approval=True,publication_disabled=True)))
                sent=True;events.append(dict(event='CAPTURE_COMMAND_SENT',monotonic_s=now))
            if terminal:
                if terminal['state']=='ERROR':raise RuntimeError(terminal.get('error','CAPTURE_ERROR'))
                break
            time.sleep(.01)
    except BaseException as error:
        failure=type(error).__name__+': '+str(error)
    finally:
        stopping.set();process.join(8)
        forced=process.is_alive()
        if forced:process.terminate();process.join(5)
        alive=process.is_alive()
        for channel in (commands,results,previews,products):
            channel.cancel_join_thread();channel.close()
        events.append(dict(event='WORKER_STOP',monotonic_s=time.monotonic(),forced=forced,still_alive=alive))
        report=dict(events=events,terminal=terminal,error=failure,capture_recording_seen=capturing,
            baseline_product_detection_ms=baseline,worker_pid=process.pid,generation=generation,
            camera_owner_count=1,worker_stop_confirmed=not alive,plc_writes=0,
            runtime_constructed=False,journal_opened=False,service_restart_executed=False)
        (folder/'maintenance_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        if failure or forced or alive:raise RuntimeError(failure or 'WORKER_NORMAL_CLOSE_UNCONFIRMED')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approval-file',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    config_path=DEVICE/'config/standalone.json'
    config=json.loads(config_path.read_text(encoding='utf-8'))
    overlay=(config_path.parent/config['pythonpath']).resolve()
    if not overlay.is_relative_to(DEVICE):raise RuntimeError('NONLOCAL_DEPENDENCY')
    # Same native NumPy overlay as the operating entrypoint, before importing cv2/np.
    sys.path.insert(1,str(overlay))
    approval=json.loads(args.approval_file.read_text(encoding='utf-8'))
    request=validate_approval(approval)
    digest=verify_sources(args.manifest)
    if approval['candidate_manifest_sha256']!=digest:raise RuntimeError('APPROVAL_CANDIDATE_MISMATCH')
    verify_operating_baseline(args.manifest)
    if sha(config_path)!=approval['standalone_config_sha256']:raise RuntimeError('RUNTIME_CONFIG_CHANGED')
    if config.get('plc_contract')!='LEGACY_THREE_BOOL':raise RuntimeError('OPERATING_BASELINE_CHANGED')
    if not args.execute:
        print(json.dumps({'approval':'VALID','candidate':'VERIFIED','camera_started':False}));return
    if sys.platform!='linux':raise RuntimeError('NATIVE_JETSON_MAINTENANCE_ONLY')
    import fcntl
    data_root=(config_path.parent/config['data_root']).resolve()
    if not data_root.is_relative_to(DEVICE/'data'):raise RuntimeError('DATA_ROOT_OUTSIDE_DEVICE')
    with (data_root/'standalone-owner.lock').open('a+b') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        station,state=preflight(config,approval)
        package=(config_path.parent/config['package']).resolve()
        if not package.is_relative_to(DEVICE/'assets'):raise RuntimeError('NONLOCAL_PACKAGE')
        from src.recipe.package import load_package
        package_info=load_package(package)
        if package_info.manifest_hash!=approval['package_manifest_sha256']:raise RuntimeError('PACKAGE_CHANGED')
        folder=DEVICE/'tmp/verify/field_raw_capture_014/evidence'/request['clip_id']
        folder.mkdir(parents=True,exist_ok=False)
        context=dict(approval=approval,preflight=state,source_manifest_sha256=digest,
            zone=approval['inspection_zone'],result_publication='NO_RUNTIME_NO_GATEWAY')
        (folder/'approval.json').write_text(json.dumps(context,ensure_ascii=False,indent=2),encoding='utf-8')
        try:
            report=supervise(package,station,folder,request,context)
            print(json.dumps(report,ensure_ascii=False))
        finally:
            paths=[p for p in folder.rglob('*') if p.is_file()]
            manifest=[dict(path=p.relative_to(folder).as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths)]
            (folder/'COMPLETE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    # The caller separately confirms service restoration; no automatic restart here.


if __name__=='__main__':main()
