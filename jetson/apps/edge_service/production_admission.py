"""Reserve one production command without owning Journal I/O or PLC authority.

Runtime validates the current PLC/track before calling activation. The storage
owner durably admits the immutable job first; this module only then dispatches
it, with an extra frame cutoff at that durable completion. Late completions of
released reservations never become commands for a later request.
"""
from dataclasses import dataclass
import json
import math
import queue
import time
import uuid

from src.camera.fresh_frame import FreshFrameSelector, TriggerContext, finite_number
from src.journal.sqlite import ConflictError
from src.configuration import recorded_package


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


@dataclass(frozen=True)
class ProductionAdmission:
    admission_id: str
    generation: str
    session_id: int
    runtime_session_id: str
    camera_epoch: str
    package_sha256: str
    prepared_monotonic: float
    deadline_monotonic: float
    job_json: str
    calibration_json: str
    experiment_json: str

    def payload(self):
        """Return a detached job; mutating it cannot change the reservation."""
        return json.loads(self.job_json)

    @property
    def job(self):
        return self.payload()


def _camera_epoch(service, now):
    """Only process-local evidence: no status(), SQL, disk usage or fsync."""
    heartbeat_at = service.heartbeat.value
    # The child may renew between caller timestamp and this sample.
    now = time.monotonic()
    if not service.process or not service.process.is_alive():
        raise ConflictError('WORKER_EXITED')
    if not 0 <= now - heartbeat_at <= 5:
        raise ConflictError('WORKER_HEARTBEAT_LOST')
    preview = service.preview
    if (not preview or not 0 <= now - service.preview_received < 2
            or preview.get('generation') != service.generation):
        raise ConflictError('CAMERA_NOT_READY')
    epoch = preview.get('freshness', {}).get('camera_epoch')
    if not isinstance(epoch, str) or not epoch:
        raise ConflictError('CAMERA_EPOCH_REQUIRED')
    return epoch


def _guards(service, expected_state):
    if service.closed.is_set() or service.error or service.state != expected_state or service.active:
        raise ConflictError('BUSY_OR_RECOVERY')
    if service.switching or service.mock.state not in ('IDLE', 'RECOVERY'):
        raise ConflictError('CONTROL_CYCLE_BUSY')
    if service.storage_pending is not None:
        raise ConflictError('STORAGE_PENDING')
    if not service.calibration:
        raise ConflictError('CALIBRATION_REQUIRED')
    owner = service.production_owner
    if not service.production_enabled or owner is None or not owner.operating:
        raise ConflictError('PRODUCTION_OWNER_REQUIRED')
    return owner


def prepare(service, binding):
    with service.lock:
        if getattr(service, 'production_admission_pending', None) is not None:
            raise ConflictError('ADMISSION_PENDING')
        owner = _guards(service, 'IDLE')
        now = time.monotonic()
        epoch = _camera_epoch(service, now)
        if (binding.get('runtime_session_id') != owner.session_id
                or binding.get('worker_generation') != service.generation
                or binding.get('camera_epoch') != epoch):
            raise ConflictError('PRODUCTION_ADMISSION_IDENTITY_MISMATCH')
        if not service.station.get('fresh_frame'):
            raise ConflictError('FRESH_FRAME_REQUIRED')
        base = dict(cell_id=service.station['cell_id'], plc_session_id=service.session,
            package_sha256=service.package.manifest_hash, kind='inspect', control_mode='production',
            source_mode='PRODUCTION_AUTO', view_assessment={}, runtime_binding=binding,
            human_acceptance='PENDING', physical_output_enabled=False)
        # The storage owner replaces only these two IDs after allocating its
        # durable counter. The original receipt timestamp remains auditable.
        trigger = TriggerContext(trigger_id=uuid.uuid4().hex, cell_id=base['cell_id'],
            plc_session_id=service.session, cycle_id=1, request_id=1,
            trigger_received_monotonic=now, trigger_source='LOCAL_TEST', capture_epoch=epoch,
            deadline_monotonic=now + service.station['inspection_timeout_seconds'])
        selector = FreshFrameSelector(trigger, service.station['fresh_frame'],
            service.station['max_frame_age_seconds'], service.station['frame_spacing_seconds'])
        context = ProductionAdmission(uuid.uuid4().hex, service.generation, service.session,
            owner.session_id, epoch, service.package.manifest_hash, now, selector.deadline,
            _json(dict(kind='admit', base=base, package=recorded_package(service.package, getattr(service,'configuration',None)),
                       trigger=trigger.to_dict())), _json(service.calibration),
            _json(dict(source_mode='PRODUCTION_AUTO', session_id=owner.session_id,
                human_acceptance='PENDING', physical_output_enabled=False,
                inspection_motion_mode=owner.inspection_motion_mode, capture_zone=owner.zone)))
        service.cancellation.clear()
        service.production_admission_pending = context
        service.state = 'ADMITTING'
        return context


def _receipt(context, saved, now):
    if (saved.get('context') is not context or saved.get('error') is not None
            or not isinstance(saved.get('result'), dict)):
        raise ConflictError('ADMISSION_STORAGE_FAILED_OR_CONTEXT_MISMATCH')
    durable = saved.get('durable_monotonic')
    if (type(durable) not in (int, float) or not math.isfinite(durable)
            or not context.prepared_monotonic <= durable <= now):
        raise ConflictError('ADMISSION_DURABILITY_TIME_INVALID')
    result = saved['result']
    request, row, trigger = result.get('request'), result.get('row'), result.get('trigger')
    if not isinstance(request, dict) or not isinstance(row, dict) or not isinstance(trigger, dict):
        raise ConflictError('ADMISSION_RECEIPT_INVALID')
    expected = context.payload()
    number = request.get('request_id')
    if type(number) is not int or not 1 <= number <= 4294967295:
        raise ConflictError('ADMISSION_REQUEST_ID_INVALID')
    expected_request = dict(expected['base'], request_id=number, cycle_id=number, attempt=1)
    expected_trigger = dict(expected['trigger'], request_id=number, cycle_id=number)
    if (result.get('created') is not True or request != expected_request or trigger != expected_trigger
            or row.get('state') != 'ACCEPTED' or row.get('request') != expected_request
            or row.get('package') != expected['package']
            or not isinstance(row.get('inspection_id'), str) or not row['inspection_id']):
        raise ConflictError('ADMISSION_DURABLE_IDENTITY_MISMATCH')
    if result.get('inspection_id', row['inspection_id']) != row['inspection_id']:
        raise ConflictError('ADMISSION_DURABLE_IDENTITY_MISMATCH')
    return request, row, trigger, durable


def unstarted_receipt(service, context, saved):
    """Validate a reserved, unexecuted request, including after capture expiry.

    This grants no camera or PLC authority. Runtime may use the receipt to
    persist a nonexecuted ERROR; activation still enforces the capture clock.
    """
    with service.lock:
        if getattr(service, 'production_admission_pending', None) is not context:
            raise ConflictError('ADMISSION_CONTEXT_MISMATCH')
        owner = _guards(service, 'ADMITTING')
        now = time.monotonic()
        epoch = _camera_epoch(service, now)
        if (service.generation != context.generation or service.session != context.session_id
                or service.package.manifest_hash != context.package_sha256
                or owner.session_id != context.runtime_session_id or epoch != context.camera_epoch
                or _json(service.calibration) != context.calibration_json):
            raise ConflictError('ADMISSION_CONTEXT_CHANGED')
        if service.cancellation.is_set():
            raise ConflictError('ADMISSION_CANCELLED')
        return _receipt(context, saved, now)


def activate(service, context, saved):
    with service.lock:
        request, row, trigger, durable = unstarted_receipt(service, context, saved)
        now = time.monotonic()
        if now >= context.deadline_monotonic:
            raise ConflictError('ADMISSION_DEADLINE_EXCEEDED')
        selector = FreshFrameSelector(TriggerContext(**trigger), service.station['fresh_frame'],
            service.station['max_frame_age_seconds'], service.station['frame_spacing_seconds'])
        active = dict(inspection_id=row['inspection_id'], request=request, accepted_monotonic=now,
            deadline=trigger['deadline_monotonic'],
            calibration=json.loads(context.calibration_json), trigger=trigger,
            production_binding=dict(request['runtime_binding'], inspection_id=row['inspection_id']),
            experiment_policy=json.loads(context.experiment_json),
            durable_admission_monotonic=durable)
        # Admission/fsync and dispatch never restart either original clock.
        # Frame selection owns the short window; processing/storage owns total.
        active['capture_deadline'] = selector.deadline
        # Queue failure must not call _fault(), which would synchronously write
        # a Journal result. Runtime hands cancellation to the storage owner.
        try:
            service.commands.put_nowait(active)
        except queue.Full:
            service.state, service.error = 'RECOVERY', 'COMMAND_QUEUE_FULL'
            service.cancellation.set()
            raise ConflictError('COMMAND_QUEUE_FULL')
        service.active = active
        service.production_admission_pending = None
        service.state = 'BUSY'
        return row, True


def release(service, context, reason):
    """Invalidate this reservation; caller owns durable cancel/audit ordering."""
    with service.lock:
        if getattr(service, 'production_admission_pending', None) is not context:
            return False
        service.production_admission_pending = None
        service.cancellation.set()
        if service.state == 'ADMITTING':
            service.state = 'IDLE'
        service.health_diagnostics.record('PRODUCTION_ADMISSION_RELEASED',
            admission_id=context.admission_id, reason=str(reason))
        return True


def result_context_error(active, result, fresh_config):
    """Recheck Worker frame selection against the Service-owned durable cutoff."""
    try:
        floor = active['durable_admission_monotonic']
        evidence = result['fresh_frame']
        epsilon_ms = fresh_config['boundary_epsilon_ms']
        if (not finite_number(floor) or floor < 0
                or not finite_number(epsilon_ms) or epsilon_ms < 0):
            return 'ADMISSION_FRAME_FLOOR_INVALID'
        epsilon = epsilon_ms / 1000
        effective = max(active['trigger']['trigger_received_monotonic'], floor)
        reported = evidence.get('source_not_before_monotonic')
        effective_reported = evidence.get('effective_source_not_before_monotonic')
        if (not finite_number(reported) or not finite_number(effective_reported)
                or reported != floor or effective_reported != effective):
            return 'ADMISSION_FRAME_FLOOR_MISMATCH'
        selected, observations = evidence['selected_frames'], result['observations']
        if not isinstance(selected, list) or not isinstance(observations, list):
            return 'ADMISSION_FRAME_SELECTION_MISMATCH'
        ids = [observation['frame_id'] for observation in observations]
        if ([frame['frame_id'] for frame in selected] != ids or len(set(ids)) != len(ids)
                or (not ids and result.get('decision') != 'ERROR')):
            return 'ADMISSION_FRAME_SELECTION_MISMATCH'
        previous_time = effective + epsilon
        previous_sequence = -1
        now = time.monotonic()
        for frame, observation in zip(selected, observations):
            fresh = observation['freshness']
            source = fresh['estimated_source_monotonic']
            sequence = fresh['sequence']
            if (frame['frame_id'] != fresh['frame_id']
                    or frame['estimated_source_monotonic'] != source
                    or frame['sequence'] != sequence
                    or frame['camera_epoch'] != fresh['camera_epoch']
                    or fresh['camera_epoch'] != active['trigger']['capture_epoch']):
                return 'ADMISSION_FRAME_SELECTION_MISMATCH'
            if (type(source) not in (int, float) or not math.isfinite(source)
                    or not previous_time < source <= now
                    or type(sequence) is not int or sequence <= previous_sequence):
                return 'ADMISSION_FRAME_BEFORE_DURABILITY_OR_OUT_OF_ORDER'
            if 'capture_deadline' in active:
                selected_at = frame.get('selected_at_monotonic')
                if (not finite_number(selected_at) or not source <= selected_at <= now
                        or selected_at >= active['capture_deadline']
                        or fresh.get('selected_at_monotonic') != selected_at):
                    return 'ADMISSION_FRAME_OUTSIDE_CAPTURE_WINDOW'
            previous_time, previous_sequence = source, sequence
        return None
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return 'ADMISSION_FRAME_EVIDENCE_INCOMPLETE'
