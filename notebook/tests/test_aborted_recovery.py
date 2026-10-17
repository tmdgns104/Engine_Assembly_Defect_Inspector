"""Abort settlement is not a fabricated final and never issues another grant."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from src.journal.sqlite import Journal
from src.runtime.aborted_recovery import record_abort, valid_abort, digest, canonical
from src.runtime.initial_approval import count_unfinished_inspections


def display_runtime(journal):
    from src.runtime.standalone import StandaloneRuntime
    runtime = StandaloneRuntime.__new__(StandaloneRuntime)
    runtime.service = NS(journal=journal, generation='fixture-generation')
    runtime.session_id = 'fixture-runtime'
    runtime._diagnostic_events = None
    runtime.aborted_inspection = None
    return runtime


class AbortRecoveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.j = Journal(Path(temp.name), min_free_bytes=0); self.addCleanup(self.j.close)
        binding = dict(plc_contract='OPENER_CYCLIC', plc_request_token='0000000000000001:1:1',
                       runtime_session_id='old', request_accepted_monotonic=1)
        self.identifier, _ = self.j.admit(dict(cell_id='t',plc_session_id=1,request_id=1,
            cycle_id=1,attempt=1,control_mode='production',runtime_binding=binding), {})
        self.j.finish(self.identifier, dict(decision='REVIEW', reason='ORIGINAL_MOTION',
            production_identity=dict(binding,inspection_id=self.identifier)),
            [dict(kind='raw',data=b'original fixture evidence',width=1,height=1)])
        raw = self.j.db.execute('SELECT result_json FROM inspections').fetchone()[0]
        event = dict(connection_session=1, trial_request_id=1,pid=100,result_count=0,done_count=0,completed_count=0)
        events = [dict(event,event='REQUEST_RECEIVED',monotonic_s=1),
                  dict(event,event='TRIAL_ABORTED_NO_NEW_DONE',phase='DISARMED',armed=False,monotonic_s=2)]
        self.proof = dict(inspection_id=self.identifier,result_sha256=digest(raw),actor='fixture-supervisor',
            reason='aborted without output',confirmations=['PHYSICAL_STOP','PRODUCT_HELD','ABORT_WITHOUT_RESULT'],
            failed=dict(boot=1,connection=1,request_id=1,phase='DISARMED',armed=False,initial_revoked=True,
                result_count=0,done_count=0,completed_count=0,raw100='00000000',events=events,pid=100,
                trace_sha256=digest(canonical(events)),approval_id='a'*32,runtime_session='old'),
            approval=dict(id='a'*32,state='REVOKED',token=binding['plc_request_token'],runtime='old'),
            current=dict(boot=1,connection=2,request_id=1,approval_id='a'*32,phase='DISARMED',raw100='00000000',
                observed_at=10,generated=10,received=10,connected=True,fresh=True,run_idle=True,bool_valid=True,
                controls=dict(Inspection_Request=False,Mc_Run=False,EStop_OK=True,Stop_PB=True),
                result_count=0,done_count=0,completed_count=0,runtime_session='current'),
            owners=dict(worker_state='IDLE',worker_alive=True,active_inspection_id=None,storage_pending=False,final_commit_pending=False,
                assembly_active=None,assembly_pending=0,assembly_outstanding=0,runtime_session='current'))

    def test_append_only_settlement_preserves_original_and_does_not_create_final(self):
        before = tuple(self.j.db.execute('SELECT * FROM inspections').fetchone())
        self.assertEqual(count_unfinished_inspections(self.j.db),1)
        record_abort(self.j,self.identifier,self.proof,now=10)
        self.assertTrue(valid_abort(self.j.db,self.identifier))
        self.assertEqual(count_unfinished_inspections(self.j.db),0)
        self.assertEqual(before,tuple(self.j.db.execute('SELECT * FROM inspections').fetchone()))
        self.assertIsNone(self.j.db.execute("SELECT 1 FROM service_state WHERE key LIKE 'integrated_decision:%'").fetchone())
        with self.assertRaises(ValueError):record_abort(self.j,self.identifier,self.proof,now=10)

    def test_missing_nullable_owner_fields_or_pid_do_not_prove_idle(self):
        for key in ('active_inspection_id','assembly_active','final_commit_pending'):
            proof=copy.deepcopy(self.proof);proof['owners'].pop(key)
            with self.assertRaises(ValueError):record_abort(self.j,self.identifier,proof,now=10)
        proof=copy.deepcopy(self.proof);proof['failed'].pop('pid')
        for event in proof['failed']['events']:event.pop('pid')
        with self.assertRaises(ValueError):record_abort(self.j,self.identifier,proof,now=10)

    def test_abort_and_final_cannot_both_commit(self):
        record_abort(self.j,self.identifier,self.proof,now=10)
        with self.assertRaisesRegex(ValueError,'ABORTED_INSPECTION'):
            self.j.commit_integrated(dict(inspection_id=self.identifier,request_token='unused',decision='ERROR'))

    def test_supervised_abort_settlement_is_not_restored_as_unresolved(self):
        runtime = display_runtime(self.j)
        runtime._event(dict(event='LINE_CANCELLED_RESULT_BLOCKED',
            inspection_id=self.identifier, reason='fixture blocked'))
        record_abort(self.j,self.identifier,self.proof,now=10)
        runtime._restore_aborted_inspection()
        self.assertIsNone(runtime.aborted_inspection)

    def test_missing_stale_wrong_context_active_and_transmitted_evidence_block(self):
        for group,key,value in [('failed','done_count',1),('failed','initial_revoked',False),
            ('approval','state','ACCEPTED'),('current','generated',8),('current','connection',1),
            ('owners','storage_pending',True),('owners','assembly_outstanding',1),
            ('failed','trace_sha256','0'*64)]:
            with self.subTest(group=group,key=key):
                proof=copy.deepcopy(self.proof);proof[group][key]=value
                with self.assertRaises(ValueError):record_abort(self.j,self.identifier,proof,now=10)
        self.assertEqual(count_unfinished_inspections(self.j.db),1)

    def test_bare_flag_or_tampered_original_never_exempts(self):
        record_abort(self.j,self.identifier,self.proof,now=10)
        with self.j.db:
            # Corrupt only the isolated test database, never operating history.
            self.j.db.execute("UPDATE service_state SET value='{}' WHERE key LIKE 'aborted_cycle:%'")
        self.assertEqual(count_unfinished_inspections(self.j.db),1)

    def test_real_accepted_and_low_disk_still_block(self):
        record_abort(self.j,self.identifier,self.proof,now=10)
        self.j.admit(dict(cell_id='t',plc_session_id=1,request_id=2,cycle_id=2,attempt=1),{})
        self.assertEqual(count_unfinished_inspections(self.j.db),1)
        self.j.min_free_bytes=10**20
        with self.assertRaises(OSError):self.j.capacity()

    def plc_owned_proof(self):
        proof=copy.deepcopy(self.proof)
        proof['request_authority']='PLC_AUTOMATIC_REPEAT'
        proof['approval']=None
        proof['failed'].update(initial_revoked=False,approval_id='',
            request_snapshot=dict(boot=1,connection=1,request_id=1,approval_id='',phase='REQUEST_RECEIVED'),
            cycle_policy=dict(policy='PLC_AUTOMATIC_REPEAT',software_permission_required=False),
            initial_approval=None)
        proof['failed']['events'][-1]['publication_enabled']=False
        proof['failed']['trace_sha256']=digest(canonical(proof['failed']['events']))
        proof['current'].update(boot=2,connection=1,request_id=0,approval_id='')
        self.journal_cancel()
        return proof

    def journal_cancel(self):
        runtime=display_runtime(self.j)
        runtime._event(dict(event='LINE_CANCELLED_RESULT_BLOCKED',inspection_id=self.identifier,
                            request_token='0000000000000001:1:1',reason='PYTHON_NOT_READY'))

    def test_plc_owned_abort_needs_no_fabricated_revoked_approval(self):
        proof=self.plc_owned_proof()
        before=tuple(self.j.db.execute('SELECT * FROM inspections').fetchone())
        record_abort(self.j,self.identifier,proof,now=10)
        self.assertTrue(valid_abort(self.j.db,self.identifier))
        self.assertEqual(count_unfinished_inspections(self.j.db),0)
        self.assertEqual(before,tuple(self.j.db.execute('SELECT * FROM inspections').fetchone()))

    def repeated_cycle_proof(self):
        proof = self.plc_owned_proof()
        proof['counter_evidence'] = 'REQUEST_BASELINE_V1'
        counts = dict(result_count=2, done_count=2, completed_count=2)
        proof['failed'].update(counts)
        proof['failed']['request_snapshot'].update(counts)
        proof['failed']['request_snapshot']['evidence_source'] = 'BOUND_REQUEST_AND_C_EVENT'
        for event in proof['failed']['events']:
            event.update(counts)
        proof['failed']['trace_sha256'] = digest(canonical(proof['failed']['events']))
        return proof

    def test_prior_completed_cycles_do_not_prevent_aborting_unsent_request(self):
        proof = self.repeated_cycle_proof()
        before = tuple(self.j.db.execute('SELECT * FROM inspections').fetchone())
        record_abort(self.j, self.identifier, proof, now=10)
        self.assertTrue(valid_abort(self.j.db, self.identifier))
        self.assertEqual(count_unfinished_inspections(self.j.db), 0)
        self.assertEqual(before, tuple(self.j.db.execute('SELECT * FROM inspections').fetchone()))
        self.assertIsNone(self.j.db.execute("SELECT 1 FROM service_state WHERE key LIKE 'integrated_decision:%'").fetchone())

    def test_baseline_counters_cannot_hide_output_missing_data_or_counter_reset(self):
        original = self.repeated_cycle_proof()
        for target, key, value in [('last_event','done_count',3), ('last_event','result_count',1),
                ('failed','result_count',3), ('snapshot','completed_count',None),
                ('snapshot','done_count',-1), ('current','result_count',2)]:
            proof = copy.deepcopy(original)
            obj = {'last_event':proof['failed']['events'][-1], 'failed':proof['failed'],
                   'snapshot':proof['failed']['request_snapshot'], 'current':proof['current']}[target]
            obj[key] = value
            proof['failed']['trace_sha256'] = digest(canonical(proof['failed']['events']))
            with self.subTest(target=target,key=key), self.assertRaises(ValueError):
                record_abort(self.j, self.identifier, proof, now=10)
        self.assertEqual(count_unfinished_inspections(self.j.db), 1)

    def test_abort_commit_rechecks_live_state_and_rolls_back_on_change(self):
        proof = self.repeated_cycle_proof()
        def changed(): raise ValueError('PLC_CHANGED_DURING_ABORT_RECOVERY')
        with self.assertRaisesRegex(ValueError, 'PLC_CHANGED'):
            record_abort(self.j, self.identifier, proof, now=10, recheck=changed)
        self.assertFalse(valid_abort(self.j.db, self.identifier))
        self.assertEqual(self.j.db.execute("SELECT count(*) FROM events WHERE event_type='SUPERVISED_CYCLE_ABORTED'").fetchone()[0], 0)

    def test_cached_aborted_display_clears_only_after_verified_settlement(self):
        runtime = display_runtime(self.j)
        self.journal_cancel()
        runtime._restore_aborted_inspection()
        self.assertIsNotNone(runtime.aborted_inspection)
        record_abort(self.j, self.identifier, self.repeated_cycle_proof(), now=10)
        self.assertIsNone(runtime._aborted_status())
        self.assertIsNone(runtime.aborted_inspection)

    def test_plc_owned_recovery_rejects_missing_policy_residue_old_boot_or_grant(self):
        original=self.plc_owned_proof()
        for group,key,value in [('failed','cycle_policy',{}),('failed','initial_revoked',True),
                ('failed','approval_id','a'*32),('current','boot',1),('current','request_id',1)]:
            proof=copy.deepcopy(original);proof[group][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):record_abort(self.j,self.identifier,proof,now=10)

    def test_aborted_ui_shows_raw_not_historical_final(self):
        from src.runtime.standalone_web import line_view
        aborted=dict(inspection_id=self.identifier,raw_decision='REVIEW',raw_journal='COMPLETE',
            assembly='NOT_RUN',integrated='INCOMPLETE',plc_publication='BLOCKED')
        view=line_view(dict(aborted_inspection=aborted, integrated_counts={'ERROR':99}),{})
        self.assertEqual(view['phase'],'ABORTED')
        self.assertEqual(view['verdict'],'INCOMPLETE')
        self.assertEqual(view['aborted_inspection']['raw_decision'],'REVIEW')
        self.assertIsNone(view['last_result'])


class AbortDisplayRestoreTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.journal = Journal(temp.name, min_free_bytes=0)
        self.addCleanup(self.journal.close)
        self.runtime = display_runtime(self.journal)

    def blocked_inspection(self, number, monotonic, contract='OPENER_CYCLIC'):
        binding = dict(plc_contract=contract, plc_request_token=f'0000000000000001:1:{number}')
        identifier, _ = self.journal.admit(dict(cell_id='display', plc_session_id=1,
            request_id=number, cycle_id=number, attempt=1, control_mode='production',
            runtime_binding=binding), {})
        self.journal.finish(identifier, dict(decision='ERROR', reason='fixture raw error'))
        # Use the actual runtime writer: immutable event plus publication cache.
        self.runtime._event(dict(event='LINE_CANCELLED_RESULT_BLOCKED',
            inspection_id=identifier, reason=f'blocked-{number}', monotonic_s=monotonic))
        return identifier, binding

    def test_restore_uses_saved_event_without_mutating_journal(self):
        identifier, binding = self.blocked_inspection(1, 50)
        before = self.journal.db.total_changes
        self.runtime._restore_aborted_inspection()
        self.assertEqual(self.runtime.aborted_inspection, dict(inspection_id=identifier,
            reason='blocked-1', request_token=binding['plc_request_token'],
            plc_publication='BLOCKED', restored_from_journal=True))
        self.assertEqual(self.journal.db.total_changes, before)

    def test_new_boot_with_lower_monotonic_clock_is_the_latest_abort(self):
        self.blocked_inspection(1, 90_000)
        self.journal.producer_session = 'new-producer-session'
        identifier, _ = self.blocked_inspection(2, 5)
        self.runtime._restore_aborted_inspection()
        self.assertEqual(self.runtime.aborted_inspection['inspection_id'], identifier)

    def test_bare_or_tampered_abort_key_cannot_hide_unresolved_request(self):
        identifier, _ = self.blocked_inspection(1, 50)
        with self.journal.db:
            self.journal.db.execute('INSERT INTO service_state VALUES (?,?)',
                ('aborted_cycle:'+identifier, '{}'))
        before = self.journal.db.total_changes
        self.runtime._restore_aborted_inspection()
        self.assertEqual(self.runtime.aborted_inspection['inspection_id'], identifier)
        self.assertEqual(self.journal.db.total_changes, before)

    def test_settled_recent_records_do_not_hide_an_unresolved_abort(self):
        identifier, _ = self.blocked_inspection(1, 1)
        for number in range(2, 35):
            settled, binding = self.blocked_inspection(number, number)
            self.journal.commit_integrated(dict(inspection_id=settled,
                request_token=binding['plc_request_token'], decision='ERROR'))
        self.runtime._restore_aborted_inspection()
        self.assertIsNotNone(self.runtime.aborted_inspection)
        self.assertEqual(self.runtime.aborted_inspection['inspection_id'], identifier)

    def test_other_contract_and_completed_final_are_not_restored(self):
        self.blocked_inspection(1, 1, contract='LEGACY_THREE_BOOL')
        identifier, binding = self.blocked_inspection(2, 2)
        self.journal.commit_integrated(dict(inspection_id=identifier,
            request_token=binding['plc_request_token'], decision='ERROR'))
        self.runtime._restore_aborted_inspection()
        self.assertIsNone(self.runtime.aborted_inspection)


if __name__ == '__main__':unittest.main()
