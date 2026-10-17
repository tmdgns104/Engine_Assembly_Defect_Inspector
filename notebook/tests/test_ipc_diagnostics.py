"""Local diagnostic evidence survives reconnect without retaining identities."""
import threading
import struct
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch
from src.control.opener_cyclic import OpenerGateway
from src.runtime.health_diagnostics import HealthDiagnostics


class IpcDiagnosticsTests(unittest.TestCase):
    def one_result_exchange(self, *, age=0.05, ready=True, context=(1,2,3),
                            phase='REQUEST_RECEIVED', send_error=False):
        """One deterministic IPC iteration, without network or actual PLC writes."""
        g=OpenerGateway.__new__(OpenerGateway)
        g.path='isolated-fixture/ipc'; g.runtime_session='a'*32
        g.lock=threading.Lock(); g.stop=Mock()
        g.stop.is_set.side_effect=[False,True]
        g.health=(ready,False,9.99); g.writes_enabled=True
        g.ready_reason='TEST'; g.initial_pending=None; g.sent=set()
        g.pending=(context,'b'*32,'PASS',10-age)
        g.diagnostics=HealthDiagnostics()
        snapshot=dict(boot=1,connection=2,request_id=3,generated=10,
                      phase=phase,reason='',approval_id='')
        client=Mock()
        client.__enter__=Mock(return_value=client)
        client.__exit__=Mock(return_value=False)
        client.getsockopt.return_value=struct.pack('3i',123,123,123)
        if send_error: client.sendall.side_effect=[None,OSError('fixture ambiguous send')]
        with ExitStack() as stack:
            for name,value in [('socket.socket',Mock(return_value=client)),
                               ('socket.AF_UNIX',1),('socket.SOCK_SEQPACKET',5),('socket.SO_PEERCRED',17),
                               ('os.geteuid',Mock(return_value=123)),
                               ('Path.stat',Mock(return_value=SimpleNamespace(st_uid=123,st_mode=0o700))),
                               ('time.monotonic',Mock(return_value=10)),
                               ('decode_snapshot',Mock(return_value=snapshot))]:
                stack.enter_context(patch('src.control.opener_cyclic.'+name,value,create=True))
            if send_error:
                with self.assertRaises(OSError):g._connected_loop()
            else:g._connected_loop()
        return g,client

    def test_queued_result_without_valid_context_is_not_transmitted_or_counted(self):
        for kwargs in ({'age':.401},{'ready':False},{'context':(9,2,3)},
                       {'context':(1,9,3)},{'context':(1,2,4)}, {'phase':'DISARMED'}):
            with self.subTest(kwargs=kwargs):
                g,client=self.one_result_exchange(**kwargs)
                self.assertIsNone(g.pending)
                self.assertFalse(g.sent)
                self.assertEqual(client.sendall.call_count,1)  # Only health, no result.
                self.assertEqual(struct.unpack_from('<I',client.sendall.call_args.args[0],104)[0],1)

    def test_socket_write_is_not_c_acceptance_or_plc_completion(self):
        g,client=self.one_result_exchange()
        self.assertEqual(client.sendall.call_count,2)
        self.assertEqual(g.sent,{(1,2,3)})
        self.assertEqual(g.snapshot['phase'],'REQUEST_RECEIVED')
        self.assertIsNone(g.pending)
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):
            g.result(g.snapshot,'b'*32,'PASS')

    def test_ambiguous_result_send_escapes_for_connection_loss_handler(self):
        g,client=self.one_result_exchange(send_error=True)
        self.assertEqual(client.sendall.call_count,2)
        self.assertFalse(g.sent)
        # _run connection loss handler discards this pending item; separate test
        # below checks that it cannot be replayed on a different connection.
        self.assertIsNotNone(g.pending)

    def test_snapshot_timeout_reason_survives_clearing_pending(self):
        g=OpenerGateway.__new__(OpenerGateway)
        g.lock=threading.Lock();g.stop=threading.Event()
        g.diagnostics=HealthDiagnostics();g.snapshot={'generated':9}
        g.last_valid_snapshot_at=9;g.last_snapshot_receive_at=9.01
        g.pending=('private-token',);g.initial_pending=('private-approval',)
        def disconnected():
            g.stop.set()
            raise ValueError('IPC_SNAPSHOT_TIMEOUT')
        g._connected_loop=disconnected
        g._run()
        event=g.diagnostics.snapshot()['latest']['IPC_CONNECTION_LOST']
        self.assertEqual(event['reason'],'IPC_SNAPSHOT_TIMEOUT')
        self.assertEqual(event['last_valid_snapshot'],9)
        self.assertIsNone(g.pending);self.assertIsNone(g.initial_pending)
        self.assertEqual(g.health,(False,False,0))
        self.assertNotIn('private',str(event))

    def test_bounded_diagnostics_and_no_sensitive_exception_text(self):
        g=OpenerGateway.__new__(OpenerGateway)
        g.lock=threading.Lock();g.stop=threading.Event();g.diagnostics=HealthDiagnostics(4)
        def disconnected():
            g.stop.set();raise OSError('secret path or token')
        g._connected_loop=disconnected;g._run()
        for i in range(20):g._diagnose('IPC_SNAPSHOT_RECEIVED',retain=False,interval_ms=i)
        report=g.diagnostics.snapshot()
        self.assertEqual(report['counts']['IPC_SNAPSHOT_RECEIVED'],20)
        self.assertEqual(len(report['events']),1)
        self.assertNotIn('secret',str(report))
