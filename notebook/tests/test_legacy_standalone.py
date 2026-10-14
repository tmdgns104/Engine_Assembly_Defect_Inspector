"""Existing PLC compatibility; these tests never connect to equipment."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace as NS
from collections import deque
import tempfile
from contextlib import closing
import base64
import socket

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'jetson'))
import standalone_service
from src.control import production_plc, omron_cip
from src.runtime.standalone import StandaloneRuntime
from src.runtime.production import ProductionRuntime
from src.journal.sqlite import Journal


class ExistingPlcCompatibilityTests(unittest.TestCase):
    def make_handshake(self):
        self.assertTrue(hasattr(production_plc, 'LegacyStandaloneHandshake'),
                        'Standalone runtime must support the existing three BOOL PLC')
        gateway = production_plc.MockPlcGateway()
        gateway.probe_contract = lambda: {
            'Inspection_Request': gateway.request,
            'Jetson_Result': gateway.result,
            'Jetson_Done': gateway.done}
        events = []
        handshake = production_plc.LegacyStandaloneHandshake(gateway, events.append)
        return gateway, handshake, events

    def start_request(self):
        gateway, handshake, events = self.make_handshake()
        handshake.poll(0)
        gateway.request = True
        handshake.poll(1)
        handshake.bind('actual-inspection')
        return gateway, handshake, events

    def test_select_existing_contract_without_silent_v3_fallback(self):
        self.assertTrue(hasattr(standalone_service, 'plc_contract'))
        self.assertEqual(standalone_service.plc_contract({}), 'STANDALONE_V3')
        self.assertEqual(standalone_service.plc_contract(
            {'plc_contract': 'LEGACY_THREE_BOOL'}), 'LEGACY_THREE_BOOL')
        with self.assertRaises(ValueError):
            standalone_service.plc_contract({'plc_contract': 'anything'})

    def test_active_listener_is_not_mistaken_for_closed_port(self):
        self.assertTrue(hasattr(standalone_service, 'check_port_available'))
        with socket.socket() as server:
            server.bind(('127.0.0.1', 0)); server.listen()
            with self.assertRaises(OSError):
                standalone_service.check_port_available('127.0.0.1', server.getsockname()[1])

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux deployment TIME_WAIT semantics')
    def test_time_wait_does_not_block_normal_service_restart(self):
        self.assertTrue(hasattr(standalone_service, 'check_port_available'))
        with socket.socket() as server:
            server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            server.bind(('127.0.0.1',0));server.listen()
            port=server.getsockname()[1]
            with socket.create_connection(('127.0.0.1',port),timeout=2) as client:
                connection,_=server.accept()
                connection.shutdown(socket.SHUT_WR);connection.close()
                self.assertEqual(client.recv(1),b'')
        # Reproduce the original startup failure before checking the fix.
        with socket.socket() as plain:
            with self.assertRaises(OSError): plain.bind(('127.0.0.1',port))
        standalone_service.check_port_available('127.0.0.1',port)

    def test_pass_fail_write_order_and_polarity(self):
        for decision, bit in [('PASS', False), ('FAIL', True)]:
            with self.subTest(decision=decision):
                gateway, handshake, events = self.start_request()
                handshake.publish('actual-inspection', decision, True, 2)
                self.assertEqual(gateway.writes,
                                 [('Jetson_Result', bit), ('Jetson_Done', True)])
                self.assertEqual(handshake.publication, 'ACKNOWLEDGED')
                self.assertFalse(handshake.status()['plc_consumption_confirmed'])
                self.assertEqual(handshake.status()['ack_scope'], 'WRITE_READBACK_ONLY')
                self.assertTrue(all(e['plc_consumption_confirmed'] is False for e in events))

    def test_review_error_have_no_bool_equivalent_and_write_nothing(self):
        for decision in ('REVIEW', 'ERROR'):
            gateway, handshake, _ = self.start_request()
            handshake.publish('actual-inspection', decision, True, 2)
            self.assertEqual(gateway.writes, [])
            self.assertEqual(handshake.state, 'WAIT_PRODUCT_CLEAR')
            self.assertIn('UNREPRESENTABLE', handshake.reason)

    def test_request_off_does_not_publish_late_pass(self):
        gateway, handshake, _ = self.start_request()
        gateway.request = False
        handshake.publish('actual-inspection', 'PASS', True, 2)
        self.assertEqual(gateway.writes, [])
        self.assertEqual(handshake.state, 'WAIT_PRODUCT_CLEAR')
        self.assertEqual(handshake.reason, 'LEGACY_REQUEST_WITHDRAWN_RESULT_BLOCKED')

    def test_request_chatter_does_not_create_second_result(self):
        gateway, handshake, _ = self.start_request()
        token = handshake.token
        gateway.request = False
        handshake.poll(2)
        gateway.request = True
        handshake.poll(3)
        handshake.publish('actual-inspection', 'PASS', True, 4)
        self.assertEqual(handshake.token, token)
        self.assertEqual(gateway.writes, [])

    def test_boot_residual_request_or_done_does_not_replay(self):
        for residual in ('request', 'done'):
            gateway, handshake, _ = self.make_handshake()
            setattr(gateway, residual, True)
            handshake.poll(0)
            self.assertEqual(handshake.state, 'RESYNC_REQUIRED')
            self.assertEqual(gateway.writes, [])

    def test_shutdown_blocks_late_result_without_changing_outputs(self):
        gateway, handshake, _ = self.start_request()
        handshake.shutdown()
        handshake.publish('actual-inspection', 'PASS', True, 3)
        self.assertTrue(handshake.cancelled)
        self.assertEqual(gateway.writes, [])

    def test_gateway_probes_only_existing_tags_and_diagnostic_mode_cannot_write(self):
        self.assertTrue(hasattr(omron_cip, 'LegacyStandaloneGateway'))
        gateway = omron_cip.LegacyStandaloneGateway('192.0.2.1', '192.0.2.2',
                                                  writes_enabled=False)
        read = []
        with patch.object(gateway, '_read_bool', side_effect=lambda tag: read.append(tag) or False):
            self.assertEqual(len(gateway.probe_contract()), 3)
        self.assertEqual(set(read), {'Inspection_Request', 'Jetson_Result', 'Jetson_Done'})
        with patch.object(gateway, '_message') as message:
            self.assertEqual(gateway.write_done(True).status, 'FAILED')
            self.assertEqual(gateway.write_result(False).status, 'FAILED')
            message.assert_not_called()

    def test_idle_reconnect_rechecks_residual_done(self):
        gateway, handshake, _ = self.make_handshake()
        handshake.poll(0)
        gateway.connected = False
        handshake.poll(1)
        gateway.connected = True
        gateway.done = True
        handshake.poll(2)
        self.assertEqual(handshake.state, 'RESYNC_REQUIRED')
        self.assertEqual(gateway.writes, [])

    def test_integrated_final_is_durable_and_assembly_remains_required(self):
        cases = [('PASS', 'PASS_CANDIDATE', 'PASS', False),
                 ('PASS', 'FAIL_CANDIDATE', 'FAIL', True),
                 ('FAIL', 'PASS_CANDIDATE', 'FAIL', True),
                 ('PASS', 'REVIEW', 'REVIEW', None),
                 ('ERROR', 'PASS_CANDIDATE', 'ERROR', None)]
        for existing, assembly, final, bit in cases:
            with self.subTest(existing=existing, assembly=assembly), tempfile.TemporaryDirectory() as folder, closing(Journal(Path(folder), min_free_bytes=0)) as journal:
                g, h, _ = self.make_handshake()
                g.contract_version = 'LEGACY_THREE_BOOL'
                h.poll(0); g.request = True; h.poll(1)
                request = dict(cell_id='test', plc_session_id=1, request_id=1, cycle_id=1,
                    attempt=1, runtime_binding={'plc_request_token':h.token})
                identifier, _ = journal.admit(request, {'manifest':{'product_id':'engine','release_id':'test'}})
                pixel = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aHioAAAAASUVORK5CYII=')
                journal.finish(identifier, {'decision':existing, 'reason':'synthetic unit fixture'},
                    images=[dict(kind='raw', data=pixel, width=1, height=1)])
                h.bind(identifier)
                r = StandaloneRuntime.__new__(StandaloneRuntime)
                r.service = NS(journal=journal)
                r.gateway, r.handshake, r.session_id = g, h, 'test-session'
                r.bridge = NS(inspection_id=identifier, poll=lambda:None, error=None, phase='INSPECTION_DURABLE')
                r.assembly = NS(submit=lambda row:None, evidence_path=lambda i:'test-evidence',
                    result=lambda i:dict(state='COMPLETE', three_frames={'state':assembly}))
                r.assembly_submitted, r.published_ids, r.history = {}, set(), deque()
                r.line_profile, r.error, r._event = {'assembly_deadline_s':30}, None, Mock()
                write = g._write
                def checked_write(tag, value):
                    self.assertIsNotNone(journal.db.execute('SELECT value FROM service_state WHERE key=?',
                        ('integrated_decision:'+identifier,)).fetchone())
                    return write(tag, value)
                g._write = checked_write
                r._poll_result(2)
                self.assertEqual(r.history[0]['decision'], final)
                self.assertFalse(r.history[0]['plc_consumption_confirmed'])
                self.assertEqual(g.writes, [] if bit is None else [('Jetson_Result',bit),('Jetson_Done',True)])


class ExistingPlcRuntimeTests(unittest.TestCase):
    def runtime(self):
        r = StandaloneRuntime.__new__(StandaloneRuntime)
        r.gateway = production_plc.MockPlcGateway()
        r.gateway.contract_version = 'LEGACY_THREE_BOOL'
        r.gateway.probe_contract = lambda: {'Inspection_Request':r.gateway.request,
            'Jetson_Result':r.gateway.result,'Jetson_Done':r.gateway.done}
        r.handshake = production_plc.LegacyStandaloneHandshake(r.gateway, lambda e: None)
        r.service = NS(active=None, generation='g')
        r.coordinator = NS(_tracker=NS(_track_id=None))
        r.assembly = NS(ready=True)
        r.epoch, r.next_plc_poll_at, r.arrival, r.error = 'camera', 0, None, None
        r.operating, r.eligible = True, False
        r._profile_ready = lambda: True
        r._event, r._cancel_pending, r._fault = Mock(), Mock(), Mock()
        r.line_profile = {'arrival_deadline_s':30}
        r.latest_packet = None
        return r

    def test_existing_request_acceptance_never_calls_v3_service_tick(self):
        self.assertTrue(hasattr(StandaloneRuntime, '_poll_legacy_plc'))
        r = self.runtime()
        r._poll_plc(0)
        r.gateway.request = True
        r._poll_plc(1)
        self.assertEqual(r.handshake.state, 'REQUEST_LATCHED')
        self.assertEqual(r.arrival['epoch'], 'camera')
        self.assertEqual(r.gateway.writes, [])
        self.assertIsNone(r.handshake.cycle_id)

    def test_legacy_trigger_requires_fresh_current_product_and_unchanged_stability(self):
        self.assertTrue(hasattr(StandaloneRuntime, '_trigger_legacy'))
        r = self.runtime()
        r.handshake.poll(0)
        r.gateway.request = True
        r.handshake.poll(1)
        r.arrival = dict(epoch='camera',generation='g',preexisting_track=None,track=None)
        r.zone = {'polygon_normalized':[[0,0],[1,0],[1,1],[0,1]]}
        r.coordinator._tracker._track_id = 'new-track'
        r.eligible = True
        p = dict(monotonic_s=2,camera_epoch='camera',generation='g',integrity={'valid':True},
                 stable=False, frame_id='fresh',provider={'observations':[{
                     'bbox':dict(x1=.2,y1=.2,x2=.8,y2=.8)}]})
        r.latest_packet = p
        with patch.object(ProductionRuntime, '_trigger') as trigger:
            r._trigger(2)
            trigger.assert_not_called()
            p['stable'] = True
            p['monotonic_s'] = .5
            r._trigger(2)
            trigger.assert_not_called()
            p['monotonic_s'] = 2
            r._trigger(2)
            trigger.assert_called_once()
        self.assertEqual(r.gateway.writes, [])  # No InPosition/motor/pusher writes.

    def test_profile_not_verified_does_not_start_inspection(self):
        self.assertTrue(hasattr(StandaloneRuntime, '_trigger_legacy'))
        r = self.runtime()
        r.handshake.poll(0)
        r.gateway.request = True
        r.handshake.poll(1)
        r._profile_ready = lambda: False
        with patch.object(ProductionRuntime, '_trigger') as trigger:
            r._trigger(2)
            trigger.assert_not_called()
        self.assertEqual(r.gateway.writes, [])


if __name__ == '__main__':
    unittest.main()
