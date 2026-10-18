"""Bounded maintenance recording through the existing camera Worker.

This component owns no camera, inspection request, PLC output or decision. A
fresh physical stop is required throughout recording; loss of that condition
ends the diagnostic clip and leaves a separate interruption record.
"""
import math
import time
from urllib.parse import urlsplit

PREFIX = '/api/v1/maintenance/diagnostic-capture'
MUTATIONS = frozenset((PREFIX+'/start', PREFIX+'/stop'))


def local_capture_request(request):
    host = request.headers.get('host', '')
    return bool(request.client and request.client.host in ('127.0.0.1', '::1')
        and urlsplit('//'+host).hostname in ('127.0.0.1', 'localhost', '::1')
        and request.headers.get('origin') == request.url.scheme+'://'+host
        and request.headers.get('content-type', '').split(';', 1)[0].strip() == 'application/json'
        and request.headers.get('sec-fetch-site', 'same-origin') in ('same-origin', 'none'))


class StoppedCapture:
    def __init__(self, runtime):
        self.runtime = runtime
        self.lease = None
        self.last = dict(state='IDLE', interruption=None)
        self.stop_requested = False

    def _guard(self):
        r = self.runtime
        if r.closing or r.error or r.gateway.contract_version != 'OPENER_CYCLIC':
            raise ValueError('DIAGNOSTIC_RUNTIME_NOT_READY')
        snapshot = r.gateway.read_snapshot(time.monotonic())
        now = time.monotonic()
        if (not snapshot or not all(snapshot.get(k) is True for k in ('connected', 'fresh', 'bool_valid'))
                or any(not isinstance(snapshot.get(k), (int,float)) or not 0 <= now-snapshot[k] <= .5
                       for k in ('generated', 'received'))):
            raise ValueError('DIAGNOSTIC_FRESH_PLC_REQUIRED')
        if (snapshot.get('controls') != dict(Inspection_Request=False, Mc_Run=False, EStop_OK=True, Stop_PB=True)
                or snapshot.get('raw100') != '00000000'
                or snapshot.get('phase') not in ('SYNC_LOW', 'DISARMED')):
            raise ValueError('DIAGNOSTIC_PHYSICAL_STOP_AND_REQUEST_LOW_REQUIRED')
        health, assembly = r.service.health(), r.assembly.status()
        if (health.get('state') != 'IDLE' or not health.get('ready') or not health.get('camera_ready')
                or not health.get('worker_alive') or health.get('storage_pending')
                or r.service.active or r.handshake.token or r.final_pending or r.audit_pending
                or not assembly.get('ready') or assembly.get('pending') or assembly.get('outstanding')
                or assembly.get('active_identifier')):
            raise ValueError('DIAGNOSTIC_CAMERA_AND_STORAGE_IDLE_REQUIRED')
        return dict(runtime_session=r.session_id, service_session=r.service.session,
            camera_epoch=r.epoch, worker_generation=r.service.generation,
            plc_boot=snapshot['boot'], plc_connection=snapshot['connection'], request_id=snapshot['request_id'])

    def start(self, body):
        from src.vision.diagnostic_capture import validate_request
        if self.lease or self.runtime.service.diagnostic_capture.value['state'] in ('STARTING','ARMED','RECORDING','WAIT_SAFE_FLUSH','SAVING'):
            raise ValueError('DIAGNOSTIC_CAPTURE_ALREADY_ACTIVE')
        if set(body)-{'clip_id','duration_seconds','max_frames','max_bytes','condition'}:
            raise ValueError('UNKNOWN_DIAGNOSTIC_CAPTURE_INPUT')
        bounded = dict(duration_seconds=5, max_frames=100, max_bytes=128*1024*1024)
        bounded.update(body)
        # Avoid NaN and reject larger requests instead of silently truncating them.
        for key, maximum in (('duration_seconds',5),('max_frames',100),('max_bytes',128*1024*1024)):
            value=bounded[key]
            if type(value) not in (int,float) or not math.isfinite(value) or not 1 <= value <= maximum:
                raise ValueError('DIAGNOSTIC_MAINTENANCE_LIMIT:'+key)
        bounded = validate_request(bounded)
        identity = self._guard()
        result = self.runtime.service.diagnostic_capture.start(bounded,
            dict(identity, maintenance_diagnostic_only=True, plc_control=False,
                 visibility='Scene condition is operator metadata, never detector truth'))
        self.lease = identity
        self.stop_requested = False
        self.last = dict(state='RECORDING', clip_id=bounded['clip_id'], interruption=None)
        return result

    def stop(self):
        if self.lease and not self.stop_requested:
            self.runtime.service.diagnostic_capture.stop()
            self.stop_requested = True
        return self.status()

    def poll(self, now):
        if self.lease is None:
            return
        capture = self.runtime.service.diagnostic_capture
        if capture.value['state'] not in ('STARTING','RECORDING','SAVING'):
            self.last['state'] = capture.value['state']
            self.lease = None
            return
        if self.stop_requested:
            return
        try:
            if self._guard() != self.lease:
                raise ValueError('DIAGNOSTIC_CAPTURE_OWNER_CHANGED')
        except Exception as error:
            if self.last['interruption'] is None:
                self.last['interruption'] = str(error)
                try:
                    capture.record(dict(clip_id=self.last['clip_id'], event='MAINTENANCE_CAPTURE_INTERRUPTED',
                        reason=str(error), monotonic=now, valid_for_capture_acceptance=False))
                except Exception as trace_error:
                    self.last['trace_error'] = type(trace_error).__name__+':'+str(trace_error)
            try:
                self.stop()
            except Exception as stop_error:
                # The Worker also has the fixed five-second limit. Diagnostic
                # queue failure must not become an inspection result or PLC fault.
                self.last['stop_error'] = type(stop_error).__name__+':'+str(stop_error)

    def status(self):
        return dict(self.last, active=self.lease is not None, diagnostic_only=True)


def install_capture_routes(app, runtime):
    runtime.maintenance_capture = StoppedCapture(runtime)

    @app.get(PREFIX+'/status')
    def status():
        with runtime.lock:
            return runtime.maintenance_capture.status()

    @app.post(PREFIX+'/start')
    def start(body:dict):
        with runtime.lock, runtime.service.lock:
            return runtime.maintenance_capture.start(body)

    @app.post(PREFIX+'/stop')
    def stop(body:dict):
        if body:
            raise ValueError('DIAGNOSTIC_STOP_REQUIRES_EMPTY_BODY')
        with runtime.lock, runtime.service.lock:
            return runtime.maintenance_capture.stop()
