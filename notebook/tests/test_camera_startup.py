"""Worker startup must not consume the camera driver's first-frame deadline."""
from queue import Queue
import unittest
from unittest.mock import Mock, patch

from training.capture_windows.camera import CameraClient


class CameraStartupTests(unittest.TestCase):
    def client(self):
        client = CameraClient()
        client.process = Mock()
        client.process.is_alive.return_value = True
        client.frames, client.events = Queue(), Queue()
        client.stop = Mock()
        client.state = 'connecting'
        client.started = 100.0
        client.stream_id = 'test'
        return client

    def test_starting_worker_has_its_own_bounded_deadline(self):
        client = self.client()
        with patch('training.capture_windows.camera.time.monotonic', return_value=116):
            client.poll()
        self.assertEqual(client.state, 'connecting')
        self.assertIsNone(client.deadline)
        with patch('training.capture_windows.camera.time.monotonic', return_value=131):
            client.poll()
        self.assertEqual(client.state, 'stopping')
        self.assertIn('실행 준비', client.error)
        client.stop.set.assert_called_once()

    def test_worker_ready_starts_fifteen_second_camera_deadline(self):
        client = self.client()
        client.events.put(('ready', 108.0))
        with patch('training.capture_windows.camera.time.monotonic', return_value=116):
            client.poll()
        self.assertEqual(client.state, 'connecting')
        self.assertEqual(client.worker_started, 108.0)
        self.assertEqual(client.error, '')
        with patch('training.capture_windows.camera.time.monotonic', return_value=124):
            client.poll()
        self.assertEqual(client.state, 'stopping')
        self.assertIn('연결 시간 초과', client.error)

    def test_worker_error_still_stops_without_waiting(self):
        client = self.client()
        client.events.put(('error', '선택한 장치 열기 실패'))
        with patch('training.capture_windows.camera.time.monotonic', return_value=101):
            client.poll()
        self.assertEqual(client.error, '선택한 장치 열기 실패')
        self.assertEqual(client.state, 'stopping')


if __name__ == '__main__':
    unittest.main()
