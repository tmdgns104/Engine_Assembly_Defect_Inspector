"""Cancelled admission maintenance never rewrites original evidence or outputs."""
import copy
import json
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'jetson'))
from src.journal.sqlite import Journal
from src.runtime.aborted_recovery import (CANCELLED_EVENT, CANCELLED_POLICY,
    canonical, digest, record_abort, record_cancelled_abort, valid_abort,
    validate_cancelled_record)
from notebook.tests.test_aborted_recovery import display_runtime


class CancelledAdmissionRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.j = Journal(self.temp.name,min_free_bytes=0)
        self.addCleanup(self.j.close)
        binding = dict(plc_contract='OPENER_CYCLIC',plc_request_token='0000000000000001:1:7',
                       runtime_session_id='old',request_accepted_monotonic=1.)
        request = dict(cell_id='fixture',plc_session_id=1,request_id=7,cycle_id=7,attempt=1,
                       control_mode='production',runtime_binding=binding)
        self.identifier,_ = self.j.admit(request,{'fixture':'no-field'})
        self.runtime = display_runtime(self.j)
        self.runtime.session_id = 'old'
        self.runtime.assembly_submitted = {}
        self.runtime._event(dict(event='LINE_CANCELLED_RESULT_BLOCKED',
            inspection_id=self.identifier,reason='PYTHON_NOT_READY'))
        self.j.cancel(self.identifier,'USER_CANCELLED')
        row = self.row()
        counts = dict(result_count=6,done_count=6,completed_count=6)
        event = dict(connection_session=1,trial_request_id=7,pid=123,**counts)
        trace = [dict(event,event='REQUEST_RECEIVED',monotonic_s=1.),
                 dict(event,event='TRIAL_ABORTED_NO_NEW_DONE',monotonic_s=1.1,
                      phase='DISARMED',armed=False,publication_enabled=False)]
        self.proof = dict(inspection_id=self.identifier,result_sha256=digest(row['result_json']),
            actor='fixture-supervisor',reason='stopped cancelled admission without output',
            confirmations=['PHYSICAL_STOP','PRODUCT_REMOVED_OR_HELD_OFF_LINE','ABORT_WITHOUT_RESULT'],
            request_authority='PLC_AUTOMATIC_REPEAT',counter_evidence='REQUEST_BASELINE_V1',approval=None,
            failed=dict(boot=1,connection=1,request_id=7,phase='DISARMED',armed=False,
                initial_revoked=False,initial_approval=None,approval_id='',raw100='00000000',
                runtime_session='old',pid=123,events=trace,trace_sha256=digest(canonical(trace)),
                cycle_policy=dict(policy='PLC_AUTOMATIC_REPEAT',software_permission_required=False),
                request_snapshot=dict(boot=1,connection=1,request_id=7,phase='REQUEST_RECEIVED',
                    approval_id='',evidence_source='BOUND_REQUEST_AND_C_EVENT',**counts),**counts),
            current=dict(boot=2,connection=1,request_id=0,phase='DISARMED',raw100='00000000',
                approval_id='',observed_at=10.,generated=10.,received=10.,connected=True,fresh=True,
                run_idle=True,bool_valid=True,runtime_session='new',result_count=0,done_count=0,completed_count=0,
                controls=dict(Inspection_Request=False,Mc_Run=False,EStop_OK=True,Stop_PB=True)),
            owners=dict(worker_state='IDLE',worker_alive=True,active_inspection_id=None,
                storage_pending=False,final_commit_pending=False,assembly_active=None,
                assembly_pending=0,assembly_outstanding=0,runtime_session='new',
                production_admission_pending=False,request_start_pending=False))

    def row(self):
        return self.j.db.execute('SELECT * FROM inspections WHERE inspection_id=?',(self.identifier,)).fetchone()

    def record(self,proof=None,recheck=lambda:True):
        return record_cancelled_abort(self.j,self.identifier,proof or self.proof,now=10.,recheck=recheck)

    def test_append_only_settlement_preserves_cancelled_row_and_restores_cleanly(self):
        before = tuple(self.row())
        self.runtime._restore_aborted_inspection()
        self.assertIsNotNone(self.runtime.aborted_inspection)
        receipt = self.record()
        self.assertEqual(receipt['policy'],CANCELLED_POLICY)
        self.assertEqual(receipt['grants_created'],0)
        self.assertFalse(receipt['classification_created'])
        self.assertFalse(receipt['result_replay_allowed'])
        self.assertEqual(tuple(self.row()),before)
        self.assertEqual(self.j.db.execute('SELECT count(*) FROM frame_assets').fetchone()[0],0)
        self.assertIsNone(self.j.db.execute("SELECT 1 FROM service_state WHERE key LIKE 'integrated_decision:%'").fetchone())
        self.assertTrue(valid_abort(self.j.db,self.identifier))
        self.assertIsNone(self.runtime._aborted_status())
        restored = display_runtime(self.j)
        restored._restore_aborted_inspection()
        self.assertIsNone(restored.aborted_inspection)
        with self.assertRaisesRegex(ValueError,'ALREADY_RECORDED'):
            self.record()
        reopened = Journal(self.temp.name,min_free_bytes=0)
        try:
            self.assertTrue(valid_abort(reopened.db,self.identifier))
            self.assertEqual(tuple(reopened.db.execute('SELECT * FROM inspections WHERE inspection_id=?',
                (self.identifier,)).fetchone()),before)
        finally:reopened.close()

    def test_old_COMPLETE_policy_does_not_accept_CANCELLED_rows(self):
        with self.assertRaisesRegex(ValueError,'ABORT_REQUIRES_DURABLE_RAW'):
            record_abort(self.j,self.identifier,self.proof,now=10.)

    def test_control_proof_faults_do_not_create_receipt(self):
        changes = {
            'result_transmitted':lambda p:p['failed'].update(result_count=7),
            'old_boot':lambda p:p['current'].update(boot=1),
            'request_high':lambda p:p['current']['controls'].update(Inspection_Request=True),
            'running':lambda p:p['current']['controls'].update(Mc_Run=True),
            'stale':lambda p:p['current'].update(received=9.),
            'wrong_token':lambda p:p['failed'].update(request_id=8),
            'missing_handling':lambda p:p.update(confirmations=['PHYSICAL_STOP']),
            'pending_admission':lambda p:p['owners'].update(production_admission_pending=True),
            'missing_admission_owner':lambda p:p['owners'].pop('production_admission_pending'),
            'pending_request_storage':lambda p:p['owners'].update(request_start_pending=True),
            'missing_counter':lambda p:p['failed']['request_snapshot'].pop('result_count'),
            'bad_numeric':lambda p:p['current'].update(generated=None),
            'bad_trace_hash':lambda p:p['failed'].update(trace_sha256='0'*64),
        }
        for name,change in changes.items():
            with self.subTest(fault=name):
                proof = copy.deepcopy(self.proof)
                change(proof)
                with self.assertRaises((ValueError,TypeError,KeyError)):
                    self.record(proof)
                self.assertIsNone(self.j.db.execute('SELECT 1 FROM service_state WHERE key=?',
                    ('aborted_cycle:'+self.identifier,)).fetchone())

    def test_missing_or_tampered_cancel_event_blocks_recovery(self):
        row = self.j.db.execute("SELECT event_id,payload_json FROM events WHERE event_type='INSPECTION_CANCELLED'").fetchone()
        with self.j.db:
            self.j.db.execute("UPDATE events SET payload_sha256=? WHERE event_id=?",('0'*64,row[0]))
        with self.assertRaisesRegex(ValueError,'HASH_MISMATCH'):
            self.record()
        with self.j.db:
            self.j.db.execute('UPDATE events SET payload_sha256=? WHERE event_id=?',(digest(row[1]),row[0]))
            self.j.db.execute("DELETE FROM outbox WHERE event_id IN (SELECT event_id FROM events WHERE event_type='LINE_CANCELLED_RESULT_BLOCKED')")
            self.j.db.execute("DELETE FROM events WHERE event_type='LINE_CANCELLED_RESULT_BLOCKED'")
        with self.assertRaisesRegex(ValueError,'DURABLE_CANCELLATION_AND_BLOCK'):
            self.record()

    def test_even_zero_counter_proof_cannot_hide_publication_event(self):
        with self.j.db:
            self.j._event('INTEGRATED_INSPECTION_COMPLETED',dict(inspection_id=self.identifier,decision='ERROR'))
        with self.assertRaisesRegex(ValueError,'COMPLETION_OR_PUBLICATION_EXISTS'):
            self.record()

    def test_readonly_preflight_rejects_assets_and_publication_cache(self):
        changes = self.j.db.total_changes
        evidence = validate_cancelled_record(self.j.db,self.row(),self.proof,10.)
        self.assertEqual(set(evidence),{'INSPECTION_CANCELLED','LINE_CANCELLED_RESULT_BLOCKED'})
        self.assertEqual(self.j.db.total_changes,changes)
        with self.j.db:
            self.j.db.execute('INSERT INTO frame_assets VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                ('asset',self.identifier,'raw','isolated-fixture.png','0'*64,1,1,1,None,'top','PENDING'))
        with self.assertRaisesRegex(ValueError,'HAS_IMAGE_ASSETS'):
            self.record()
        with self.j.db:
            self.j.db.execute('DELETE FROM frame_assets WHERE asset_id=?',('asset',))
            self.j.db.execute('UPDATE service_state SET value=? WHERE key=?',
                (canonical(dict(publication_status='IPC_QUEUED')),'production_publication:'+self.identifier))
        with self.assertRaisesRegex(ValueError,'PUBLICATION_EXISTS'):
            self.record()

    def test_source_change_during_recheck_rolls_back_settlement(self):
        before = tuple(self.row())
        def change_source():
            self.j.db.execute("UPDATE inspections SET completed_at='changed' WHERE inspection_id=?",(self.identifier,))
            return True
        with self.assertRaisesRegex(ValueError,'CHANGED_DURING_RECOVERY'):
            self.record(recheck=change_source)
        self.assertEqual(tuple(self.row()),before)
        self.assertFalse(valid_abort(self.j.db,self.identifier))
        self.assertEqual(self.j.db.execute('SELECT count(*) FROM events WHERE event_type=?',
            (CANCELLED_EVENT,)).fetchone()[0],0)

    def test_commit_recheck_failure_rolls_back_both_new_records(self):
        for recheck in (None,lambda:False):
            with self.subTest(recheck=recheck):
                before = self.j.db.execute('SELECT count(*) FROM events').fetchone()[0]
                with self.assertRaisesRegex(ValueError,'FRESH_MAINTENANCE_RECHECK'):
                    self.record(recheck=recheck)
                self.assertEqual(self.j.db.execute('SELECT count(*) FROM events').fetchone()[0],before)
                self.assertIsNone(self.j.db.execute('SELECT 1 FROM service_state WHERE key=?',
                    ('aborted_cycle:'+self.identifier,)).fetchone())
        def slow_recheck():
            time.sleep(.55)
            return True
        with self.assertRaisesRegex(ValueError,'CURRENT_STOPPED_SEPARATE_CONTEXT'):
            self.record(recheck=slow_recheck)
        self.assertEqual(self.j.db.execute('SELECT count(*) FROM events WHERE event_type=?',
            (CANCELLED_EVENT,)).fetchone()[0],0)

    def test_slow_history_uses_fresh_commit_evidence_without_relaxing_age(self):
        import src.runtime.aborted_recovery as recovery
        original = recovery._cancelled_events
        clock = [10.]
        def history(*args):
            clock[0] += .25
            return original(*args)
        def fresh():
            proof = copy.deepcopy(self.proof)
            stamp = clock[0]
            proof['current'].update(observed_at=stamp, generated=stamp, received=stamp)
            return proof
        with patch.object(recovery, '_cancelled_events', side_effect=history), \
                patch.object(recovery.time, 'monotonic', side_effect=lambda:clock[0]):
            receipt = self.record(recheck=fresh)
        self.assertGreater(receipt['observed_at'], 10.2)
        self.assertTrue(valid_abort(self.j.db, self.identifier))

    def test_refresh_cannot_change_control_identity_or_hide_pending_owner(self):
        for change in (lambda p:p['current'].update(boot=3),
                       lambda p:p['current']['controls'].update(Mc_Run=True),
                       lambda p:p['owners'].update(request_start_pending=True),
                       lambda p:p.update(actor='different')):
            proof = copy.deepcopy(self.proof)
            change(proof)
            with self.assertRaises(ValueError):
                self.record(recheck=lambda:proof)
            self.assertFalse(valid_abort(self.j.db, self.identifier))

    def test_receipt_or_original_tampering_fails_closed_and_banner_restores(self):
        self.record()
        key = 'aborted_cycle:'+self.identifier
        original = self.j.db.execute('SELECT value FROM service_state WHERE key=?',(key,)).fetchone()[0]
        for change in (lambda p:p.update(grants_created=1),
                       lambda p:p['proof']['current'].update(observed_at=None),
                       lambda p:p['proof'].update(owners=None),
                       lambda p:p.update(policy='UNKNOWN_POLICY')):
            value = json.loads(original)
            change(value)
            with self.j.db:self.j.db.execute('UPDATE service_state SET value=? WHERE key=?',(canonical(value),key))
            self.assertFalse(valid_abort(self.j.db,self.identifier))
            restored = display_runtime(self.j)
            restored._restore_aborted_inspection()
            self.assertEqual(restored.aborted_inspection['inspection_id'],self.identifier)
        with self.j.db:self.j.db.execute('UPDATE service_state SET value=? WHERE key=?',(original,key))
        self.assertTrue(valid_abort(self.j.db,self.identifier))
        with self.j.db:self.j.db.execute("UPDATE inspections SET state='COMPLETE' WHERE inspection_id=?",(self.identifier,))
        self.assertFalse(valid_abort(self.j.db,self.identifier))


if __name__ == '__main__':
    unittest.main()
