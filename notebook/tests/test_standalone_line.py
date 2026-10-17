"""Serial line contract tests; these never open a camera or real PLC."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'jetson'))
from src.control.standalone_plc import LineHandshake, TAGS, LineGateway
from src.control.production_plc import IoResult
from src.vision.integrated_decision import combine_decisions
from notebook.tests.assembly_result_fixture import assembly_result


class MemoryPLC:
    contract_version = 'STANDALONE_V3'
    backend = 'OMRON_CIP_BENCH'
    def __init__(self):
        self.values = {k: False if kind == 'BOOL' else 0 for k, (kind, _) in TAGS.items()}
        self.values['PLC_NoPusherMode'] = True
        self.writes = []
        self.fail = None
    def probe_contract(self): return dict(self.values)
    def read_inputs(self): return dict(self.values)
    def write(self, name, value):
        self.writes.append((name, value))
        if name == self.fail: return IoResult('UNKNOWN', error='lost ACK')
        self.values[name] = value
        if name == 'Jetson_SessionId':
            self.values.update(PLC_SessionEcho=value, PLC_RunPermit=False, Inspection_Request=False)
        return IoResult('ACK', value)


class LineTests(unittest.TestCase):
    def line(self):
        self.plc, self.events = MemoryPLC(), []
        h = LineHandshake(self.plc, self.events.append, session_id=7)
        h.service_tick(0, ready=True, product_clear=True)
        h.service_tick(1, ready=True, product_clear=True)
        self.assertEqual(h.state, 'ARMED')
        return h
    def request(self, h, identifier=1):
        self.plc.values.update(PLC_RunPermit=True, PLC_CycleId=identifier, Inspection_Request=True)
        h.service_tick(2, ready=True, product_clear=False)
        self.assertIsNotNone(h.token)
        h.bind('a' * 32)
    def test_one_cycle_repeated_request_never_reinspects_or_republishes(self):
        h = self.line(); self.request(h); token = h.token
        for t, high in enumerate([True, False, True, True, False, True], 3):
            self.plc.values['Inspection_Request'] = high
            h.service_tick(t, ready=False, product_clear=False)
            self.assertEqual(h.token, token)
        h.publish('a' * 32, 'REVIEW', True, 10)
        h.publish('a' * 32, 'REVIEW', True, 11)
        self.assertEqual(self.plc.writes.count(('Jetson_Done', True)), 1)
        self.assertEqual(self.plc.values['Jetson_ResultCode'], 3)
    def test_request_off_is_not_ack_and_same_id_cannot_be_reused(self):
        h = self.line(); self.request(h); h.publish('a' * 32, 'PASS', True, 3)
        self.plc.values['Inspection_Request'] = False
        h.service_tick(4, ready=False, product_clear=True)
        self.assertEqual(h.state, 'WAIT_REQUEST_OFF')
        self.plc.values['PLC_AckCycleId'] = 1
        h.service_tick(5, ready=True, product_clear=True)
        self.assertEqual(h.state, 'ARMED')
        self.plc.values['Inspection_Request'] = True
        h.service_tick(6, ready=True, product_clear=True)
        self.assertIsNone(h.token)
        self.assertNotEqual(h.state, 'REQUEST_LATCHED')
    def test_stop_cancels_and_late_result_is_not_published(self):
        h = self.line(); self.request(h)
        self.plc.values['PLC_RunPermit'] = False
        h.service_tick(3, ready=False, product_clear=False)
        h.publish('a' * 32, 'PASS', True, 4)
        self.assertNotIn(('Jetson_Done', True), self.plc.writes)
    def test_lost_write_ack_never_sends_done_or_retries(self):
        h = self.line(); self.request(h); self.plc.fail = 'Jetson_ResultCode'
        h.publish('a' * 32, 'FAIL', True, 3)
        count = len(self.plc.writes)
        h.service_tick(4, ready=True, product_clear=True)
        h.publish('a' * 32, 'FAIL', True, 4)
        self.assertEqual(len(self.plc.writes), count)
        self.assertNotIn(('Jetson_Done', True), self.plc.writes)
    def test_boot_residual_run_is_not_an_automatic_start(self):
        self.plc, self.events = MemoryPLC(), []
        self.plc.values.update(PLC_RunPermit=True, Inspection_Request=True, PLC_CycleId=9)
        h = LineHandshake(self.plc, self.events.append, session_id=8)
        h.service_tick(0, ready=False, product_clear=False)
        self.assertIsNone(h.token)
        self.assertFalse(self.plc.values['Jetson_Ready'])
        self.assertFalse(self.plc.values['PLC_RunPermit'])
    def test_pusher_or_wrong_mode_blocks_ready(self):
        h = self.line(); self.plc.values['Pusher_Forward'] = True
        h.service_tick(2, ready=True, product_clear=True)
        self.assertFalse(self.plc.values['Jetson_Ready'])
    def test_motor_and_plc_owned_writes_are_unaddressable(self):
        g = LineGateway('192.0.2.1', '192.0.2.2')
        for name in ('CV_Run', 'Pusher_Forward', 'PLC_RunPermit', 'Inspection_Request'):
            with self.assertRaises(ValueError): g.write(name, True)


class FinalDecisionTests(unittest.TestCase):
    def test_basic_pass_with_optional_assembly_uncertainty(self):
        for a in ('PASS', 'FAIL', 'REVIEW', 'ERROR'):
            for b in ('PASS_CANDIDATE', 'FAIL_CANDIDATE', 'REVIEW', 'ERROR'):
                result = combine_decisions(a, assembly_result(b))
                self.assertEqual(result['decision'] == 'PASS', a == 'PASS')
    def test_missing_or_failed_assembly_cannot_default_pass(self):
        for value in ({}, {'state': 'NOT_RUN'}, {'state': 'ERROR'}, {'state': 'COMPLETE'}):
            self.assertIn(combine_decisions('PASS', value)['decision'], ('ERROR', 'REVIEW'))
    def test_only_basic_defect_changes_final_pass_fail(self):
        self.assertEqual(combine_decisions('FAIL', assembly_result('PASS_CANDIDATE'))['decision'], 'FAIL')
        self.assertEqual(combine_decisions('PASS', assembly_result('FAIL_CANDIDATE'))['decision'], 'PASS')

if __name__ == '__main__': unittest.main()
