"""Jetson 통합 객체 조립. CPU 진단 장치는 명시 옵션에서만 선택한다."""
import uuid

from apps.edge_service.inspection import InspectionService
from src.runtime.adapters import ManualObservationSource, MockPLCAdapter
from src.runtime.integrated import IntegratedRuntime
from src.runtime.logging_support import RuntimeLog
from src.runtime.cell_supervisor import FaultPolicy
from src.runtime.vision_coordinator import VisionRuntimeCoordinator
from src.tracking.contracts import InspectionWindow, SingleActiveTrackerConfig


def build_runtime(package_root, station, data_root, mode='mock', diagnostic_devices=False,
                  tracker_config=None, recovery_policy=None, package_self_test_replay=False, auto_profile=None):
    if mode not in ('mock','auto','production'):
        raise ValueError('REAL_PLC_NOT_IMPLEMENTED')
    if mode == 'auto':
        if diagnostic_devices or package_self_test_replay or auto_profile is None:
            raise ValueError('AUTO_REQUIRES_LIVE_CAMERA_AND_PROFILE')
        from src.recipe.package import load_package
        from src.runtime.auto_profile import validate_profile
        from src.runtime.auto_adapters import WorkerObservationSource, LocalResultOutput
        from src.runtime.automatic import AutomaticRuntime
        tracker_config = validate_profile(auto_profile,load_package(package_root))
        station = dict(station,auto_profile=auto_profile)
        recovery_policy = FaultPolicy(auto_profile['consecutive_error_limit'],auto_profile['recovery_attempt_limit'])
    if diagnostic_devices and package_self_test_replay:
        raise ValueError('DIAGNOSTIC_DEVICE_MODES_ARE_EXCLUSIVE')
    # 진단 수동 좌표의 기본값일 뿐 엔진/컨베이어 튜닝 값이 아니다.
    config = tracker_config or SingleActiveTrackerConfig(InspectionWindow(.4,.1,.6,.9),
        'x',1,.5,.05,2,1)
    coordinator = VisionRuntimeCoordinator(uuid.uuid4().hex,config)
    observation, plc = ManualObservationSource(), MockPLCAdapter()
    if mode == 'auto':
        observation, plc = WorkerObservationSource(), LocalResultOutput()
    options = {}
    if diagnostic_devices:
        from src.runtime.diagnostic_devices import diagnostic_worker_main
        options['worker_target'] = diagnostic_worker_main
    if package_self_test_replay:
        from src.runtime.package_replay import package_replay_worker_main
        options['worker_target'] = package_replay_worker_main
    log_owner = RuntimeLog(data_root)
    service = None
    try:
        service = InspectionService(package_root,station,data_root,production=(mode=='production'),**options)
        if mode=='production':
            import json
            import hashlib
            from pathlib import Path
            from src.runtime.production import ProductionRuntime
            from src.runtime.production_profile import tracker_config as production_tracker_config, proposed_zone
            from src.runtime.auto_adapters import WorkerObservationSource, LocalResultOutput
            row=service.journal.db.execute("SELECT value FROM service_state WHERE key='production_zone'").fetchone()
            zone=json.loads(row[0]) if row else proposed_zone()
            area_path=Path(__file__).resolve().parents[2]/'config/area_clearance.json'
            area_version=None
            if not diagnostic_devices and not package_self_test_replay:
                area_version=hashlib.sha256(area_path.read_bytes()).hexdigest() if area_path.exists() else 'MISSING_AREA_CONFIG'
            config=production_tracker_config(zone,wait_area_clear=bool(area_version))
            coordinator=VisionRuntimeCoordinator(uuid.uuid4().hex,config)
            return ProductionRuntime(service,coordinator,WorkerObservationSource(),LocalResultOutput(),log_owner,config,
                recovery_policy or FaultPolicy(),zone=zone,area_config_version=area_version)
        if mode == 'auto':
            auto_profile=service.station['auto_profile']
            config=validate_profile(auto_profile,service.package)
            coordinator=VisionRuntimeCoordinator(uuid.uuid4().hex,config)
            return AutomaticRuntime(service,coordinator,observation,plc,log_owner,config,
                                    recovery_policy,profile=auto_profile)
        return IntegratedRuntime(service,coordinator,observation,plc,log_owner,config,
                                 recovery_policy or FaultPolicy())
    except BaseException:
        try:
            if service is not None: service.close()
        finally:
            observation.close()
            plc.close()
            log_owner.close()
        raise
