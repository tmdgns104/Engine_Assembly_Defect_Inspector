"""Machine admission for a qualified PLC line; no browser or human grant files.

Transport admission follows durable settlement, not global Area Clearance.
The runtime separately checks product identity and journals bounded ERRORs
when a new request cannot safely be associated with a new product.
Each IPC admission is attempted once and bound to current device generations.
Recovery needs an observed stopped PLC followed by a NEW physical START. This
module never commands a motor and does not claim electrical or physical safety.
"""
import uuid

from src.runtime.initial_approval import JournalAdmissionGuard

POLICY = 'PLC_AUTOMATIC_REPEAT'


class AutomaticAdmission:
    def __init__(self, runtime_session):
        self.session = runtime_session
        self.binding = None
        self.admission_id = None
        self.deadline = 0
        self.state = 'WAIT_STOPPED_BASELINE'
        self.reason = 'WAIT_QUALIFIED_PLC_AND_CAMERA'
        self.failed = False
        self.clearance = None
        self.last_complete = None
        self.blocked_request_since = None
        self.journal_gate = JournalAdmissionGuard()

    def _wait(self, reason):
        self.reason = reason
        return False

    def poll(self, s, ready, epoch, generation, now, gateway, journal, *, settlement,
             clearance, prepare):
        if self.failed:
            return False
        if not (ready and epoch and generation):
            return self._wait('WAIT_AUTO_QUALIFICATION_OR_HEALTH')
        if not (s and s['connected'] and s['fresh'] and s['run_idle'] and s['bool_valid']
                and 0 <= now-s['generated'] <= .5 and 0 <= now-s['received'] <= .2):
            self.binding = None
            self.admission_id = None
            gateway.cancel()
            return self._wait('WAIT_FRESH_PLC_CONNECTION')
        binding = (self.session, s['boot'], s['connection'], epoch, generation)
        if binding != self.binding:
            if self.binding is not None:
                gateway.cancel()
            self.binding = binding
            self.admission_id = None
            self.state = 'WAIT_STOPPED_BASELINE'
            self.clearance = None
        if self.state == 'WAIT_ADAPTER_ADMISSION':
            if s.get('approval_id') == self.admission_id and s['phase'] != 'DISARMED':
                self.state = 'WAIT_PHYSICAL_START' if s['phase'] == 'SYNC_LOW' else 'ACTIVE'
            elif now > self.deadline:
                self.failed = True
                gateway.cancel()
                return self._wait('AUTOMATIC_ADMISSION_NOT_ACKNOWLEDGED')
            else:
                return False
        if s['phase'] == 'DISARMED' and self.admission_id:
            self.admission_id = None
            self.clearance = None
            self.state = 'WAIT_STOPPED_BASELINE'
        # A HIGH before the adapter has accepted a request has no safe result
        # token. Bound this wait even after admission ACK (notably SYNC_LOW).
        # Accepted cycles have their own inspection/result deadlines.
        controls = s['controls']
        unaccepted = s['phase'] in ('DISARMED', 'SYNC_LOW', 'IDLE', 'READY_NEXT')
        if unaccepted and controls['Inspection_Request']:
            if self.blocked_request_since is None:
                self.blocked_request_since = now
            if now-self.blocked_request_since >= 2:
                self.failed = True
                gateway.cancel()
                return self._wait('UNACCEPTED_REQUEST_RESIDUE_TIMEOUT_PHYSICAL_STOP_REQUIRED')
        else:
            self.blocked_request_since = None
        if self.admission_id and s['phase'] != 'READY_NEXT':
            self.reason = ('WAIT_NEW_PHYSICAL_START' if s['phase'] == 'SYNC_LOW'
                           else 'WAIT_PLC_REQUEST' if s['phase'] == 'IDLE' else 'CURRENT_CYCLE_ACTIVE')
            return False
        if not controls['EStop_OK'] or not controls['Stop_PB']:
            return self._wait('PLC_CONTROL_INHIBIT')
        if controls['Inspection_Request'] or s['raw100'] != '00000000':
            return self._wait('WAIT_REQUEST_AND_RESULT_DONE_RESET')
        self.blocked_request_since = None
        if not (s['request_id'] == s['result_count'] == s['done_count'] == s['completed_count']):
            return self._wait('PREVIOUS_CYCLIC_TRANSACTION_INCOMPLETE')
        if not settlement['clean']:
            return self._wait(settlement.get('reason') or 'PREVIOUS_RESULT_NOT_SETTLED')
        previous = settlement.get('previous')
        if s['request_id'] and not previous:
            return self._wait('PREVIOUS_RESULT_NOT_SETTLED')
        if previous:
            expected = f"{s['boot']:016x}:{s['connection']}:{s['request_id']}"
            if previous.get('request_token') != expected or previous.get('durable') is not True:
                return self._wait('PREVIOUS_RESULT_IDENTITY_MISMATCH')
        continuing = bool(self.admission_id and s['phase'] == 'READY_NEXT')
        if not continuing and (controls['Mc_Run'] or s['phase'] not in ('DISARMED', 'SYNC_LOW', 'READY_NEXT')):
            return self._wait('WAIT_STOPPED_BASELINE_AND_NEW_START')
        try:
            with journal.lock:
                if self.journal_gate.count(journal.db):
                    return self._wait('JOURNAL_UNFINISHED_INSPECTION')
                journal.capacity()
            identifier = uuid.uuid4().hex
            evidence = dict(admission_id=identifier, policy=POLICY, binding=binding,
                previous=previous, clearance=clearance, human_approval=False,
                fresh_start_required=not continuing, transaction_admission_only=True)
            # The event must be durable before the sole IPC attempt.
            prepare(evidence, now)
            gateway.automatic_arm(s, identifier)
        except Exception as error:
            self.failed = True
            gateway.cancel()
            return self._wait('AUTOMATIC_JOURNAL_OR_ADMISSION_ERROR:'+type(error).__name__)
        self.last_complete = previous
        self.admission_id = identifier
        self.clearance = clearance
        self.deadline = now+2
        self.state = 'WAIT_ADAPTER_ADMISSION'
        self.reason = 'WAIT_ADAPTER_ADMISSION'
        return False  # Never grant the legacy global CLEAR permission.

    def status(self):
        return dict(policy=POLICY, state=self.state, reason=self.reason,
            admission_id=self.admission_id, browser_required=False,
            per_product_manual_approval=False, failed=self.failed,
            last_complete=self.last_complete, clearance=self.clearance)

    def accepts(self, snapshot):
        return bool(not self.failed and self.admission_id and self.binding
            and snapshot and (snapshot['boot'], snapshot['connection']) == self.binding[1:3]
            and snapshot.get('approval_id') == self.admission_id
            and snapshot['phase'] == 'REQUEST_RECEIVED')
