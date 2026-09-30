"""기존 area deploy의 해시 확인·managed start 순서를 current 최초 전환에 재사용.

노트북에 보관하고 배포 중에만 Jetson tmp/deploy에 반입한다.
기존 코드/DB의 백업·정상 종료를 먼저 완료해야 한다. 이 도구는 기존 자료를
삭제하거나 Journal/환경/승인을 덮어쓰지 않는다. 실패 시 옛 managed 경로로 복귀한다.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import shutil
import socket
import subprocess
import sys
import tarfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate_bundle(archive, expected_sha):
    if digest(archive.read_bytes()) != expected_sha:
        raise ValueError('ARCHIVE_SHA256_MISMATCH')
    with tarfile.open(archive) as bundle:
        members = bundle.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)):
            raise ValueError('DUPLICATE_ARCHIVE_MEMBER')
        for member in members:
            path = PurePosixPath(member.name)
            if (path.is_absolute() or '..' in path.parts or '\\' in member.name
                    or ':' in member.name or path.parts[0] not in ('current', 'assets', 'config')):
                raise ValueError('UNSAFE_ARCHIVE_PATH')
            if member.name == 'current/config':
                if not member.issym() or member.linkname != '../assets/runtime_config':
                    raise ValueError('UNEXPECTED_CONFIG_LINK')
            elif not member.isfile():
                raise ValueError('ONLY_REGULAR_FILES_AND_CONFIG_LINK_ALLOWED')
            if member.name.startswith('current/config/'):
                raise ValueError('WRITE_THROUGH_CONFIG_LINK_FORBIDDEN')
        release = json.load(bundle.extractfile('current/release.json'))
        if (release['links'] != {'current/config': '../assets/runtime_config'}
                or release['physical_output_enabled'] is not False):
            raise ValueError('RELEASE_CONTRACT_MISMATCH')
        if set(names) != set(release['files']) | set(release['links']) | {'current/release.json'}:
            raise ValueError('ARCHIVE_MEMBERS_MISMATCH')
        for name, sha in release['files'].items():
            if digest(bundle.extractfile(name).read()) != sha:
                raise ValueError('ARCHIVE_FILE_MISMATCH: ' + name)
    return release


def require_stopped(port):
    with socket.socket() as connection:
        connection.settimeout(2)
        if connection.connect_ex(('127.0.0.1', port)) == 0:
            raise RuntimeError('STOP_EXISTING_MANAGED_RUNTIME_FIRST')
    owners = subprocess.run(['fuser', '/dev/video0'], capture_output=True, text=True)
    if owners.stdout.strip():
        raise RuntimeError('CAMERA_STILL_OWNED: ' + owners.stdout.strip())
    if owners.returncode not in (0, 1):
        raise RuntimeError('CAMERA_OWNER_CHECK_FAILED')


def validate_runtime_settings(before, after):
    """Only the explicit, mutually exclusive PLC or development MOCK choice may change."""
    selected = {'plc_bench', 'mock_auto_request','inspection_motion_mode','conveyor_capture_zone_normalized'}
    if ({k: v for k, v in after.items() if k not in selected} !=
            {k: v for k, v in before.items() if k not in selected}):
        raise ValueError('ONLY_GATEWAY_SELECTION_MAY_CHANGE')
    if type(after.get('plc_bench')) is not bool or type(after.get('mock_auto_request')) is not bool:
        raise ValueError('EXPLICIT_BOOL_GATEWAY_SELECTION_REQUIRED')
    if after['plc_bench'] == after['mock_auto_request']:
        raise ValueError('CHOOSE_EXACTLY_ONE_GATEWAY_MODE')
    mode=after.get('inspection_motion_mode','STATIONARY')
    if mode not in ('STATIONARY','CONVEYOR_MOTION_DEV','CONVEYOR_MOTION_PLC_BENCH'):
        raise ValueError('INSPECTION_MOTION_MODE_INVALID')
    if mode in ('CONVEYOR_MOTION_DEV','CONVEYOR_MOTION_PLC_BENCH'):
        if (mode=='CONVEYOR_MOTION_DEV' and (after['plc_bench'] or after['mock_auto_request'] is not True)
                or mode=='CONVEYOR_MOTION_PLC_BENCH' and (after['plc_bench'] is not True or after['mock_auto_request'])):
            raise ValueError('CONVEYOR_MOTION_GATEWAY_INVALID')
        points=after.get('conveyor_capture_zone_normalized')
        if (not isinstance(points,list) or len(points)!=4 or
                any(not isinstance(p,list) or len(p)!=2 or
                    any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in p)
                    for p in points)):
            raise ValueError('CONVEYOR_CAPTURE_ZONE_INVALID')
        x1,y1=points[0]; x2,y2=points[2]
        if points!=[[x1,y1],[x2,y1],[x2,y2],[x1,y2]] or x2-x1<.1 or y2-y1<.1:
            raise ValueError('CONVEYOR_CAPTURE_ZONE_INVALID')
    elif after.get('conveyor_capture_zone_normalized') is not None:
        raise ValueError('CAPTURE_ZONE_ONLY_IN_CONVEYOR_MOTION_MODE')


def install_first_layout(base, archive, expected_sha, station, settings_path):
    base = base.resolve(strict=True)
    archive = archive.resolve(strict=True)
    stage = base / 'tmp' / 'deploy' / 'unpacked'
    if archive.parent != base / 'tmp' / 'deploy':
        raise ValueError('USE_ONE_BOUNDED_DEPLOY_DIRECTORY')
    if any((base / name).exists() or (base / name).is_symlink()
           for name in ('current', 'assets', 'config')):
        raise FileExistsError('FIRST_LAYOUT_ONLY: preserve an existing current/assets/config')
    if stage.exists() or stage.is_symlink() or (base / 'tmp').is_symlink() or archive.parent.is_symlink():
        raise ValueError('STAGING_PATH_MUST_BE_NEW_AND_LOCAL')
    release = validate_bundle(archive, expected_sha)
    settings_bytes = settings_path.read_bytes()
    settings = json.loads(settings_bytes)
    paths = {key: (base / 'config' / settings[key]).resolve()
             for key in ('package', 'station', 'data_root', 'pythonpath')}
    if (paths['package'] != base / 'assets/products/ENGINE_Z3005_5/dynamic_parts_005'
            or paths['station'] != base / 'config/station.json'
            or not paths['data_root'].is_relative_to(base / 'data')
            or not paths['data_root'].is_dir()
            or paths['pythonpath'] != base / 'env_candidates/numpy_compat_001/overlay'
            or not paths['pythonpath'].is_dir()):
        raise ValueError('CHECK_DEVICE_PATHS_AND_PRESERVED_DATA_FIRST')
    station_bytes = station.read_bytes()
    if digest(station_bytes) != release['files']['config/station.example.json']:
        raise ValueError('STATION_DRIFT_REQUIRES_DEVICE_REVIEW')
    require_stopped(settings.get('port', 18771))
    stage.mkdir()
    with tarfile.open(archive) as bundle:
        # 직접 쓰므로 tar의 경로/권한/링크 확장 동작에 의존하지 않는다.
        for member in bundle.getmembers():
            if member.issym():
                continue
            destination = stage / member.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as target:
                target.write(bundle.extractfile(member).read())
            destination.chmod(0o644)
    (stage / 'current/config').symlink_to('../assets/runtime_config')
    (stage / 'config/station.json').write_bytes(station_bytes)
    (stage / 'config/runtime.json').write_bytes(settings_bytes)
    env = dict(os.environ, PYTHONPATH=str(paths['pythonpath']))
    subprocess.run([sys.executable, '-B', '-X', 'utf8', str(stage / 'current/launch_live.py'),
                    '--package', str(stage / 'assets/products/ENGINE_Z3005_5/dynamic_parts_005'),
                    '--station', str(stage / 'config/station.json'),
                    '--data-root', str(paths['data_root']), '--check-only'], env=env, check=True)
    for name in ('assets', 'config', 'current'):
        (stage / name).rename(base / name)
    stage.rmdir()
    subprocess.run([sys.executable, '-B', '-X', 'utf8', str(base / 'current/manage_live.py'),
                    'start', '--config', str(base / 'config/runtime.json')], env=env, check=True)
    return {'release_id': release['release_id'], 'runtime_path': str(base / 'current'),
            'data_root': str(paths['data_root']), 'previous_files_deleted': 0,
            'auto_started': False, 'archive_sha256': expected_sha}


def update_current(base, archive, expected_sha, settings_path):
    """Replace current code and the reviewed area policy; preserve other assets/data/env."""
    base = base.resolve(strict=True)
    archive = archive.resolve(strict=True)
    upload = base / 'tmp/deploy'
    stage = base / 'current.next'
    rollback = upload / 'rollback-current'
    current = base / 'current'
    runtime_path = base / 'config/runtime.json'
    if (archive.parent != upload or settings_path.resolve(strict=True).parent != upload
            or not current.is_dir() or current.is_symlink()
            or stage.exists() or stage.is_symlink() or rollback.exists() or rollback.is_symlink()):
        raise ValueError('CURRENT_UPDATE_PATH_OR_STAGE_INVALID')
    old_release = json.loads((current / 'release.json').read_text(encoding='utf-8'))
    area_name = 'assets/runtime_config/area_clearance.json'
    area_path = base / area_name
    old_area = area_path.read_bytes()
    if digest(old_area) != old_release['files'].get(area_name):
        raise ValueError('CURRENT_AREA_CONFIG_DRIFT')
    for name, expected in old_release['files'].items():
        if name.startswith('current/') and digest((base / name).read_bytes()) != expected:
            raise ValueError('CURRENT_CODE_DRIFT: ' + name)
    old_settings = runtime_path.read_bytes()
    before = json.loads(old_settings)
    after = json.loads(settings_path.read_bytes())
    validate_runtime_settings(before, after)
    release = validate_bundle(archive, expected_sha)
    with tarfile.open(archive) as bundle:
        new_area = bundle.extractfile(area_name).read()
    new_area_value = json.loads(new_area)
    if (new_area != old_area and
            (new_area_value.get('mode') != 'DARK_SURFACE_SELF_OBSERVED'
             or new_area_value.get('references') or
             new_area_value.get('roi') != 'DYNAMIC_DARK_SURFACE_FULL_HEIGHT')):
        raise ValueError('ONLY_REVIEWED_DARK_SURFACE_AREA_CHANGE_ALLOWED')
    for name, expected in release['files'].items():
        if (not name.startswith('current/') and name != area_name
                and digest((base / name).read_bytes()) != expected):
            raise ValueError('PRESERVED_ASSET_OR_CONFIG_MISMATCH: ' + name)
    require_stopped(before.get('port', 18771))
    area_backup = upload / 'area-clearance-before-update.json'
    if area_backup.exists():
        raise FileExistsError('AREA_CONFIG_BACKUP_ALREADY_EXISTS')
    area_backup.write_bytes(old_area)
    stage.mkdir()
    try:
        with tarfile.open(archive) as bundle:
            for member in bundle.getmembers():
                if member.name == 'current/config' or not member.name.startswith('current/'):
                    continue
                destination = stage / PurePosixPath(member.name).relative_to('current')
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open('xb') as target:
                    target.write(bundle.extractfile(member).read())
                destination.chmod(0o644)
        (stage / 'config').symlink_to('../assets/runtime_config')
        current.rename(rollback)
        try:
            stage.rename(current)
            if new_area != old_area:
                incoming = upload / 'area-clearance-incoming.json'
                incoming.write_bytes(new_area)
                os.replace(incoming, area_path)
            runtime_path.write_bytes(settings_path.read_bytes())
            resolved = {key: str((runtime_path.parent / after[key]).resolve())
                        for key in ('package', 'station', 'data_root', 'pythonpath')}
            env = dict(os.environ, PYTHONPATH=resolved['pythonpath'])
            command = [sys.executable, '-B', '-X', 'utf8', str(current / 'launch_live.py'),
                            '--package', resolved['package'], '--station', resolved['station'],
                            '--data-root', resolved['data_root'], '--check-only']
            command.append('--plc-bench' if after['plc_bench'] else '--mock-auto-request')
            if after.get('inspection_motion_mode','STATIONARY')!='STATIONARY':
                command.extend(['--inspection-motion-mode',after['inspection_motion_mode'],
                                '--conveyor-capture-zone',json.dumps(after['conveyor_capture_zone_normalized'])])
            subprocess.run(command, env=env, cwd=current, check=True)
        except Exception:
            runtime_path.write_bytes(old_settings)
            if area_path.read_bytes() != old_area:
                restore = upload / 'area-clearance-restore.json'
                restore.write_bytes(old_area)
                os.replace(restore, area_path)
            if current.exists() and (current / 'release.json').exists():
                current.rename(stage)
            rollback.rename(current)
            raise
    finally:
        if stage.exists() and stage.is_dir() and not stage.is_symlink():
            shutil.rmtree(stage)
    return {'release_id': release['release_id'], 'runtime_path': str(current),
            'rollback_path': str(rollback), 'auto_started': False,
            'archive_sha256': expected_sha, 'area_config_sha256': digest(new_area),
            'area_config_backup': str(area_backup)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--station', type=Path)
    parser.add_argument('--runtime-settings', type=Path, required=True)
    parser.add_argument('--update-current', action='store_true')
    args = parser.parse_args()
    if args.update_current:
        result = update_current(args.base, args.archive, args.sha256, args.runtime_settings)
    else:
        if args.station is None:
            parser.error('--station is required for first install')
        result = install_first_layout(args.base, args.archive, args.sha256, args.station, args.runtime_settings)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
