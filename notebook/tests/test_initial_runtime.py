import json
from contextlib import ExitStack
from unittest.mock import Mock
from notebook.tests import test_full_frame_request as base
from src.runtime.initial_approval import InitialApproval
import unittest
import struct
import threading
import time
from types import SimpleNamespace as NS
from unittest.mock import patch
from src.control import opener_cyclic as ipc

class RuntimeInitialWiring(unittest.TestCase):
    setUp=base.RuntimeFixture.setUp
    observe=base.RuntimeFixture.observe
    def test_cyclic_poll_publishes_current_challenge_without_clear(self):
        self.r.line_profile.update(initial_authorization='EXPLICIT_ONE_SHOT_V1',
            request_start_qualification={'verified':False})
        self.r.initial_approval=InitialApproval(self.j.root/'initial',self.g.runtime_session)
        self.addCleanup(self.r.initial_approval.close)
        self.observe(1,0)
        self.g.writes_enabled=True
        self.g.initial_arm=Mock()
        self.g.set(self.now+.1,'DISARMED',number=0,request=False,Mc_Run=False)
        self.r._poll_cyclic_plc(self.now+.1)
        path=self.r.initial_approval.root/'challenge.json'
        self.assertTrue(path.exists())
        self.assertTrue(json.loads(path.read_text())['eligible'])
        self.assertFalse(self.r._clear(self.now+.1))
        self.g.initial_arm.assert_not_called()

class GrantQueueRace(unittest.TestCase):
    def test_reserved_grant_waits_for_owner_health_renewal_and_sends_once(self):
        g=ipc.OpenerGateway.__new__(ipc.OpenerGateway)
        g.path='/private/ipc';g.lock=threading.Lock();g.stop=threading.Event()
        g.runtime_session='a'*32;g.writes_enabled=True;g.sent=set()
        g.health=(False,False,0);g.pending=None;g.initial_error=None
        g.initial_pending=(1,1,'b'*32,time.monotonic())
        sent=[];reads=[]
        class Client:
            def __enter__(self):return self
            def __exit__(self,*unused):pass
            def settimeout(self,*unused):pass
            def connect(self,*unused):pass
            def getsockopt(self,*unused):return struct.pack('3i',1,0,0)
            def recv(self,*unused):
                if reads:
                    assert g.initial_pending is not None
                    g.health_update(True,False,time.monotonic())
                reads.append(1)
                b=bytearray(160);b[:8]=b'EAI1\x03\0\x01\0'
                now=time.monotonic();struct.pack_into('<QIIddd',b,8,1,1,0,now,now,0)
                struct.pack_into('<7I',b,48,15,10,0,0,0,0,0)
                return bytes(b)
            def sendall(self,b):
                sent.append(b)
                if struct.unpack_from('<I',b,104)[0]==4:g.stop.set()
        with patch.object(ipc.socket,'SOCK_SEQPACKET',5,create=True), \
             patch.object(ipc.socket,'AF_UNIX',1,create=True), \
             patch.object(ipc.socket,'SO_PEERCRED',17,create=True), \
             patch.object(ipc.os,'geteuid',lambda:0,create=True), \
             patch.object(ipc,'Path',lambda unused:NS(parent=NS(stat=lambda:NS(st_uid=0,st_mode=0)))), \
             patch.object(ipc.socket,'socket',lambda *unused:Client()):
            g._connected_loop()
        grants=[b for b in sent if struct.unpack_from('<I',b,104)[0]==4]
        self.assertEqual(len(grants),1)
        self.assertIsNone(g.initial_pending)
        self.assertEqual(grants[0][128:],b'b'*32)

class AtomicSnapshotClock(unittest.TestCase):
    def test_new_snapshot_after_loop_start_is_fresh_at_read(self):
        g=ipc.OpenerGateway.__new__(ipc.OpenerGateway)
        g.lock=threading.Lock();g.snapshot={'generated':10.02}
        with patch.object(ipc.time,'monotonic',return_value=10.03):
            observed=g.read_snapshot(10.0)
        self.assertEqual(observed['observed_at'],10.03)
        self.assertEqual(observed['generated'],10.02)

    def test_actual_future_and_stale_snapshots_are_rejected(self):
        g=ipc.OpenerGateway.__new__(ipc.OpenerGateway)
        g.lock=threading.Lock()
        for generated in (10.04,9.0):
            g.snapshot={'generated':generated}
            with patch.object(ipc.time,'monotonic',return_value=10.03):
                self.assertIsNone(g.read_snapshot(10.0))

class IpcReceivePolling(unittest.TestCase):
    def run_loop(self, arrivals, *, send_error=False):
        g=ipc.OpenerGateway.__new__(ipc.OpenerGateway)
        g.path='/private/ipc';g.lock=threading.Lock();g.stop=threading.Event()
        g.runtime_session='a'*32;g.writes_enabled=True;g.sent=set()
        g.health=(True,False,10.0);g.pending=None;g.initial_pending=None
        g.snapshot=None;g.error=None
        clock=[10.0];sent=[];events=iter(arrivals)
        class Client:
            def __enter__(self):return self
            def __exit__(self,*unused):pass
            def settimeout(self,*unused):pass
            def connect(self,*unused):pass
            def getsockopt(self,*unused):return struct.pack('3i',1,0,0)
            def recv(self,*unused):
                when,kind=next(events);clock[0]=when
                if kind=='timeout':raise ipc.socket.timeout('poll')
                if kind=='eof':return b''
                if kind=='stop':g.stop.set()
                b=bytearray(160);b[:8]=b'EAI1\x03\0\x01\0'
                struct.pack_into('<QIIddd',b,8,1,1,0,when,when,0)
                struct.pack_into('<7I',b,48,15,10,0,0,0,0,0)
                return bytes(b)
            def sendall(self,b):
                sent.append(b)
                if send_error:raise ipc.socket.timeout('ambiguous send')
        with ExitStack() as stack:
            for name,value in (('SOCK_SEQPACKET',5),('AF_UNIX',1),('SO_PEERCRED',17)):
                stack.enter_context(patch.object(ipc.socket,name,value,create=True))
            stack.enter_context(patch.object(ipc.os,'geteuid',lambda:0,create=True))
            stack.enter_context(patch.object(ipc,'Path',lambda unused:NS(parent=NS(stat=lambda:NS(st_uid=0,st_mode=0)))))
            stack.enter_context(patch.object(ipc.socket,'socket',lambda *unused:Client()))
            stack.enter_context(patch.object(ipc.time,'monotonic',lambda:clock[0]))
            g._connected_loop()
        return g,sent

    def test_short_receive_timeout_does_not_disconnect_or_send_health(self):
        g,sent=self.run_loop([(10.01,'frame'),(10.12,'timeout'),(10.16,'stop')])
        self.assertEqual(len(sent),2) # No heartbeat fabricated during timeout.
        self.assertEqual(g.snapshot['generated'],10.16)
        self.assertIsNone(g.error)

    def test_repeated_timeouts_expire_since_last_valid_snapshot(self):
        with self.assertRaisesRegex(ValueError,'IPC_SNAPSHOT_TIMEOUT'):
            self.run_loop([(10.01,'frame'),(10.12,'timeout'),(10.30,'timeout'),(10.52,'timeout')])

    def test_no_first_snapshot_is_also_bounded(self):
        with self.assertRaisesRegex(ValueError,'IPC_SNAPSHOT_TIMEOUT'):
            self.run_loop([(10.1,'timeout'),(10.51,'timeout')])

    def test_send_timeout_is_not_treated_as_receive_poll_or_retried(self):
        with self.assertRaisesRegex(ipc.socket.timeout,'ambiguous send'):
            self.run_loop([(10.01,'frame')],send_error=True)

    def test_peer_eof_still_fails_immediately(self):
        with self.assertRaisesRegex(ValueError,'IPC_SCHEMA_INVALID'):
            self.run_loop([(10.01,'eof')])
