"""Automatic request admission without filesystem work on the control owner.

One bounded storage job owns durability. Runtime continues checking actual PLC,
camera and cancellation state while waiting; it never dispatches before commit.
This is not an independent heartbeat thread or an extension of the C lease.
"""
from copy import deepcopy
import math
import queue
import time
from types import SimpleNamespace
import uuid

from src.runtime.inspection_bridge import InspectionBridge
from src.runtime.inspection_start import tracked_frame_evidence
from apps.edge_service.production_admission import unstarted_receipt


class RequestStart:
    def __init__(self, runtime):
        self.runtime = runtime
        self.pending = None
        self.events = []
        self.readiness = None
        self.readiness_key = None
        self.readiness_at = 0.
        self.capture_events = False
        self.last_error = None
        self.deferred_events = queue.Queue(maxsize=32)

    def defer_event(self, value):
        """Service monitor hands off audit metadata under Service.lock only."""
        self.deferred_events.put_nowait(deepcopy(value))

    def _drain_deferred(self):
        while len(self.events) < 64:
            try:
                value = self.deferred_events.get_nowait()
            except queue.Empty:
                return
            self.event(value)

    def owns(self):
        r = self.runtime
        return bool(self.pending or self.events or not self.deferred_events.empty() or (
            not r.service.active and not r.final_pending and not r.audit_pending
            and (not r.bridge.inspection_id or r.bridge.inspection_id in r.published_ids)))

    def _previous(self):
        r = self.runtime
        identifier = r.handshake.inspection_id or r.bridge.inspection_id
        token = r.handshake.token
        if not token:
            previous = r._automatic_previous or {}
            identifier, token = previous.get('inspection_id'), previous.get('request_token')
        return identifier, token

    def _key(self, snapshot):
        r = self.runtime
        return (r.session_id, r.service.session, r.service.generation,
                r.service.package.manifest_hash, r.epoch,
                snapshot.get('boot') if snapshot else None,
                snapshot.get('connection') if snapshot else None, *self._previous())

    def _readiness_key(self, snapshot):
        # SQL readiness queries Journal/previous publication, not a product
        # tracker. Keep every execution/PLC/previous-request owner in its key.
        # Bound requests continue using the full key, including tracking session.
        return self._key(snapshot)[1:]

    def event(self, value):
        if not self.capture_events:
            return False
        r = self.runtime
        if len(self.events) >= 64:
            raise ValueError('REQUEST_EVENT_BUFFER_FULL')
        payload = dict(runtime_session_id=r.session_id, monotonic_s=time.monotonic(),
            worker_generation=r.service.generation, physical_output_enabled=False)
        payload.update(deepcopy(value))
        self.events.append(payload)
        if r._diagnostic_events is not None:
            r._diagnostic_events.append(deepcopy(value))
        return True

    def _submit(self, kind, job, *, reservation=None, binding=None, final=None):
        if self.pending:
            raise ValueError('REQUEST_START_STORAGE_ALREADY_PENDING')
        r = self.runtime
        now = time.monotonic()
        snapshot = r.gateway.read_snapshot(now)
        live_token = (r.handshake.token if snapshot and snapshot['phase'] == 'REQUEST_RECEIVED'
            and r.handshake.state in ('REQUEST_LATCHED', 'INSPECTING')
            and r.handshake.inspection_id not in r.published_ids else None)
        context = dict(kind=kind, key=self._key(snapshot), snapshot=deepcopy(snapshot),
            token=live_token, started=now,
            camera_epoch=(r.service.preview or {}).get('freshness', {}).get('camera_epoch'),
            deadline=now+r.line_profile['arrival_deadline_s'],
            reservation=reservation, binding=deepcopy(binding), final=deepcopy(final),
            aborted=None)
        context['idle_readiness'] = kind == 'readiness' and live_token is None
        if context['idle_readiness']:
            context['key'] = self._readiness_key(snapshot)
        if kind == 'finish_no_input':
            # The expired capture window never becomes a fresh camera window.
            # Only terminal ERROR persistence receives this bounded deadline.
            timeout = r.service.station['inspection_timeout_seconds']
            if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
                raise ValueError('INVALID_UNEXECUTED_COMPLETION_TIMEOUT')
            context['deadline'] = now + timeout
        elif reservation is not None and hasattr(reservation, 'deadline_monotonic'):
            context['deadline'] = min(context['deadline'], reservation.deadline_monotonic)
        # Service activation expects this exact immutable reservation identity.
        owner = reservation if kind == 'admit' else context
        context['completion_owner'] = owner
        r.service.storage.submit_request(owner, job)
        self.pending = context

    def _flush(self):
        if self.events and not self.pending:
            values, self.events = self.events, []
            try:
                self._submit('events', dict(kind='events', events=values))
            except queue.Full:
                self.events = values + self.events

    def _request_readiness(self, snapshot):
        identifier, token = self._previous()
        self._submit('readiness', dict(kind='readiness',
            previous_identifier=identifier, previous_token=token))

    def settlement(self):
        r = self.runtime
        if r.aborted_inspection:
            return dict(clean=False, reason='UNRESOLVED_CANCELLED_REQUEST', previous=None)
        if r.error or r.service.error or r.service.active:
            return dict(clean=False, reason='WAIT_HEALTHY_IDLE_INSPECTION_OWNER', previous=None)
        assembly = r.assembly.status()
        if any(assembly.get(key) for key in ('active_identifier', 'pending', 'outstanding')):
            return dict(clean=False, reason='WAIT_ASSEMBLY_OWNER_IDLE', previous=None)
        identifier, token = self._previous()
        evidence = self.readiness or {}
        if evidence.get('unfinished') != 0:
            return dict(clean=False, reason='JOURNAL_UNFINISHED_OR_NOT_CHECKED', previous=None)
        if not identifier:
            return dict(clean=True, reason=None, previous=None)
        row, final = evidence.get('previous_row'), evidence.get('previous_final')
        if (evidence.get('previous_identifier') != identifier or evidence.get('previous_token') != token
                or not row or row['state'] not in ('COMPLETE', 'CANCELLED') or not final
                or not (row.get('result') or {}).get('storage_success')
                or final.get('request_token') != token or identifier not in r.published_ids):
            return dict(clean=False, reason='PREVIOUS_RESULT_NOT_DURABLE_OR_IDENTIFIED', previous=None)
        binding = row['request'].get('runtime_binding', {})
        return dict(clean=True, reason=None, previous=dict(inspection_id=identifier,
            request_token=token, decision=final['decision'], durable=True,
            tracking_session=binding.get('runtime_session_id'),
            cycle_id=binding.get('cycle_id'), track_id=binding.get('track_id')))

    def ready(self, snapshot):
        return bool(self.readiness_key == self._readiness_key(snapshot) and self.settlement()['clean'])

    def begin(self, binding, now):
        r = self.runtime
        if self.pending:
            return
        reservation = r.service.prepare_production_admission(binding)
        job = reservation.payload()
        if self.events:
            job['events'], self.events = self.events, []
        try:
            self._submit('admit', job, reservation=reservation, binding=binding)
        except Exception:
            r.service.release_production_admission(reservation, 'REQUEST_STORAGE_SUBMIT_FAILED')
            raise
        r.phase, r.line_wait = 'ADMITTING', 'WAIT_DURABLE_REQUEST_ADMISSION'

    def no_input(self, decision, reason, now):
        r = self.runtime
        if self.pending:
            return
        if decision != 'ERROR':
            raise ValueError('NO_INPUT_CANNOT_PASS')
        binding = dict(runtime_session_id=r.session_id, cycle_id=None, track_id=None,
            plc_request_token=r.handshake.token, plc_contract=r.gateway.contract_version,
            line_cycle_id=r.handshake.cycle_id, line_session_id=r.handshake.session_id,
            camera_epoch=r.epoch, worker_generation=r.service.generation)
        base = dict(cell_id=r.service.station['cell_id'], plc_session_id=r.service.session,
            package_sha256=r.service.package.manifest_hash, kind='inspect',
            control_mode='production', source_mode='PRODUCTION_AUTO',
            runtime_binding=binding, view_assessment={})
        reservation = SimpleNamespace(admission_id=uuid.uuid4().hex)
        if r.service.production_admission_pending or r.service.state != 'IDLE':
            raise ValueError('NO_INPUT_ADMISSION_OWNER_BUSY')
        r.service.production_admission_pending = reservation
        r.service.state = 'ADMITTING'
        result = dict(decision=decision, reason=reason, reason_code=reason,
            disposition='HOLD', observations=[], assets=[], production_identity=binding,
            execution=dict(source='not_executed', control='production',
                           worker_generation=r.service.generation))
        job = dict(kind='no_input', base=base, package=r.service.package.snapshot(),
            trigger=None, no_input_result=result)
        if self.events:
            job['events'], self.events = self.events, []
        try:
            self._submit('no_input', job, reservation=reservation, binding=binding,
                final=dict(decision=decision, existing_decision='NOT_RUN',
                    assembly_decision='NOT_RUN', policy='NO_INPUT_IS_NEVER_PASS', reason=reason))
        except Exception:
            r.service.release_production_admission(reservation, 'NO_INPUT_SUBMIT_FAILED')
            raise

    def _live_error(self, context, now):
        r = self.runtime
        health = r.service.health()
        snapshot = r.gateway.read_snapshot(now)
        now = time.monotonic()
        if (not snapshot or not all(snapshot.get(k) for k in ('connected','fresh','run_idle','bool_valid'))
                or not 0 <= now-snapshot['generated'] <= .5
                or not 0 <= now-snapshot['received'] <= .2):
            return 'REQUEST_STORAGE_PLC_UNAVAILABLE', health, snapshot
        current_key = (self._readiness_key(snapshot) if context.get('idle_readiness')
                       else self._key(snapshot))
        if context['key'] != current_key:
            return 'REQUEST_STORAGE_OWNER_CHANGED', health, snapshot
        if (health.get('error') or not health.get('worker_alive') or not health.get('camera_ready')
                or not r.service.storage.thread.is_alive() or r.service.switching
                or health.get('camera_epoch') != context['camera_epoch']
                or not r.assembly.ready or r.error):
            return health.get('error') or r.error or 'REQUEST_STORAGE_OWNER_UNAVAILABLE', health, snapshot
        if context['token']:
            token = f"{snapshot['boot']:016x}:{snapshot['connection']}:{snapshot['request_id']}"
            if (token != context['token'] or snapshot['phase'] != 'REQUEST_RECEIVED'
                    or not all(snapshot['controls'].get(k) for k in
                        ('Inspection_Request','Mc_Run','EStop_OK','Stop_PB'))
                    or r.handshake.cancelled):
                return 'REQUEST_STORAGE_CONTROL_CANCELLED', health, snapshot
        if now > context['deadline']:
            if context['kind'] == 'admit' and context.get('activation_receipt'):
                return 'ADMISSION_OBSERVATION_DEADLINE_EXCEEDED', health, snapshot
            if context['kind'] == 'finish_no_input':
                return 'UNEXECUTED_COMPLETION_STORAGE_DEADLINE_EXCEEDED', health, snapshot
            return 'REQUEST_STORAGE_DEADLINE_EXCEEDED', health, snapshot
        return None, health, snapshot

    def _check_admission_owner(self, binding):
        r = self.runtime
        cycle = r.coordinator.active_cycle
        if (not cycle or cycle.cycle_id != binding['cycle_id']
                or r.coordinator._tracker._track_id != binding['track_id']
                or r.handshake.state != 'REQUEST_LATCHED' or r.handshake.inspection_id
                or r.cycle_issue or r.automatic_identity_block):
            raise ValueError('ADMISSION_CURRENT_TRACK_OR_REQUEST_CHANGED')

    def _finish_observation_timeout(self, context):
        """Queue exactly one same-ID ERROR after verified durable admission."""
        r = self.runtime
        self._check_admission_owner(context['binding'])
        request, row, _, durable = unstarted_receipt(
            r.service, context['reservation'], context['activation_receipt'])
        # Slow/failed admission is a storage failure, not missing observation.
        if durable > context['deadline']:
            raise ValueError('REQUEST_STORAGE_DEADLINE_EXCEEDED')
        reason = 'ADMISSION_OBSERVATION_DEADLINE_EXCEEDED'
        result = dict(decision='ERROR', reason=reason, reason_code=reason,
            disposition='HOLD', observations=[], assets=[],
            production_identity=dict(context['binding'], inspection_id=row['inspection_id']),
            execution=dict(source='not_executed', control='production',
                worker_generation=r.service.generation),
            admission_wait=dict(stage='AFTER_DURABLE_ADMISSION_BEFORE_CAPTURE',
                durable_admission_monotonic=durable, observation_deadline_monotonic=context['deadline']))
        self.pending = None
        try:
            self._submit('finish_no_input', dict(kind='finish_no_input',
                inspection_id=row['inspection_id'], request=request, package=row['package'],
                no_input_result=result), reservation=context['reservation'], binding=context['binding'],
                final=dict(decision='ERROR', existing_decision='NOT_RUN', assembly_decision='NOT_RUN',
                           policy='NO_INPUT_IS_NEVER_PASS', reason=reason))
            self.pending['original_admission'] = context
        except Exception:
            self.pending = context
            raise
        r.phase, r.line_wait = 'ADMITTING', 'WAIT_UNEXECUTED_ERROR_DURABILITY'
        r.service.health_diagnostics.record('ADMISSION_OBSERVATION_EXPIRED',
            inspection_id=row['inspection_id'], request_token=context['token'],
            observation_deadline_monotonic=context['deadline'],
            terminal_storage_deadline_monotonic=self.pending['deadline'])

    def _completed_owner(self, snapshot):
        """An acknowledged durable final may wait for fresh readiness SQL.

        This evidence is recorded only after final commit/publication. It does
        not itself admit another request; admission still needs its new SQL
        result, current identity, sequence and counters.
        """
        r = self.runtime
        previous = r._automatic_previous or {}
        token = previous.get('request_token')
        if (not snapshot or not token or previous.get('inspection_id') not in r.published_ids
                or r.service.active or r.final_pending or r.audit_pending
                or r.aborted_inspection or r.service.error or r.error):
            return False
        boot, connection, number = token.split(':')
        if (snapshot['boot'] != int(boot,16) or snapshot['connection'] != int(connection)
                or not all(snapshot['controls'].get(k) for k in ('Mc_Run','EStop_OK','Stop_PB'))):
            return False
        number = int(number)
        if snapshot['request_id'] == number:
            return snapshot['phase'] in ('REQUEST_RECEIVED','TEST_RESULT_READY','RESULT_SENT',
                'DONE_SENT','WAIT_REQUEST_OFF','CLEARING_DONE','READY_NEXT','IDLE')
        baseline = previous.get('start_counters') or {}
        return bool(snapshot['request_id'] == number+1 and snapshot['phase']=='REQUEST_RECEIVED'
            and all(key in baseline and snapshot.get(key)==baseline[key]+1
                    for key in ('result_count','done_count','completed_count')))

    def _block(self, context, reason):
        if context['aborted']:
            return
        context['aborted'] = reason
        r = self.runtime
        r.gateway.health_update(False, False, time.monotonic())
        active = r.service.active
        if active and (active.get('request', {}).get('runtime_binding', {}).get('plc_request_token')
                       == context['token']):
            r.service.cancellation.set()
        if context['kind'] != 'readiness' or context['token']:
            r.handshake.fault(reason)
            r._fault(reason)
        self.last_error = reason

    def _release(self, context, reason):
        if context.get('reservation') is not None:
            self.runtime.service.release_production_admission(context['reservation'], reason)

    def _cancel_admitted(self, context, saved, reason):
        result = saved.get('result') or {}
        identifier = result.get('inspection_id') or (result.get('row') or {}).get('inspection_id')
        if identifier:
            self._submit('cancel', dict(kind='cancel', inspection_id=identifier, reason=reason),
                reservation=context.get('reservation'))
            self.pending['cancelled_identity'] = identifier
            self.pending['cancel_reason'] = reason
            self.pending['cancelled_request_token'] = context['token']
        else:
            self._release(context, reason)

    def _bind(self, row, binding, now):
        r = self.runtime
        r.bridge = InspectionBridge(r.service, r.coordinator)
        r.bridge.request, r.bridge.inspection_id = row['request'], row['inspection_id']
        r.bridge.phase = 'INSPECTION_REQUESTED'
        r.handshake.bind(row['inspection_id'])
        if binding['track_id'] is not None:
            r.inspected_tracks.add(binding['track_id'])
        r.phase, r.pending_started = 'INSPECTING', now
        r._event(dict(event='PRODUCTION_INSPECTION_BOUND', inspection_id=row['inspection_id'], identity=binding))

    def _poll(self, now):
        r, context = self.runtime, self.pending
        error, health, snapshot = self._live_error(context, now)
        if error == 'ADMISSION_OBSERVATION_DEADLINE_EXCEEDED' and not context['aborted']:
            try:
                self._finish_observation_timeout(context)
                context = self.pending
                error, health, snapshot = self._live_error(context, time.monotonic())
            except Exception as exc:
                error = str(exc)
        if error:
            self._block(context, error)
        # A queued known job may retain health only with fresh owners and the
        # same control identity. Initial readiness has no prior authority.
        qualified = context['token'] is not None or self.ready(snapshot) or self._completed_owner(snapshot)
        ready = bool(not error and not context['aborted'] and qualified
                     and r.operating and r._profile_ready())
        r.gateway.ready_reason = error or ('REQUEST_STORAGE_PENDING' if ready else 'WAIT_REQUEST_STORAGE_CHECK')
        r.gateway.health_update(ready, False, time.monotonic())
        saved = context.get('activation_receipt')
        if saved is None:
            try:
                saved = r.service.storage.request_completed.get_nowait()
            except queue.Empty:
                return
            if saved.get('context') is not context['completion_owner']:
                self._block(context, 'REQUEST_STORAGE_COMPLETION_IDENTITY_MISMATCH')
                return  # Do not release another pending job's reservation.
            r.service.health_diagnostics.record('REQUEST_STORAGE_COMPLETED', kind=context['kind'],
                request_token=context['token'], duration_ms=saved.get('duration_ms'),
                timings=saved.get('timings'), error=saved.get('error'), aborted=context['aborted'])
        self.pending = None
        if context['kind'] == 'cancel':
            if saved.get('error'):
                self.pending = context  # Reservation remains held until recovery.
                self._block(context, 'REQUEST_CANCEL_STORAGE_FAILED:'+str(saved['error']))
            else:
                self._release(context, 'ADMISSION_CANCEL_DURABLE')
                identifier = context.get('cancelled_identity')
                if identifier:
                    r.aborted_inspection = dict(inspection_id=identifier,
                        reason=context.get('cancel_reason', 'ADMISSION_CANCELLED'),
                        request_token=context.get('cancelled_request_token'), plc_publication='BLOCKED')
                    r.published_ids.add(identifier)  # Never replay a cancelled row.
            return
        reason = context['aborted'] or saved.get('error')
        if reason:
            if saved.get('error'):
                self._block(context, 'REQUEST_STORAGE_FAILED:'+str(saved['error']))
            if context['kind'] in ('admit', 'no_input', 'finish_no_input'):
                self._cancel_admitted(context, saved, str(reason))
            self.readiness = None
            return
        if context['kind'] == 'readiness':
            self.readiness, self.readiness_key = saved['result'], context['key']
            self.readiness_at = time.monotonic()
        elif context['kind'] == 'admit':
            try:
                binding = context['binding']
                self._check_admission_owner(binding)
                if not tracked_frame_evidence(r.latest_packet, r.handshake.accepted_at,
                        binding['camera_epoch'], binding['worker_generation'], time.monotonic()):
                    # One preview miss does not change the durable request owner.
                    # Stay ADMITTING, reuse this exact receipt, and keep checking
                    # controls/owners/deadline each tick. No camera job is sent
                    # until a current qualifying frame arrives; neither clock
                    # restarts and no second Journal admission is created.
                    if 'activation_receipt' not in context:
                        packet = r.latest_packet or {}
                        r.service.health_diagnostics.record('ADMISSION_WAIT_CURRENT_FRAME',
                            request_token=context['token'], inspection_id=saved['result']['row']['inspection_id'],
                            frame_id=packet.get('frame_id'),
                            provider_status=packet.get('provider', {}).get('status'),
                            deadline_monotonic=context['deadline'])
                    context['activation_receipt'] = saved
                    self.pending = context
                    return
                row, _ = r.service.activate_production_admission(context['reservation'], saved)
                self._bind(row, binding, time.monotonic())
                self.readiness = None
            except Exception as exc:
                self._block(context, str(exc))
                self._cancel_admitted(context, saved, str(exc))
        elif context['kind'] in ('no_input', 'finish_no_input'):
            if context['kind'] == 'finish_no_input':
                try:
                    self._check_admission_owner(context['binding'])
                    original = context['original_admission']
                    unstarted_receipt(r.service, original['reservation'], original['activation_receipt'])
                    row = saved['result']['row']
                    before = original['activation_receipt']['result']['row']
                    if (row['inspection_id'] != before['inspection_id']
                            or row['request'] != before['request'] or row['package'] != before['package']
                            or row['state'] != 'COMPLETE' or row['result']['decision'] != 'ERROR'
                            or not row['result']['storage_success']):
                        raise ValueError('UNEXECUTED_COMPLETION_RECEIPT_MISMATCH')
                except Exception as exc:
                    self._block(context, str(exc))
                    self._cancel_admitted(context, saved, str(exc))
                    return
            self._release(context, 'NO_INPUT_DURABLE')
            self._bind(saved['result']['row'], context['binding'], time.monotonic())
            # Supply the already read durable row; no SQL on this control path.
            r._commit_and_publish(saved['result']['row']['inspection_id'], context['final'],
                                  time.monotonic(), durable_row=saved['result']['row'])
            self.readiness = None

    def tick(self, now):
        """Called under Runtime/Service locks, before any Journal acquisition."""
        if not self.owns():
            return False
        r = self.runtime
        self.capture_events = True
        try:
            self._drain_deferred()
            if self.pending:
                self._observations()
                self._poll(now)
                self._flush()
                return True
            if self.events:
                self._flush()
                if self.pending:
                    self._poll(time.monotonic())
                else:
                    r._storage_wait_health(time.monotonic())
                return True
            r._acquisition(now)
            snapshot = r.gateway.read_snapshot(now)
            # Request admission is rechecked after previous-result changes and
            # periodically while idle. SQL is never borrowed by the control loop.
            active_request = r.handshake.state == 'REQUEST_LATCHED' and not r.handshake.cancelled
            if (not active_request and not r.error and snapshot
                    and (self.readiness_key != self._readiness_key(snapshot) or self.readiness is None
                         or now-self.readiness_at > 1.)):
                self._request_readiness(snapshot)
                self._poll(time.monotonic())
                return True
            r._poll_plc(now)
            if r.audit_pending:
                return True
            self._observations()
            now = time.monotonic()
            if r.operating and r.observation_started_at is not None:
                since = (r.latest_packet or {}).get('processed_monotonic', r.observation_started_at)
                if now-since > r.observation_stale_seconds:
                    r._fault('CAMERA_OR_OBSERVATION_STREAM_UNAVAILABLE')
            r._trigger(now)
            self._flush()
            return True
        finally:
            self.capture_events = False

    def _observations(self):
        # Bounded work each turn, including while storage is delayed. Identity
        # revalidation must inspect current observations, not a frozen tracker.
        r = self.runtime
        if (getattr(r.service, 'storage_pending', None) or r.final_pending
                or (getattr(r.bridge, 'phase', None) == 'INSPECTION_DURABLE'
                    and r.bridge.inspection_id not in r.published_ids)):
            # Completed-preview verification reads its durable row. The normal
            # raw/final path resumes those observations once SQL is available.
            return
        for _ in range(32):
            try:
                packet = r.service.products.get_nowait()
            except queue.Empty:
                break
            r._packet(packet)
