"""Field HMI with an opt-in authenticated preparation path; never web START."""
import json
from pathlib import Path
from urllib.parse import urlsplit
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse


def field_reset_allowed(request, hosts):
    """A local same-origin Reset action, not a generated operator capability."""
    host = request.headers.get('host', '')
    return bool(host in hosts and request.headers.get('origin') == request.url.scheme+'://'+host
                and request.headers.get('content-type','').split(';',1)[0].strip() == 'application/json'
                and request.headers.get('sec-fetch-site','same-origin') in ('same-origin','none'))


def saved_line_history(journal):
    """Restore display evidence only; never put old results into the publisher."""
    with journal.lock:
        rows = journal.db.execute(
            "SELECT i.inspection_id,s.value FROM inspections i JOIN service_state s "
            "ON s.key='integrated_decision:'||i.inspection_id "
            "WHERE i.state='COMPLETE' ORDER BY i.completed_at DESC LIMIT 30").fetchall()
        history = []
        for identifier, value in rows:
            final = json.loads(value)
            if (final.get('inspection_id') == identifier and final.get('synthetic') is False
                    and final.get('source') in ('INTEGRATED_ACTUAL_INSPECTION','NO_ACTUAL_INSPECTION')
                    and final.get('decision') in ('PASS','FAIL','REVIEW','ERROR')):
                history.append(dict(final, publication_status='UNKNOWN', plc_consumption_confirmed=False))
        if not history:
            return []
        identifiers = [row['inspection_id'] for row in history]
        placeholders = ','.join('?' for _ in identifiers)
        events = journal.db.execute(
            "SELECT event_type,payload_json FROM events WHERE event_type IN "
            "('PLC_CYCLIC_COMPLETION_OBSERVED','SUPERVISED_CYCLIC_COMPLETION_OBSERVED') "
            "AND json_extract(payload_json,'$.payload.inspection_id') IN ("+placeholders+") "
            "ORDER BY occurred_at DESC LIMIT 120", identifiers).fetchall()
    for _, payload in events:
        event = json.loads(payload).get('payload', {})
        for row in history:
            if (row['inspection_id'] == event.get('inspection_id') and row.get('request_token')
                    and row['request_token'] == event.get('request_token')):
                row.update(cyclic_done_reset_observed=True, publication_status='CYCLIC_DONE_AND_REQUEST_RESET')
    return history


def with_saved_history(status, saved):
    """Current-session receipt details take precedence over restored display rows."""
    rows = {row['inspection_id']: row for row in saved}
    rows.update({row['inspection_id']: row for row in status.get('history', [])})
    return dict(status, history=sorted(rows.values(), key=lambda row: row.get('completed_at') or '', reverse=True)[:30])


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
        phase, title, detail = 'INSPECTING', '엔진 검사 중', '현재 요청에 연결된 새 영상으로 기본 부품 검사와 오조립 참고 분석을 수행합니다.'
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
            (token == latest.get('request_token') and snap.get('transaction_settled') is True
             and snap.get('raw100') == '00000000'
             and not (snap.get('controls') or {}).get('Inspection_Request')))
    approval = status.get('initial_approval') or {}
    supervised = approval if approval.get('policy') == 'SUPERVISED_REPEAT_TEST' else None
    if supervised and phase not in ('ERROR', 'WAIT_CAMERA', 'WAIT_PLC', 'INSPECTING', 'WAIT_PRODUCT'):
        if (supervised.get('challenge') or {}).get('eligible'):
            phase, title, detail = 'PREPARE', '감독형 시험 모드 · 준비 대기', '현재는 감독형 유지보수 시험 정책입니다. PLC 자동 반복 정책이 활성화된 상태가 아닙니다.'
        elif supervised.get('state') == 'RESERVED':
            phase, title, detail = 'WAIT_START', '승인 접수 · 시작 준비 확인 중', '새 승인이 OpENer에 반영되는지 확인 중입니다. 아직 START를 누르지 마세요.'
            snap = plc.get('snapshot') or {}
            if snap.get('approval_id') == supervised.get('approval_id') and snap.get('phase') in ('SYNC_LOW', 'IDLE'):
                title, detail = '검사 준비됨 · 현장 START 대기', '손을 뗀 상태에서 실제 PLC START를 한 번 누르세요.'
    values = plc.get('last_values') or {}
    automatic = status.get('plc_cycle')
    if automatic and automatic.get('failed'):
        phase, title = 'ERROR', '자동검사 보류 · 현장 STOP 필요'
        detail = ('자동 복구·결과 재송신을 차단했습니다. 현장 STOP으로 운전을 해제하고 '
                  'Request/Result/Done 및 미완료 기록을 확인한 뒤 감독하 유지보수 복구가 필요합니다. '
                  +str(automatic.get('reason') or 'AUTOMATIC_ADMISSION_FAILED'))
    if automatic and phase not in ('ERROR', 'WAIT_CAMERA', 'WAIT_PLC', 'INSPECTING', 'WAIT_PRODUCT'):
        reason = automatic.get('reason')
        phase, title, detail = 'HOLD', '자동검사 · 다음 제품 접수 보류', {
            'WAIT_AUTO_QUALIFICATION_OR_HEALTH': '현장 자동운전 설정 검증 또는 카메라·검사 준비가 필요합니다.',
            'WAIT_STOPPED_BASELINE_AND_NEW_START': 'PLC 정지 상태 확인 후 현장 START를 새로 눌러야 합니다.',
            'WAIT_REQUEST_AND_RESULT_DONE_RESET': '이전 PLC Request 또는 Result/Done 해제를 기다립니다.',
            'PREVIOUS_RESULT_IDENTITY_MISMATCH': '연결 또는 요청 식별자가 이전 완료 기록과 다릅니다. 현장 STOP 후 감독하에 기록을 대조해야 합니다.',
            'PREVIOUS_RESULT_NOT_DURABLE_OR_IDENTIFIED': '이전 검사 저장·요청 식별을 확인할 수 없습니다. 현장 STOP 후 Journal을 점검하세요.',
        }.get(reason, reason or '상태 확인 중')
        if reason == 'WAIT_NEW_PHYSICAL_START':
            phase, title, detail = 'WAIT_START', '검사 준비됨 · 현장 START 대기', '웹 조작 없이 PLC의 실제 START 버튼으로 운전을 시작합니다.'
        elif reason == 'WAIT_PLC_REQUEST':
            phase, title, detail = 'WAIT_REQUEST', '검사 대기중', '센서·PLC의 새 검사 요청을 자동으로 기다립니다. 브라우저는 닫아도 됩니다.'
    if automatic and automatic.get('product_identity_reason') and phase not in ('ERROR', 'WAIT_CAMERA', 'WAIT_PLC', 'INSPECTING'):
        reason = str(automatic['product_identity_reason'])
        if automatic.get('request_identity_block'):
            phase, title = 'HOLD', '새 제품 식별 실패 — 검사 미실행'
            detail = ('현재 요청의 제품 구분 근거를 기다립니다. 요청 전에 관찰한 같은 진입의 근거가 '
                      '기한 안에 확인되면 자동 검사하며, 부족하면 검사 미실행 ERROR·NG로 기록합니다. '+reason)
        elif (automatic.get('product_passage') or {}).get('invalid') or reason=='PREVIOUS_RUNTIME_PRODUCT_EXIT_UNPROVEN':
            phase, title = 'HOLD', '제품 관찰 복구 필요'
            detail = '이전 제품 문맥을 입증할 수 없습니다. 현재 제품의 검사 판정이 아닙니다. '+reason
        else:
            phase, title = 'WAIT_PRODUCT_MOVEMENT', '다음 제품 준비 중 — 이전 제품 이동 관찰'
            detail = '이전 제품의 이송과 새 제품의 진입을 자동으로 관찰합니다. 화면 전체가 비어 있을 필요는 없습니다. '+reason
    aborted = status.get('aborted_inspection')
    if aborted:
        phase, title, verdict = 'ABORTED', '검사 중단 · 현장 STOP 및 복구 필요', 'INCOMPLETE'
        detail = ('원시 AI 검사 '+str(aborted.get('raw_decision') or '미확인')+
                  ' · 원시 Journal '+str(aborted.get('raw_journal'))+
                  ' · 필수 조립 검사 '+str(aborted.get('assembly'))+
                  ' · 통합 최종판정 '+str(aborted.get('integrated'))+
                  ' · PLC '+str(aborted.get('plc_publication')))
    return dict(phase=phase, title=title, detail=detail, verdict=verdict, aborted_inspection=aborted,
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
        automatic=automatic, recent_results=[{k:row.get(k) for k in
            ('inspection_id','decision','reason','completed_at','plc_result_value','publication_status')}
            for row in list(status.get('history', []))[:30]],
        motor_feedback='UNVERIFIED', final_policy='필수 부품 결합 유무만 PASS/FAIL · 오조립은 참고용(최종 판정에 미반영)')


def configure_line_web(app, runtime, identity):
    from src.runtime.stopped_capture import MUTATIONS, local_capture_request, install_capture_routes
    install_capture_routes(app, runtime)
    from src.runtime.run_capture import MUTATIONS as RUN_MUTATIONS, install_run_capture_routes
    install_run_capture_routes(app, runtime)
    from src.runtime.supervised_web import PreparationAccess, PREPARE_PATH
    access = None
    recovery_access = None
    restored_history = None
    web = getattr(runtime, 'line_profile', {}).get('supervised_web', {})
    if web.get('enabled') is True:
        if not runtime._supervised_policy():
            raise ValueError('SUPERVISED_WEB_REQUIRES_SUPERVISED_POLICY')
        access = PreparationAccess(runtime.initial_approval.root, web.get('allowed_hosts'))
    maintenance = getattr(runtime, 'line_profile', {}).get('maintenance_recovery', {})
    if maintenance.get('enabled') is True:
        if not runtime._automatic_policy():raise ValueError('AUTOMATIC_MAINTENANCE_ONLY')
        hosts = maintenance.get('allowed_hosts')
        if (not isinstance(hosts,list) or not hosts or len(hosts)>8
                or any(not isinstance(host,str) or not host or '/' in host or '@' in host or '*' in host
                       or urlsplit('//'+host).netloc != host for host in hosts)):
            raise ValueError('EXPLICIT_MAINTENANCE_WEB_HOSTS_REQUIRED')
        recovery_access = frozenset(hosts)

    @app.middleware('http')
    async def read_only_field_ui(request, call_next):
        if request.method not in ('GET', 'HEAD'):
            if request.method == 'POST' and request.url.path in MUTATIONS | RUN_MUTATIONS:
                if not local_capture_request(request):
                    return JSONResponse({'error':'LOCAL_SAME_ORIGIN_DIAGNOSTIC_REQUIRED'}, status_code=403)
                # The existing inspection session-token middleware still runs.
                # Physical STOP and idle checks run inside the endpoint lock.
                return await call_next(request)
            if request.method == 'POST' and request.url.path == '/api/v1/maintenance/product-context/close' and recovery_access:
                if not field_reset_allowed(request,recovery_access):
                    return JSONResponse({'error':'LOCAL_SAME_ORIGIN_RESET_REQUIRED'},status_code=403)
                try:
                    if not 1 <= int(request.headers.get('content-length','0')) <= 2048:
                        raise ValueError('BOUNDED_JSON_BODY_REQUIRED')
                    raw=b''
                    async for part in request.stream():
                        raw+=part
                        if len(raw)>2048:raise ValueError('BODY_TOO_LARGE')
                    body=json.loads(raw)
                    if not isinstance(body,dict) or set(body)!={'identifier','actor','reason','confirmations'}:
                        raise ValueError('EXPLICIT_CONTEXT_RECOVERY_FIELDS_REQUIRED')
                    return JSONResponse(runtime.close_previous_product_context(**body),headers={'Cache-Control':'no-store'})
                except (ValueError,KeyError,TypeError) as error:
                    return JSONResponse({'error':str(error)},status_code=409)
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
        if request.url.path == '/auto':
            return RedirectResponse('/line')
        return await call_next(request)

    @app.get('/api/v1/release')
    def release(): return identity

    @app.get('/api/v1/line/view')
    def view():
        nonlocal restored_history
        # One bounded Journal read per service, independent from preview polling.
        if restored_history is None:
            restored_history = saved_line_history(runtime.service.journal)
        return line_view(with_saved_history(runtime.status(), restored_history), identity)

    @app.get('/api/v1/line/consumed-frames')
    def consumed_frames():
        return JSONResponse(runtime.consumed_frame_snapshot(),headers={'Cache-Control':'no-store'})

    @app.get('/api/v1/maintenance/product-context/status')
    def recovery_status():
        value=(runtime.previous_product_recovery_status() if recovery_access else
               dict(eligible=False,reason='MAINTENANCE_RECOVERY_DISABLED'))
        return JSONResponse(dict(value,enabled=recovery_access is not None),headers={'Cache-Control':'no-store'})

    @app.get('/line_details.js')
    def line_details():
        from fastapi.responses import Response
        path=Path(__file__).resolve().parents[2]/'apps/edge_service/line_details.js'
        return Response(path.read_text(encoding='utf-8'),media_type='application/javascript',
                        headers={'Cache-Control':'no-store'})

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
    def page(maintenance=False):
        legacy = identity.get('plc_contract') == 'LEGACY_THREE_BOOL'
        note = ('기존 PLC 요청·결과·완료 3개 신호를 사용합니다. 푸셔·컨베이어 로직은 PLC 원본 그대로입니다. '
                'Jetson은 모터·푸셔를 명령하지 않습니다. 쓰기 응답 확인은 PLC의 결과 소비 확인과 다릅니다.'
                if legacy else '출력 명령과 실제 모터 피드백은 다릅니다. 푸셔는 제외되어 있습니다.')
        template = Path(__file__).resolve().parents[2] / 'apps/edge_service/line_hmi.html'
        html = template.read_text(encoding='utf-8').replace('__CONTROL_NOTE__', note)
        parts = dict(MAINTENANCE_PANEL='', MAINTENANCE_SCRIPT='', MAINTENANCE_LINK='',
                     MAINTENANCE_RESET='', MAINTENANCE_RENDER='')
        if maintenance:
            parts.update(MAINTENANCE_PANEL=template.with_name('supervised_panel.html').read_text(encoding='utf-8'),
                MAINTENANCE_SCRIPT=template.with_name('supervised_panel.js').read_text(encoding='utf-8'),
                MAINTENANCE_LINK='<a id="prepare-link" href="#supervised-panel" hidden>감독형 유지보수 시험 준비</a>',
                MAINTENANCE_RESET='prepareChallenge=null;checks().forEach(c=>c.checked=false);prepareEnabled();',
                MAINTENANCE_RENDER='renderSupervised(v.supervised,live&&v.plc.connected&&v.runtime_loop_alive);')
        for key, value in parts.items():
            html = html.replace('__'+key+'__', value)
        return html

    @app.get('/line', response_class=HTMLResponse)
    def line():
        return page()

    @app.get('/maintenance/supervised', response_class=HTMLResponse)
    def supervised_maintenance():
        if not access:
            return JSONResponse({'error':'SUPERVISED_MAINTENANCE_DISABLED'}, status_code=403)
        return page(maintenance=True)
