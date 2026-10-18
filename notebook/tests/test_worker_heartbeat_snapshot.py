"""Concurrent pulse renewal must not look like a future or missing heartbeat."""
import os
from pathlib import Path
import sys
import threading
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

sys.path.insert(0, os.environ.get('ENGINE_HEALTH_TEST_SOURCE', str(Path(__file__).resolve().parents[2]/'jetson')))
from apps.edge_service.inspection import InspectionService
from src.runtime.health_diagnostics import HealthDiagnostics


class HeartbeatSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.clock = NS(now=10.0)
        self.service = InspectionService.__new__(InspectionService)
        self.service.__dict__.update(lock=threading.RLock(), process=NS(is_alive=lambda:True,pid=1),
            preview={'freshness':{'camera_epoch':'e'}}, preview_received=9.9,
            heartbeat=NS(value=10.0), error=None, state='IDLE', generation='g',
            calibration={'confirmed':True}, switching=False, storage_pending=None, active=None,
            journal=NS(root=Path(__file__).parent,min_free_bytes=0), health_diagnostics=HealthDiagnostics())

    def check(self):
        with patch('apps.edge_service.inspection.time.monotonic', lambda:self.clock.now):
            return self.service.health()

    def test_pulse_renewed_during_snapshot_is_healthy(self):
        clock = self.clock
        class RenewingHeartbeat:
            @property
            def value(self):
                clock.now += .001
                return clock.now
        self.service.heartbeat = RenewingHeartbeat()
        result = self.check()
        self.assertTrue(result['ready'], result)
        self.assertGreaterEqual(result['worker_heartbeat_age_s'], 0)

    def test_real_stale_heartbeat_still_blocks(self):
        self.service.heartbeat.value = 4.9
        self.assertEqual(self.check()['error'], 'WORKER_HEARTBEAT_LOST')

    def test_actual_future_heartbeat_still_blocks(self):
        self.service.heartbeat.value = 11.0
        self.assertEqual(self.check()['error'], 'WORKER_HEARTBEAT_LOST')


if __name__ == '__main__':
    unittest.main()
