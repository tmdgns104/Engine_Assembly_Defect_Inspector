"""Focused boot gates; no camera, model, or PLC hardware is started."""
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch
from unittest.mock import Mock
import struct
import sys

JETSON = Path(__file__).resolve().parents[2] / 'jetson'
sys.path.insert(0, str(JETSON))

import boot_live
from boot_live import start_allowed
from src.control.omron_cip import OmronCipGateway
from src.control.production_plc import IoResult
from src.control.production_plc import MockPlcGateway, RequestHandshake
from src.runtime.production import ProductionRuntime
from src.runtime.production_profile import calibration_sha


def ready_status():
    return {
        'error': None, 'active_cycle': None, 'operating': False, 'phase': 'STOPPED',
        'auto_stop_requested': False,
        'inspection_service': {'ready': True, 'camera_ready': True, 'active_inspection_id': None},
        'plc': {'backend': 'OMRON_CIP_BENCH', 'physical_output_enabled': False,
                'available': True, 'Inspection_Request': False, 'state': 'SYNC_LOW'},
        'area_observation_valid': True,
        'area_occupancy': {'state': 'CLEAR', 'reference_valid': True},
        'inspection_zone': {'confirmed': True},
    }


class BootTests(TestCase):
    def test_only_empty_ready_request_low_can_arm(self):
        value = ready_status()
        self.assertEqual(start_allowed(value), (True, 'READY'))
        for path, key, bad in [
            ('plc', 'available', False), ('plc', 'Inspection_Request', True),
            ('inspection_service', 'camera_ready', False),
            ('area_occupancy', 'state', 'OCCUPIED'),
        ]:
            changed = ready_status()
            changed[path][key] = bad
            self.assertFalse(start_allowed(changed)[0])
        stopped = ready_status()
        stopped['auto_stop_requested'] = True
        self.assertEqual(start_allowed(stopped), (False, 'OPERATOR_STOP'))

    def test_development_mock_boot_requires_explicit_mode_and_empty_camera(self):
        value = ready_status()
        value['plc'].update(backend='MOCK', hardware_status='HARDWARE_NOT_VERIFIED')
        value['mock_auto_request_enabled'] = True
        self.assertEqual(start_allowed(value, mock_auto_request=True), (True, 'READY'))
        self.assertFalse(start_allowed(value)[0])
        value['area_occupancy']['state'] = 'OCCUPIED'
        self.assertFalse(start_allowed(value, mock_auto_request=True)[0])

    def test_real_plc_off_does_not_block_healthy_tracking_boot(self):
        value = ready_status()
        value['plc'].update(available=False, Inspection_Request=None, state='SYNC_LOW')
        self.assertEqual(start_allowed(value), (True, 'READY'))

    def test_unavailable_request_during_initial_sync_does_not_require_manual_resync(self):
        gateway = MockPlcGateway()
        gateway.connected = False
        handshake = RequestHandshake(gateway, lambda event: None)
        handshake.poll(1.)
        self.assertEqual(handshake.state, 'SYNC_LOW')
        gateway.connected = True
        handshake.poll(2.)
        self.assertEqual(handshake.state, 'ARMED')

    def test_idle_plc_loss_waits_for_a_fresh_low_but_inflight_loss_stays_blocked(self):
        gateway=MockPlcGateway(); handshake=RequestHandshake(gateway,lambda event:None)
        handshake.poll(1.)
        gateway.connected=False; handshake.poll(2.)
        self.assertEqual(handshake.state,'SYNC_LOW')
        gateway.connected=True; handshake.poll(3.)
        self.assertEqual(handshake.state,'ARMED')
        gateway.request=True; handshake.poll(4.)
        self.assertEqual(handshake.state,'REQUEST_LATCHED')
        gateway.connected=False; handshake.poll(5.)
        self.assertEqual(handshake.state,'RESYNC_REQUIRED')

    def test_gateway_is_lazy_and_reconnects_on_read_only(self):
        gateway = OmronCipGateway('192.168.50.3', '192.168.50.2')
        self.assertIsNone(gateway.socket)
        with patch.object(gateway, '_connect', side_effect=OSError('PLC off')):
            self.assertEqual(gateway.read_request().status, 'FAILED')
        self.assertIsNone(gateway.socket)
        connection = SimpleNamespace(close=lambda: None)
        with patch.object(gateway, '_connect', side_effect=lambda: setattr(gateway, 'socket', connection)):
            with patch.object(gateway, '_message', return_value=struct.pack('<HH', 0x00C1, 0)):
                self.assertEqual(gateway.read_request(), IoResult('ACK', False))

    def test_runtime_rejects_high_plc_before_auto(self):
        for reply in (IoResult('ACK', True),):
            handshake = SimpleNamespace(state='SYNC_LOW', request=None)
            runtime = SimpleNamespace(
                lock=nullcontext(), service=SimpleNamespace(lock=nullcontext(), active=None,
                    lab=SimpleNamespace(mode='MANUAL'), status=lambda: {'ready': True}, calibration={}),
                operating=False, error=None, coordinator=SimpleNamespace(active_cycle=None),
                zone={'confirmed': True, 'calibration_sha': calibration_sha({})},
                handshake=handshake, gateway=SimpleNamespace(backend='OMRON_CIP_BENCH',
                    read_request=lambda: reply), area_config_version=None)
            with self.assertRaisesRegex(ValueError, 'VALID_PLC_REQUEST_LOW_REQUIRED_AT_AUTO_START'):
                ProductionRuntime.start_auto(runtime)
            self.assertFalse(runtime.operating)
            self.assertEqual(handshake.state, 'SYNC_LOW')

    def test_runtime_starts_tracking_with_plc_off(self):
        handshake=SimpleNamespace(state='SYNC_LOW',request=None)
        service=SimpleNamespace(lock=nullcontext(),active=None,lab=SimpleNamespace(mode='MANUAL'),
            status=lambda:{'ready':True},calibration={},generation='worker',production_tracking=Mock())
        runtime=SimpleNamespace(lock=nullcontext(),service=service,operating=False,error=None,
            coordinator=SimpleNamespace(active_cycle=None),
            zone={'confirmed':True,'calibration_sha':calibration_sha({})},
            handshake=handshake,gateway=SimpleNamespace(backend='OMRON_CIP_BENCH',
                read_request=lambda:IoResult('FAILED')),area_config_version=None,
            observation_times=[],_reset_departure_candidate=Mock(),area_window=SimpleNamespace(reset=Mock()),
            _event=Mock(),auto_mock_request=False)
        runtime.status=lambda:{'operating':runtime.operating}
        self.assertTrue(ProductionRuntime.start_auto(runtime)['operating'])
        self.assertEqual(handshake.state,'SYNC_LOW')
        service.production_tracking.set.assert_called_once()

    def test_auto_post_uses_existing_session_token(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self): return b'{"operating":true}'

        with patch.object(boot_live.manage_live, 'api', return_value={'token': 'local-token'}):
            with patch.object(boot_live, 'urlopen', return_value=Response()) as send:
                self.assertTrue(boot_live.post_auto(18771)['operating'])
        request = send.call_args.args[0]
        self.assertEqual(request.get_header('X-inspection-token'), 'local-token')
        self.assertEqual(request.get_method(), 'POST')

    def test_operator_stop_cancels_pending_boot_arming(self):
        service = SimpleNamespace(lock=nullcontext(), active=None,
                                  production_tracking=Mock())
        runtime = SimpleNamespace(lock=nullcontext(), service=service,
                                  handshake=SimpleNamespace(state='ARMED'),
                                  coordinator=SimpleNamespace(active_cycle=None),
                                  auto_stop_requested=False, operating=False,
                                  _event=Mock())
        runtime.status = lambda: {'auto_stop_requested': runtime.auto_stop_requested}
        result = ProductionRuntime.stop_auto(runtime)
        self.assertTrue(result['auto_stop_requested'])
        self.assertEqual(runtime.phase, 'STOPPED')

    def test_mock_auto_request_is_once_per_track_and_off_only_after_done(self):
        events = []
        gateway = MockPlcGateway()
        handshake = RequestHandshake(gateway, events.append)
        tracker = SimpleNamespace(_track_id=1)
        runtime = SimpleNamespace(auto_mock_request=True, operating=True, error=None,
            coordinator=SimpleNamespace(_tracker=tracker), gateway=gateway,
            handshake=handshake, auto_requested_tracks=set(), auto_request_token=None,
            _event=events.append)
        packet = {'frame_id': 'real-frame-1', 'sequence': 1}
        ProductionRuntime._auto_request_for_track(runtime, packet)
        token = handshake.token
        self.assertEqual(handshake.state, 'REQUEST_LATCHED')
        self.assertEqual(runtime.auto_requested_tracks, {1})
        ProductionRuntime._auto_request_for_track(runtime, packet)
        self.assertEqual(handshake.token, token)
        handshake.inspection_id = 'durable-id'
        handshake.state = 'WAIT_REQUEST_OFF'
        handshake.publication = 'ACKNOWLEDGED'
        gateway.done = True
        ProductionRuntime._auto_request_off_after_done(runtime)
        self.assertFalse(gateway.request)
        self.assertFalse(gateway.done)
        self.assertEqual(handshake.state, 'ARMED')
        ProductionRuntime._auto_request_for_track(runtime, packet)
        self.assertFalse(gateway.request)
        tracker._track_id = 2
        ProductionRuntime._auto_request_for_track(runtime, {'frame_id': 'real-frame-2', 'sequence': 2})
        self.assertTrue(gateway.request)
        self.assertNotEqual(handshake.token, token)
        self.assertEqual(runtime.auto_requested_tracks, {1, 2})

    def test_mock_auto_request_does_not_acknowledge_failed_publication(self):
        gateway = MockPlcGateway()
        gateway.request = True
        gateway.done = True
        handshake = RequestHandshake(gateway, lambda _: None)
        handshake.state = 'RESYNC_REQUIRED'
        handshake.publication = 'UNKNOWN'
        handshake.token = 'unknown-token'
        runtime = SimpleNamespace(auto_mock_request=True, auto_request_token='unknown-token',
            handshake=handshake, gateway=gateway, _event=Mock())
        ProductionRuntime._auto_request_off_after_done(runtime)
        self.assertTrue(gateway.request)
        runtime._event.assert_not_called()


if __name__ == '__main__':
    main(verbosity=2)
