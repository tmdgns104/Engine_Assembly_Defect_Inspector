"""Authorize one bounded diagnostic window; never issue inspection/PLC commands."""
import time

from src.runtime.stopped_capture import StoppedCapture
from src.vision.run_capture import validate_run_request

PREFIX = '/api/v1/maintenance/run-capture'
MUTATIONS = frozenset((PREFIX+'/arm', PREFIX+'/stop'))


class RunCaptureControl:
    def __init__(self, runtime):
        self.runtime = runtime
        self.owner = None
        self.signals = None
        self.deadline = 0
        self.last_sample = 0
        self.last = dict(state='IDLE', interruption=None, diagnostic_only=True)

    def arm(self, body):
        request = validate_run_request(body)
        r = self.runtime
        if self.owner is not None:
            raise ValueError('RUN_CAPTURE_ALREADY_ACTIVE_OR_UNSAVED')
        signals = getattr(r.service,'run_capture_signals',None)
        if signals is None:
            raise ValueError('RUN_CAPTURE_WORKER_NOT_SUPPORTED')
        owner = StoppedCapture(r)._guard()
        signals.reset()
        result = r.service.diagnostic_capture.arm_run(request,
            dict(owner,run_capture_approved=True,plc_control=False),signals)
        self.owner, self.signals = owner, signals
        self.deadline = time.monotonic()+60
        self.last_sample = 0
        self.last = dict(state='ARMED_WAIT_WORKER',clip_id=request['clip_id'],interruption=None,
                         diagnostic_only=True,duration_seconds=request['duration_seconds'])
        return result

    def _interrupt(self, reason):
        if self.last['interruption'] is None:
            self.last['interruption'] = str(reason)
        self.stop()

    def stop(self):
        if self.owner is not None and self.signals:
            self.signals.stop_code.value = 1
            self.signals.flush_until.value = 0
            self.last['state'] = 'WAIT_SAFE_FLUSH'
            trace = getattr(self.runtime.service.diagnostic_capture,'trace',None)
            if hasattr(trace,'seal'): trace.seal()
        return self.status()

    def _snapshot(self, now):
        snap = self.runtime.gateway.read_snapshot(now)
        now = time.monotonic()
        if (not snap or not all(snap.get(k) is True for k in ('connected','fresh','bool_valid'))
                or any(type(snap.get(k)) not in (int,float) or not 0 <= now-snap[k] <= .5
                       for k in ('generated','received'))):
            raise ValueError('RUN_CAPTURE_FRESH_PLC_REQUIRED')
        return snap

    def _safe_flush(self, snap):
        r = self.runtime
        health, assembly = r.service.health(), r.assembly.status()
        # An inspection ERROR does not forbid saving its diagnostic evidence.
        # Physical STOP, no output/request and real storage idle still do.
        return bool(snap['controls'] == dict(Inspection_Request=False,Mc_Run=False,EStop_OK=True,Stop_PB=True)
            and snap.get('raw100') == '00000000' and not r.closing
            and not r.service.active and not health.get('storage_pending')
            and health.get('state') not in ('BUSY','CANCELLING','SWITCHING')
            and not r.handshake.token and not r.final_pending and not r.audit_pending
            and not assembly.get('pending') and not assembly.get('outstanding')
            and not assembly.get('active_identifier'))

    def poll(self, now):
        if self.owner is None: return
        # Revoke first. A stale callback cannot indefinitely authorize disk IO.
        self.signals.flush_until.value = 0
        capture = self.runtime.service.diagnostic_capture
        try:
            snap = self._snapshot(time.monotonic())
            r = self.runtime
            # runtime.session_id belongs to the product observation window:
            # every accepted PLC cycle renews it while this same runtime,
            # Service, camera Worker and PLC connection continue running.
            # Keep the arm-time tracking ID as provenance, not device identity.
            owner_same = (r.service.session == self.owner['service_session']
                and r.epoch == self.owner['camera_epoch']
                and r.service.generation == self.owner['worker_generation']
                and snap.get('boot') == self.owner['plc_boot']
                and snap.get('connection') == self.owner['plc_connection']
                and getattr(r.service,'run_capture_signals',None) is self.signals)
            state = capture.value.get('worker_state',capture.value.get('state'))
            if not owner_same:
                self._interrupt('RUN_CAPTURE_OWNER_CHANGED')
            elif state == 'ERROR' and not self.signals.stop_code.value:
                self._interrupt('RUN_CAPTURE_WORKER_ERROR:'+str(capture.value.get('error')))
            elif not self.signals.stop_code.value:
                controls = snap['controls']
                health = r.service.health()
                # The existing PLC contract uses Stop_PB=True for a healthy,
                # released STOP circuit, including while Mc_Run=True.
                if (r.closing or r.error or not controls.get('EStop_OK') or not controls.get('Stop_PB')
                        or not health.get('worker_alive') or not health.get('camera_ready')
                        or health.get('error')):
                    self._interrupt('RUN_CAPTURE_RUNTIME_OR_DEVICE_FAULT')
                elif not self.signals.started_at.value:
                    if now >= self.deadline:
                        self._interrupt('RUN_CAPTURE_ARM_TIMEOUT')
                    elif controls.get('Mc_Run'):
                        if state != 'ARMED' or controls.get('Inspection_Request'):
                            self._interrupt('RUN_CAPTURE_START_BEFORE_READY')
                        else:
                            self.signals.started_at.value = now
                            self.last['state'] = 'RECORDING'
                    elif controls != dict(Inspection_Request=False,Mc_Run=False,EStop_OK=True,Stop_PB=True):
                        self._interrupt('RUN_CAPTURE_ARM_CONTROLS_CHANGED')
                elif (not controls.get('Mc_Run')
                      or now >= self.signals.started_at.value+self.last['duration_seconds']
                      or state in ('WAIT_SAFE_FLUSH','SAVING','ERROR','SAVED')):
                    self.stop()
            if self.signals.started_at.value and not self.signals.stop_code.value and now-self.last_sample >= .1:
                capture.record(dict(clip_id=self.last['clip_id'],event='RUN_CAPTURE_STATE',
                    monotonic_s=now,plc=snap,inspection_id=(r.service.active or {}).get('inspection_id'),
                    service_state=r.service.health().get('state'),handshake_state=getattr(r.handshake,'state',None),
                    request_token=r.handshake.token,line_state=getattr(r,'line_state',None)))
                self.last_sample = now
            trace = getattr(capture,'trace',None)
            if getattr(capture,'trace_error',None) or getattr(trace,'error',None):
                self._interrupt('RUN_CAPTURE_TRACE_FAILED')
            if self.signals.stop_code.value and self._safe_flush(snap):
                self.signals.flush_until.value = time.monotonic()+.15
                if hasattr(trace,'permit_flush'): trace.permit_flush(self.signals)
            trace_pending = bool(getattr(getattr(trace,'queue',None),'unfinished_tasks',0))
            if state in ('SAVED','SAVED_WITH_DROPS','ERROR') and not trace_pending:
                self.last['state'] = 'ERROR' if capture.value.get('error') or getattr(capture,'trace_error',None) or getattr(trace,'error',None) else state
                self.owner = None
                self.signals.flush_until.value = 0
        except Exception as error:
            self.signals.flush_until.value = 0
            self._interrupt(type(error).__name__+':'+str(error))

    def status(self):
        return dict(self.last,active=self.owner is not None)


def install_run_capture_routes(app, runtime):
    runtime.run_capture = RunCaptureControl(runtime)

    @app.get(PREFIX+'/status')
    def status():
        with runtime.lock:
            return runtime.run_capture.status()

    @app.post(PREFIX+'/arm')
    def arm(body:dict):
        with runtime.lock,runtime.service.lock:
            return runtime.run_capture.arm(body)

    @app.post(PREFIX+'/stop')
    def stop(body:dict):
        if body: raise ValueError('RUN_CAPTURE_STOP_REQUIRES_EMPTY_BODY')
        with runtime.lock,runtime.service.lock:
            return runtime.run_capture.stop()
