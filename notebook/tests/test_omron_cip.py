"""Focused three-BOOL CIP contract checks; no network or PLC writes."""
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'jetson'))

from src.control.omron_cip import CipError, OmronCipGateway
from src.control.production_plc import RequestHandshake


class OmronCipGatewayTests(unittest.TestCase):
    def setUp(self):
        self.gateway = OmronCipGateway.__new__(OmronCipGateway)
        self.gateway.last = {}
        self.gateway.socket = Mock()  # These tests replace the transport message method.

    def test_read_request_requires_bool_type_and_value(self):
        self.gateway._message = Mock(return_value=struct.pack('<HH', 0xC1, 0))
        self.assertEqual(self.gateway.read_request().value, False)
        self.gateway._message.assert_called_once_with(0x4C, 'Inspection_Request', b'\x01\x00')
        self.gateway._message.return_value = struct.pack('<HH', 0xC1, 2)
        self.assertEqual(self.gateway.read_request().status, 'FAILED')

    def test_write_result_checks_ack_and_readback(self):
        self.gateway._message = Mock(side_effect=[b'', struct.pack('<HH', 0xC1, 1)])
        self.assertEqual(self.gateway.write_result(True).status, 'ACK')
        self.assertEqual(self.gateway._message.call_args_list[0].args,
                         (0x4D, 'Jetson_Result', struct.pack('<HHH', 0xC1, 1, 1)))
        self.assertEqual(self.gateway._message.call_args_list[1].args,
                         (0x4C, 'Jetson_Result', b'\x01\x00'))

    def test_lost_write_ack_is_unknown_and_not_retried(self):
        self.gateway._message = Mock(side_effect=CipError('ACK_LOST'))
        self.assertEqual(self.gateway.write_done(True).status, 'UNKNOWN')
        self.assertEqual(self.gateway._message.call_count, 1)

    def test_readback_mismatch_is_unknown(self):
        self.gateway._message = Mock(side_effect=[b'', struct.pack('<HH', 0xC1, 0)])
        self.assertEqual(self.gateway.write_done(True).status, 'UNKNOWN')

    def test_only_result_and_done_are_writable(self):
        with self.assertRaisesRegex(ValueError, 'WRITE_TAG_NOT_ALLOWED'):
            self.gateway._write_bool('Inspection_Request', True)

    def test_existing_handshake_keeps_result_before_done(self):
        writes = []

        class Gateway:
            backend = 'OMRON_CIP_BENCH'

            def read_request(self):
                from src.control.production_plc import IoResult
                return IoResult('ACK', True)

            def write_result(self, value):
                from src.control.production_plc import IoResult
                writes.append(('Result', value))
                return IoResult('ACK', value)

            def write_done(self, value):
                from src.control.production_plc import IoResult
                writes.append(('Done', value))
                return IoResult('ACK', value)

        handshake = RequestHandshake(Gateway(), lambda event: None)
        handshake.state = 'INSPECTING'
        handshake.request = True
        handshake.token = 'cycle-1'
        handshake.inspection_id = 'inspection-1'
        handshake.publish('inspection-1', 'REVIEW', True, 10.0)
        self.assertEqual(writes, [('Result', True), ('Done', True)])
        self.assertEqual(handshake.state, 'WAIT_REQUEST_OFF')


if __name__ == '__main__':
    unittest.main()
