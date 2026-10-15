"""Latest-image reads must not execute status, Journal or camera work."""
import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'jetson'))
from apps.edge_service.inspection import InspectionService
from apps.edge_service.inspection_api import create_app
from notebook.tests.supervised_asgi_fixture import LocalAsgiClient


class PreviewSnapshot(unittest.TestCase):
    def setUp(self):
        self.s = InspectionService.__new__(InspectionService)
        self.s.lock = threading.RLock()
        self.s.process = NS(is_alive=lambda: True)
        self.s.generation = 'g1'
        self.s.state = 'BUSY'
        self.s.preview_received = 99.95
        self.s.preview = dict(generation='g1', jpeg=b'annotated', jpeg_no_slots=b'plain',
            freshness=dict(frame_id='epoch-7', sequence=7, camera_epoch='epoch',
                estimated_source_monotonic=99.8, source_time='original source time'))
        self.s.status = Mock(side_effect=AssertionError('heavy status must not run'))
        self.s.journal = Mock(side_effect=AssertionError('no DB in preview'))

    def snapshot(self):
        with patch('apps.edge_service.inspection.time.monotonic', return_value=100):
            return self.s.preview_snapshot()

    def test_busy_latest_image_and_identity_are_one_snapshot(self):
        p = self.snapshot()
        self.assertEqual(p['jpeg_no_slots'], b'plain')
        self.assertEqual(p['freshness']['frame_id'], 'epoch-7')
        self.assertAlmostEqual(p['frame_age_ms'], 200)
        self.assertAlmostEqual(p['received_age_ms'], 50)
        self.s.preview['freshness']['frame_id'] = 'epoch-8'
        self.assertEqual(p['freshness']['frame_id'], 'epoch-7')
        self.s.status.assert_not_called()

    def test_dead_stale_recovery_and_wrong_generation_are_unavailable(self):
        for name, value in [('state', 'RECOVERY'), ('state', 'STOPPED'),
                            ('preview_received', 97), ('preview_received', 101),
                            ('generation', 'g2'), ('preview', None),
                            ('process', NS(is_alive=lambda: False))]:
            old = getattr(self.s, name)
            setattr(self.s, name, value)
            self.assertIsNone(self.snapshot(), name)
            setattr(self.s, name, old)
        for source in [97, 101, float('nan')]:
            self.s.preview['freshness']['estimated_source_monotonic'] = source
            self.assertIsNone(self.snapshot(), source)

    def test_api_uses_snapshot_only_and_skips_duplicate_jpeg(self):
        p = self.snapshot()
        self.s.preview_snapshot = Mock(return_value=p)
        with LocalAsgiClient(create_app(self.s, None)) as client:
            r = client.get('/api/v1/preview.jpg')
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.text, 'annotated')
            self.assertEqual(r.headers['x-frame-id'], 'epoch-7')
            self.assertAlmostEqual(float(r.headers['x-frame-age-ms']), 200, places=2)
            r = client.get('/api/v1/preview.jpg', headers={'if-none-match': r.headers['etag']})
            self.assertEqual(r.status_code, 304)
            self.assertEqual(r.text, '')
            self.s.preview_snapshot.return_value = None
            self.assertEqual(client.get('/api/v1/preview.jpg').status_code, 503)
        self.s.status.assert_not_called()


if __name__ == '__main__':
    unittest.main()
