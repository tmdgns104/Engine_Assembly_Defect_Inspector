"""Field HMI with an opt-in authenticated preparation path; never web START."""
import json
from pathlib import Path
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse


def line_view(status, identity):
    """Present recorded facts; preview/BOOL defaults are never final verdicts."""
    plc = status.get('plc') or {}
    service = status.get('inspection_service') or {}
    assembly = status.get('assembly_component') or {}
    packet = status.get('latest_frame') or {}
    fresh = bool(packet and service.get('camera_ready') and not status.get('stale_observation'))
    line = status.get('line_state') or 'INITIALIZING'
    phase, title, detail = 'WAIT_REQUEST', '검사 대기중', 'PLC의 새 검사 요청을 기다립니다.'
    verdict = 'NOT_RUN'
    if status.get('error') or service.get('error') or assembly.get('error'):
        phase, title, detail = 'ERROR', '시스템 오류 · 검사 중단', str(status.get('error') or service.get('error') or assembly.get('error'))
    elif not fresh:
        phase, title, detail = 'WAIT_CAMERA', '새 영상 수신 대기', '카메라 미준비 또는 영상 갱신 지연입니다. 현재 제품의 판정이 아닙니다.'
    elif not plc.get('available'):
        phase, title, detail = 'WAIT_PLC', 'PLC 연결 대기', '카메라 영상과 PLC 통신 상태를 별도로 확인합니다.'
    elif line == 'WAIT_FIELD_PROFILE':
        phase, title, detail = 'BLOCKED', '검사 대기중', '현재 벨트의 검사 위치 설정이 미완료입니다. 영상 미리보기만 실행 중입니다.'
    elif plc.get('state') == 'INSPECTING':
        phase, title, detail = 'INSPECTING', '엔진 검사 중', '현재 요청에 연결된 새 영상으로 기존 검사와 네 부품 조립 검사를 수행합니다.'
        verdict = 'PENDING'
    elif plc.get('state') == 'REQUEST_LATCHED':
        phase, title, detail = 'WAIT_PRODUCT', 'PLC 요청 접수 · 영상 조건 대기', '제품 위치·새 프레임·안정 조건을 확인 중입니다. 검사 완료가 아닙니다.'
    elif plc.get('state') in ('RESYNC_REQUIRED', 'WAIT_PRODUCT_CLEAR', 'HOLD'):
        phase, title, detail = 'HOLD', '다음 검사 보류', {
            'LEGACY_REQUEST_WITHDRAWN_RESULT_BLOCKED': '검사 요청이 해제되어 이번 결과 전송을 막았습니다. 제품 이탈을 기다립니다.',
            'LEGACY_COMPLETED_WAIT_PRODUCT_CLEAR': '이전 결과 전송 후 제품 이탈을 기다립니다. 같은 제품의 중복 요청은 제외합니다.'
        }.get(line, plc.get('reason') or line)
    elif not assembly.get('ready'):
        phase, title, detail = 'BLOCKED', '분류기 준비 대기', '네 부품 상태 검사는 최종 판정의 필수 요소입니다.'
    elif not plc.get('network_plc_writes_enabled'):
        phase, title, detail = 'BLOCKED', '결과 전송 비활성', '현재 설정은 PLC 읽기 전용입니다. 자동공정 실행 준비 완료가 아닙니다.'
    latest = next((dict(row) for row in status.get('history', [])
                   if row.get('source') in ('INTEGRATED_ACTUAL_INSPECTION', 'NO_ACTUAL_INSPECTION')
                   and row.get('synthetic') is False
                   and row.get('decision') in ('PASS', 'FAIL', 'REVIEW', 'ERROR')), None)
    legacy = plc.get('contract_version') == 'LEGACY_THREE_BOOL'
    if latest and legacy:
        latest['plc_consumption_confirmed'] = False
    if latest:
        latest['existing_inspector'] = latest.get('existing_decision', latest.get('existing_inspector'))
        latest['assembly_inspector'] = latest.get('assembly_decision', latest.get('assembly_inspector'))
        latest['journal_saved'] = True  # History is appended only after the durable final.
        # Receipt/consumption must be tied to this cycle, not a later global count.
        snap = plc.get('snapshot') or {}
        token = f"{snap.get('boot',0):016x}:{snap.get('connection',0)}:{snap.get('request_id',0)}"
        latest['cyclic_done_reset_observed'] = bool(latest.get('cyclic_done_reset_observed') or
            (token == latest.get('request_token') and snap.get('phase') == 'READY_NEXT'
             and snap.get('completed_count') == snap.get('request_id')))
    approval = status.get('initial_approval') or {}
    supervised = approval if approval.get('policy') == 'SUPERVISED_REPEAT_TEST' else None
    if supervised and phase not in ('ERROR', 'WAIT_CAMERA', 'WAIT_PLC', 'INSPECTING', 'WAIT_PRODUCT'):
        if (supervised.get('challenge') or {}).get('eligible'):
            phase, title, detail = 'PREPARE', '다음 검사 · 사용자 확인 대기', '벨트 실제 정지와 이전 제품 정리 후 아래 확인란을 선택하세요.'
        elif supervised.get('state') == 'RESERVED':
            phase, title, detail = 'WAIT_START', '승인 접수 · 시작 준비 확인 중', '새 승인이 OpENer에 반영되는지 확인 중입니다. 아직 START를 누르지 마세요.'
            snap = plc.get('snapshot') or {}
            if snap.get('approval_id') == supervised.get('approval_id') and snap.get('phase') in ('SYNC_LOW', 'IDLE'):
                title, detail = '검사 준비됨 · 현장 START 대기', '손을 뗀 상태에서 실제 PLC START를 한 번 누르세요.'
    values = plc.get('last_values') or {}
    return dict(phase=phase, title=title, detail=detail, verdict=verdict,
        issue=status.get('runtime_issue'), runtime_loop_alive=status.get('runtime_loop_alive', False),
        line_state=line, release=identity.get('release_id') or identity.get('app_release'),
        mode=identity.get('mode'), camera=dict(fresh=fresh, frame_id=packet.get('frame_id'),
            source_time=(packet.get('freshness') or {}).get('received_at')),
        progress=service.get('progress') or {},
        current_inspection_id=plc.get('inspection_id'),
        plc=dict(connected=plc.get('available') is True,
            request=plc.get('Inspection_Request'), result_bit=values.get('Jetson_Result'),
            done=values.get('Jetson_Done'), publication_enabled=plc.get('network_plc_writes_enabled') is True,
            publication_status=plc.get('publication_status', 'NOT_STARTED'),
            consumption_confirmed=not legacy and plc.get('plc_consumption_confirmed') is True,
            duplicate_requests_ignored=plc.get('duplicate_requests_ignored', 0)),
        last_result=latest, counts=status.get('integrated_counts') or {}, supervised=supervised,
        motor_feedback='UNVERIFIED', final_policy='기존 검사 + 네 부품 조립 검사 모두 필수')


def configure_line_web(app, runtime, identity):
    from src.runtime.supervised_web import PreparationAccess, PREPARE_PATH
    access = None
    web = getattr(runtime, 'line_profile', {}).get('supervised_web', {})
    if web.get('enabled') is True:
        if not runtime._supervised_policy():
            raise ValueError('SUPERVISED_WEB_REQUIRES_SUPERVISED_POLICY')
        access = PreparationAccess(runtime.initial_approval.root, web.get('allowed_hosts'))

    @app.middleware('http')
    async def read_only_field_ui(request, call_next):
        if request.method not in ('GET', 'HEAD'):
            if request.method == 'POST' and request.url.path == PREPARE_PATH and access:
                if not access.permits(request):
                    return JSONResponse({'error':'SUPERVISOR_AUTHORIZATION_REQUIRED'}, status_code=403)
                try:
                    # Reject over-size/chunked bodies without buffering unbounded data.
                    if not 1 <= int(request.headers.get('content-length', '0')) <= 2048:
                        raise ValueError('BOUNDED_JSON_BODY_REQUIRED')
                    raw = b''
                    async for part in request.stream():
                        raw += part
                        if len(raw) > 2048: raise ValueError('BODY_TOO_LARGE')
                    body = json.loads(raw)
                    if not isinstance(body, dict) or set(body) != {'challenge_id','confirmations'}:
                        raise ValueError('EXPLICIT_PREPARATION_FIELDS_REQUIRED')
                    result = runtime.prepare_supervised(body['challenge_id'], body['confirmations'])
                    return JSONResponse(result, status_code=202, headers={'Cache-Control':'no-store'})
                except (ValueError, TypeError, KeyError):
                    return JSONResponse({'error':'PREPARATION_REJECTED_REFRESH_AND_RECONFIRM'}, status_code=409)
            return JSONResponse({'error': 'PHYSICAL_BUTTONS_ONLY_IN_STANDALONE_MODE'}, status_code=403)
        if request.url.path == '/auto' and access:
            return RedirectResponse('/line')
        return await call_next(request)

    @app.get('/api/v1/release')
    def release(): return identity

    @app.get('/api/v1/line/view')
    def view(): return line_view(runtime.status(), identity)

    @app.get('/api/v1/line/final/{identifier}')
    def final(identifier: str):
        runtime.assembly.checked_id(identifier)
        journal = runtime.service.journal
        with journal.lock:
            row = journal.db.execute('SELECT value FROM service_state WHERE key=?',
                                     ('integrated_decision:'+identifier,)).fetchone()
        return json.loads(row[0]) if row else {'state': 'PENDING_OR_NOT_RUN'}

    # Existing camera/evidence pages stay available. The line page states what
    # is final vs. a component and never calls a mutation API on page load.
    @app.get('/line', response_class=HTMLResponse)
    def line():
        legacy = identity.get('plc_contract') == 'LEGACY_THREE_BOOL'
        note = ('기존 PLC 요청·결과·완료 3개 신호를 사용합니다. 푸셔·컨베이어 로직은 PLC 원본 그대로입니다. '
                'Jetson은 모터·푸셔를 명령하지 않습니다. 쓰기 응답 확인은 PLC의 결과 소비 확인과 다릅니다.'
                if legacy else '출력 명령과 실제 모터 피드백은 다릅니다. 푸셔는 제외되어 있습니다.')
        template = Path(__file__).resolve().parents[2] / 'apps/edge_service/line_hmi.html'
        return template.read_text(encoding='utf-8').replace('__CONTROL_NOTE__', note)
