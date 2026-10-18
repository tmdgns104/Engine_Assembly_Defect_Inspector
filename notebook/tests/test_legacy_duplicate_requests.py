"""Request bounce cannot create a second product or stop acquisition.

In-memory PLC only. Request OFF still invalidates output because the installed
ladder does not distinguish sensor clearance from a physical Stop.
"""
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock

from notebook.tests import test_legacy_standalone as fixtures
from src.runtime.production import ProductionRuntime


class DuplicateRequestTests(unittest.TestCase):
    def start(self):
        return fixtures.ExistingPlcCompatibilityTests().start_request()

    def test_held_high_is_one_inspection_and_one_result(self):
        g, h, events = self.start()
        token = h.token
        for t in range(2, 40):
            h.poll(t)
        h.publish('actual-inspection', 'FAIL', True, 40)
        for t in range(41, 45):
            h.poll(t)
        self.assertEqual(h.token, token)
        self.assertEqual(sum(e['event'] == 'PLC_REQUEST_LATCHED' for e in events), 1)
        self.assertEqual(g.writes, [('Jetson_Result', True), ('Jetson_Done', True)])

    def test_bounce_holds_only_current_cycle_and_never_reuses_result(self):
        g, h, events = self.start()
        token = h.token
        for t, level in enumerate([False, True, False, True], 2):
            g.request = level
            h.poll(t)
        h.publish('actual-inspection', 'PASS', True, 6)
        self.assertEqual(h.state, 'WAIT_PRODUCT_CLEAR')
        self.assertEqual(h.token, token)
        self.assertEqual(h.status()['duplicate_requests_ignored'], 2)
        self.assertEqual(g.writes, [])
        self.assertFalse(any(e['event'] == 'PLC_FAULT' for e in events))
        self.assertFalse(h.release_cleared_cycle(product_clear=True))  # Still high.

    def test_clearance_low_and_done_low_all_required_to_rearm(self):
        g, h, events = self.start()
        old = h.token
        g.request = False
        h.poll(2)
        self.assertFalse(h.release_cleared_cycle(product_clear=False))
        g.done = True
        self.assertFalse(h.release_cleared_cycle(product_clear=True))
        g.done = False
        self.assertTrue(h.release_cleared_cycle(product_clear=True))
        self.assertEqual(h.state, 'ARMED')
        self.assertIsNone(h.token)
        self.assertEqual(g.writes, [])
        g.request = True
        h.poll(3)
        self.assertNotEqual(h.token, old)
        with self.assertRaises(ValueError):
            h.publish('actual-inspection', 'PASS', True, 4)
        self.assertEqual(g.writes, [])

    def test_done_cleared_duplicate_waits_for_visual_departure(self):
        g, h, events = self.start()
        token = h.token
        h.publish('actual-inspection', 'PASS', True, 2)
        g.request = False
        h.poll(3)
        self.assertEqual(h.state, 'WAIT_PRODUCT_CLEAR')
        g.request = True
        h.poll(4)
        self.assertEqual(h.token, token)
        self.assertEqual(h.status()['duplicate_requests_ignored'], 1)
        self.assertEqual(g.writes, [('Jetson_Result', False), ('Jetson_Done', True),
                                    ('Jetson_Done', False)])
        self.assertFalse(h.release_cleared_cycle(product_clear=False))

    def test_request_drops_between_result_and_done_remains_transport_fault(self):
        g, h, events = self.start()
        original = g.write_result
        def write(value):
            reply = original(value)
            g.request = False
            return reply
        g.write_result = write
        h.publish('actual-inspection', 'PASS', True, 2)
        self.assertEqual(h.state, 'RESYNC_REQUIRED')
        self.assertEqual(g.writes, [('Jetson_Result', False)])
        self.assertFalse(h.release_cleared_cycle(product_clear=True))

    def test_link_loss_during_hold_is_not_silently_rearmed(self):
        g, h, events = self.start()
        g.request = False
        h.poll(2)
        g.connected = False
        h.poll(3)
        self.assertEqual(h.state, 'RESYNC_REQUIRED')
        self.assertEqual(g.writes, [])


class DuplicateRuntimeTests(unittest.TestCase):
    def runtime(self):
        r = fixtures.ExistingPlcRuntimeTests().runtime()
        r._clear = Mock(return_value=False)
        r.latest_packet = None
        r.area_observation = None
        return r

    def test_cancelled_cycle_keeps_acquisition_alive_on_repeated_edges(self):
        r = self.runtime()
        r._poll_plc(0)
        r.gateway.request = True
        r._poll_plc(1)
        token = r.handshake.token
        for t, value in enumerate([False, True, False, True], 2):
            r.gateway.request = value
            r._poll_plc(t)
        self.assertIsNone(r.error)
        self.assertTrue(r.operating)
        r._fault.assert_not_called()
        self.assertEqual(r.handshake.state, 'WAIT_PRODUCT_CLEAR')
        self.assertEqual(r.handshake.token, token)
        self.assertEqual(r.gateway.writes, [])
        with unittest.mock.patch.object(ProductionRuntime, '_trigger') as trigger:
            r._trigger(8)
            trigger.assert_not_called()

    def test_rearm_requires_post_withdrawal_clear_camera_evidence(self):
        r = self.runtime()
        r._poll_plc(0)
        r.gateway.request = True
        r._poll_plc(1)
        r.gateway.request = False
        r._poll_plc(2)
        r._clear.return_value = True
        r.latest_packet = {'monotonic_s':3}
        r.area_observation = {'first_clear_monotonic':1}
        r._poll_plc(3)
        self.assertEqual(r.handshake.state, 'WAIT_PRODUCT_CLEAR')
        r.area_observation['first_clear_monotonic'] = 3
        r._poll_plc(4)
        self.assertEqual(r.handshake.state, 'ARMED')
        self.assertEqual(r.gateway.writes, [])
        r._fault.assert_not_called()

    def test_cancelled_transaction_can_retire_only_without_worker_or_fault(self):
        r = self.runtime()
        r._poll_plc(0)
        r.gateway.request = True
        r._poll_plc(1)
        r.gateway.request = False
        r._poll_plc(2)
        r.bridge = NS(inspection_id='cancelled', phase='INSPECTION_RUNNING')
        r.published_ids = {'cancelled'}
        self.assertIsNone(r._area_transaction_block())
        r.service.active = {'inspection_id':'cancelled'}
        self.assertIsNotNone(r._area_transaction_block())
        r.service.active = None
        r.service.error = 'CAMERA_FAULT'
        self.assertIsNotNone(r._area_transaction_block())


if __name__ == '__main__':
    unittest.main()
