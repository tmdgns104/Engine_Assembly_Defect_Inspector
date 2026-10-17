"""No actuator I/O: analysis storage failures and stopped camera replacement."""
from collections import deque
from copy import deepcopy
from types import SimpleNamespace as NS
import threading
import unittest
from unittest.mock import Mock, patch

from src.runtime.standalone import StandaloneRuntime
from notebook.tests.assembly_result_fixture import assembly_result


class AssemblyPublicationTests(unittest.TestCase):
    def runtime(self, result):
        r=StandaloneRuntime.__new__(StandaloneRuntime)
        r.bridge=NS(inspection_id='a'*32,poll=lambda:None,error=None,phase='INSPECTION_DURABLE')
        r.handshake=NS(cancelled=False,state='INSPECTING',token='new-request')
        r.service=NS(journal=NS(detail=lambda _:dict(state='COMPLETE',decision='PASS')))
        r.assembly=NS(submit=Mock(),result=lambda _:result,evidence_path=lambda _:'assembly/result.json')
        r.published_ids=set();r.assembly_submitted={};r.line_profile={'assembly_deadline_s':30};r.error=None
        r._commit_and_publish=Mock();r._fault=Mock();r._cancel_pending=Mock()
        return r

    def test_saved_alignment_review_publishes_basic_pass(self):
        r=self.runtime(assembly_result('REVIEW'));r._poll_result(1)
        self.assertEqual(r._commit_and_publish.call_args.args[1]['decision'],'PASS')

    def test_saved_assembly_fail_is_reference_and_publishes_basic_pass(self):
        r = self.runtime(assembly_result('FAIL_CANDIDATE'))
        r._poll_result(1)
        final = r._commit_and_publish.call_args.args[1]
        self.assertEqual(final['decision'], 'PASS')
        self.assertEqual(final['assembly_inspector'], 'FAIL')
        self.assertFalse(final['assembly_affects_final'])

    def test_raw_loss_storage_failure_and_dead_process_never_publish(self):
        for reason in ('RAW_FILE_HASH_MISMATCH','ASSEMBLY_RECORDING_FAILED','ASSEMBLY_PROCESS_EXITED'):
            r=self.runtime(dict(state='ERROR',reason=reason));r._poll_result(1)
            r._commit_and_publish.assert_not_called();r._fault.assert_called_once()

    def test_deadline_is_system_failure_not_fake_ng(self):
        r=self.runtime(None);r._poll_result(1);r._poll_result(32)
        r._commit_and_publish.assert_not_called();r._fault.assert_called_once()

    def test_cancelled_journal_is_not_optional_analysis(self):
        r=self.runtime(assembly_result('REVIEW'))
        r.service.journal.detail=lambda _:dict(state='CANCELLED',decision='ERROR',result={'reason':'STOP'})
        r._poll_result(1)
        r._commit_and_publish.assert_not_called();r._cancel_pending.assert_called_once()


class CameraRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.clock=patch('src.runtime.standalone.time.monotonic',return_value=100.)
        self.guard=patch('src.runtime.standalone.count_unfinished_inspections',return_value=0)
        self.clock.start();self.guard_mock=self.guard.start()
        self.addCleanup(self.clock.stop);self.addCleanup(self.guard.stop)
        self.make_runtime()

    def make_runtime(self):
        self.snapshot=dict(connected=True,fresh=True,run_idle=True,bool_valid=True,generated=100.,received=100.,
            phase='DISARMED',raw100='00000000',boot=2,connection=3,
            controls=dict(Mc_Run=False,Inspection_Request=False,EStop_OK=True,Stop_PB=True))
        self.r=StandaloneRuntime.__new__(StandaloneRuntime)
        r=self.r;r.lock=threading.RLock();r.gateway=NS(contract_version='OPENER_CYCLIC',read_snapshot=lambda _:deepcopy(self.snapshot))
        r.service=NS(lock=threading.RLock(),active=None,storage_pending=None,switching=False,
            generation='new',package=NS(root='same-package'),production_tracking=threading.Event(),
            journal=NS(lock=threading.RLock(),db=object()),
            health=lambda:dict(state='IDLE',ready=True,camera_ready=True,error=None),
            activate=Mock(return_value={'activated':True}))
        r.handshake=NS(token=None,state='HOLD',inputs={},fault=Mock(),retire_automatic=Mock())
        r.assembly=NS(status=lambda:dict(outstanding=0,error=None))
        r.final_pending=None;r.bridge=NS(inspection_id=None);r.published_ids=set()
        r.operating=True;r.error='CAMERA_OR_OBSERVATION_STREAM_UNAVAILABLE'
        r.worker_generation='old';r.coordinator=object();r._passage_history=deque()
        r.latest_packet={'processed_monotonic':80};r.observation_started_at=0
        r._event=Mock();r._reset_unbound_observation=Mock();r._restore_previous_product_identity=Mock()
        r._cancel_pending=Mock()
        r.logger=Mock();r._automatic_policy=lambda:True

    def test_running_or_stale_or_pending_cyclic_state_never_replaces_worker(self):
        for change in ('running','request','stale','output','storage','assembly'):
            with self.subTest(change=change):
                self.make_runtime();self.guard_mock.return_value=0
                if change=='running': self.snapshot['controls']['Mc_Run']=True
                if change=='request': self.snapshot['controls']['Inspection_Request']=True
                if change=='stale': self.snapshot['received']=99.
                if change=='output': self.snapshot['raw100']='01000100'
                if change=='storage': self.r.service.storage_pending={'id':'active'}
                if change=='assembly': self.r.assembly.status=lambda:dict(outstanding=1,error=None)
                self.r._recover_camera();self.r.service.activate.assert_not_called()

    def test_stopped_recovery_replaces_stale_preview_without_erasing_product_proof(self):
        self.r._recover_camera()
        self.r.service.activate.assert_called_once_with('same-package')
        self.assertIsNone(self.r.error);self.assertIsNone(self.r.latest_packet)
        self.assertFalse(self.r.operating)  # Normal acquisition waits for fresh frames.
        self.r._restore_previous_product_identity.assert_called_once()
        self.r.handshake.retire_automatic.assert_called_once()

    def test_camera_can_recover_for_abort_proof_without_mutating_unfinished_journal(self):
        self.guard_mock.return_value=1
        original=self.r.service.journal.db
        self.r._recover_camera()
        self.r.service.activate.assert_called_once()
        self.assertIs(self.r.service.journal.db,original)
        self.r._cancel_pending.assert_called_once_with('CAMERA_RECOVERY')

    def test_connection_change_during_recovery_cannot_clear_fault(self):
        def activate(_):
            self.snapshot['connection']=4;return {'activated':True}
        self.r.service.activate.side_effect=activate;self.r._recover_camera()
        self.assertIsNotNone(self.r.error)
        self.r.handshake.retire_automatic.assert_not_called()


if __name__=='__main__':unittest.main()
