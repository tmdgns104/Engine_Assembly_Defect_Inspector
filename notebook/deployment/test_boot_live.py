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

    def test_runtime_rejects_high_or_unavailable_plc_before_auto(self):
        for reply in (IoResult('ACK', True), IoResult('FAILED')):
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


if __name__ == '__main__':
    main(verbosity=2)
