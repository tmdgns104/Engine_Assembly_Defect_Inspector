"""Software-only supervised admission; never opens PLC or camera devices."""
import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

from src.journal.sqlite import Journal
from src.runtime.supervised_approval import SupervisedApproval, POLICY, CONFIRMATIONS


class SupervisedApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.j = Journal(Path(self.tmp.name)/'journal', min_free_bytes=0)
        self.addCleanup(self.j.close)
        self.a = SupervisedApproval(Path(self.tmp.name)/'approval', 'a'*32)
        self.addCleanup(self.a.close)
        self.g = Mock()
        self.prepare = Mock()
        self.now = time.monotonic()
        self.s = dict(boot=1, connection=1, request_id=0, generated=self.now,
            received=self.now, connected=True, fresh=True, run_idle=True, bool_valid=True,
            raw100='00000000', phase='DISARMED', approval_id='',
            result_count=0, done_count=0, completed_count=0,
            controls=dict(Inspection_Request=False, Mc_Run=False, EStop_OK=True, Stop_PB=True))
        self.settlement = dict(clean=True, reason=None, previous=None)

    def poll(self, ready=True, epoch='e', generation='g'):
        self.s.update(generated=self.now, received=self.now)
        self.a.poll(self.s, ready, epoch, generation, self.now, self.g, self.j,
                    settlement=self.settlement, prepare=self.prepare)

    def grant(self):
        self.poll()
        challenge = self.a.status()['challenge']
        self.assertTrue(challenge['eligible'], challenge)
        identifier = self.a.submit(challenge['id'], list(CONFIRMATIONS), self.now)
        self.poll()
        self.s.update(approval_id=identifier, phase='SYNC_LOW')
        self.assertTrue(self.a.valid())
        return identifier

    def finish(self, decision='REVIEW'):
        number = self.s['request_id']+1
        self.s.update(request_id=number, phase='REQUEST_RECEIVED')
        token = f"{self.s['boot']:016x}:{self.s['connection']}:{number}"
        self.a.accept(self.s, token)
        self.settlement = dict(clean=True, reason=None,
            previous=dict(inspection_id=f'{number:032x}', request_token=token,
                          decision=decision, durable=True, tracking_session=f'track-session-{number}',
                          cycle_id=f'cycle-{number}', track_id=1))
        self.s.update(phase='READY_NEXT', result_count=number, done_count=number,
                      completed_count=number)
        self.poll()
        return token

    def test_four_outcomes_need_fresh_operator_grant_and_preserve_history(self):
        identifiers, tokens = [], []
        for decision in ('PASS', 'FAIL', 'REVIEW', 'ERROR'):
            identifiers.append(self.grant())
            tokens.append(self.finish(decision))
            self.assertFalse(self.a.valid())
            before = self.g.supervised_arm.call_count
            for _ in range(3): self.poll()
            self.assertEqual(self.g.supervised_arm.call_count, before)
        self.assertEqual(len(set(identifiers)), 4)
        self.assertEqual(len(set(tokens)), 4)
        self.assertEqual(self.a.db.execute('SELECT count(*) FROM approvals').fetchone()[0], 4)
        self.assertEqual(self.prepare.call_count, 4)
        self.assertEqual(self.s['completed_count'], 4)

    def test_missing_confirmation_and_stale_challenge_never_grant(self):
        self.poll(); c = self.a.status()['challenge']
        for confirms in ([], list(CONFIRMATIONS)[:-1]):
            with self.assertRaises(ValueError): self.a.submit(c['id'], confirms, self.now)
        with self.assertRaises(ValueError): self.a.submit('old', list(CONFIRMATIONS), self.now)
        with self.assertRaises(ValueError): self.a.submit(c['id'], list(CONFIRMATIONS), self.now+6)
        self.g.supervised_arm.assert_not_called()

    def test_duplicate_click_is_not_queued_for_next_trial(self):
        self.poll(); c = self.a.status()['challenge']
        self.a.submit(c['id'], list(CONFIRMATIONS), self.now)
        with self.assertRaises(ValueError): self.a.submit(c['id'], list(CONFIRMATIONS), self.now)
        self.poll(); self.poll()
        self.assertEqual(self.g.supervised_arm.call_count, 1)

    def test_unclean_controls_outputs_or_counters_block(self):
        self.grant(); self.finish()
        saved = copy.deepcopy(self.s)
        for key in ('Inspection_Request', 'Mc_Run', 'EStop_OK', 'Stop_PB'):
            self.s = copy.deepcopy(saved)
            self.s['controls'][key] = not saved['controls'][key]
            self.poll(); self.assertFalse(self.a.status()['challenge']['eligible'], key)
        for values in ({'raw100':'01000000'}, {'raw100':'00000100'}, {'completed_count':0},
                       {'phase':'WAIT_REQUEST_OFF'}, {'connected':False}):
            self.s = dict(copy.deepcopy(saved), **values)
            self.poll(); self.assertFalse(self.a.status()['challenge']['eligible'], values)

    def test_unsettled_storage_or_active_worker_blocks(self):
        self.grant(); self.finish()
        self.settlement['clean'] = False
        self.poll(); self.assertFalse(self.a.status()['challenge']['eligible'])

    def test_reconnect_revokes_no_automatic_rearm(self):
        self.grant(); self.s['connection'] += 1; self.poll()
        self.assertEqual(self.a.state, 'REVOKED')
        self.assertFalse(self.a.valid())
        for _ in range(3): self.poll()
        self.assertEqual(self.g.supervised_arm.call_count, 1)

    def test_active_request_lost_never_looks_completed(self):
        self.grant(); self.s.update(request_id=1, phase='REQUEST_RECEIVED')
        self.a.accept(self.s, '0000000000000001:1:1')
        self.s.update(connection=2, phase='DISARMED'); self.poll()
        self.assertFalse(self.a.status()['challenge']['eligible'])

    def test_service_restart_does_not_restore_reserved_grant(self):
        old = self.grant()
        other = SupervisedApproval(self.a.root, 'c'*32)
        self.addCleanup(other.close)
        other.poll(self.s, True, 'e', 'g', self.now, self.g, self.j,
                   settlement=self.settlement, prepare=self.prepare)
        self.assertFalse(other.valid())
        self.assertIsNone(other.approval_id)
        self.assertEqual(other.db.execute('SELECT id FROM approvals').fetchone()[0], old)

    def test_ready_false_or_camera_generation_change_revokes(self):
        self.grant(); self.poll(generation='other')
        self.assertFalse(self.a.valid())
        self.assertEqual(self.a.state, 'REVOKED')

    def test_unfinished_journal_disk_and_db_fail_closed(self):
        self.j.admit(dict(cell_id='f', plc_session_id=1, request_id=1, cycle_id=1,
                         attempt=1, control_mode='production'), {})
        self.poll(); self.assertFalse(self.a.status()['challenge']['eligible'])
        self.j.capacity = Mock(side_effect=OSError('disk'))
        self.poll(); self.assertTrue(self.a.failed)
        self.g.supervised_arm.assert_not_called()


if __name__ == '__main__': unittest.main()
