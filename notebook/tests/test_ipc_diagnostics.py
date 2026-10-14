"""Local diagnostic evidence survives reconnect without retaining identities."""
import threading
import unittest
from unittest.mock import Mock
from src.control.opener_cyclic import OpenerGateway
from src.runtime.health_diagnostics import HealthDiagnostics


class IpcDiagnosticsTests(unittest.TestCase):
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
