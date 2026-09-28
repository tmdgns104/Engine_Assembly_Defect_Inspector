"""Jetson 단일 실행 시작점: 인자 해석 → 구성 → API 실행 → 종료."""
import argparse
import json
from pathlib import Path

from apps.edge_service.integration_api import create_integrated_app
from src.runtime.bootstrap import build_runtime


def main():
    parser = argparse.ArgumentParser(description='Jetson 통합 Runtime · 소프트웨어 통합 후보')
    parser.add_argument('--package',required=True)
    parser.add_argument('--station',required=True)
    parser.add_argument('--data-root',required=True)
    parser.add_argument('--port',type=int,default=18768)
    parser.add_argument('--mode',choices=['mock','auto'],default='mock')
    parser.add_argument('--auto-profile',help='AUTO 제품/영역/시간 설정 JSON; 누락 시 AUTO 실행 거절')
    diagnostic=parser.add_mutually_exclusive_group()
    diagnostic.add_argument('--diagnostic-devices',action='store_true',help='CPU 합성 장치 전용; 실제 카메라/모델 아님')
    diagnostic.add_argument('--package-self-test-replay',action='store_true',help='임시 검증 영상 재생 + 실제 Detector; 물리 Camera 아님')
    parser.add_argument('--collector-url')
    parser.add_argument('--collector-token-file')
    parser.add_argument('--recovery-config',help='선택적 반복 오류/명시적 복구 한도 JSON; 생산 기본 한도 없음')
    args = parser.parse_args()
    station = json.loads(Path(args.station).read_text(encoding='utf-8'))
    package = Path(args.package).resolve()
    # 설정 오류는 장수 프로세스를 만들기 전에 확인한다.
    token = None
    if args.collector_url:
        if not args.collector_token_file:
            parser.error('--collector-token-file이 필요합니다')
        token = Path(args.collector_token_file).read_text(encoding='utf-8').strip()
        if len(token)<32:
            parser.error('collector token은 최소 32자여야 합니다')
    from src.runtime.cell_supervisor import FaultPolicy
    policy = FaultPolicy(**json.loads(Path(args.recovery_config).read_text(encoding='utf-8'))) if args.recovery_config else FaultPolicy()
    runtime = build_runtime(package,station,args.data_root,args.mode,args.diagnostic_devices,
        recovery_policy=policy,package_self_test_replay=args.package_self_test_replay,
        auto_profile=json.loads(Path(args.auto_profile).read_text(encoding='utf-8')) if args.auto_profile else None)
    products = package.parent.parent
    catalog = {p.parent.relative_to(products).as_posix():p.parent for p in products.glob('*/*/manifest.json')}
    catalog.setdefault('current',package)
    try:
        if args.collector_url:
            from src.journal.sync import OutboxSender
            runtime.service.sender = OutboxSender(runtime.service.journal,args.collector_url,token)
            runtime.service.sender.start()
        import uvicorn
        uvicorn.run(create_integrated_app(runtime,catalog),host='127.0.0.1',port=args.port,log_level='info')
    finally:
        if not runtime.closed and not runtime.closing:
            runtime.close()


if __name__=='__main__':
    main()
