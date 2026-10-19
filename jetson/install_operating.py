"""새 Jetson 설치 전용. 운영 코드·모델은 보존하고 장치 설정만 만든다.

서비스 시작, 패키지 설치, PLC/네트워크 제어는 하지 않는다.
기존 장치 업데이트에는 사용하지 않는다.
"""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from contextlib import closing

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / 'portable/operating_runtime.tar.gz'
MAX_UNPACKED_BYTES = 512 * 1024**2


def digest(path):
    with path.open('rb') as stream:
        return stream_digest(stream)


def stream_digest(stream):
    result = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        result.update(chunk)
    return result.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def validate_member_name(name):
    parts = PurePosixPath(name).parts
    if (not parts or name != '/'.join(parts) or '..' in parts or ':' in name
            or '\\' in name or PurePosixPath(name).is_absolute()
            or (parts[0] not in ('current', 'assets', 'templates', 'history') and name != 'bundle.json')):
        raise ValueError('INVALID_BUNDLE_PATH: ' + name)


def verify_bundle(archive_path=ARCHIVE):
    """외부 해시와 파일별 해시를 모두 확인한다. GPU/카메라는 열지 않는다."""
    receipt = read_json(archive_path.with_suffix('.json'))
    if digest(archive_path) != receipt['sha256']:
        raise ValueError('BUNDLE_SHA256_MISMATCH')
    with tarfile.open(archive_path) as archive:
        members = archive.getmembers()
        names = [m.name for m in members]
        if len(names) != len(set(names)) or len(names) > 500:
            raise ValueError('DUPLICATE_OR_EXCESSIVE_BUNDLE_MEMBERS')
        if sum(m.size for m in members) > MAX_UNPACKED_BYTES:
            raise ValueError('BUNDLE_SIZE_LIMIT')
        for member in members:
            validate_member_name(member.name)
            if not member.isfile() or member.size < 0:
                raise ValueError('REGULAR_FILES_ONLY: ' + member.name)
        if archive.getmember('bundle.json').size > 1024**2:
            raise ValueError('BUNDLE_METADATA_SIZE_LIMIT')
        metadata = json.load(archive.extractfile('bundle.json'))
        if metadata['schema_version'] != 1 or metadata['source_release'] != receipt['source_release']:
            raise ValueError('BUNDLE_IDENTITY_MISMATCH')
        if set(names) != set(metadata['files']) | {'bundle.json'}:
            raise ValueError('BUNDLE_MEMBER_SET_MISMATCH')
        for name, expected in metadata['files'].items():
            if not re.fullmatch('[a-f0-9]{64}', expected):
                raise ValueError('INVALID_FILE_HASH')
            if stream_digest(archive.extractfile(name)) != expected:
                raise ValueError('BUNDLE_FILE_HASH_MISMATCH: ' + name)
        for name, expected in metadata['source_file_hashes'].items():
            target = 'templates/'+name[7:] if name.startswith('config/') else name
            if metadata['files'].get(target) != expected:
                raise ValueError('OPERATING_SOURCE_NOT_PRESERVED: '+name)
    return metadata


def check_new_base(base):
    """다시 실행해도 운영 원장·환경을 자동 교체하지 않는다."""
    for parent in (base, *base.parents):
        if parent.is_symlink():
            raise ValueError('INSTALL_PATH_SYMLINK')
    for name in ('current', 'assets', 'config', 'data', 'history', 'templates', 'service', 'installation.json'):
        path = base / name
        if path.exists() or path.is_symlink():
            raise FileExistsError('EXISTING_INSTALLATION_PRESERVED: ' + str(path))


def validate_device(camera, station_id, base, username):
    if not re.fullmatch('/dev/[A-Za-z0-9_./:-]+', camera) or '..' in PurePosixPath(camera).parts:
        raise ValueError('EXPLICIT_CAMERA_DEVICE_REQUIRED')
    if not re.fullmatch('[A-Za-z0-9_-]{1,64}', station_id):
        raise ValueError('UNIQUE_STATION_ID_REQUIRED')
    if not re.fullmatch('[a-z_][a-z0-9_-]*', username):
        raise ValueError('INVALID_SERVICE_USER')
    # systemd 문법/쉘 확장과 Unix socket 길이 문제를 설치 전에 거부한다.
    text = str(base)
    if not re.fullmatch('/[A-Za-z0-9_./-]+', text) or '..' in PurePosixPath(text).parts:
        raise ValueError('SIMPLE_ABSOLUTE_LINUX_INSTALL_PATH_REQUIRED')
    if len((text+'/data/engine_dynamic_pose_002/opener/ipc').encode()) > 100:
        raise ValueError('UNIX_SOCKET_PATH_TOO_LONG')


def device_config(stage, base, camera, station_id):
    station = read_json(stage/'templates/station.json')
    station.update(camera_device=camera, station_id=station_id)
    config = read_json(stage/'templates/standalone.json')
    config.update(pythonpath='../current', listen_host='127.0.0.1',
                  cyclic_transport_activation_approved=False, cyclic_publication_enabled=False,
                  opener_ipc_path=str(base/'data/engine_dynamic_pose_002/opener/ipc'))
    profile = read_json(stage/'templates/line_profile.json')
    profile['camera'] = station
    # 기존 장치의 촬영 구도·승인/자격을 새 장치의 확인 사실로 복사하지 않는다.
    profile['observed_capture_zone']['confirmed'] = False
    profile['field_profile_verified'] = False
    profile['ng_exit_policy_verified'] = False
    profile['supervised_web'] = {'enabled': False, 'allowed_hosts': ['127.0.0.1:18771']}
    profile['maintenance_recovery'] = {'enabled': True, 'allowed_hosts': ['127.0.0.1:18771']}
    for key in ('request_start_qualification', 'clearance_qualification', 'automatic_operation_qualification'):
        for field in profile.get(key, {}):
            if field == 'verified' or field.endswith('_verified'):
                profile[key][field] = False
    for name, value in (('station', station), ('standalone', config), ('line_profile', profile)):
        write_json(stage/'config'/f'{name}.json', value)
    (stage/'config/standalone.env').write_text('PYTHONUTF8=1\nPYTHONDONTWRITEBYTECODE=1\n', encoding='utf-8')


def service_text(base, username):
    return f'''[Unit]
Description=Engine integrated standalone PLC inspection
After=network.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
User={username}
SupplementaryGroups=video render
WorkingDirectory={base}/current
EnvironmentFile={base}/config/standalone.env
ExecStart={base}/envs/app_v1/bin/python -B -X utf8 {base}/current/standalone_service.py --config {base}/config/standalone.json
Restart=on-failure
RestartSec=10
TimeoutStartSec=180
TimeoutStopSec=45
KillMode=control-group
KillSignal=SIGTERM
UMask=0027
NoNewPrivileges=true
StandardOutput=journal
StandardError=journal
SyslogIdentifier=engine-inspector

[Install]
WantedBy=multi-user.target
'''


def write_release(base, metadata):
    """코드 해시는 유지하고 이 장치에 생성한 설정을 별도 설치 ID로 식별한다."""
    hashes = {p.relative_to(base).as_posix(): digest(p)
              for folder in ('current', 'assets', 'config', 'service')
              for p in (base/folder).rglob('*')
              if p.is_file() and not p.is_symlink() and p != base/'current/release.json'
              and '__pycache__' not in p.parts}
    identity = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:16]
    release = {'schema_version': 1, 'release_id': 'engine-install-'+identity,
               'source_release': metadata['source_release'], 'source_commit': metadata['source_commit'],
               'qualification': 'NEW_DEVICE_NOT_COMMISSIONED',
               'physical_output_enabled': read_json(base/'config/standalone.json')['cyclic_publication_enabled'],
               'files': hashes, 'links': {'current/config': '../assets/runtime_config'}}
    write_json(base/'current/release.json', release)
    return release


def verify_installed(base):
    release = read_json(base/'current/release.json')
    for name, expected in release['files'].items():
        path = base/name
        if not path.resolve().is_relative_to(base.resolve()) or digest(path) != expected:
            raise ValueError('INSTALLED_HASH_MISMATCH: ' + name)
    if not (base/'current/config').is_symlink() or (base/'current/config').resolve() != (base/'assets/runtime_config').resolve():
        raise ValueError('CONFIG_LINK_MISMATCH')
    return release


def require_local_line_ready(base):
    """새 장치 최초 설정 때만 사용. 이미 시작한 원장/서비스에는 손대지 않는다."""
    active = subprocess.run(['systemctl', 'is-active', 'engine-inspector.service'],
                            capture_output=True, text=True)
    if active.stdout.strip() not in ('inactive', 'failed', 'unknown'):
        raise ValueError('SERVICE_MUST_NOT_BE_RUNNING')
    if any((base/'data').rglob('standalone-owner.lock')):
        raise ValueError('EXISTING_RUNTIME_DATA_PRESERVED')
    # 기준 촬영 서버가 아직 카메라/원장을 소유한 채로 전환하지 않는다.
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(('127.0.0.1', 18771))
    addresses = json.loads(subprocess.check_output(
        ['ip', '-j', 'address', 'show', 'dev', 'enP8p1s0'], text=True))
    if not any(item.get('local') == '192.168.50.2' for row in addresses for item in row['addr_info']):
        raise ValueError('CONFIRMED_PLC_INTERFACE_ADDRESS_REQUIRED')
    if not Path(read_json(base/'config/station.json')['camera_device']).exists():
        raise ValueError('CAMERA_DEVICE_MISSING')


def read_confirmed_reference(data_root, expected):
    """새 장치의 기존 기준 등록 기록만 읽는다. 승인/DB 행을 만들어 넣지 않는다."""
    database = data_root/'journal.sqlite3'
    if not database.is_file():
        raise ValueError('NEW_DEVICE_REFERENCE_REQUIRED')
    with closing(sqlite3.connect(database.as_uri()+'?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        records = db.execute('SELECT * FROM inspections ORDER BY rowid').fetchall()
        if not records or any(json.loads(r['request_json']).get('kind') != 'calibrate'
                              or r['state'] == 'ACCEPTED' for r in records):
            raise ValueError('ONLY_FINISHED_NEW_DEVICE_REFERENCE_RECORDS_ALLOWED')
        latest = records[-1]
        row = db.execute('SELECT payload_json FROM calibrations WHERE package_sha256=? '
                         'AND station_id=? ORDER BY confirmed_at DESC LIMIT 1',
                         (expected['manifest_sha256'], expected['station_id'])).fetchone()
        candidate = json.loads(row[0]) if row else {}
        result = json.loads(latest['result_json'] or '{}')
        if (latest['state'] != 'COMPLETE' or not latest['completed_at']
                or result.get('storage_success') is not True or result.get('decision') != 'REVIEW'
                or candidate.get('confirmed') is not True
                or candidate.get('source_inspection_id') != latest['inspection_id']
                or any(candidate.get(key) != value for key, value in expected.items())):
            raise ValueError('CONFIRMED_CURRENT_DEVICE_REFERENCE_REQUIRED')
        source = result.get('calibration_candidate') or {}
        if candidate != dict(source, confirmed=True, source_inspection_id=latest['inspection_id']):
            raise ValueError('REFERENCE_CANDIDATE_RECORD_MISMATCH')
        assets = db.execute("SELECT relative_path,sha256 FROM frame_assets WHERE inspection_id=? AND kind='raw'",
                            (latest['inspection_id'],)).fetchall()
        frames = candidate.get('source_frame_ids', [])
        if len(assets) != 3 or len(frames) != 3 or len(set(frames)) != 3:
            raise ValueError('THREE_NEW_REFERENCE_FRAMES_REQUIRED')
        for asset in assets:
            path = (data_root/asset['relative_path']).resolve()
            if not path.is_relative_to(data_root.resolve()) or digest(path) != asset['sha256']:
                raise ValueError('REFERENCE_ORIGINAL_HASH_MISMATCH')
    return candidate


def read_confirmed_zone(data_root, reference):
    """기존 /auto 화면에서 사람이 확인한 영역만 읽어 연결한다."""
    with closing(sqlite3.connect((data_root/'journal.sqlite3').as_uri()+'?mode=ro', uri=True)) as db:
        row = db.execute("SELECT value FROM service_state WHERE key='production_zone'").fetchone()
    zone = json.loads(row[0]) if row else {}
    reference_sha = hashlib.sha256(json.dumps(reference, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if zone.get('confirmed') is not True or zone.get('calibration_sha') != reference_sha:
        raise ValueError('NEW_DEVICE_CONFIRMED_ZONE_REQUIRED')
    return zone


def load_local_reference(base):
    sys.path.insert(0, str(base/'current'))
    from src.recipe.package import load_package
    from src.configuration import station_settings
    from src.decision.calibration import station_fingerprint
    from src.runtime.production_profile import validate_zone
    config = read_json(base/'config/standalone.json')
    package = load_package((base/'config'/config['package']).resolve())
    station = station_settings(read_json(base/'config/station.json'))
    expected = dict(coordinate_space='normalized_image', manifest_sha256=package.manifest_hash,
                    product_id=package.manifest['product_id'],
                    capture_sha256=package.manifest['files']['capture']['sha256'],
                    recipe_sha256=package.manifest['files']['recipe']['sha256'],
                    station_id=station['station_id'], cell_id=station['cell_id'],
                    station_sha256=station_fingerprint(station))
    data_root = (base/'config'/config['data_root']).resolve()
    reference = read_confirmed_reference(data_root, expected)
    zone = read_confirmed_zone(data_root, reference)
    validate_zone(zone)
    return reference, zone


def enable_plc(base, *, stopped, camera_checked, contract_checked):
    """명시적인 현장 확인 뒤 최초 설정만 완료한다. 서비스/PLC 동작은 시작하지 않는다."""
    if not (stopped and camera_checked and contract_checked):
        raise ValueError('LOCAL_STOP_CAMERA_AND_PLC_CONTRACT_CONFIRMATION_REQUIRED')
    release = verify_installed(base)
    installation = read_json(base/'installation.json')
    if installation.get('local_setup_confirmed'):
        raise ValueError('ALREADY_CONFIGURED_USE_EXISTING_SERVICE_PROCEDURE')
    require_local_line_ready(base)
    reference, zone = load_local_reference(base)
    config = read_json(base/'config/standalone.json')
    if config['cyclic_publication_enabled'] or config['cyclic_transport_activation_approved']:
        raise ValueError('EXPECTED_DISABLED_NEW_DEVICE_CONFIG')
    # 설정 전 사본을 보존하고 코드·모델·임계값·원장은 변경하지 않는다.
    shutil.copy2(base/'config/standalone.json', base/'config/standalone.before-plc.json')
    shutil.copy2(base/'config/line_profile.json', base/'config/line_profile.before-plc.json')
    profile = read_json(base/'config/line_profile.json')
    reference_sha = hashlib.sha256(json.dumps(reference, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    profile['observed_capture_zone'] = zone
    for key in ('request_start_qualification', 'clearance_qualification', 'automatic_operation_qualification'):
        if 'calibration_sha' in profile.get(key, {}):
            profile[key]['calibration_sha'] = reference_sha
    write_json(base/'config/line_profile.json', profile)
    config.update(cyclic_transport_activation_approved=True, cyclic_publication_enabled=True)
    write_json(base/'config/standalone.json', config)
    updated = write_release(base, release)
    installation.update(local_setup_confirmed=True, release_id=updated['release_id'],
                        local_reference_inspection_id=reference['source_inspection_id'],
                        configured_at=datetime.now(timezone.utc).isoformat(),
                        new_device_execution='NOT_VERIFIED', runtime_started=False)
    write_json(base/'installation.json', installation)
    return installation


def prepare(base, camera, station_id, username, archive_path=ARCHIVE):
    """명시한 새 폴더에만 설치한다. 가상환경·systemd·PLC는 시작하지 않는다."""
    validate_device(camera, station_id, base, username)
    check_new_base(base)
    metadata = verify_bundle(archive_path)
    base.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.portable-', dir=base))
    with tarfile.open(archive_path) as archive:
        for member in archive.getmembers():
            if member.name == 'bundle.json':
                continue
            destination = stage/member.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, destination.open('xb') as target:
                shutil.copyfileobj(source, target)
            if digest(destination) != metadata['files'][member.name]:
                raise ValueError('SOURCE_CHANGED_DURING_INSTALL')
            destination.chmod(0o755 if member.name == 'current/opener/OpENer' else 0o644)
    (stage/'current/config').symlink_to('../assets/runtime_config', target_is_directory=True)
    (stage/'config').mkdir()
    (stage/'data').mkdir()
    (stage/'service').mkdir()
    device_config(stage, base, camera, station_id)
    (stage/'service/engine-inspector.service').write_text(service_text(base, username), encoding='utf-8')
    release = write_release(stage, metadata)
    write_json(stage/'installation.json', dict(release_id=release['release_id'],
               source_release=metadata['source_release'], station_id=station_id,
               database='history/journal.sqlite3 is historical, active data/ is empty',
               runtime_started=False, new_device_execution='NOT_VERIFIED'))
    check_new_base(base)
    for name in ('assets', 'templates', 'history', 'config', 'data', 'service', 'current', 'installation.json'):
        (stage/name).rename(base/name)
    stage.rmdir()
    return read_json(base/'installation.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--verify', action='store_true', help='오프라인 파일 해시 검사만')
    mode.add_argument('--prepare', action='store_true', help='새 Linux 장치 폴더 준비만')
    mode.add_argument('--enable-plc', action='store_true', help='현장 확인 후 새 장치의 최초 PLC 설정만')
    parser.add_argument('--base', type=Path, default=Path.home()/'oned_device_bench')
    parser.add_argument('--camera')
    parser.add_argument('--station-id')
    parser.add_argument('--confirm-stopped', action='store_true')
    parser.add_argument('--confirm-camera-setup', action='store_true')
    parser.add_argument('--confirm-plc-contract', action='store_true')
    args = parser.parse_args()
    if args.verify:
        metadata = verify_bundle()
        result = {key:metadata[key] for key in ('source_release', 'source_commit', 'model_count', 'new_device_execution')}
        result['files_verified'] = len(metadata['files'])
    else:
        if platform.system() != 'Linux' or platform.machine() != 'aarch64':
            parser.error('새 Jetson Orin Nano의 Linux aarch64에서만 --prepare를 실행하세요.')
        if os.geteuid() == 0:
            parser.error('sudo 없이 실제 운영 사용자로 설치하세요.')
        base = args.base.expanduser().absolute()
        if args.enable_plc:
            result = enable_plc(base, stopped=args.confirm_stopped,
                                camera_checked=args.confirm_camera_setup, contract_checked=args.confirm_plc_contract)
        else:
            if not args.camera or not args.station_id:
                parser.error('--camera와 --station-id가 필요합니다.')
            if not Path(args.camera).exists():
                parser.error('지정한 카메라 장치가 없습니다.')
            result = prepare(base, args.camera, args.station_id, getpass.getuser())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
