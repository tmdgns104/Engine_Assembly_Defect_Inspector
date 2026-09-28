"""기존 API/HMI를 유지하고 통합 제어·상태만 추가한다."""
import asyncio
import logging
from contextlib import asynccontextmanager
from functools import wraps

from fastapi.responses import JSONResponse
from apps.edge_service.inspection_api import create_app
from src.journal.sqlite import ConflictError


def create_integrated_app(runtime, catalog):
    app = create_app(runtime.service,catalog,own_service=False)

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            await asyncio.to_thread(runtime.close)

    app.router.lifespan_context = lifespan

    @app.middleware('http')
    async def log_request_error(request, call_next):
        try:
            response = await call_next(request)
        except Exception:
            logging.getLogger(__name__).exception('API 처리 오류: %s %s',request.method,request.url.path)
            return JSONResponse({'error':'INTERNAL_ERROR_SEE_RUNTIME_LOG'},status_code=500)
        if response.status_code >= 400:
            logging.getLogger(__name__).warning('API 요청 거부: %s %s status=%s',
                request.method,request.url.path,response.status_code)
        return response

    def guard_existing_mutation(endpoint,path):
        @wraps(endpoint)
        def guarded(*args, **kwargs):
            # 검사 cycle 시작과 기존 패키지/Mock 변경의 검사→실행 경쟁도 직렬화한다.
            with runtime.lock:
                if getattr(runtime,'operating',False):
                    raise ConflictError('AUTO_RUNNING_STOP_BEFORE_CONFIGURATION')
                if runtime.coordinator.active_cycle is not None:
                    raise ConflictError('INTEGRATED_CYCLE_OWNS_CONTROL')
                if path == '/api/v1/packages/activate' and hasattr(runtime,'activate_profile'):
                    body=kwargs.get('body') or (args[0] if args else {})
                    if body.get('id') not in catalog:
                        raise ValueError('LOCAL_PACKAGE_NOT_FOUND')
                    return runtime.activate_profile(catalog[body['id']],body.get('auto_profile') or runtime.profile)
                return endpoint(*args,**kwargs)
        return guarded

    for route in app.routes:
        path = getattr(route,'path','')
        guarded = path in ('/api/v1/packages/activate','/api/v1/inspection-jobs') or path.startswith(('/api/v1/mock/','/api/v1/calibrations/','/api/v1/lab/','/api/v1/live/'))
        if guarded and 'POST' in getattr(route,'methods',()):
            route.dependant.call = guard_existing_mutation(route.dependant.call,path)

    @app.get('/api/v1/runtime/status')
    def status():
        return runtime.status()

    @app.get('/api/v1/diagnostics/capture')
    def capture_status():
        with runtime.lock,runtime.service.lock:
            return dict(runtime.service.diagnostic_capture.value)

    @app.post('/api/v1/diagnostics/capture/start')
    def capture_start(body:dict):
        with runtime.lock,runtime.service.lock:
            return runtime.service.diagnostic_capture.start(body,dict(
                runtime_session_id=runtime.session_id,zone=getattr(runtime,'zone',None),
                operating=getattr(runtime,'operating',False),
                calibration_source=(runtime.service.calibration or {}).get('source_inspection_id'),
                bench_conditions='Camera position and product plane require operator confirmation; not conveyor validation'))

    @app.post('/api/v1/diagnostics/capture/stop')
    def capture_stop():
        with runtime.lock,runtime.service.lock:
            return runtime.service.diagnostic_capture.stop()

    if hasattr(runtime,'start_auto'):
        from fastapi.responses import HTMLResponse
        from pathlib import Path
        @app.get('/auto',response_class=HTMLResponse)
        def auto_hmi():
            return (Path(__file__).parent/'auto_hmi.html').read_text(encoding='utf-8')

        @app.post('/api/v1/runtime/auto/start')
        def auto_start():
            return runtime.start_auto()

        @app.post('/api/v1/runtime/auto/stop')
        def auto_stop():
            return runtime.stop_auto()

        @app.post('/api/v1/runtime/auto/recover-empty-area')
        def recover_empty_area(body:dict):
            return runtime.recover_empty_area(**body)

    if hasattr(runtime,'configure_zone'):
        @app.post('/api/v1/runtime/production/area-reference/approve')
        def approve_area_reference(body:dict): return runtime.approve_area_reference(**body)

        @app.post('/api/v1/runtime/production/zone')
        def production_zone(body:dict): return runtime.configure_zone(body)

        @app.post('/api/v1/runtime/production/mock/{action}')
        def production_mock(action:str,body:dict): return runtime.mock_action(action,body)

    @app.post('/api/v1/runtime/cycles')
    def start(body: dict):
        if runtime.service.lab.mode!='MANUAL': raise ConflictError('LAB_MODE_OWNS_TRIGGER')
        return runtime.start_cycle(body['runtime_session_id'],body['cycle_id'],body['view_assessment'])

    @app.post('/api/v1/runtime/observations')
    def observe(body: dict):
        return runtime.observe(body['runtime_session_id'],body['cycle_id'],body['observation'])

    @app.post('/api/v1/runtime/clearance')
    def clearance(body: dict):
        return runtime.clearance(**body)

    @app.post('/api/v1/runtime/recover-cycle')
    def recover_cycle(body: dict):
        return runtime.recover_cycle(**body)

    @app.post('/api/v1/runtime/recover-infrastructure')
    def recover_infrastructure(body: dict):
        return runtime.recover_infrastructure(body['actor'],body['reason'])

    @app.exception_handler(KeyError)
    async def missing(request,error):
        return JSONResponse({'error':'MISSING_FIELD: '+str(error)},status_code=422)

    @app.exception_handler(TypeError)
    async def invalid_type(request,error):
        return JSONResponse({'error':'INVALID_INPUT: '+str(error)},status_code=422)

    return app
