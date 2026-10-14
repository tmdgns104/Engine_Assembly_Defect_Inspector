import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock
from src.journal.sqlite import Journal
from src.runtime.initial_approval import InitialApproval, POLICY, atomic_json
from src.control.opener_cyclic import command, decode_snapshot

class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.j=Journal(Path(self.temp.name)/'journal',min_free_bytes=0);self.addCleanup(self.j.close)
        self.a=InitialApproval(Path(self.temp.name)/'approval','a'*32);self.addCleanup(self.a.close)
        self.g=Mock();self.now=time.monotonic()
        self.s=dict(boot=1,connection=1,request_id=0,generated=self.now,received=self.now,
            fresh=True,connected=True,run_idle=True,bool_valid=True,raw100='00000000',
            phase='DISARMED',approval_id='',controls=dict(Inspection_Request=False,Mc_Run=False,EStop_OK=True,Stop_PB=True))
    def poll(self,ready=True,epoch='e',generation='g'):
        self.a.poll(self.s,ready,epoch,generation,self.now,self.g,self.j)
    def request(self,**values):
        c=json.loads((self.a.root/'challenge.json').read_text())
        r=dict(approval_id='b'*32,binding=c['binding'],policy=POLICY,created=self.now,
            confirmations=['PHYSICAL_STOP','SUPERVISED','NO_UNFINISHED_PRODUCT','REAL_AI_OUTPUT'])
        r.update(values);atomic_json(self.a.root/'request.json',r)
    def grant(self):
        self.poll();self.request();self.poll()
        self.g.initial_arm.assert_called_once();self.assertTrue(self.a.valid())
    def test_requires_explicit_approval(self):
        self.poll();self.g.initial_arm.assert_not_called()
    def test_reserve_before_c_and_consume_once(self):
        self.grant()
        self.assertEqual(self.a.db.execute('SELECT state FROM approvals').fetchone()[0],'RESERVED')
        self.s.update(approval_id='b'*32,phase='REQUEST_RECEIVED',request_id=1)
        self.a.accept(self.s,'token')
        self.assertEqual(self.a.db.execute('SELECT state FROM approvals').fetchone()[0],'ACCEPTED')
        with self.assertRaises(ValueError):self.a.accept(self.s,'token2')
    def test_low_normal_controls_required(self):
        for key,value in [('Inspection_Request',True),('Mc_Run',True),('EStop_OK',False),('Stop_PB',False)]:
            with self.subTest(key=key):
                saved=copy.deepcopy(self.s);self.s['controls'][key]=value;self.poll()
                self.assertFalse(json.loads((self.a.root/'challenge.json').read_text())['eligible'])
                self.s=saved
    def test_stale_data_and_camera_unknown(self):
        self.s['received']-=1;self.poll()
        self.assertFalse(json.loads((self.a.root/'challenge.json').read_text())['eligible'])
        self.s['received']=self.now;self.poll(epoch=None)
        self.assertFalse(json.loads((self.a.root/'challenge.json').read_text())['eligible'])
    def test_wrong_approval_id(self):
        self.grant();self.s['approval_id']='c'*32
        with self.assertRaises(ValueError):self.a.accept(self.s,'token')
    def test_restart_never_restores_grant(self):
        self.grant()
        second=InitialApproval(self.a.root,'d'*32);self.addCleanup(second.close)
        self.assertFalse(second.valid());self.assertIsNone(second.approval_id)
        self.poll();self.request(binding=self.a.binding)
        second.poll(self.s,True,'e','g',self.now,self.g,self.j)
        self.assertTrue(second.failed)
        self.assertEqual(self.g.initial_arm.call_count,1)
    def test_reconnect_revokes_reserved_grant(self):
        self.grant();self.s['connection']=2;self.poll()
        self.assertFalse(self.a.valid());self.assertEqual(self.a.state,'REVOKED')
    def test_camera_generation_change_revokes(self):
        self.grant();self.poll(generation='new');self.assertFalse(self.a.valid())
    def test_wrong_runtime_and_stale_approval(self):
        self.poll();self.request(created=self.now-10);self.poll()
        self.assertTrue(self.a.failed);self.g.initial_arm.assert_not_called()
    def test_missing_confirmation_rejected(self):
        self.poll();self.request(confirmations=[]);self.poll();self.assertTrue(self.a.failed)
    def test_wrong_session_binding(self):
        self.poll();self.request(binding={'runtime':'f'*32});self.poll()
        self.assertTrue(self.a.failed);self.g.initial_arm.assert_not_called()
    def test_residual_result_not_eligible(self):
        self.s['raw100']='01000000';self.poll()
        self.assertFalse(json.loads((self.a.root/'challenge.json').read_text())['eligible'])
    def test_unfinished_journal_blocks_approval(self):
        req=dict(cell_id='test',plc_session_id=1,request_id=1,cycle_id=1,attempt=1,
                 control_mode='production')
        self.j.admit(req, {})
        self.poll()
        self.assertFalse(json.loads((self.a.root/'challenge.json').read_text())['eligible'])
    def test_duplicate_id_cannot_be_reserved_again(self):
        self.grant()
        with self.a.db:
            self.a.db.execute("UPDATE approvals SET state='REVOKED'")
        other=InitialApproval(self.a.root,'a'*32);self.addCleanup(other.close)
        self.poll();self.request()
        other.poll(self.s,True,'e','g',self.now,self.g,self.j)
        self.assertTrue(other.failed);self.assertEqual(self.g.initial_arm.call_count,1)
    def test_completion_blocks_same_product(self):
        self.grant();self.s.update(approval_id='b'*32,phase='REQUEST_RECEIVED',request_id=1)
        self.a.accept(self.s,'token')
        self.s['phase']='READY_NEXT';self.poll()
        self.assertEqual(self.a.state,'FIRST_CYCLE_COMPLETE')
        with self.assertRaises(ValueError):self.a.accept(self.s,'token2')
    def test_unused_approval_expires(self):
        self.grant();self.now+=121;self.poll();self.assertFalse(self.a.valid())
    def test_c_disarm_never_rearms_after_low(self):
        self.grant();self.s['approval_id']='b'*32;self.poll()
        self.assertEqual(self.a.state,'REVOKED')
        self.s['approval_id']='';self.poll();self.assertFalse(self.a.valid())
    def test_ipc_failure_reservation_remains_spent(self):
        self.g.initial_arm.side_effect=ValueError('disconnected')
        self.poll();self.request();self.poll()
        self.assertFalse(self.a.valid())
        self.assertEqual(self.a.db.execute('SELECT count(*) FROM approvals').fetchone()[0],1)
    def test_storage_error_disarms(self):
        self.a.db.execute('DROP TABLE approvals');self.a.db.commit()
        self.poll();self.request();self.poll()
        self.assertTrue(self.a.failed);self.g.initial_arm.assert_not_called()
    def test_v1_and_wrong_size_rejected(self):
        for b in (bytes(128),bytes(160)):
            with self.assertRaises(ValueError):decode_snapshot(b,self.now)
    def test_v2_command_layout(self):
        b=command(self.s,'a'*32,4,approval_id='b'*32,now=self.now)
        self.assertEqual(len(b),160);self.assertEqual(b[:8],b'EAI1\x03\0\x02\0')
        self.assertEqual(b[128:],b'b'*32)
