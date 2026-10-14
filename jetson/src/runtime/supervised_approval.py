"""One fresh operator reservation per product; human clearance is not AI CLEAR.

The Runtime thread is the sole ledger/IPC owner. HTTP only queues a short-lived
request for a current challenge. Reservations survive failures as spent records;
no grant is restored on process restart. FIRST_PRODUCT_ONLY remains unchanged.
"""
import json
import sqlite3
import uuid

from src.runtime.initial_approval import InitialApproval, atomic_json

POLICY = 'SUPERVISED_REPEAT_TEST'
CONFIRMATIONS = ('PHYSICAL_STOP', 'SUPERVISED', 'PREVIOUS_PRODUCT_CLEARED',
                 'ONE_NEW_PRODUCT_HANDS_OFF', 'REAL_AI_NG_CAN_RESTART')


def settled_snapshot(s, now):
    """Software evidence only. The operator must independently confirm motion."""
    if not s:
        return False
    controls = s['controls']
    return bool(s['connected'] and s['fresh'] and s['run_idle'] and s['bool_valid']
        and 0 <= now-s['generated'] <= .5 and 0 <= now-s['received'] <= .2
        and not controls['Inspection_Request'] and not controls['Mc_Run']
        and controls['EStop_OK'] and controls['Stop_PB']
        and s['raw100'] == '00000000'
        and s['phase'] in ('DISARMED', 'SYNC_LOW', 'READY_NEXT')
        and s['request_id'] == s['result_count'] == s['done_count'] == s['completed_count'])


class SupervisedApproval(InitialApproval):
    def __init__(self, root, runtime_session):
        super().__init__(root, runtime_session)
        self.challenge = None
        self.challenge_key = None
        self.last_complete = None
        self.prepared_count = 0
        # Append-only evidence; the existing approvals table remains the spent-ID ledger.
        self.db.execute('CREATE TABLE IF NOT EXISTS supervised_evidence '
                        '(approval_id TEXT PRIMARY KEY REFERENCES approvals(id), value TEXT NOT NULL)')
        self.db.commit()

    def submit(self, challenge_id, confirmations, now):
        """Queue only; caller holds the Runtime lock and has authenticated operator."""
        c = self.challenge
        path = self.root/'request.json'
        if (not c or not c['eligible'] or c['id'] != challenge_id
                or not 0 <= now-c['generated'] <= 2 or path.exists()
                or confirmations != list(CONFIRMATIONS)):
            raise ValueError('CURRENT_CHALLENGE_AND_ALL_PHYSICAL_CONFIRMATIONS_REQUIRED')
        identifier = uuid.uuid4().hex
        atomic_json(path, dict(approval_id=identifier, policy=POLICY, binding=c['binding'],
            challenge_id=c['id'], created=now, confirmations=confirmations))
        return identifier

    def _observe_grant(self, s, binding, ready, settlement, now, gateway):
        if not self.approval_id or self.state == 'REVOKED':
            return
        if (not ready or binding != self.binding or not s or not s['connected']
                or not s['fresh'] or not s['run_idle'] or not s['bool_valid']):
            self.context_loss = dict(expected=self.binding, actual=binding, ready=bool(ready))
            self.revoke('APPROVAL_CONTEXT_OR_READINESS_LOST')
            gateway.cancel()
            return
        previous = settlement.get('previous')
        if (self.token and previous and previous.get('request_token') == self.token
                and previous.get('durable') is True
                and s.get('approval_id') == self.approval_id
                and s['phase'] == 'READY_NEXT' and not s['controls']['Inspection_Request']
                and s['raw100'] == '00000000'
                and s['request_id'] == s['completed_count'] == s['done_count'] == s['result_count']):
            self.last_complete = dict(previous, approval_id=self.approval_id)
            if self.state != 'COMPLETED_WAIT_OPERATOR':
                self._record('COMPLETED_WAIT_OPERATOR', 'WAIT_PHYSICAL_STOP_AND_PRODUCT_CLEAR', self.token)
        elif self.state in ('RESERVED', 'ACCEPTED'):
            acknowledged = s.get('approval_id') == self.approval_id
            reason = ('ADAPTER_DISARMED' if acknowledged and s['phase'] == 'DISARMED' else
                      'GRANT_NOT_ACKNOWLEDGED' if not acknowledged and now > self.arm_deadline else
                      'APPROVAL_EXPIRED' if not self.token and now > self.expires else None)
            if reason:
                self.revoke(reason)
                gateway.cancel()

    def poll(self, snapshot, ready, epoch, generation, now, gateway, journal, *, settlement, prepare):
        try:
            binding = (dict(runtime=self.session, boot=snapshot['boot'], connection=snapshot['connection'],
                            epoch=epoch, generation=generation) if snapshot else None)
            self._observe_grant(snapshot, binding, ready, settlement, now, gateway)
            with journal.lock:
                unfinished = self.journal_gate.count(journal.db, fresh=(self.root/'request.json').exists())
                journal.capacity()
            # A revoked in-flight trial cannot be cleared by an operator checkbox.
            previous_complete = not self.token or bool(self.last_complete
                and self.last_complete['request_token'] == self.token)
            own_context = bool(self.approval_id or not snapshot or snapshot['request_id'] == 0)
            eligible = bool(not self.failed and ready and epoch is not None and generation is not None
                and self.state not in ('RESERVED', 'ACCEPTED') and not unfinished
                and previous_complete and own_context and settlement.get('clean') is True
                and settled_snapshot(snapshot, now))
            reason = ('READY_FOR_OPERATOR_CONFIRMATIONS' if eligible else
                      'PREVIOUS_REQUEST_NOT_COMPLETED' if not previous_complete else
                      settlement.get('reason') or 'WAIT_READY_STOPPED_CLEAN_STATE')
            key = json.dumps([binding, eligible, self.approval_id, self.token,
                (snapshot or {}).get('request_id'), (snapshot or {}).get('completed_count'), reason], sort_keys=True)
            if key != self.challenge_key:
                self.challenge_key = key
                self.challenge = dict(id=uuid.uuid4().hex, policy=POLICY, binding=binding,
                                      eligible=eligible, reason=reason, generated=now)
            self.challenge.update(generated=now, eligible=eligible, reason=reason)
            if now-self.challenge_at >= .5:
                atomic_json(self.root/'challenge.json', self.challenge)
                self.challenge_at = now
            path = self.root/'request.json'
            if not path.exists():
                return
            if path.is_symlink() or path.stat().st_size > 4096:
                raise ValueError('APPROVAL_REQUEST_FILE_INVALID')
            request = json.loads(path.read_text(encoding='utf-8'))
            path.unlink()  # Never leave an invalid request queued for later.
            identifier = request.get('approval_id', '')
            if (not eligible or request.get('binding') != binding or request.get('policy') != POLICY
                    or request.get('challenge_id') != self.challenge['id']
                    or not 0 <= now-request.get('created', -999) <= 5
                    or request.get('confirmations') != list(CONFIRMATIONS)
                    or len(identifier) != 32 or any(c not in '0123456789abcdef' for c in identifier)):
                self.reason = 'STALE_OR_INVALID_PREPARATION_REJECTED'
                return
            evidence = dict(request, previous=settlement.get('previous'),
                previous_approval_id=self.approval_id, operator_clearance_source='EXPLICIT_HUMAN_CONFIRMATION',
                ai_clearance_granted=False, observed_software_snapshot=snapshot)
            with self.db:
                self.db.execute('INSERT INTO approvals VALUES (?,?,?,?,?,?)',
                    (identifier,self.session,json.dumps(binding,sort_keys=True),'RESERVED',None,'RESERVED_BEFORE_IPC'))
                self.db.execute('INSERT INTO supervised_evidence VALUES (?,?)',
                                (identifier,json.dumps(evidence,sort_keys=True)))
            self.approval_id, self.binding, self.token = identifier, binding, None
            self.state, self.reason = 'RESERVED', 'WAIT_NEW_PHYSICAL_START_AND_REQUEST'
            self.expires, self.arm_deadline = now+120, now+2
            self.last_complete = None
            self.prepared_count += 1
            self.challenge['eligible'] = False
            # Reserve first. Failure in retirement or IPC permanently spends this ID.
            prepare(evidence, now)
            gateway.supervised_arm(snapshot, identifier)
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError) as error:
            self.failed = True
            self.reason = 'SUPERVISED_APPROVAL_FAILED:'+type(error).__name__
            if self.challenge:
                self.challenge.update(eligible=False, reason=self.reason)
            gateway.cancel()
            if self.approval_id:
                try: self.revoke(self.reason)
                except (OSError, sqlite3.Error, ValueError): self.state='STORAGE_UNCERTAIN'

    def status(self):
        return dict(super().status(), policy=POLICY, challenge=self.challenge,
            prepared_count=self.prepared_count, last_complete=self.last_complete,
            required_confirmations=list(CONFIRMATIONS),
            clearance_source='OPERATOR_ONLY_NOT_AI_CLEAR', previous_approval_reused=False)
