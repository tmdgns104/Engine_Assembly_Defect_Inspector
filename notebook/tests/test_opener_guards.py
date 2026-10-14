from pathlib import Path
import json
import struct
import sys
import unittest
import cv2
import numpy as np
from types import SimpleNamespace as NS
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'jetson'))
from standalone_service import plc_contract,close_resources
from src.control.opener_cyclic import CyclicHandshake,decode_snapshot,command
from src.runtime.standalone import StandaloneRuntime
from src.runtime.standalone_web import line_view
from src.runtime.opener_process import OpenerProcess
from notebook.tests.test_standalone_runtime import FinalBoundaryTests

def snapshot(phase='REQUEST_RECEIVED',request=1):
    return dict(boot=123,connection=1,request_id=request,generated=2,received=2,accepted_at=1,
        connected=True,fresh=True,run_idle=True,bool_valid=True,phase=phase,raw100='00000000',
        controls=dict(Inspection_Request=True,EStop_OK=True,Mc_Run=True,Stop_PB=True),reason='fixture')

class CyclicGuards(unittest.TestCase):
    def test_review_error_keep_ai_identity_and_queue_plc_completion(self):
        for decision in ('REVIEW','ERROR'):
            with self.subTest(decision=decision):
                g=NS(runtime_session='a'*32,read_snapshot=lambda now:snapshot(),cancel=Mock(),result=Mock())
                h=CyclicHandshake(g,lambda x:None);h.poll(2);h.bind('b'*32)
                h.publish('b'*32,decision,True,2)
                self.assertEqual(h.publication,'IPC_QUEUED')
                self.assertEqual(g.result.call_args.args[2],decision)
                self.assertFalse(h.cancelled)
    def test_control_fault_still_blocks_review_error_done(self):
        for decision in ('REVIEW','ERROR'):
            with self.subTest(decision=decision):
                g=NS(runtime_session='a'*32,read_snapshot=lambda now:snapshot(),cancel=Mock(),result=Mock())
                h=CyclicHandshake(g,lambda x:None);h.poll(2);h.bind('b'*32)
                g.read_snapshot=lambda now:snapshot('DISARMED')
                h.publish('b'*32,decision,True,2)
                g.result.assert_not_called()
    def test_startup_cannot_select_two_result_publishers(self):
        self.assertEqual(plc_contract({'plc_contract':'OPENER_CYCLIC'}),'OPENER_CYCLIC')
        with self.assertRaisesRegex(ValueError,'MULTIPLE_PLC'):
            plc_contract(dict(plc_contract='OPENER_CYCLIC',legacy_publication_enabled=True))
    def test_supervisor_cannot_launch_without_field_approval(self):
        with self.assertRaisesRegex(ValueError,'NOT_APPROVED'):
            OpenerProcess('does-not-exist','bad','/not-created/ipc')
    def test_snapshot_length_version_and_timestamp_rejected(self):
        for value in (bytes(128),b'EAI1\x01\x00\x01\x00',bytes(129)):
            with self.assertRaises(ValueError):decode_snapshot(value,10)
        b=bytearray(160);b[:8]=b'EAI1\x03\x00\x01\x00'
        struct.pack_into('<QIIddd',b,8,1,1,1,9,9,9)
        with self.assertRaises(ValueError):decode_snapshot(b,10)
    def test_packet_atomic_identity_and_completion_flags(self):
        p=command(snapshot(),'a'*32,2,identifier='b'*32,decision=2,flags=7,now=2,approval_id='c'*32)
        self.assertEqual(len(p),160)
        self.assertEqual(p[:8],b'EAI1\x03\x00\x02\x00')
        self.assertEqual(p[128:160],b'c'*32)
        self.assertEqual(struct.unpack_from('<QII',p,8),(123,1,1))
        self.assertEqual(p[32:96],b'a'*32+b'b'*32)
        self.assertEqual(struct.unpack_from('<III',p,96),(2,7,2))
    def test_stopped_or_withdrawn_context_cannot_publish_late_result(self):
        g=NS(runtime_session='a'*32,read_snapshot=lambda now:snapshot(),cancel=Mock(),result=Mock())
        h=CyclicHandshake(g,lambda x:None);h.poll(2);h.bind('b'*32)
        g.read_snapshot=lambda now:snapshot('DISARMED')
        h.publish('b'*32,'PASS',True,2)
        g.result.assert_not_called();self.assertTrue(h.cancelled)
    def test_duplicate_REQUEST_does_not_allocate_another_id(self):
        events=[];g=NS(runtime_session='a'*32,read_snapshot=lambda now:snapshot(),cancel=Mock())
        h=CyclicHandshake(g,events.append);h.poll(2);h.bind('b'*32)
        for _ in range(10):h.poll(2)
        self.assertEqual(len(events),1);self.assertEqual(h.inspection_id,'b'*32)
    def test_disconnect_has_no_implicit_explicit_fallback(self):
        g=NS(runtime_session='a'*32,read_snapshot=lambda now:None,cancel=Mock())
        h=CyclicHandshake(g,lambda x:None);h.poll(2)
        self.assertEqual(h.state,'HOLD');self.assertIsNone(h.token)
    def test_unverified_field_profile_stays_blocked(self):
        r=StandaloneRuntime.__new__(StandaloneRuntime)
        r.line_profile={'field_profile_verified':False}
        self.assertFalse(r._profile_ready())
    def test_cleanup_survives_failed_runtime_close(self):
        runtime=NS(close=Mock(side_effect=RuntimeError('close failed')))
        adapter=NS(close=Mock());lock=NS(close=Mock())
        with self.assertRaisesRegex(RuntimeError,'close failed'):
            close_resources(runtime,None,None,adapter,lock)
        adapter.close.assert_called_once();lock.close.assert_called_once()
    def test_constructor_failure_closes_already_created_owners(self):
        gateway=NS(close=Mock());adapter=NS(close=Mock());lock=NS(close=Mock())
        close_resources(None,None,gateway,adapter,lock)
        gateway.close.assert_called_once();adapter.close.assert_called_once();lock.close.assert_called_once()
    def test_recovery_requires_real_stopped_snapshot(self):
        g=NS(runtime_session='a'*32,read_snapshot=lambda now:snapshot(),cancel=Mock())
        h=CyclicHandshake(g,lambda x:None)
        with self.assertRaisesRegex(ValueError,'STOPPED_REQUEST_LOW'):h.resync()
        s=snapshot('DISARMED');s['controls'].update(Inspection_Request=False,Mc_Run=False)
        g.read_snapshot=lambda now:s
        h.resync()
        self.assertEqual(h.state,'SYNC_LOW');self.assertIsNone(h.token)

class DurableIdentityGuards(FinalBoundaryTests):
    def test_review_journal_is_not_relabelled_as_ai_fail(self):
        identifier=self.candidate();self.r._commit_and_publish(identifier,{'decision':'REVIEW'},5)
        final=self.r.history[0]
        self.assertEqual(final['decision'],'REVIEW')
        self.assertEqual(final['plc_decision'],'FAIL')
        self.assertEqual(final['plc_result_value'],1)
        self.assertTrue(final['plc_done_requested'])
        saved=json.loads(self.journal.db.execute('SELECT value FROM service_state WHERE key=?',
            ('integrated_decision:'+identifier,)).fetchone()[0])
        self.assertEqual(saved['decision'],'REVIEW')
        self.assertEqual(saved['plc_result_policy'],'PASS_OK_OTHER_NG_V1')
    def candidate(self):
        self.r.gateway=NS(contract_version='OPENER_CYCLIC')
        binding=dict(plc_request_token=self.h.token,runtime_session_id='session',
                     worker_generation='g',camera_epoch='camera',track_id=7,cycle_id='c')
        request=dict(self.r.service.allocate_request(),runtime_binding=binding)
        identifier,_=self.journal.admit(request,self.r.service.package.snapshot())
        raw = cv2.imencode('.png', np.full((8,8,3),127,np.uint8))[1].tobytes()
        self.journal.finish(identifier,dict(decision='PASS',reason='fixture',execution={'source':'mock'}),
                            [dict(kind='raw',data=raw,width=8,height=8)])
        self.h.bind(identifier);self.h.publish=Mock()
        self.r.coordinator=NS(active_cycle=NS(cycle_id='c'),_tracker=NS(_track_id=7))
        return identifier
    def test_product_change_before_commit_blocks_send(self):
        identifier=self.candidate();self.r.coordinator._tracker._track_id=8
        with self.assertRaisesRegex(ValueError,'PRODUCT_CHANGED'):
            self.r._commit_and_publish(identifier,{'decision':'PASS'},5)
        self.h.publish.assert_not_called()
    def test_camera_generation_change_blocks_send(self):
        identifier=self.candidate();self.r.epoch='reconnected'
        with self.assertRaisesRegex(ValueError,'CONTEXT_MISMATCH'):
            self.r._commit_and_publish(identifier,{'decision':'PASS'},5)
        self.h.publish.assert_not_called()
    def test_journal_failure_never_publishes(self):
        identifier=self.candidate();self.journal.db.close()
        with self.assertRaises(Exception):self.r._commit_and_publish(identifier,{'decision':'PASS'},5)
        self.h.publish.assert_not_called()
    def test_fixture_provenance_is_not_actual_AI(self):
        identifier=self.candidate();self.r._commit_and_publish(identifier,{'decision':'PASS'},5)
        self.assertTrue(self.r.history[0]['synthetic'])
        self.assertEqual(self.r.history[0]['source'],'INTEGRATED_FIXTURE_INSPECTION')

if __name__=='__main__':unittest.main()
