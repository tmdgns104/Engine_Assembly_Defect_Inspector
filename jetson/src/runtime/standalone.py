"""Continuous line owner: existing vision + frozen assembly, then one PLC result.

Software acquisition starts without a browser. Physical Run remains PLC-owned.
Each accepted PLC cycle opens a fresh observation window. Its first unambiguous
track can be bound; no previous-product pose or prediction is inherited.
"""
import json
import queue
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone

from src.control.standalone_plc import LineHandshake
from src.runtime.production import ProductionRuntime
from src.runtime.inspection_bridge import InspectionBridge
from src.runtime.production_profile import calibration_sha
from src.runtime.inspection_start import FULL_FRAME, start_policy, tracked_frame_evidence
from src.runtime.completed_evidence import validate_completed_evidence
from src.vision.integrated_decision import combine_decisions, POLICY as FINAL_POLICY
from src.runtime.initial_approval import InitialApproval, JournalAdmissionGuard, count_unfinished_inspections, POLICY as INITIAL_POLICY
from src.runtime.supervised_approval import SupervisedApproval, POLICY as REPEAT_POLICY
AUTO_POLICY = 'PLC_AUTOMATIC_REPEAT'
from src.runtime.product_passage import ProductPassage
from src.runtime.consumed_frames import ConsumedFrames
from src.tracking.contracts import TrackState
from src.runtime.product_context_recovery import latest_product, valid_context_close, record_context_close, digest


def arrival_evidence(packet, accepted_at, epoch, generation, zone):
    """Geometry/freshness only; class labels are not arguments."""
    if not packet or packet['monotonic_s'] <= accepted_at:
        return False
    if packet['camera_epoch'] != epoch or packet['generation'] != generation:
        return False
    observations = packet.get('provider', {}).get('observations', [])
    if len(observations) != 1 or not packet['integrity']['valid']:
        return False
    box = observations[0]['bbox']
    x1, y1 = zone['polygon_normalized'][0]
    x2, y2 = zone['polygon_normalized'][2]
    return bool(x1 < box['x1'] < box['x2'] < x2 and y1 < box['y1'] < box['y2'] < y2)


class StandaloneRuntime(ProductionRuntime):
    OBSERVATION_ISSUES = frozenset({
        'TRACK_ASSOCIATION_OR_GAP_LOST', 'PRODUCT_OBSERVATION_GAP',
        'INVALID_OR_STALE_PRODUCT_OBSERVATION', 'PRODUCT_FRAME_ORDER_INVALID',
        'MULTIPLE_PRODUCT_AMBIGUITY', 'PRODUCT_DEPARTURE_NOT_OBSERVED',
    })

    def __init__(self, *args, line_profile, assembly, **kwargs):
        self.configured = threading.Event()
        self.consumed_frames = ConsumedFrames()
        self.line_profile, self.assembly = dict(line_profile), assembly
        policy = start_policy(self.line_profile, getattr(kwargs.get('gateway'), 'contract_version', None))
        if (policy == FULL_FRAME) != args[5].plc_request_tracking:
            raise ValueError('START_POLICY_TRACKER_CONFIG_MISMATCH')
        if policy == FULL_FRAME and kwargs.get('inspection_motion_mode', 'STATIONARY') != 'STATIONARY':
            raise ValueError('PLC_REQUEST_POLICY_USES_EXISTING_STATIONARY_QUALITY_CHECKS')
        self.initial_approval = None
        self.plc_cycle = None
        self._automatic_previous = None
        self._automatic_cycle_evidence = None
        self._automatic_started_at = time.monotonic()
        self.previous_tracking_diagnostic = None
        self.prior_product_identity_block = None
        self._journal_readiness = JournalAdmissionGuard()
        self._unaccepted_request_at = None
        self.product_passage = None
        self._passage_history = deque(maxlen=args[5].max_missed_frames+2)
        self.product_separation = None
        self.automatic_identity_block = None
        self.request_product_separation = None
        self.cyclic_admissions = 0
        self.cyclic_rearm_evidence = None
        self.arrival = None
        self.assembly_submitted = {}
        self.recovery_at = 0
        self.camera_retry_at = 0
        self.camera_recovery = None
        self.issue = None
        self.aborted_inspection = None
        self.final_pending = None
        self.audit_pending = None
        self.audit_error = None
        self.request_start = None
        self.cycle_issue = None
        self.line_wait = 'INITIALIZING'
        super().__init__(*args, **kwargs)
        self.shadow = assembly  # Reuse existing evidence routes, not post-commit shadow dispatch.
        self.service.journal.outbox_limit = None  # Optional notebook export is not a PLC dependency.
        self.service.journal.min_free_bytes = line_profile['min_free_bytes']
        self._restore_aborted_inspection()
        if self._automatic_policy():
            self.plc_cycle = dict(policy=AUTO_POLICY, reason='WAIT_STOPPED_BASELINE',
                software_permission_required=False, per_product_manual_approval=False, browser_required=False)
            self._restore_previous_product_identity()
            from src.runtime.request_start import RequestStart
            self.request_start = RequestStart(self)
        if self._initial_policy() or self._supervised_policy():
            approval_type = SupervisedApproval if self._supervised_policy() else InitialApproval
            self.initial_approval = approval_type(self.service.journal.root/'first-product-approval',
                                                  self.gateway.runtime_session)
        self.configured.set()

    def start_auto(self):
        raise ValueError('PHYSICAL_START_OWNS_LINE_RUN; SOFTWARE_ACQUISITION_IS_AUTOMATIC')

    def _event(self, value):
        # These are observation diagnostics, not request/result/exit authority.
        # Synchronous SQLite commits here can checkpoint the WAL while the PLC
        # health owner is handling its first product. Keep the bounded trace in
        # memory; actual requests, results, separation and aborts remain durable.
        if self._automatic_policy() and value.get('event') in (
                'VISION_PASSAGE_STARTED', 'PRODUCTION_TRACK_STATE',
                'PRODUCTION_DEPARTURE_EDGE_ASSESSED'):
            if self._diagnostic_events is not None:
                self._diagnostic_events.append(dict(value))
            payload = dict(value)
            name = payload.pop('event')
            self.service.health_diagnostics.record(name,
                runtime_session_id=self.session_id,
                worker_generation=self.service.generation, **payload)
            return
        start = getattr(self, 'request_start', None)
        if start and start.event(value):
            return
        return super()._event(value)

    def _completion_event(self, value):
        """Persist completion audits on the existing storage owner, never omit them."""
        if not self._automatic_policy():
            return self._event(value)
        if getattr(self, 'audit_pending', None):
            raise ValueError('COMPLETION_AUDIT_ALREADY_PENDING')
        now = time.monotonic()
        payload = dict(runtime_session_id=self.session_id, monotonic_s=now,
            worker_generation=self.service.generation, physical_output_enabled=False)
        payload.update(value)
        context = dict(inspection_id=value['inspection_id'], request_token=value['request_token'],
            generation=self.service.generation, camera_epoch=self.epoch, started=now,
            deadline=now+self.line_profile['arrival_deadline_s'],
            start_counters=dict((self._automatic_cycle_evidence or {}).get('start_counters') or {}))
        self.service.storage.submit_audit(context, payload)
        self.audit_pending = context
        self.audit_error = None

    def _completion_audit_health(self, now):
        """Validate live owners/controls while a known completion commit is pending.

        This cannot admit a request or publish a result. C keeps its existing
        lease and request deadline; a subsequent edge waits for the audit.
        """
        context = self.audit_pending
        health = self.service.health()
        snapshot = self.gateway.read_snapshot(now)
        identity_ok = False
        if snapshot:
            now = snapshot.get('observed_at', now)
            boot, connection, request = context['request_token'].split(':')
            same_session = snapshot['boot'] == int(boot, 16) and snapshot['connection'] == int(connection)
            counters = context['start_counters']
            completed = all(key in counters and snapshot.get(key) == counters[key]+1
                for key in ('result_count', 'done_count', 'completed_count'))
            same_request = snapshot['request_id'] == int(request)
            next_request = (snapshot['request_id'] == int(request)+1 and completed
                and snapshot['phase'] == 'REQUEST_RECEIVED' and snapshot['raw100'] == '00000000'
                and snapshot['controls']['Inspection_Request'])
            active = snapshot['phase'] in ('REQUEST_RECEIVED', 'TEST_RESULT_READY', 'RESULT_SENT',
                'DONE_SENT', 'WAIT_REQUEST_OFF', 'CLEARING_DONE')
            settled = (snapshot['phase'] in ('READY_NEXT', 'IDLE') and completed
                and snapshot['raw100'] == '00000000' and not snapshot['controls']['Inspection_Request'])
            identity_ok = same_session and ((same_request and (active or settled)) or next_request)
        ready = bool(identity_ok and not self.audit_error
            and context['inspection_id'] in self.published_ids
            and context['request_token'] == self.handshake.token and not self.handshake.cancelled
            and self.operating and not self.error and self._profile_ready() and self.assembly.ready
            and snapshot['connected'] and snapshot['fresh'] and snapshot['run_idle'] and snapshot['bool_valid']
            and 0 <= now-snapshot['generated'] <= .5 and 0 <= now-snapshot['received'] <= .2
            and all(snapshot['controls'][key] for key in ('Mc_Run', 'EStop_OK', 'Stop_PB'))
            and not health['error'] and health['camera_ready'] and health['state'] in ('BUSY', 'IDLE')
            and context['generation'] == self.service.generation and context['camera_epoch'] == health['camera_epoch']
            and self.service.storage.thread.is_alive() and context['started'] <= now <= context['deadline'])
        self.gateway.ready_reason = 'COMPLETION_AUDIT_IN_PROGRESS' if ready else 'COMPLETION_AUDIT_CONTROL_INVALID'
        self.gateway.health_update(ready, False, time.monotonic())

    def _poll_completion_audit(self, now):
        """Return True while admission/observation handling must wait for storage."""
        pending = getattr(self, 'audit_pending', None)
        if pending is None:
            return False
        if not self.audit_error:
            try:
                saved = self.service.storage.audit_completed.get_nowait()
            except queue.Empty:
                saved = None
            if saved:
                if saved['context'] is not pending or saved['error']:
                    self.audit_error = 'COMPLETION_AUDIT_FAILED:'+str(saved['error'] or 'CONTEXT_CHANGED')
                else:
                    self.service.health_diagnostics.record('COMPLETION_AUDIT_DURABLE',
                        inspection_id=pending['inspection_id'], duration_ms=saved.get('duration_ms', 0))
                    self.audit_pending = None
                    return False
            elif now > pending['deadline'] or not self.service.storage.thread.is_alive():
                self.audit_error = 'COMPLETION_AUDIT_TIMEOUT_OR_OWNER_LOST'
            if self.audit_error:
                self.error = self.audit_error
                self.gateway.cancel()
                self.service.health_diagnostics.record('COMPLETION_AUDIT_FAILED', reason=self.audit_error,
                    inspection_id=pending['inspection_id'])
        try:
            self._completion_audit_health(now)
        except Exception as error:
            self.audit_error = 'COMPLETION_AUDIT_HEALTH_CHECK:'+type(error).__name__+':'+str(error)
            self.error = self.audit_error
            self.gateway.cancel()
            self.gateway.ready_reason = self.audit_error
            self.gateway.health_update(False, False, time.monotonic())
            self.service.health_diagnostics.record('COMPLETION_AUDIT_FAILED', reason=self.audit_error,
                inspection_id=pending['inspection_id'])
        return True

    def _restore_aborted_inspection(self):
        """Restore a recorded blocked cycle for display; never restore a grant."""
        from src.runtime.aborted_recovery import valid_abort
        journal = self.service.journal
        with journal.lock:
            # Journal append order remains meaningful across boots and producer
            # sessions. Apply settlement filters before selecting the latest row.
            rows = journal.db.execute("""
                SELECT e.payload_json, i.request_json
                FROM events e JOIN inspections i
                  ON i.inspection_id=json_extract(e.payload_json,'$.payload.inspection_id')
                WHERE e.event_type='LINE_CANCELLED_RESULT_BLOCKED'
                  AND json_extract(i.request_json,'$.runtime_binding.plc_contract')='OPENER_CYCLIC'
                  AND NOT EXISTS(SELECT 1 FROM service_state s
                      WHERE s.key='integrated_decision:' || i.inspection_id)
                ORDER BY e.rowid DESC
            """).fetchall()
            for row in rows:
                event = json.loads(row[0])['payload']
                # A bare state key is not a maintenance receipt. Validate its
                # immutable event and original request before retiring the block.
                if valid_abort(journal.db, event['inspection_id']):
                    continue
                binding = json.loads(row[1])['runtime_binding']
                self.aborted_inspection = dict(inspection_id=event['inspection_id'], reason=event['reason'],
                    request_token=binding.get('plc_request_token'), plc_publication='BLOCKED',
                    restored_from_journal=True)
                break

    def _fault(self, reason):
        if (getattr(self.gateway, 'contract_version', None) in ('LEGACY_THREE_BOOL', 'OPENER_CYCLIC')
                and reason in self.OBSERVATION_ISSUES and self.operating and not self.error):
            self._observation_issue(reason)
            return
        super()._fault(reason)
        if self.handshake.state != 'RESYNC_REQUIRED':
            self.handshake.fault(reason, 'BLOCKED')

    def _observation_issue(self, reason):
        """Keep acquisition alive; never recycle an accepted product's identity."""
        if self._completed_preview_issue(reason):
            return
        if self._automatic_policy() and self.product_passage:
            self.product_passage._fail('PRODUCT_PASSAGE_INTERRUPTED:'+reason)
            # This diagnostic belongs to an already published inspection. It
            # cannot cancel that result or become a fault of the next token.
            previous = self._automatic_previous or {}
            if self.product_passage.identity.get('inspection_id') == previous.get('inspection_id'):
                if not self.issue or self.issue.get('reason') != reason:
                    self.issue = dict(reason=reason, scope='COMPLETED_CYCLE_TRACKING',
                        request_token=previous.get('request_token'), active=False,
                        action='REASSESS_ON_NEXT_VALID_PLC_CYCLE')
                    self._event(dict(event='COMPLETED_CYCLE_TRACKING_UNCERTAIN', **self.issue))
                return
        if self.cycle_issue:
            return
        now = time.monotonic()
        unbound = (self.handshake.token is None and self.handshake.state in ('SYNC_LOW', 'ARMED')
                   and not self.service.active and not self.bridge.inspection_id)
        self.issue = dict(reason=reason, scope='UNBOUND_PREVIEW' if unbound else 'REQUEST',
            request_token=self.handshake.token, inspection_id=self.bridge.inspection_id,
            occurred_at=datetime.now(timezone.utc).isoformat(), monotonic_s=now,
            active=not unbound, action='REACQUIRE_PREVIEW' if unbound else 'WAIT_VERIFIED_PRODUCT_CLEAR')
        self._event(dict(event='LINE_OBSERVATION_ISSUE', **self.issue))
        self.eligible = False
        if unbound:
            self._reset_unbound_observation(now)
            return
        self.cycle_issue = dict(self.issue)
        # Preserve the raw worker record. A late PASS can only become ERROR for
        # this token; it cannot enter the next request or be sent to the PLC.
        if self.service.active:
            self._cancel_active_inspection(reason)
        elif self.handshake.state == 'REQUEST_LATCHED':
            self._finish_without_frames('ERROR', reason, now)

    def _completed_preview_issue(self, reason):
        """Only post-durability detection gaps become publication diagnostics.

        A changed owner, raw acquisition failure, stale camera, or cancelled
        control request still follows the existing fault path.
        """
        if (reason not in ('PRODUCT_OBSERVATION_GAP', 'TRACK_ASSOCIATION_OR_GAP_LOST')
                or not self._automatic_policy() or self.bridge.phase != 'INSPECTION_DURABLE'
                or not self.bridge.inspection_id or self.cycle_issue
                or self.bridge.inspection_id in self.published_ids):
            return False
        row = self.service.journal.detail(self.bridge.inspection_id)
        if not row or row.get('decision') not in ('PASS', 'FAIL'):
            return False
        try:
            self._validate_cyclic_final(row['request']['runtime_binding'],
                dict(inspection_id=row['inspection_id'], decision=row['decision']), time.monotonic(), row)
        except ValueError:
            return False
        self.issue = dict(reason=reason, scope='COMPLETED_INSPECTION_PREVIEW', active=False,
            inspection_id=row['inspection_id'], request_token=self.handshake.token,
            action='RETAIN_DURABLE_REQUEST_BOUND_RESULT')
        # The existing completion audit persists this with publication. No extra
        # synchronous Journal commit is added to the cyclic health path.
        return True

    def _reset_unbound_observation(self, now):
        self._replace_tracking_session(uuid.uuid4().hex)
        self.inspected_tracks.clear()
        self.window_event = None
        self.eligible = False
        self.new_product_after = now
        self._reset_departure_candidate()
        self.area_window.reset()

    def _release_unused_preview(self, packet):
        """Forget a lost preview, never a PLC-bound or previously inspected product."""
        from src.tracking.contracts import TrackState, TrackingReason
        tracker = self.coordinator._tracker
        if (not self._automatic_policy() or not self.operating or self.error
                or tracker._state != TrackState.WAIT_AREA_CLEAR
                or tracker._reason not in (TrackingReason.MISSED_OBSERVATION_LIMIT,
                                           TrackingReason.TRACK_ASSOCIATION_INVALID)
                or self.handshake.token or self.service.active or self.bridge.inspection_id
                or self.final_pending or tracker._inspection_id or self.inspected_tracks
                or self.product_passage or self.prior_product_identity_block
                or self.automatic_identity_block
                or (self.cyclic_admissions and not self.product_separation)):
            return False
        now = time.monotonic()
        snapshot = self.gateway.read_snapshot(now)
        if (not snapshot or not snapshot['connected'] or not snapshot['fresh']
                or not snapshot['run_idle'] or not snapshot['bool_valid']
                or not 0 <= now-snapshot['generated'] <= .5
                or not 0 <= now-snapshot['received'] <= .2
                or snapshot['phase'] not in ('SYNC_LOW', 'IDLE')
                or snapshot['controls']['Inspection_Request'] or snapshot['raw100'] != '00000000'):
            return False
        previous = self.session_id
        # Repositioning an uninspected model can invalidate preview association.
        # Retire that unused identity, then require subsequent fresh observations;
        # this neither proves departure nor replaces a PLC-bound product.
        self._reset_unbound_observation(packet['monotonic_s'])
        self.service.health_diagnostics.record('UNBOUND_PREVIEW_REACQUIRED',
            previous_tracking_session=previous, runtime_session_id=self.session_id,
            frame_id=packet['frame_id'], product_exit_claimed=False)
        return True

    def _observation_hold(self, packet, provider):
        if self._automatic_policy() and self.product_passage:
            # Parent has checked frame identity, order, quality and model hash.
            # Observe the completed product separately: a new upstream box must
            # never be associated with the old Track while waiting for exit.
            proof = self.product_passage.observe(packet, time.monotonic())
            self.eligible = False
            self.area_wait_reason = self.product_passage.reason
            settled = self._automatic_transaction_settled()
            pending = bool(proof and self._pending_entry_matches_request(proof, packet))
            if proof and (settled or pending):
                self._event(dict(event='AUTOMATIC_PRODUCT_SEPARATED', evidence=proof))
                self.product_separation = proof
                self.product_passage = None
                self._reset_unbound_observation(packet['monotonic_s'])
                self.last_sequence = packet['sequence']
                self.last_time = packet['monotonic_s']
                self.latest_packet = packet
                if pending:
                    # The upstream entry existed before this request. Only its
                    # proof was pending; no AI work or result has been bound yet.
                    self.request_product_separation = self.product_separation
                    self.product_separation = None
                    self.automatic_identity_block = None
                    self.arrival.update(track=None,preexisting_track=None,cycle_id=None)
                    self._event(dict(event='PLC_REQUEST_ENTRY_PROVEN', token=self.handshake.token,
                        evidence=self.request_product_separation))
            return True
        if self._release_unused_preview(packet):
            return True  # Reacquire from a subsequent valid Worker frame.
        issue = self.cycle_issue
        if not issue:
            return False
        if getattr(self.gateway, 'contract_version', None) == 'OPENER_CYCLIC':
            # Continue the parent's validated clearance observation after C has
            # cancelled/completed a token. Never call the legacy release API.
            return bool(self.service.active)
        # Parent validated packet identity, age, absence and the configured area
        # evidence already. Request OFF or a timeout is never product clearance.
        area = self.area_observation or {}
        healthy_clear = bool(self.area_config_version and self._absence_ready()
            and self._area_approval_current(area) and area.get('state') == 'CLEAR'
            and area.get('first_clear_monotonic', -1) >= issue['monotonic_s']
            and not self.service.active and not self.service.error)
        self._diagnostic_reason = 'REQUEST_ISSUE_OBSERVING_FOR_CLEARANCE'
        if (healthy_clear and self.handshake.state == 'WAIT_PRODUCT_CLEAR'
                and self.handshake.release_cleared_cycle(product_clear=True)):
            self._event(dict(event='LINE_REQUEST_ISSUE_CLEARED', previous_issue=issue,
                             clearance_frame_id=packet['frame_id'], plc_writes=0))
            self._reset_unbound_observation(time.monotonic())
            self.arrival = None
            self.cycle_issue = None
            self.issue = dict(issue, active=False, action='CLEARED_WAIT_NEW_REQUEST')
        return True

    def stop_auto(self):
        # Maintenance stop cannot assert motion. Physical independent STOP remains required.
        with self.lock, self.service.lock:
            self._fault('LOCAL_MAINTENANCE_HOLD')
            self.handshake.fault('LOCAL_MAINTENANCE_HOLD', 'BLOCKED')
            self.handshake.shutdown()
            return self.status()

    def _initial_policy(self):
        return (self._full_frame_policy()
            and self.line_profile.get('initial_authorization') == INITIAL_POLICY
            and self.line_profile.get('cycle_admission') == 'FIRST_PRODUCT_ONLY')

    def _supervised_policy(self):
        return (self._full_frame_policy()
            and self.line_profile.get('initial_authorization') == REPEAT_POLICY
            and self.line_profile.get('cycle_admission') == REPEAT_POLICY)

    def _automatic_policy(self):
        return (self._full_frame_policy()
            and self.line_profile.get('cycle_admission') == AUTO_POLICY)

    def _restore_previous_product_identity(self):
        """A service restart is not evidence that the last product has left.

        Keep unproven departure as diagnostic history, never synthesize CLEAR.
        New-cycle admission separately verifies C transaction and Journal
        readiness, and cannot claim that it identifies a different physical item.
        """
        journal = self.service.journal
        with journal.lock:
            row = latest_product(journal.db)
            proof = None if not row else journal.db.execute("""
                SELECT 1 FROM events WHERE event_type='AUTOMATIC_PRODUCT_SEPARATED'
                  AND json_extract(payload_json,'$.payload.evidence.inspection_id')=?
                  AND json_extract(payload_json,'$.payload.evidence.reason')='PRODUCT_TRAJECTORY_AND_EXIT_STRIP'
                  AND json_extract(payload_json,'$.payload.evidence.duration_s')>=1.2-1e-9
                LIMIT 1
            """,(row['inspection_id'],)).fetchone()
            closed = bool(row and valid_context_close(journal.db, row['inspection_id']))
        self.prior_product_identity_block = (
            'PREVIOUS_RUNTIME_PRODUCT_EXIT_UNPROVEN' if row and not proof and not closed else None)

    def _product_recovery_proof(self, identifier=None):
        """Caller holds runtime/service locks; no confirmations are invented."""
        now=time.monotonic()
        s=self.gateway.read_snapshot(now)
        if not s: raise ValueError('CURRENT_PLC_SNAPSHOT_REQUIRED')
        s=dict(s,observed_at=now,runtime_session=self.gateway.runtime_session)
        health=self.service.health(); a=self.assembly.status(); j=self.service.journal
        if self.error or health.get('error') or a.get('error'):
            raise ValueError('OWNER_ERROR_BLOCKS_CONTEXT_RECOVERY')
        with j.lock:
            row=latest_product(j.db)
            if not row or (identifier is not None and row['inspection_id']!=identifier):raise ValueError('LATEST_PRODUCT_CONTEXT_REQUIRED')
            identifier=row['inspection_id']
            final=j.db.execute('SELECT value FROM service_state WHERE key=?',('integrated_decision:'+identifier,)).fetchone()[0]
        proof=dict(inspection_id=identifier,
            request_sha256=digest(row['request_json']),result_sha256=digest(row['result_json']),final_sha256=digest(final),
            current=s,owners=dict(runtime_session=self.gateway.runtime_session,
                worker_state=health.get('state'),worker_alive=health.get('worker_alive'),camera_ready=health.get('camera_ready'),
                active_inspection_id=health.get('active_inspection_id'),storage_pending=health.get('storage_pending'),
                final_commit_pending=self.final_pending is not None,
                assembly_active=a.get('active_identifier'),assembly_pending=a.get('pending'),assembly_outstanding=a.get('outstanding')))
        return row,final,proof

    def previous_product_recovery_status(self):
        """On-demand preflight, never a normal admission gate or a reset on GET."""
        from src.runtime.product_context_recovery import validate_state
        if not self._automatic_policy():
            return dict(eligible=False,reason='AUTOMATIC_CONTEXT_RECOVERY_ONLY')
        with self.lock, self.service.lock:
            try:
                row,final,proof=self._product_recovery_proof()
                j=self.service.journal
                with j.lock:
                    if valid_context_close(j.db,row['inspection_id']):
                        return dict(eligible=False,reason='CONTEXT_RECOVERY_ALREADY_RECORDED',inspection_id=row['inspection_id'])
                    if count_unfinished_inspections(j.db):
                        raise ValueError('UNFINISHED_INSPECTION_BLOCKS_CONTEXT_RECOVERY')
                j.capacity()
                validate_state(row,final,proof,time.monotonic())
                return dict(eligible=True,reason='PHYSICAL_CONFIRMATION_AND_AUTHENTICATION_REQUIRED',
                    inspection_id=row['inspection_id'],completed_at=row['completed_at'],
                    plc=proof['current']['controls'],outputs=proof['current']['raw100'])
            except (ValueError,KeyError,TypeError,OSError) as error:
                return dict(eligible=False,reason=str(error))

    def close_previous_product_context(self, identifier, actor, reason, confirmations):
        """Authenticated maintenance only; no PLC write, grant, or result replay."""
        if not self._automatic_policy(): raise ValueError('AUTOMATIC_CONTEXT_RECOVERY_ONLY')
        with self.lock, self.service.lock:
            row,final,proof=self._product_recovery_proof(identifier)
            proof.update(actor=actor,reason=reason,confirmations=confirmations)
            j=self.service.journal;s=proof['current'];now=s['observed_at']
            def recheck():
                current=self.gateway.read_snapshot(time.monotonic())
                if not current or any(current.get(k)!=s.get(k) for k in
                        ('boot','connection','request_id','phase','controls','raw100')):
                    raise ValueError('PLC_CHANGED_DURING_CONTEXT_RECOVERY')
                from src.runtime.product_context_recovery import validate
                validate(row,final,dict(proof,current=dict(current,observed_at=time.monotonic(),
                    runtime_session=self.gateway.runtime_session)),time.monotonic())
            receipt=record_context_close(j,identifier,proof,now=now,recheck=recheck)
            self._restore_previous_product_identity()
            self.product_passage=self.product_separation=self.request_product_separation=None
            self.automatic_identity_block=None
            self.cyclic_admissions=0
            self._reset_unbound_observation(time.monotonic())
            self.latest_packet=None
            self.observation_started_at=time.monotonic()
            self.handshake.retire_automatic()  # seen_token is preserved: no replay.
            self._automatic_previous=None
            self.arrival=None
            self.cycle_issue=self.issue=None
            return receipt

    def _automatic_health(self, snapshot, healthy, now):
        """Check actual owners/storage, not an application-issued right to inspect.

        No ID, file, ledger or arm command is created. A C request is identified
        solely by adapter boot/connection/request counter. Visual departure is
        diagnostic; each accepted cycle requires a new observation window.
        """
        self.plc_cycle['reason'] = 'WAIT_AUTO_QUALIFICATION_OR_HEALTH'
        if not healthy:
            return False
        if not (snapshot and snapshot['connected'] and snapshot['fresh']
                and snapshot['run_idle'] and snapshot['bool_valid']
                and 0 <= now-snapshot['generated'] <= .5
                and 0 <= now-snapshot['received'] <= .2):
            self.plc_cycle['reason'] = 'WAIT_FRESH_PLC_CONNECTION'
            return False
        controls = snapshot['controls']
        unaccepted = snapshot['phase'] in ('DISARMED','SYNC_LOW','IDLE','READY_NEXT')
        if unaccepted and controls['Inspection_Request']:
            if self._unaccepted_request_at is None:
                self._unaccepted_request_at = now
            if now-self._unaccepted_request_at >= 2:
                self.gateway.cancel()
                self.plc_cycle['reason'] = 'UNACCEPTED_REQUEST_RESIDUE_TIMEOUT_PHYSICAL_STOP_REQUIRED'
                return False
        else:
            self._unaccepted_request_at = None
        # A BUSY owner is healthy. Do not acquire the Journal lock while its
        # storage worker commits raw/final evidence. The storage health path
        # and current-request deadlines still detect failure or a stalled job.
        active = (self.service.active or self.final_pending
            or self.handshake.state in ('REQUEST_LATCHED','INSPECTING','WAIT_REQUEST_OFF'))
        if not active:
            if getattr(self, 'request_start', None):
                ready = self.request_start.ready(snapshot)
                if not ready:
                    self.plc_cycle['reason'] = 'WAIT_DURABLE_REQUEST_READINESS'
                    return False
                self.plc_cycle['reason'] = ('WAIT_NEW_PHYSICAL_START' if snapshot['phase']=='SYNC_LOW'
                    else 'WAIT_PLC_REQUEST' if snapshot['phase']=='IDLE'
                    else snapshot['reason'] if snapshot['phase']=='DISARMED' else 'CURRENT_CYCLE_ACTIVE')
                return True
            try:
                journal = self.service.journal
                with journal.lock:
                    if self._journal_readiness.count(journal.db):
                        self.plc_cycle['reason'] = 'JOURNAL_UNFINISHED_INSPECTION'
                        return False
                    journal.capacity()
                settlement = self._supervised_settlement()
                if not settlement['clean']:
                    self.plc_cycle['reason'] = settlement['reason']
                    return False
            except Exception as error:
                self.plc_cycle['reason'] = 'JOURNAL_OR_STORAGE_NOT_READY:'+type(error).__name__
                return False
        self.plc_cycle['reason'] = ('WAIT_NEW_PHYSICAL_START' if snapshot['phase']=='SYNC_LOW'
            else 'WAIT_PLC_REQUEST' if snapshot['phase']=='IDLE'
            else snapshot['reason'] if snapshot['phase']=='DISARMED'
            else 'CURRENT_CYCLE_ACTIVE')
        return True

    def _automatic_request_evidence(self, snapshot, ready, now):
        """Validate a new C transaction, never claim a distinct physical item.

        C increments completed_count only after Result, later cyclic Done,
        Request LOW and Done reset. Counters survive the brief LOW-to-new-edge
        race that a Python poll may miss; boot/connection must remain identical.
        """
        if (not ready or self.error or self.aborted_inspection or self.service.error
                or self.service.active or self.final_pending
                or getattr(self, 'audit_pending', None)
                or getattr(self.service, 'storage_pending', None)):
            raise ValueError('CURRENT_SYSTEM_OR_STORAGE_NOT_READY')
        if (not snapshot or snapshot['phase'] != 'REQUEST_RECEIVED'
                or not all(snapshot[k] for k in ('connected','fresh','bool_valid','run_idle'))
                or not 0 <= now-snapshot['generated'] <= .5
                or not 0 <= now-snapshot['received'] <= .2
                or not 0 <= now-snapshot['accepted_at'] < self.line_profile['arrival_deadline_s']
                or snapshot['accepted_at'] < self._automatic_started_at
                or snapshot['raw100'] != '00000000'
                or not all(snapshot['controls'].get(k) for k in
                           ('Inspection_Request','Mc_Run','EStop_OK','Stop_PB'))):
            raise ValueError('NEW_CYCLIC_REQUEST_CONTEXT_INVALID')
        counters = {key: snapshot.get(key) for key in ('result_count','done_count','completed_count')}
        if any(type(value) is not int or value < 0 for value in counters.values()):
            raise ValueError('CYCLIC_COMPLETION_COUNTERS_REQUIRED')
        if getattr(self, 'request_start', None):
            if not self.request_start.ready(snapshot):
                raise ValueError('REQUEST_READINESS_EVIDENCE_NOT_CURRENT')
        else:
            journal = self.service.journal
            with journal.lock:
                if self._journal_readiness.count(journal.db):
                    raise ValueError('JOURNAL_UNFINISHED_INSPECTION')
                journal.capacity()
        settlement = self._supervised_settlement()
        if not settlement['clean']:
            raise ValueError(settlement['reason'])
        previous = self._automatic_previous
        if self.cyclic_admissions and not previous:
            raise ValueError('PREVIOUS_REQUEST_NOT_SETTLED')
        if previous:
            prefix = f"{snapshot['boot']:016x}:{snapshot['connection']}:"
            token = previous['request_token']
            if (not token.startswith(prefix)
                    or snapshot['request_id'] != int(token.rsplit(':',1)[1])+1):
                raise ValueError('CYCLIC_SESSION_OR_REQUEST_SEQUENCE_CHANGED')
            baseline = previous.get('start_counters') or {}
            if any(key not in baseline or counters[key] != baseline[key]+1 for key in counters):
                raise ValueError('PREVIOUS_RESULT_DONE_RESET_NOT_CONFIRMED')
            if (settlement.get('previous') or {}).get('inspection_id') != previous['inspection_id']:
                raise ValueError('PREVIOUS_DURABLE_RESULT_MISMATCH')
        return dict(policy='PLC_CYCLE_FRESH_OBSERVATION_V1',
            request_token=f"{snapshot['boot']:016x}:{snapshot['connection']}:{snapshot['request_id']}",
            accepted_at=snapshot['accepted_at'], start_counters=counters,
            previous_transaction=settlement.get('previous'),
            physical_product_identity_proven=False, product_exit_claimed=False)

    def _start_automatic_observation_window(self, evidence):
        diagnostic = dict(passage=self.product_passage.status() if self.product_passage else None,
            restored_identity_reason=self.prior_product_identity_block, issue=self.issue)
        self._event(dict(event='PLC_CYCLE_OBSERVATION_WINDOW_STARTED', evidence=evidence,
                         prior_tracking=diagnostic))
        self.previous_tracking_diagnostic = diagnostic
        self._automatic_cycle_evidence = evidence
        self.request_product_separation = self.product_separation  # Optional real proof only.
        self.product_passage = self.product_separation = None
        self.automatic_identity_block = self.prior_product_identity_block = None
        self.cycle_issue = self.issue = None
        self._passage_history.clear()
        # Only validated new cycles retire preview identity. Keep epoch,
        # generation and source sequence guards; never adopt queued old frames.
        self._reset_unbound_observation(evidence['accepted_at'])
        self.latest_packet = None
        self.observation_started_at = evidence['accepted_at']
        self.absent.clear()

    def _automatic_transaction_settled(self):
        now = time.monotonic()
        s = self.gateway.read_snapshot(now)
        old = self.product_passage.identity if self.product_passage else {}
        prefix = f"{s['boot']:016x}:{s['connection']}:" if s else ''
        settled = bool(s and s['connected'] and s['fresh'] and s['bool_valid'] and s['run_idle']
            and 0 <= now-s['generated'] <= .5 and 0 <= now-s['received'] <= .2
            and old.get('request_token', '').startswith(prefix)
            and int(old['request_token'].rsplit(':', 1)[1]) <= s['request_id']
            and s['raw100'] == '00000000'
            and s.get('transaction_settled') is True
            and not s['controls']['Inspection_Request'] and not self.service.active)
        if settled and self.product_passage:
            self.product_passage.settled_transaction = dict(boot=s['boot'],connection=s['connection'],
                request_id=s['request_id'],previous_token=old['request_token'],observed_at=now)
        return settled

    def _pending_entry_matches_request(self, proof, packet):
        """Resolve a Request/proof race without adopting a later product.

        The old LOW/output reset was already observed on this connection. The
        positive upstream entry must start before the current Request, and the
        same still-live token must have no inspection bound. Existing deadlines
        and control checks remain in force; a proof after cancellation is inert.
        """
        h = self.handshake
        p = self.product_passage
        settled = p.settled_transaction if p else None
        entry = proof.get('upstream_entry') or {}
        context = self.arrival or {}
        if (self.automatic_identity_block != 'PREVIOUS_PRODUCT_IDENTITY_OR_EXIT_UNPROVEN'
                or self.prior_product_identity_block or not settled or not entry
                or h.state != 'REQUEST_LATCHED' or h.cancelled or h.inspection_id
                or self.service.active or self.error or self.cycle_issue
                or context.get('token') != h.token
                or entry['first_time'] > h.accepted_at
                or packet['camera_epoch'] != context.get('epoch')
                or packet['generation'] != context.get('generation')):
            return False
        now = time.monotonic()
        s = self.gateway.read_snapshot(now)
        return bool(s and s['connected'] and s['fresh'] and s['bool_valid'] and s['run_idle']
            and 0 <= now-s['generated'] <= .5 and 0 <= now-s['received'] <= .2
            and 0 <= now-h.accepted_at < self.line_profile['arrival_deadline_s']
            and (s['boot'],s['connection']) == (settled['boot'],settled['connection'])
            and s['request_id'] > settled['request_id']
            and f"{s['boot']:016x}:{s['connection']}:{s['request_id']}" == h.token
            and s['phase'] == 'REQUEST_RECEIVED' and s['raw100'] == '00000000'
            and all(s['controls'].get(k) for k in ('Inspection_Request','Mc_Run','EStop_OK','Stop_PB')))

    def _automatic_exit_evidence(self, now, settlement):
        proof = self.product_separation
        previous = settlement.get('previous') or {}
        if (proof and proof.get('inspection_id') == previous.get('inspection_id')
                and proof.get('camera_epoch') == self.epoch
                and proof.get('generation') == self.service.generation):
            return proof
        return None

    def _area_clearance(self, packet, provider):
        if self._automatic_policy():
            # Diagnostic only in this policy. Neither MATCH nor UNKNOWN is
            # authority to close a product identity or admit the next request.
            return None
        return super()._area_clearance(packet, provider)

    def _supervised_settlement(self):
        """Durable previous result and idle owners; never infer physical clearance."""
        if getattr(self, 'request_start', None):
            return self.request_start.settlement()
        if self.error or self.service.error or self.service.active:
            return dict(clean=False, reason='WAIT_HEALTHY_IDLE_INSPECTION_OWNER', previous=None)
        assembly = self.assembly.status()
        if assembly.get('active_identifier') or assembly.get('pending') or assembly.get('outstanding'):
            return dict(clean=False, reason='WAIT_ASSEMBLY_OWNER_IDLE', previous=None)
        identifier = self.handshake.inspection_id or self.bridge.inspection_id
        expected_token = self.handshake.token
        if self._automatic_policy() and not expected_token:
            # Retiring a settled software Track does not erase its transaction.
            # Reload the exact saved final, including after a normal PLC STOP.
            # Admission still checks the adapter boot/connection/request token.
            completed = self._automatic_previous or {}
            identifier = completed.get('inspection_id')
            expected_token = completed.get('request_token')
        if not identifier:
            return dict(clean=True, reason=None, previous=None)
        journal = self.service.journal
        row = journal.detail(identifier)
        with journal.lock:
            saved = journal.db.execute('SELECT value FROM service_state WHERE key=?',
                                      ('integrated_decision:'+identifier,)).fetchone()
        final = json.loads(saved[0]) if saved else None
        if (not row or row['state'] not in ('COMPLETE', 'CANCELLED') or not final
                or not row['result'].get('storage_success')
                or final.get('request_token') != expected_token
                or identifier not in self.published_ids):
            return dict(clean=False, reason='PREVIOUS_RESULT_NOT_DURABLE_OR_IDENTIFIED', previous=None)
        binding = row['request'].get('runtime_binding', {})
        previous = dict(inspection_id=identifier, request_token=final['request_token'],
            decision=final['decision'], durable=True, tracking_session=binding.get('runtime_session_id'),
            cycle_id=binding.get('cycle_id'), track_id=binding.get('track_id'))
        return dict(clean=True, reason=None, previous=previous)

    def _prepare_supervised_product(self, evidence, now):
        """Close the old software identity under explicit human evidence, not CLEAR."""
        self._event(dict(event='SUPERVISED_PRODUCT_CONTEXT_CLOSED',
            approval_id=evidence['approval_id'], previous=evidence['previous'],
            confirmations=evidence['confirmations'], ai_clearance_granted=False))
        self._reset_unbound_observation(now)
        self.latest_packet = None
        self.observation_started_at = now
        self.absent = []
        self.arrival = None
        self.cycle_issue = None
        self.issue = None
        self.last_retirement = None
        self.cyclic_rearm_evidence = None
        self.handshake.retire_supervised()

    def prepare_supervised(self, challenge_id, confirmations):
        with self.lock, self.service.lock:
            if not self._supervised_policy() or not self.initial_approval:
                raise ValueError('SUPERVISED_POLICY_NOT_ENABLED')
            identifier = self.initial_approval.submit(challenge_id, confirmations, time.monotonic())
            return dict(approval_id=identifier, state='QUEUED_NOT_ARMED', motor_command=False)

    def _profile_ready(self):
        if self._automatic_policy():
            return self._automatic_readiness()['normal_profile_ready']
        if self._initial_policy() or self._supervised_policy():
            # Software policy selection only. Actual permission is a live, durable
            # operator grant; field qualification remains explicitly unverified.
            return True
        if self._full_frame_policy():
            qualification = self.line_profile.get('request_start_qualification', {})
            return bool(qualification.get('verified') is True
                and qualification.get('policy') == FULL_FRAME
                and qualification.get('calibration_sha') == calibration_sha(self.service.calibration)
                and isinstance(qualification.get('evidence'), str) and qualification['evidence'].strip())
        return bool(self.line_profile.get('field_profile_verified') is True
            and self.zone.get('confirmed')
            and self.zone.get('calibration_sha') == calibration_sha(self.service.calibration)
            and self.area_config_version)

    def _automatic_readiness(self):
        """Configuration validity is not unattended recovery qualification.

        Live STOP/freshness/storage/camera/identity guards remain in their actual
        owners. An unsupported PLC response timer cannot become an application
        permission gate for normal, supervised PLC-owned cycles.
        """
        q = self.line_profile.get('automatic_operation_qualification', {})
        normal = bool(q.get('policy') == AUTO_POLICY
            and self.service.calibration
            and q.get('calibration_sha') == calibration_sha(self.service.calibration)
            and q.get('exit_edge') in ('left', 'right')
            and q.get('passage_policy') == 'PRODUCT_TRAJECTORY_AND_EXIT_STRIP')
        limits = [reason for key, reason in (
            ('plc_online_equivalence_verified', 'ONLINE_PLC_EQUIVALENCE_UNVERIFIED'),
            ('plc_timeout_stop_recovery_verified', 'PLC_TIMEOUT_STOP_RECOVERY_UNVERIFIED'),
            ('unoccluded_exit_verified', 'FIELD_PRODUCT_EXIT_UNVERIFIED'),
            ('class1_stability_verified', 'CLASS1_STABILITY_UNVERIFIED')) if q.get(key) is not True]
        return dict(normal_profile_ready=normal, software_permission_required=False,
            unattended_recovery_verified=bool(normal and q.get('verified') is True and not limits),
            field_limits=limits, fault_recovery='PHYSICAL_STOP_AND_DIAGNOSIS',
            raw_photo_sensor_required=False, independent_plc_timeout_required=False)

    def _remember_bound_passage_packet(self, packet):
        tracker = self.coordinator._tracker
        binding = (self.bridge.request or {}).get('runtime_binding', {})
        if (not self._automatic_policy() or self.product_passage
                or self.handshake.state != 'INSPECTING' or not self.handshake.token
                or packet is not self.latest_packet or self.error or self.cycle_issue
                or tracker._state in (TrackState.LOST, TrackState.WAIT_AREA_CLEAR)
                or binding.get('track_id') != tracker._track_id
                or binding.get('runtime_session_id') != self.session_id
                or binding.get('plc_request_token') != self.handshake.token):
            return
        owner = (self.handshake.token, self.session_id, tracker._track_id)
        self._passage_history.append((owner, packet))

    def _apply_packet(self, packet):
        result = super()._apply_packet(packet)
        # The provider alone cannot associate a box with the bound product.
        # Preserve observations only after the existing tracker accepted them.
        self._remember_bound_passage_packet(packet)
        return result

    def _packet(self, packet):
        # Record the data actually removed from the Worker queue. Even rejected
        # packets are visible; diagnostic sampling never changes the verdict.
        was_invalid = bool(self.product_passage and self.product_passage.invalid)
        try:
            return super()._packet(packet)
        finally:
            self.consumed_frames.record(packet, consumed_at=time.monotonic(),
                outcome=getattr(self, '_diagnostic_reason', None),
                passage=self.product_passage.reason if self.product_passage else None,
                token=self.handshake.token,
                passage_state=self.product_passage.status() if self.product_passage else None)
            if self.product_passage and self.product_passage.invalid and not was_invalid:
                self.consumed_frames.checkpoint('PRODUCT_PASSAGE_FIRST_INVALID', self.product_passage.status())

    def consumed_frame_snapshot(self):
        with self.lock:
            captured = self.consumed_frames.capture(include_checkpoints=True)
        # Diagnostic copying must not hold the PLC control/health loop's lock.
        return self.consumed_frames.copy_snapshot(captured)

    def _clear(self, now):
        if self._automatic_policy():
            return False  # Area observation remains diagnostic, never forced CLEAR.
        if self._supervised_policy():
            return False  # Operator product removal never becomes AI Area CLEAR.
        if self._full_frame_policy():
            # Actual departure evidence only; initial permission has its own IPC
            # command and durable ledger. Never synthesize this from an approval.
            qualification = self.line_profile.get('clearance_qualification', {})
            if not (qualification.get('verified') is True and self.area_config_version
                    and qualification.get('config_sha') == self.area_config_version
                    and qualification.get('calibration_sha') == calibration_sha(self.service.calibration)
                    and isinstance(qualification.get('evidence'), str) and qualification['evidence'].strip()):
                return False
            if (self.line_profile.get('cycle_admission') == 'FIRST_PRODUCT_ONLY'
                    and self.cyclic_admissions):
                return False
        area = self.area_observation
        return bool(self._absence_ready() and self._area_approval_current(area)
            and area['state'] == 'CLEAR' and self.coordinator.active_cycle is None
            and not self.service.active and self.latest_packet
            and 0 <= now-self.latest_packet['processed_monotonic'] < 2)

    def _full_frame_policy(self):
        return (getattr(self, 'line_profile', {}).get('inspection_start_policy') == FULL_FRAME
                and getattr(getattr(self, 'gateway', None), 'contract_version', None) == 'OPENER_CYCLIC')

    def _inspection_start_ready(self, bound_eligible, motion_mode, motion_ready):
        if self._full_frame_policy():
            # Worker still evaluates blur/motion/pose and the three fresh frames.
            return bound_eligible
        return super()._inspection_start_ready(bound_eligible, motion_mode, motion_ready)

    def _area_transaction_block(self):
        if (getattr(self.gateway, 'contract_version', None) == 'OPENER_CYCLIC'
                and self.handshake.state in ('WAIT_PRODUCT_CLEAR', 'HOLD')
                and not self.handshake.request
                and not self.service.active and not self.service.error
                and self.operating and not self.error):
            return None
        if (getattr(self.gateway, 'contract_version', None) != 'LEGACY_THREE_BOOL'
                or self.handshake.state != 'WAIT_PRODUCT_CLEAR'):
            return super()._area_transaction_block()
        # A withdrawn request may retire visually without a PLC publication.
        # The cancelled worker must finish first; no fabricated ACK or CLEAR.
        if not self.operating or self.error:
            return 'USER_STOP_OR_SYSTEM_FAULT'
        if (getattr(self.service, 'error', None) or
                getattr(self.service, 'state', 'IDLE') in ('RECOVERY', 'STOPPED', 'CANCELLING')):
            return 'INSPECTION_SERVICE_OR_CAMERA_FAULT'
        if self.service.active:
            return 'INSPECTION_IN_FLIGHT'
        if self.bridge.inspection_id and self.bridge.inspection_id not in self.published_ids:
            return 'RESULT_NOT_SETTLED'
        if self.handshake.reason not in ('LEGACY_REQUEST_WITHDRAWN_RESULT_BLOCKED',
                                        'LEGACY_COMPLETED_WAIT_PRODUCT_CLEAR',
                                        'LEGACY_BOOL_UNREPRESENTABLE_REVIEW',
                                        'LEGACY_BOOL_UNREPRESENTABLE_ERROR'):
            return 'LEGACY_TRANSACTION_UNSETTLED'
        return None

    def _cancel_pending(self, reason):
        start = getattr(self, 'request_start', None)
        if start and start.pending and start.pending.get('reservation'):
            start._block(start.pending, reason)
            self.arrival = None
            return
        if self.bridge.inspection_id and self.bridge.inspection_id not in self.published_ids:
            self.bridge.phase = 'INSPECTION_ABORTED'
            self.phase = 'INSPECTION_ABORTED'
            self.aborted_inspection = dict(inspection_id=self.bridge.inspection_id, reason=reason,
                request_token=self.handshake.token, plc_publication=self.handshake.publication)
            self.published_ids.add(self.bridge.inspection_id)
            self._event(dict(event='LINE_CANCELLED_RESULT_BLOCKED', inspection_id=self.bridge.inspection_id, reason=reason))
        if self.service.active:
            self._cancel_active_inspection(reason)
        self.arrival = None

    def _cancel_active_inspection(self, reason):
        start = getattr(self, 'request_start', None)
        if start and start.capture_events:
            # The request event writer may own Journal. Withdraw authority and
            # signal the Worker immediately; its cancelled completion follows
            # the existing durable failure path after that writer releases it.
            self.service.cancellation.set()
            self.service.state = 'CANCELLING'
            self.gateway.health_update(False, False, time.monotonic())
            self.handshake.fault(reason)
            return
        self.service.cancel(self.service.active['inspection_id'])

    def _poll_plc(self, now):
        if now < self.next_plc_poll_at: return
        self.next_plc_poll_at = now + .1
        if getattr(self.gateway, 'contract_version', None) == 'OPENER_CYCLIC':
            self._poll_cyclic_plc(now)
            return
        if getattr(self.gateway, 'contract_version', None) == 'LEGACY_THREE_BOOL':
            self._poll_legacy_plc(now)
            return
        if self.handshake.state == 'RESYNC_REQUIRED':
            self._cancel_pending(self.handshake.reason)
            self.line_wait = self.handshake.reason
            if now < self.recovery_at or self.service.active: return
            self.recovery_at = now + 5
            # New session is the only reconnect path. Never retry an uncertain result.
            # PLC V3 drops Run on session change and requires a fresh physical Start.
            previous = self.handshake.status()
            self.gateway.close()
            session = self.service.journal.new_session('standalone-line')
            self.handshake = LineHandshake(self.gateway, self._event, session_id=session)
            self._event(dict(event='LINE_RESYNC_NEW_SESSION', previous=previous, new_session=session))
            self._replace_tracking_session(uuid.uuid4().hex)
            self.bridge = InspectionBridge(self.service, self.coordinator)
            self.inspected_tracks.clear()
            self.absent.clear()
            self.error = None
            self.latest_packet = None
            self.epoch = None
            self.last_sequence, self.last_time = -1, 0
            self.worker_generation = self.service.generation
            self.eligible = False
            self.observation_started_at = now
            self._reset_departure_candidate()
        previous = self.handshake.token
        clear = self._clear(now)
        ready = bool(self.operating and not self.error and self._profile_ready()
            and self.assembly.ready and self.service.status()['ready'])
        self.handshake.service_tick(now, ready=ready, product_clear=clear)
        if self.handshake.state == 'RESYNC_REQUIRED':
            self._cancel_pending(self.handshake.reason)
            self.operating = False
            return
        if self.handshake.token and self.handshake.token != previous:
            # A pre-existing track at the sensor edge cannot silently be adopted.
            track = self.coordinator._tracker._track_id
            self.arrival = dict(token=self.handshake.token, epoch=self.epoch,
                generation=self.service.generation, track=None, conveyor_off_at=None,
                preexisting_track=track)
            self._event(dict(event='UPSTREAM_ENTRY_ACCEPTED', line_cycle_id=self.handshake.cycle_id,
                             camera_epoch=self.epoch, preexisting_track=track))
        self.line_wait = (self.handshake.reason or ('WAIT_FIELD_PROFILE' if not self._profile_ready()
            else 'WAIT_ASSEMBLY_MODEL' if not self.assembly.ready
            else 'READY_WAIT_PHYSICAL_START' if not self.handshake.inputs.get('PLC_RunPermit')
            else self.handshake.state))

    def _poll_cyclic_plc(self, now):
        if self._poll_completion_audit(now):
            return
        health = self.service.health()
        # BUSY is a healthy inspector, not a reason to revoke an active request.
        ready = bool(self.operating and not self.error and self._profile_ready()
            and not health.get('error') and self.assembly.ready and health.get('camera_ready')
            and health.get('state') in ('IDLE', 'BUSY'))
        if self.initial_approval:
            snapshot = self.gateway.read_snapshot(now)
            if snapshot: now = snapshot.get('observed_at', now)
            options = (dict(settlement=self._supervised_settlement(), prepare=self._prepare_supervised_product)
                       if self._supervised_policy() else {})
            self.initial_approval.poll(snapshot, ready, self.epoch, self.service.generation,
                                       now, self.gateway, self.service.journal, **options)
            if self._supervised_policy() and self.initial_approval.last_complete:
                completed = self.initial_approval.last_complete
                for entry in self.history:
                    if entry['inspection_id'] == completed['inspection_id'] and not entry.get('cyclic_done_reset_observed'):
                        self._event(dict(event='SUPERVISED_CYCLIC_COMPLETION_OBSERVED', **completed))
                        entry['cyclic_done_reset_observed'] = True
                        entry['publication_status'] = 'CYCLIC_DONE_AND_REQUEST_RESET'
            if self.initial_approval.failed or (self.initial_approval.state == 'REVOKED'
                                                and not self._supervised_policy()):
                ready = False
        clear = self._clear(now)
        if self._automatic_policy():
            snapshot = self.gateway.read_snapshot(now)
            if snapshot: now = snapshot.get('observed_at', now)
            ready = self._automatic_health(snapshot, ready, now)
            if snapshot:
                token = f"{snapshot['boot']:016x}:{snapshot['connection']}:{snapshot['request_id']}"
                for entry in self.history:
                    if (entry['request_token'] == token and not entry.get('cyclic_done_reset_observed')
                            and snapshot.get('transaction_settled') is True
                            and snapshot['raw100'] == '00000000'
                            and not snapshot['controls']['Inspection_Request']):
                        self._completion_event(dict(event='PLC_CYCLIC_COMPLETION_OBSERVED',
                            inspection_id=entry['inspection_id'], request_token=token))
                        entry['cyclic_done_reset_observed'] = True
                        entry['publication_status'] = 'CYCLIC_DONE_AND_REQUEST_RESET'
        if (self._full_frame_policy() and clear and self.last_retirement
                and self.handshake.state == 'WAIT_PRODUCT_CLEAR'
                and self.last_retirement['source_monotonic'] > self.handshake.accepted_at
                and self.arrival and self.last_retirement['track_id'] == self.arrival['track']):
            self.cyclic_rearm_evidence = dict(self.last_retirement or {},
                clearance_frame_id=self.latest_packet['frame_id'])
        self.gateway.ready_reason = (health.get('error') or self.error or
            ('APPROVAL_REVOKED' if self.initial_approval and self.initial_approval.state == 'REVOKED'
             else self.plc_cycle['reason'] if self.plc_cycle and not ready
             else 'READY' if ready else 'PROFILE_MODEL_OR_OPERATING_NOT_READY'))
        self.gateway.health_update(ready, clear, time.monotonic())
        if getattr(self, 'audit_pending', None):
            return  # Preserve pending C edge; no new admission before audit durability.
        previous = self.handshake.token
        admission, admission_error = None, None
        if self._automatic_policy():
            incoming = self.gateway.read_snapshot(now)
            key = (f"{incoming['boot']:016x}:{incoming['connection']}:{incoming['request_id']}"
                   if incoming else None)
            if incoming and incoming['phase'] == 'REQUEST_RECEIVED' and key != self.handshake.seen_token:
                try:
                    admission = self._automatic_request_evidence(
                        incoming, ready, incoming.get('observed_at', now))
                except Exception as error:
                    admission_error = str(error) if isinstance(error, ValueError) else type(error).__name__
        self.handshake.poll(now)
        if self.handshake.cancelled:
            self._cancel_pending(self.handshake.reason)
        if self.handshake.token and self.handshake.token != previous:
            if self.initial_approval:
                try:
                    self.initial_approval.accept(self.handshake.snapshot, self.handshake.token)
                except Exception as error:
                    self.handshake.fault('FIRST_APPROVAL_ACCEPT_FAILED:'+type(error).__name__)
                    self._cancel_pending(self.handshake.reason)
                    return
            if self._full_frame_policy():
                repeat_allowed = ((self.line_profile.get('cycle_admission') == 'VERIFIED_CLEARANCE'
                                  and self.cyclic_rearm_evidence is not None)
                                  or (self._supervised_policy() and self.initial_approval.valid())
                                  or self._automatic_policy())
                if self.cyclic_admissions and not repeat_allowed:
                    self.handshake.fault('NEXT_PRODUCT_REQUIRES_VERIFIED_CLEARANCE')
                    self._cancel_pending(self.handshake.reason)
                    self.line_wait = self.handshake.reason
                    return
                if self._automatic_policy():
                    if (admission_error or not admission
                            or admission['request_token'] != self.handshake.token):
                        reason = admission_error or 'CYCLIC_ADMISSION_CONTEXT_CHANGED'
                        self._event(dict(event='PLC_CYCLE_ADMISSION_REJECTED', reason=reason,
                                         request_token=self.handshake.token))
                        self.handshake.fault(reason)
                        self._cancel_pending(reason)
                        self.line_wait = reason
                        return
                    self._start_automatic_observation_window(admission)
                self.cyclic_admissions += 1
                self.cyclic_rearm_evidence = None
            # This PLC raises Request AFTER transfer and its stop command.
            # A currently tracked product may already be present; require the
            # same track and NEW source frames under the selected start policy.
            self.arrival = dict(token=self.handshake.token, epoch=self.epoch,
                generation=self.service.generation, track=None,
                preexisting_track=self.coordinator._tracker._track_id)
            if self._full_frame_policy():
                cycle = self.coordinator.active_cycle
                self.arrival.update(track=self.coordinator._tracker._track_id,
                    cycle_id=cycle.cycle_id if cycle else None,
                    sequence_at_request=self.last_sequence,
                    frame_id_at_request=(self.latest_packet or {}).get('frame_id'))
                self._event(dict(event='PLC_REQUEST_TRACK_FROZEN', **self.arrival))
            self.cycle_issue = None
            self.aborted_inspection = None
        self.line_wait = ('WAIT_FIELD_PROFILE' if not self._profile_ready() else
            'CYCLIC_PUBLICATION_DISABLED' if not self.gateway.writes_enabled else
            self.handshake.reason or self.handshake.state)

    def _trigger_cyclic(self, now):
        if self._automatic_policy() and self.automatic_identity_block:
            self.line_wait = self.automatic_identity_block
            if now-self.handshake.accepted_at >= self.line_profile['arrival_deadline_s']:
                self._finish_without_frames('ERROR', self.automatic_identity_block, now)
            return
        if now-self.handshake.accepted_at >= self.line_profile['arrival_deadline_s']:
            self._finish_without_frames('ERROR', 'NO_VALID_CURRENT_PRODUCT_AT_PLC_REQUEST', now)
            return
        if not self._profile_ready() or self.error or not self.operating: return
        if self.initial_approval and not self.initial_approval.valid():
            self.handshake.fault('FIRST_PRODUCT_APPROVAL_NOT_VALID')
            return
        if self._full_frame_policy():
            self._trigger_tracked_frame(now)
            return
        context, packet = self.arrival, self.latest_packet
        if not context or not arrival_evidence(packet, self.handshake.accepted_at,
                context['epoch'], context['generation'], self.zone): return
        track = self.coordinator._tracker._track_id
        if track is None or not self.eligible or not packet.get('stable'): return
        expected = context['track'] or context['preexisting_track']
        if expected is not None and expected != track:
            self._finish_without_frames('ERROR', 'CURRENT_PRODUCT_CHANGED', now)
            return
        context['track'] = track
        self.request_wait_seconds = self.line_profile['arrival_deadline_s']
        super()._trigger(now)

    def _trigger_tracked_frame(self, now):
        context, packet = self.arrival, self.latest_packet
        if not context or context['token'] != self.handshake.token:
            self.handshake.fault('REQUEST_TRACK_CONTEXT_MISMATCH')
            return
        snapshot = self.handshake.snapshot
        if (not snapshot or not snapshot['connected'] or not snapshot['fresh']
                or not snapshot['bool_valid'] or not snapshot['run_idle']
                or not 0 <= now-snapshot['generated'] <= .5
                or not all(snapshot['controls'].get(k) for k in
                    ('Inspection_Request', 'EStop_OK', 'Mc_Run', 'Stop_PB'))):
            self.handshake.fault('REQUEST_CONTROL_CONTEXT_INVALID')
            return
        tracker = self.coordinator._tracker
        cycle = self.coordinator.active_cycle
        if context['track'] is not None and (tracker._track_id != context['track']
                or cycle is None or cycle.cycle_id != context['cycle_id']):
            self._finish_without_frames('ERROR', 'CURRENT_PRODUCT_CHANGED', now)
            return
        # No camera existed at the edge: bind its first observed epoch once, never
        # replace an existing epoch or worker generation with a later session.
        if context['epoch'] is None and packet:
            context['epoch'] = packet['camera_epoch']
        if not tracked_frame_evidence(packet, self.handshake.accepted_at,
                context['epoch'], context['generation'], now):
            return
        if packet['sequence'] <= context['sequence_at_request']:
            return
        if (tracker._track_id is None or not self.eligible or cycle is None
                or tracker._track_id in self.inspected_tracks):
            return
        if context['track'] is None:
            context.update(track=tracker._track_id, cycle_id=cycle.cycle_id)
            self._event(dict(event='PLC_REQUEST_FIRST_TRACK_BOUND', **context))
        self.request_wait_seconds = self.line_profile['arrival_deadline_s']
        super()._trigger(now)
        # This exact fresh frame established the request/Track binding, before
        # the next observation can be empty while evidence is being saved.
        self._remember_bound_passage_packet(packet)

    def _poll_legacy_plc(self, now):
        """Existing three-tag ladder: software readiness is not PLC Run permission."""
        previous = self.handshake.token
        self.handshake.poll(now)
        if self.handshake.state == 'RESYNC_REQUIRED':
            self._cancel_pending(self.handshake.reason)
            self.line_wait = self.handshake.reason
            if not self.error:
                self._fault(self.handshake.reason)
            return
        if self.handshake.state == 'WAIT_PRODUCT_CLEAR':
            if self.handshake.early_off:
                self._cancel_pending(self.handshake.reason)
            after = self.handshake.clearance_required_after
            area = self.area_observation or {}
            fresh_clear = bool(self._clear(now) and self.latest_packet
                and self.latest_packet['monotonic_s'] > after
                and area.get('first_clear_monotonic', -1) >= after)
            if not self.handshake.release_cleared_cycle(product_clear=fresh_clear):
                self.line_wait = self.handshake.reason
                return
            self.arrival = None
        if self.handshake.token and self.handshake.token != previous:
            track = self.coordinator._tracker._track_id
            self.arrival = dict(token=self.handshake.token, epoch=self.epoch,
                generation=self.service.generation, track=None, preexisting_track=track)
            self._event(dict(event='LEGACY_UPSTREAM_REQUEST_ACCEPTED',
                camera_epoch=self.epoch, preexisting_track=track,
                plc_cycle_id=None, sensor_or_stop_off_distinguishable=False))
        self.line_wait = (self.handshake.reason or
            ('WAIT_FIELD_PROFILE' if not self._profile_ready() else
             'WAIT_ASSEMBLY_MODEL' if not self.assembly.ready else
             'LEGACY_READ_ONLY_STANDBY' if not getattr(self.gateway, 'writes_enabled', False) else
             'READY_WAIT_EXISTING_PLC_REQUEST' if self.handshake.state == 'ARMED' else
             self.handshake.state))

    def _trigger(self, now):
        if self.handshake.state != 'REQUEST_LATCHED' or self.service.active: return
        if getattr(self.gateway, 'contract_version', None) == 'OPENER_CYCLIC':
            self._trigger_cyclic(now)
            return
        if getattr(self.gateway, 'contract_version', None) == 'LEGACY_THREE_BOOL':
            self._trigger_legacy(now)
            return
        elapsed = now - self.handshake.accepted_at
        expired = elapsed >= self.line_profile['arrival_deadline_s']
        if expired:
            self._finish_without_frames('ERROR', 'NO_INSPECTION_ARRIVAL_OR_STOP_NOT_CONFIRMED', now)
            return
        context = self.arrival
        if not context or context['preexisting_track'] is not None: return
        if self.error or not self.operating: return
        packet = self.latest_packet
        if not arrival_evidence(packet, self.handshake.accepted_at, context['epoch'],
                                context['generation'], self.zone): return
        track = self.coordinator._tracker._track_id
        if track is None or not self.eligible: return
        if context['track'] is None:
            context['track'] = track
            self._event(dict(event='UPSTREAM_ENTRY_TRACK_BOUND', track_id=track,
                             line_cycle_id=self.handshake.cycle_id, frame_id=packet['frame_id']))
        if context['track'] != track:
            self._finish_without_frames('ERROR', 'ARRIVING_PRODUCT_IDENTITY_CHANGED', now)
            return
        if not self.handshake.outputs.get('Jetson_InPosition'):
            if not self.handshake.in_position(): return
        if self.handshake.inputs.get('PLC_ConveyorRun'):
            context['conveyor_off_at'] = None
            return
        if context['conveyor_off_at'] is None:
            context['conveyor_off_at'] = now
            return
        # Output OFF is not physical feedback. Existing observed stability plus
        # a source frame captured after the OFF readback are both required.
        if packet['monotonic_s'] <= context['conveyor_off_at'] or not packet.get('stable'): return
        self.request_wait_seconds = self.line_profile['arrival_deadline_s']
        super()._trigger(now)

    def _trigger_legacy(self, now):
        # The installed ladder has no InPosition/ConveyorRun interface. Do not
        # forge one or claim the belt stopped from a visually stable frame.
        if now-self.handshake.accepted_at >= self.line_profile['arrival_deadline_s']:
            reason = ('FIELD_PROFILE_NOT_VERIFIED' if not self._profile_ready()
                      else self.error or 'LEGACY_NO_FRESH_STABLE_PRODUCT')
            self._finish_without_frames('ERROR', reason, now)
            return
        if not self._profile_ready() or self.error or not self.operating:
            return
        context = self.arrival
        if not context or context['preexisting_track'] is not None:
            return
        packet = self.latest_packet
        if not arrival_evidence(packet, self.handshake.accepted_at, context['epoch'],
                                context['generation'], self.zone):
            return
        track = self.coordinator._tracker._track_id
        if track is None or not self.eligible or not packet.get('stable'):
            return
        if context['track'] is None:
            context['track'] = track
            self._event(dict(event='LEGACY_REQUEST_TRACK_BOUND', track_id=track,
                             frame_id=packet['frame_id'], physical_stop_verified=False))
        if context['track'] != track:
            self._finish_without_frames('ERROR', 'ARRIVING_PRODUCT_IDENTITY_CHANGED', now)
            return
        self.request_wait_seconds = self.line_profile['arrival_deadline_s']
        super()._trigger(now)

    def _begin_inspection(self, binding, now):
        if getattr(self, 'request_start', None):
            return self.request_start.begin(binding, now)
        return super()._begin_inspection(binding, now)

    def _finish_without_frames(self, decision, reason, now):
        if getattr(self, 'request_start', None):
            return self.request_start.no_input(decision, reason, now)
        binding = dict(runtime_session_id=self.session_id, cycle_id=None, track_id=None,
            plc_request_token=self.handshake.token,
            plc_contract=getattr(self.gateway, 'contract_version', 'STANDALONE_V3'),
            line_cycle_id=self.handshake.cycle_id, line_session_id=self.handshake.session_id,
            camera_epoch=self.epoch, worker_generation=self.service.generation)
        request = dict(self.service.allocate_request(), kind='inspect', control_mode='production',
                       source_mode='PRODUCTION_AUTO', runtime_binding=binding, view_assessment={})
        identifier, created = self.service.journal.admit(request, self.service.package.snapshot())
        if not created: raise ValueError('DUPLICATE_LINE_DEADLINE_RESULT')
        self.service.journal.finish(identifier, dict(decision=decision, reason=reason,
            reason_code=reason, disposition='HOLD', observations=[], assets=[],
            production_identity=dict(binding, inspection_id=identifier),
            execution=dict(source='not_executed', control='production', worker_generation=self.service.generation)))
        self.handshake.bind(identifier)
        final = dict(decision=decision, existing_decision='NOT_RUN', assembly_decision='NOT_RUN',
                     policy='NO_INPUT_IS_NEVER_PASS', reason=reason)
        self._commit_and_publish(identifier, final, now)

    def _validate_cyclic_final(self, binding, final, now, row=None):
        if (binding.get('runtime_session_id') != self.session_id or
                binding.get('worker_generation') != self.service.generation or
                binding.get('camera_epoch') != self.epoch):
            raise ValueError('CYCLIC_FINAL_CONTEXT_MISMATCH')
        if binding.get('track_id') is not None:
            cycle = self.coordinator.active_cycle
            if (cycle is None or cycle.cycle_id != binding.get('cycle_id') or
                    self.coordinator._tracker._track_id != binding['track_id']):
                raise ValueError('CYCLIC_FINAL_PRODUCT_CHANGED')
        if self._full_frame_policy() and final['decision'] in ('PASS', 'FAIL'):
            if self._automatic_policy():
                # The completed request owns its originals and decision. A later
                # preview miss cannot turn that stored inspection into a fault.
                # Real identity/stream/control failures remain publication gates.
                health = self.service.health()
                if (health.get('error') or health.get('camera_ready') is not True
                        or health.get('worker_alive') is not True
                        or health.get('camera_epoch') != binding['camera_epoch']):
                    raise ValueError('CYCLIC_FINAL_CAMERA_UNAVAILABLE')
                snapshot = self.gateway.read_snapshot(now)
                token = (f"{snapshot['boot']:016x}:{snapshot['connection']}:{snapshot['request_id']}"
                         if snapshot else None)
                if (not snapshot or not all(snapshot.get(key) is True
                        for key in ('connected', 'fresh', 'bool_valid', 'run_idle'))
                        or not all(snapshot['controls'].get(key) is True
                            for key in ('Mc_Run', 'EStop_OK', 'Stop_PB', 'Inspection_Request'))
                        or snapshot['phase'] != 'REQUEST_RECEIVED'
                        or token != binding.get('plc_request_token') or token != self.handshake.token
                        or self.handshake.cancelled or not self.operating or self.error):
                    raise ValueError('CYCLIC_FINAL_CONTROL_CONTEXT_INVALID')
                if self.cycle_issue:
                    raise ValueError('CYCLIC_FINAL_TRACK_EVIDENCE_INVALID')
                if row is None:
                    row = self.service.journal.detail(final['inspection_id'])
                validate_completed_evidence(row, binding, final['inspection_id'],
                    self.handshake.accepted_at, now, self.service.package.manifest_hash)
                return
            from src.tracking.contracts import TrackState
            tracker = self.coordinator._tracker
            if (tracker._state in (TrackState.LOST, TrackState.WAIT_AREA_CLEAR)
                    or self.cycle_issue or not tracked_frame_evidence(self.latest_packet,
                        self.handshake.accepted_at, self.epoch, self.service.generation, now)):
                raise ValueError('CYCLIC_FINAL_TRACK_EVIDENCE_INVALID')

    def _commit_and_publish(self, identifier, final, now, durable_row=None):
        if getattr(self, 'final_pending', None):
            if self.final_pending['inspection_id'] != identifier:
                raise ValueError('FINAL_COMMIT_OWNER_CONFLICT')
            return
        row = durable_row if durable_row is not None else self.service.journal.detail(identifier)
        binding = ((row or {}).get('request') or {}).get('runtime_binding', {})
        cancelled_error = bool(row and row['state'] == 'CANCELLED'
                               and row['decision'] == final['decision'] == 'ERROR')
        if (not row or (row['state'] != 'COMPLETE' and not cancelled_error)
                or not row['result'].get('storage_success')
                or binding.get('plc_request_token') != self.handshake.token):
            raise ValueError('SAME_REQUEST_DURABLE_COMPONENT_REQUIRED')
        final = dict(final, inspection_id=identifier, line_cycle_id=self.handshake.cycle_id,
            line_session_id=self.handshake.session_id, request_token=self.handshake.token,
            runtime_session_id=self.session_id, completed_monotonic=now,
            track_id=binding.get('track_id'), completed_at=datetime.now(timezone.utc).isoformat(),
            inspection_elapsed_ms=max(0, now-self.handshake.accepted_at)*1000,
            source='INTEGRATED_ACTUAL_INSPECTION', synthetic=False)
        if self._supervised_policy():
            final.update(supervised_approval_id=self.initial_approval.approval_id,
                admission_policy=REPEAT_POLICY,
                track_uid=(str(binding['runtime_session_id'])+':'+str(binding['track_id'])
                           if binding.get('track_id') is not None else None))
        if self._automatic_policy():
            final.update(cycle_policy=AUTO_POLICY, software_permission_required=False,
                         cycle_admission_evidence=self._automatic_cycle_evidence,
                         product_separation=self.request_product_separation,
                         sensor_cycle_source='QUALIFIED_PLC_REQUEST_LATCH_NOT_RAW_SENSOR')
        if getattr(self.gateway, 'contract_version', None) == 'OPENER_CYCLIC':
            self._validate_cyclic_final(binding, final, now, row)
            if self._automatic_policy() and final['decision'] in ('PASS', 'FAIL'):
                final['publication_basis'] = 'DURABLE_BOUND_THREE_FRAME_INSPECTION_V1'
            from src.control.opener_cyclic import PLC_RESULT_POLICY
            final.update(plc_result_policy=PLC_RESULT_POLICY,
                plc_decision='PASS' if final['decision']=='PASS' else 'FAIL',
                plc_result_value=0 if final['decision']=='PASS' else 1,
                plc_done_requested=True)
            final.update(plc_contract='OPENER_CYCLIC', plc_consumption_confirmed=False,
                         ack_scope='CYCLIC_SEND_AND_REQUEST_RESET_ONLY')
            execution = row['result'].get('execution', {}).get('source', 'not_executed')
            final.update(inference_execution_source=execution, synthetic=execution=='mock',
                source='INTEGRATED_FIXTURE_INSPECTION' if execution=='mock' else
                       'INTEGRATED_ACTUAL_INSPECTION' if execution=='live' else 'NO_ACTUAL_INSPECTION')
        if getattr(self.gateway, 'contract_version', None) == 'LEGACY_THREE_BOOL':
            final.update(plc_contract='LEGACY_THREE_BOOL',
                         ack_scope='WRITE_READBACK_ONLY', plc_consumption_confirmed=False)
        if getattr(self.gateway, 'contract_version', None) == 'OPENER_CYCLIC':
            self.final_pending = dict(inspection_id=identifier, binding=dict(binding),
                request_token=self.handshake.token, generation=self.service.generation,
                camera_epoch=self.epoch)
            self.service.storage.submit_final(self.final_pending, final)
            return
        self.service.journal.commit_integrated(final)
        self._publish_committed(identifier, final, binding)

    def _poll_final_commit(self, now):
        pending = getattr(self, 'final_pending', None)
        if not pending:
            return
        try:
            saved = self.service.storage.final_completed.get_nowait()
        except queue.Empty:
            return
        self.final_pending = None
        if saved['context'] is not pending or saved['error']:
            raise ValueError('FINAL_STORAGE_FAILED:'+str(saved['error']))
        identifier = pending['inspection_id']
        if (self.handshake.cancelled or self.handshake.state != 'INSPECTING'
                or pending['request_token'] != self.handshake.token
                or identifier in self.published_ids or getattr(self, 'error', None)
                or self.service.health().get('error')):
            self._cancel_pending('FINAL_COMMIT_CONTEXT_ENDED')
            return
        self._validate_cyclic_final(pending['binding'], saved['final'], now)
        self._publish_committed(identifier, saved['final'], pending['binding'])

    def _publish_committed(self, identifier, final, binding):
        self.published_ids.add(identifier)
        self.handshake.publish(identifier, final['decision'], True, time.monotonic())
        entry = dict(final, vision_decision=final['decision'],
            publication_status=self.handshake.publication,
            request_to_publication_ms=(time.monotonic()-self.handshake.accepted_at)*1000)
        if self._automatic_policy():
            packet = self.latest_packet or {}
            entry['publication_preview_diagnostic'] = dict(frame_id=packet.get('frame_id'),
                provider_status=packet.get('provider', {}).get('status'),
                issue=self.issue if (self.issue or {}).get('scope') == 'COMPLETED_INSPECTION_PREVIEW' else None,
                affects_completed_decision=False)
        self.history.appendleft(entry)
        self.assembly_submitted.pop(identifier, None)
        if len(self.published_ids) > 512:
            self.published_ids = {item['inspection_id'] for item in self.history} | {identifier}
        self._completion_event(dict(event='INTEGRATED_INSPECTION_COMPLETED', **entry))
        if self._automatic_policy():
            self._automatic_previous = dict(inspection_id=identifier, request_token=final['request_token'],
                start_counters=(self._automatic_cycle_evidence or {}).get('start_counters'))
        if self._automatic_policy() and binding.get('track_id') is not None:
            # Retain the last actual product identity through ambiguous requests
            # whose ERROR has no Track. A timeout is never an exit observation.
            q = self.line_profile.get('automatic_operation_qualification', {})
            identity = dict(inspection_id=identifier,
                tracking_session=self.session_id, cycle_id=binding['cycle_id'],
                track_id=binding['track_id'], request_token=self.handshake.token)
            owner = (self.handshake.token, self.session_id, binding['track_id'])
            packets = [p for key, p in self._passage_history if key == owner]
            track_valid = self.coordinator._tracker._state not in (
                TrackState.LOST, TrackState.WAIT_AREA_CLEAR)
            if (packets and packets[-1] is self.latest_packet
                    and not self.cycle_issue and track_valid):
                self.product_passage = ProductPassage.from_history(identity,
                    packets, q.get('exit_edge'), tracker_config=self.tracker_config)
            else:
                self.product_passage = ProductPassage(identity, self.latest_packet,
                    q.get('exit_edge'), tracker_config=self.tracker_config)
                self.product_passage._fail('PRODUCT_PASSAGE_BOUND_HISTORY_UNAVAILABLE')
            self._passage_history.clear()
            self.product_separation = None

    def _poll_result(self, now):
        if getattr(self, 'final_pending', None):
            return
        identifier = self.bridge.inspection_id
        if not identifier or identifier in self.published_ids: return
        if self.handshake.cancelled or self.handshake.state != 'INSPECTING':
            self._cancel_pending('LINE_CONTEXT_ENDED')
            return
        if getattr(self.service, 'storage_pending', None) is not None:
            return  # No SQL read can wait for fsync or expose a pre-commit result.
        issue = getattr(self, 'cycle_issue', None)
        row = self.service.journal.detail(identifier)
        if row and row.get('state') == 'CANCELLED':
            self._fault('CANCELLED_REQUEST_IS_NOT_A_VALID_CLASSIFICATION')
            self._cancel_pending(row['result']['reason'])
            return
        if issue and issue['request_token'] == self.handshake.token:
            if not row or row['state'] not in ('COMPLETE', 'CANCELLED'):
                return  # Existing worker cancellation/timeout owns the raw record.
            self._commit_and_publish(identifier, dict(decision='ERROR',
                existing_decision=row['decision'], assembly_decision='NOT_RUN',
                policy='INVALID_CURRENT_PRODUCT_CONTEXT', reason=issue['reason']), now)
            return
        updated = self.bridge.poll()
        if updated: self.snapshot = updated
        if self.bridge.error:
            self._fault('DURABLE_BOUNDARY:'+self.bridge.error)
            return
        if self.bridge.phase != 'INSPECTION_DURABLE': return
        row = self.service.journal.detail(identifier)
        try:
            if identifier not in self.assembly_submitted:
                self.assembly_submitted[identifier] = now
                self.assembly.submit(row)
            result = self.assembly.result(identifier)
        except Exception as error:
            result = dict(state='ERROR', reason='ASSEMBLY_EXECUTION:'+type(error).__name__+':'+str(error))
        if result is None and now-self.assembly_submitted[identifier] < self.line_profile['assembly_deadline_s']:
            self.phase = 'ASSEMBLY_INSPECTING'
            return
        if result is None:
            result = dict(state='ERROR', reason='ASSEMBLY_DEADLINE')
        final = combine_decisions(row['decision'], result)
        if not final['publication_allowed']:
            self._fault('ASSEMBLY_SYSTEM_FAILURE:' + str(final['assembly_reason']))
            self._cancel_pending('ASSEMBLY_SYSTEM_FAILURE')
            return
        final['assembly_evidence'] = str(self.assembly.evidence_path(identifier))
        if self.error:
            final.update(decision='ERROR', reason=self.error)
        self._commit_and_publish(identifier, final, now)

    def _acquisition(self, now):
        status = self.service.health()
        if self.camera_recovery and self.camera_recovery.is_alive():
            return  # Replacement owns the old epoch; it is not a running frame stream.
        if status['ready'] and not self.operating and not self.error:
            self.operating = True  # Software frame acquisition only, never PLC Run.
            self.observation_started_at = now
            self.worker_generation = self.service.generation
            self.service.production_tracking.set()
        if status['state'] == 'RECOVERY' and not status['camera_ready'] and not self.service.active:
            self.line_wait = 'WAIT_CAMERA'
            if now >= self.camera_retry_at and (not self.camera_recovery or not self.camera_recovery.is_alive()):
                self.camera_retry_at = now + 30
                self.camera_recovery = threading.Thread(target=self._recover_camera, daemon=True,
                                                       name='camera-recovery')
                self.camera_recovery.start()

    def _recover_camera(self):
        # Activation can briefly hold the service lock while replacing its child.
        # V3 requires a stopped PLC session. Legacy can only establish an idle
        # request context; it has no physical-stop input or motor command.
        try:
            if getattr(self.gateway, 'contract_version', None) == 'OPENER_CYCLIC':
                self._recover_cyclic_camera()
                return
            legacy = getattr(self.gateway, 'contract_version', None) == 'LEGACY_THREE_BOOL'
            if legacy and (self.handshake.token or self.handshake.state not in ('SYNC_LOW', 'ARMED')):
                return
            if not self.handshake.inputs.get('PLC_RunPermit') and not self.service.active:
                self.service.activate(self.service.package.root)
        except Exception:
            self.logger.exception('Camera recovery waits for next bounded attempt')

    def _camera_recovery_baseline(self):
        """No absent V3 RunPermit assumption on the four-slot cyclic contract."""
        now = time.monotonic()
        s = self.gateway.read_snapshot(now)
        if (not s or not all(s.get(k) is True for k in ('connected','fresh','run_idle','bool_valid'))
                or not 0 <= now-s['generated'] <= .5 or not 0 <= now-s['received'] <= .2
                or s.get('phase') not in ('DISARMED','SYNC_LOW') or s.get('raw100') != '00000000'
                or s.get('controls') != dict(Mc_Run=False,Inspection_Request=False,EStop_OK=True,Stop_PB=True)
                or self.service.active or self.service.storage_pending or self.final_pending
                or self.service.switching or self.assembly.status().get('outstanding') != 0):
            return None
        return (s['boot'], s['connection'])

    def _recover_cyclic_camera(self):
        with self.lock, self.service.lock:
            baseline = self._camera_recovery_baseline()
            if baseline is None or self.error not in (None,'CAMERA_OR_OBSERVATION_STREAM_UNAVAILABLE'):
                return
            previous_generation = self.worker_generation
            self.operating = False
            self.observation_started_at = None
            self.handshake.fault('CAMERA_RECOVERY', 'BLOCKED')
            self._cancel_pending('CAMERA_RECOVERY')
            self._event(dict(event='CAMERA_RECOVERY_STARTED', previous_generation=previous_generation,
                connection=baseline, reason=self.service.health().get('error')))
        # Activation waits for model + camera readiness. Do not hold Runtime's
        # lock during that wait: STOP/connection/cancellation must still update.
        result = self.service.activate(self.service.package.root)
        with self.lock, self.service.lock:
            if (not result.get('activated') or self._camera_recovery_baseline() != baseline
                    or not self.service.health()['ready']
                    or self.error not in (None,'CAMERA_OR_OBSERVATION_STREAM_UNAVAILABLE')):
                return
            self._restore_previous_product_identity()  # Restart does not prove product exit.
            # Camera recovery must not depend on closing an interrupted Journal:
            # that recovery itself requires a live, idle Worker. Its unfinished
            # row remains untouched and the existing Journal admission guard
            # still blocks new requests until durable ABORT recovery succeeds.
            self.product_passage = self.product_separation = None
            self._passage_history.clear()
            self._reset_unbound_observation(time.monotonic())
            self.bridge = InspectionBridge(self.service, self.coordinator)
            self.latest_packet = None
            self.epoch = None
            self.last_sequence, self.last_time = -1, 0
            self.worker_generation = self.service.generation
            self.handshake.retire_automatic()  # Retains seen_token; never replays an old request.
            self.error = None
            self.phase, self.line_wait = 'IDLE', 'WAIT_FRESH_CAMERA_FRAME'
            self._event(dict(event='CAMERA_RECOVERY_VERIFIED', previous_generation=previous_generation,
                worker_generation=self.worker_generation, connection=baseline, product_exit_claimed=False))

    def _storage_wait_health(self, now):
        """Only known in-flight storage may defer SQL, never control health.

        C independently enforces current STOP/E-STOP, Request, connection and
        deadlines. No admission, result or lease extension occurs here.
        """
        from apps.edge_service.result_storage import raw_storage_within_deadline
        if getattr(self.gateway, 'contract_version', None) != 'OPENER_CYCLIC':
            return
        context = self.service.storage_pending or getattr(self, 'final_pending', None)
        if context is None:
            # A UI reader can briefly own Journal between storage phases.
            # That is not a not-ready observation. Do not renew health from
            # unproven context either: the normal cycle must renew the existing
            # lease on its next turn, or the unchanged lease expires in C.
            return
        health = self.service.health()
        snapshot = self.gateway.read_snapshot(now)
        token = (f"{snapshot['boot']:016x}:{snapshot['connection']}:{snapshot['request_id']}"
                 if snapshot else None)
        bound_id = self.handshake.inspection_id if getattr(self, 'final_pending', None) else self.bridge.inspection_id
        ready = bool(context and context['inspection_id'] == bound_id
            and token == self.handshake.token and snapshot['phase'] == 'REQUEST_RECEIVED'
            and snapshot['connected'] and snapshot['fresh'] and snapshot['run_idle'] and snapshot['bool_valid']
            and snapshot['controls']['Mc_Run'] and snapshot['controls']['EStop_OK']
            and snapshot['controls']['Stop_PB'] and snapshot['controls']['Inspection_Request']
            and self.operating and not self.error and self._profile_ready() and self.assembly.ready
            and not health['error'] and health['camera_ready'] and health['state'] in ('BUSY', 'IDLE')
            and context['generation'] == self.service.generation
            and self.service.storage.thread.is_alive()
            and context['camera_epoch'] == health['camera_epoch']
            # Raw storage retains the Worker deadline. Final persistence uses
            # the existing C request timeout/REQUEST_RECEIVED phase, so an
            # Assembly timeout may still produce its genuine ERROR result.
            and (getattr(self, 'final_pending', None) is not None
                 or raw_storage_within_deadline(context))
            and not self.handshake.cancelled
            and (not self.initial_approval or (not self.initial_approval.failed
                 and self.initial_approval.state != 'REVOKED')))
        self.gateway.ready_reason = health['error'] or ('DURABLE_STORAGE_IN_PROGRESS' if ready
                                                       else 'STORAGE_WAIT_CONTROL_CONTEXT_INVALID')
        self.gateway.health_update(ready, False, time.monotonic())

    def _run(self):
        self.configured.wait()
        while not self.stop.wait(.02):
            waited = time.monotonic()
            with self.lock, self.service.lock:
                self.service.health_diagnostics.record('SERVICE_LOCK_RUNTIME', retain=time.monotonic()-waited>.02, wait_ms=(time.monotonic()-waited)*1000)
                if self.closing: continue
                maintenance_capture = getattr(self, 'maintenance_capture', None)
                if maintenance_capture:
                    maintenance_capture.poll(time.monotonic())
                run_capture = getattr(self, 'run_capture', None)
                if run_capture:
                    run_capture.poll(time.monotonic())
                if self._poll_completion_audit(time.monotonic()):
                    continue
                if self.request_start:
                    try:
                        if self.request_start.tick(time.monotonic()):
                            continue
                    except Exception as error:
                        # Revoke output authority first. Persist the failure via
                        # the storage owner, not a control-thread transaction.
                        self.request_start.capture_events = True
                        try:
                            self._fault('REQUEST_START:'+type(error).__name__+':'+str(error))
                            self.request_start._flush()
                        finally:
                            self.request_start.capture_events = False
                        continue
                # Commit/fsync owns Journal, not the cyclic health schedule.
                if not self.service.journal.lock.acquire(blocking=False):
                    self._storage_wait_health(time.monotonic())
                    continue
                try:
                    now = time.monotonic()
                    self._acquisition(now)
                    self._poll_plc(now)
                    if getattr(self, 'audit_pending', None):
                        continue
                    while True:
                        try: packet = self.service.products.get_nowait()
                        except queue.Empty: break
                        self._packet(packet)
                    now = time.monotonic()
                    self._poll_final_commit(now)
                    if getattr(self, 'audit_pending', None):
                        continue
                    if self.operating and self.observation_started_at is not None:
                        since = self.latest_packet['processed_monotonic'] if self.latest_packet else self.observation_started_at
                        if now-since > self.observation_stale_seconds:
                            self._fault('CAMERA_OR_OBSERVATION_STREAM_UNAVAILABLE')
                    self._poll_result(now)
                    self._trigger(now)
                except Exception as error:
                    self.logger.exception('Standalone cycle boundary failed')
                    try: self._fault(type(error).__name__+':'+str(error))
                    except Exception:
                        self.error, self.operating = 'JOURNAL_UNAVAILABLE', False
                        self.gateway.close()
                finally:
                    self.service.journal.lock.release()

    def status(self):
        result = super().status()
        with self.service.journal.lock:
            totals = self.service.journal.db.execute("SELECT json_extract(value,'$.decision'),count(*) "
                "FROM service_state WHERE key LIKE 'integrated_decision:%' GROUP BY 1").fetchall()
        result.update(line_mode=self.line_profile['mode'], line_state=self.line_wait,
            runtime_issue=self.issue, runtime_loop_alive=self.thread.is_alive() and not self.closing,
            final_result_policy=FINAL_POLICY,
            line_profile=self.line_profile, arrival_context=self.arrival,
            actual_motor_feedback='NOT_INSTALLED_COMMAND_AND_VISUAL_STABILITY_ONLY',
            operator_control='PHYSICAL_BUTTONS', laptop_required=False,
            field_acceptance='NOT_RUN', assembly_component=self.assembly.status())
        result['plc_cycle'] = dict(self.plc_cycle) if self.plc_cycle else None
        result['consumed_frame_trace'] = self.consumed_frames.snapshot(limit=4)
        if self.plc_cycle:
            result['plc_cycle'].update(
                readiness=self._automatic_readiness(),
                product_identity_reason=self.automatic_identity_block,
                prior_tracking_diagnostic=self.previous_tracking_diagnostic,
                restored_tracking_diagnostic=self.prior_product_identity_block,
                cycle_identity_policy='PLC_CYCLE_FRESH_OBSERVATION_V1',
                request_identity_block=self.automatic_identity_block if self.handshake.state=='REQUEST_LATCHED' else None,
                product_passage=self.product_passage.status() if self.product_passage else None,
                product_separation=self.product_separation,
                area_clearance_required=False, raw_photo_sensor_available=False,
                blocked_request_deadline_s=self.line_profile['arrival_deadline_s'],
                recovery='SYSTEM_FAULT_REQUIRES_RECOVERY; PAST_TRACKING_REASSESSED_ON_NEW_PLC_CYCLE')
        if self._full_frame_policy():
            result.update(inspection_start_policy=FULL_FRAME,
                request_start_qualified=(False if self._initial_policy() or self._supervised_policy() else self._profile_ready()),
                software_start_policy_ready=self._profile_ready(),
                initial_approval=(self.initial_approval.status() if self.initial_approval else None),
                next_product_policy=self.line_profile['cycle_admission'],
                accepted_request_count=self.cyclic_admissions,
                repeat_clearance_evidence=self.cyclic_rearm_evidence,
                initial_opener_arm='EXPLICIT_ONE_SHOT_APPROVAL_AND_NEW_PHYSICAL_START',
                field_acceptance='NOT_RUN')
            if self._automatic_policy():
                result.update(initial_opener_arm='STOPPED_BASELINE_THEN_NEW_PHYSICAL_START',
                    request_start_qualified=self.line_profile.get('request_start_qualification',{}).get('verified') is True,
                    per_product_manual_controls=False)
        result['aborted_inspection'] = self._aborted_status()
        result['final_commit_pending'] = self.final_pending is not None or getattr(self, 'audit_pending', None) is not None
        result['completion_audit_pending'] = getattr(self, 'audit_pending', None) is not None
        result['completion_audit_error'] = getattr(self, 'audit_error', None)
        request_start = getattr(self, 'request_start', None)
        result['request_start_pending'] = bool(request_start and (
            request_start.pending or request_start.events or not request_start.deferred_events.empty()))
        result['ipc_health'] = self.gateway.diagnostics.snapshot() if hasattr(self.gateway, 'diagnostics') else None
        if getattr(self, 'run_capture', None):
            result['run_capture'] = self.run_capture.status()
        result['integrated_counts'] = dict.fromkeys(('PASS','FAIL','REVIEW','ERROR'), 0)
        result['integrated_counts'].update(dict(totals))
        if getattr(self.gateway, 'contract_version', None) == 'LEGACY_THREE_BOOL':
            result.update(pusher_control='EXISTING_PLC_UNCHANGED_NO_JETSON_COMMANDS',
                          actual_motor_feedback='NOT_AVAILABLE_IN_EXISTING_CONTRACT',
                          physical_stop_observable=False, plc_consumption_confirmed=False)
        return result

    def _aborted_status(self):
        aborted = getattr(self, 'aborted_inspection', None)
        if not aborted:
            return None
        identifier = aborted['inspection_id']
        from src.runtime.aborted_recovery import valid_abort
        with self.service.journal.lock:
            if valid_abort(self.service.journal.db, identifier):
                # Maintenance appended a verified settlement. Keep the original
                # result/history, but do not display it as still awaiting recovery.
                self.aborted_inspection = None
                return None
        row = self.service.journal.detail(identifier)
        with self.service.journal.lock:
            final = self.service.journal.db.execute('SELECT value FROM service_state WHERE key=?',
                ('integrated_decision:'+identifier,)).fetchone()
        return dict(aborted, raw_decision=row.get('decision') if row else None,
            raw_journal='COMPLETE' if row and row['state'] == 'COMPLETE' else 'NOT_COMPLETE',
            assembly='SUBMITTED' if identifier in self.assembly_submitted else 'NOT_RUN',
            integrated='COMPLETE' if final else 'INCOMPLETE',
            state='INSPECTION_ABORTED_STOP_AND_RECOVERY_REQUIRED')

    def close(self):
        with self.lock:
            self.operating = False
            self.handshake.shutdown()
        super().close()
        if self.initial_approval:
            self.initial_approval.close()
