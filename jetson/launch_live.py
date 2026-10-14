"""Jetson 시작점. 기존 launch_live의 경로만 인자로 분리한다.

노트북에서는 --check-only로 배포 파일을 확인한다. 실제 실행은 Jetson에서만 한다.
production은 Runtime 종류이며 실제 PLC 출력 승인을 의미하지 않는다.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_files(package, station, *, plc_bench=False, mock_auto_request=False,
                inspection_motion_mode='STATIONARY', conveyor_capture_zone=None,
                plc_contract='LEGACY_THREE_BOOL'):
    """추론·DB·카메라를 시작하기 전에 파일과 PLC 벤치 경계를 확인한다."""
    if plc_bench and mock_auto_request:
        raise ValueError('MOCK_AUTO_REQUEST_AND_REAL_PLC_ARE_EXCLUSIVE')
    if plc_contract not in ('LEGACY_THREE_BOOL', 'EXTENDED_V2'):
        raise ValueError('PLC_CONTRACT_VERSION_INVALID')
    if plc_contract == 'EXTENDED_V2' and not plc_bench:
        raise ValueError('V2_REQUIRES_EXPLICIT_REAL_PLC_MODE')
    if inspection_motion_mode not in ('STATIONARY','CONVEYOR_MOTION_DEV','CONVEYOR_MOTION_PLC_BENCH'):
        raise ValueError('INSPECTION_MOTION_MODE_INVALID')
    if inspection_motion_mode=='CONVEYOR_MOTION_DEV':
        if plc_bench or not mock_auto_request or conveyor_capture_zone is None:
            raise ValueError('CONVEYOR_MOTION_REQUIRES_EXPLICIT_MOCK_CAPTURE_ZONE')
        from src.runtime.production_profile import validate_zone
        validate_zone({'polygon_normalized':conveyor_capture_zone,'entry_policy':'product_center'})
    elif inspection_motion_mode=='CONVEYOR_MOTION_PLC_BENCH':
        if not plc_bench or mock_auto_request or conveyor_capture_zone is None:
            raise ValueError('CONVEYOR_MOTION_PLC_BENCH_REQUIRES_REAL_PLC_AND_ZONE')
        from src.runtime.production_profile import validate_zone
        validate_zone({'polygon_normalized':conveyor_capture_zone,'entry_policy':'product_center'})
    elif conveyor_capture_zone is not None:
        raise ValueError('CAPTURE_ZONE_ONLY_IN_CONVEYOR_MOTION_MODE')
    station_value = json.loads(station.read_text(encoding='utf-8'))
    config = ROOT / 'config'
    plc = json.loads((config / 'plc_reference.json').read_text(encoding='utf-8'))
    if plc['backend'] != 'MOCK' or plc['physical_output_enabled'] is not False:
        raise ValueError('MOCK_ONLY_RELEASE')
    if plc_bench and (plc.get('planned_plc_ip') != '192.168.50.3'
                      or plc.get('planned_jetson_lan_ip') != '192.168.50.2'
                      or plc.get('tags') != {
                          'Inspection_Request': 'PLC_TO_JETSON_BOOL',
                          'Jetson_Result': 'JETSON_TO_PLC_BOOL_FALSE_OK_TRUE_NG',
                          'Jetson_Done': 'JETSON_TO_PLC_BOOL'}):
        raise ValueError('PLC_BENCH_TAG_CONTRACT_MISMATCH')
    area = json.loads((config / 'area_clearance.json').read_text(encoding='utf-8'))
    if area.get('mode') == 'CONVEYOR_HORIZONTAL_TEXTURE_V1':
        from src.observation.horizontal_conveyor import validate_horizontal_config
        validate_horizontal_config(area)
        # Loading observation code is not field clearance qualification.
        raise ValueError('HORIZONTAL_TEXTURE_ISOLATED_VALIDATION_ONLY')
    if area.get('mode') == 'DARK_SURFACE_SELF_OBSERVED':
        if (area.get('references') or area.get('roi') != 'DYNAMIC_DARK_SURFACE_FULL_HEIGHT'
                or area.get('shape') != [720, 1280, 3]):
            raise ValueError('DARK_SURFACE_CONFIG_INVALID')
    elif area.get('mode') == 'CONVEYOR_DARK_BELT_SELF_OBSERVED':
        from src.observation.conveyor_occupancy import validate_conveyor_config
        validate_conveyor_config(area)
    elif area.get('mode') == 'CONVEYOR_FROZEN_EMPTY_ENVELOPE':
        from src.observation.conveyor_reference import ConveyorReferenceOccupancy
        # Verify fixed geometry, source sequence and all reference hashes before
        # any hardware startup. A parseable JSON file is not a valid calibration.
        ConveyorReferenceOccupancy.from_config(config / 'area_clearance.json')
    else:
        for reference in area['references']:
            path = (config / reference['path']).resolve()
            if not path.is_relative_to(config.resolve()) or sha256(path) != reference['sha256']:
                raise ValueError('AREA_REFERENCE_HASH_MISMATCH')
    manifest = json.loads((package / 'manifest.json').read_text(encoding='utf-8'))
    for item in manifest['files'].values():
        path = (package / item['path']).resolve()
        if not path.is_relative_to(package) or sha256(path) != item['sha256']:
            raise ValueError('PACKAGE_FILE_HASH_MISMATCH')
    release_path = ROOT / 'release.json'
    release = None
    if release_path.exists():
        release = json.loads(release_path.read_text(encoding='utf-8'))
        base = ROOT.parent
        for name, expected in release['files'].items():
            path = (base / name).resolve()
            if not path.is_relative_to(base) or sha256(path) != expected:
                raise ValueError('RELEASE_FILE_HASH_MISMATCH: ' + name)
        for name, target in release.get('links', {}).items():
            link = base / name
            if not link.is_symlink() or link.resolve() != (link.parent / target).resolve():
                raise ValueError('RELEASE_LINK_MISMATCH: ' + name)
    return station_value, {
        'release_id': release['release_id'] if release else 'SOURCE_TREE_UNPACKAGED',
        'qualification': 'DEVELOPMENT_BASELINE_NOT_PRODUCTION_ACCEPTED',
        'runtime_path': str(ROOT), 'package_path': str(package),
        'package_manifest_sha256': sha256(package / 'manifest.json'),
        'area_config_sha256': sha256(config / 'area_clearance.json'),
        'station_sha256': sha256(station),
        'backend': 'OMRON_CIP_BENCH' if plc_bench else 'MOCK',
        'plc_contract': plc_contract,
        'mock_auto_request_enabled': bool(mock_auto_request),
        'inspection_motion_mode': inspection_motion_mode,
        'conveyor_capture_zone_normalized': conveyor_capture_zone,
        'network_plc_writes_enabled': bool(plc_bench),
        'physical_output_enabled': False,
    }


def add_arguments(parser):
    parser.add_argument('--package', type=Path, required=True, help='dynamic_parts_005 패키지 폴더')
    parser.add_argument('--station', type=Path, required=True, help='장치별 카메라·검사 설정 JSON')
    parser.add_argument('--data-root', type=Path, required=True, help='Journal/Evidence 저장 폴더; 코드 밖에 둔다')
    parser.add_argument('--port', type=int, default=18771)
    parser.add_argument('--plc-bench', action='store_true',
                        help='192.168.50.3의 세 검증된 태그만 사용; 실제 PLC 결과/Done 쓰기')
    parser.add_argument('--plc-contract', choices=('LEGACY_THREE_BOOL', 'EXTENDED_V2'),
                        default='LEGACY_THREE_BOOL',
                        help='명시적 PLC 계약 선택. v2는 시작 후 7개 태그 자료형을 먼저 읽어 검증')
    parser.add_argument('--misassembly-shadow', action='store_true',
                        help='같은 요청의 저장 원본에서 동결된 오조립 모델 실행; PLC 판정과 분리')
    parser.add_argument('--mock-auto-request', action='store_true',
                        help='개발용 MOCK: 새 Track의 검사영역 진입에서 Request 자동 생성')
    parser.add_argument('--inspection-motion-mode',choices=('STATIONARY','CONVEYOR_MOTION_DEV','CONVEYOR_MOTION_PLC_BENCH'),default='STATIONARY')
    parser.add_argument('--conveyor-capture-zone',type=json.loads,
                        help='개발 이동 모드에서만 사용하는 정규화 사각형 JSON')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    parser.add_argument('--check-only', action='store_true', help='파일만 확인; 카메라/DB/모델 실행 없음')
    args = parser.parse_args()
    package = args.package.resolve()
    station, identity = check_files(package, args.station.resolve(), plc_bench=args.plc_bench,
                                   mock_auto_request=args.mock_auto_request,
                                   plc_contract=args.plc_contract,
                                   inspection_motion_mode=args.inspection_motion_mode,
                                   conveyor_capture_zone=args.conveyor_capture_zone)
    identity['data_root'] = str(args.data_root.resolve())
    identity['misassembly_shadow_enabled'] = args.misassembly_shadow
    shadow_assets = ROOT.parent/'assets/misassembly_runtime'
    if args.misassembly_shadow:
        from src.vision.misassembly_shadow import verify_assets
        verify_assets(shadow_assets)  # Hash-only; no torch/model/camera execution.
    if args.check_only:
        print(json.dumps(identity, ensure_ascii=False))
        return
    from src.runtime.bootstrap import build_runtime
    from apps.edge_service.integration_api import create_integrated_app
    import uvicorn
    gateway = None
    if args.plc_bench:
        from src.control.omron_cip import OmronCipGateway
        from src.control.plc_v2 import OmronCipV2Gateway
        gateway_type = OmronCipV2Gateway if args.plc_contract == 'EXTENDED_V2' else OmronCipGateway
        gateway = gateway_type('192.168.50.3', '192.168.50.2')
    runtime = build_runtime(package, station, args.data_root.resolve(), mode='production',
                            production_gateway=gateway,auto_mock_request=args.mock_auto_request,
                            inspection_motion_mode=args.inspection_motion_mode,
                            conveyor_capture_zone=args.conveyor_capture_zone)
    try:
        if args.misassembly_shadow:
            from src.vision.misassembly_shadow import ShadowObserver
            runtime.shadow = ShadowObserver(args.data_root.resolve(), args.data_root.resolve()/'misassembly_shadow',
                                            assets_root=shadow_assets)
        # 모델 의존 패키지 envelope는 운영자 선택 목록에 노출하지 않는다.
        app = create_integrated_app(runtime, {package.parent.name + '/' + package.name: package})

        @app.get('/api/v1/release')
        def loaded_release():
            # 시작 때 확인한 식별정보를 반환한다. 디스크의 최신 파일로 바꿔 표시하지 않는다.
            return identity

        uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='info')
    finally:
        if not runtime.closed and not runtime.closing:
            runtime.close()


if __name__ == '__main__':
    main()
