"""기존 area deploy의 해시 확인·managed start 순서를 current 최초 전환에 재사용.

노트북에 보관하고 배포 중에만 Jetson tmp/deploy에 반입한다.
기존 코드/DB의 백업·정상 종료를 먼저 완료해야 한다. 이 도구는 기존 자료를
삭제하거나 Journal/환경/승인을 덮어쓰지 않는다. 실패 시 옛 managed 경로로 복귀한다.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--station', type=Path, required=True)
    parser.add_argument('--runtime-settings', type=Path, required=True)
    args = parser.parse_args()
    result = install_first_layout(args.base, args.archive, args.sha256, args.station, args.runtime_settings)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
