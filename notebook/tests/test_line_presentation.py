"""Field display semantics only; no camera, model, or PLC connections."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'jetson'))
from src.runtime.standalone_web import line_view


def status():
    return dict(line_state='WAIT_FIELD_PROFILE', error=None,
        inspection_service=dict(camera_ready=True, ready=True, state='IDLE'),
        latest_frame=dict(frame_id='fresh-10', sequence=10), stale_observation=False,
        plc=dict(available=True, state='ARMED', contract_version='LEGACY_THREE_BOOL',
                 network_plc_writes_enabled=False, Inspection_Request=False,
                 last_values=dict(Jetson_Result=False, Jetson_Done=False)),
        assembly_component=dict(ready=True), history=[], integrated_counts={})


class LinePresentationTests(unittest.TestCase):
    def test_preview_and_false_result_bit_never_become_pass(self):
        s = status(); original = copy.deepcopy(s)
        v = line_view(s, {})
        self.assertEqual(v['phase'], 'BLOCKED')
        self.assertEqual(v['title'], '검사 대기중')
        self.assertEqual(v['verdict'], 'NOT_RUN')
        self.assertIsNone(v['last_result'])
        self.assertFalse(v['plc']['publication_enabled'])
        self.assertEqual(v['plc']['result_bit'], False)
        self.assertEqual(s, original)

    def test_history_does_not_become_current_verdict(self):
        s = status()
        s['history'] = [dict(inspection_id='old', decision='PASS',
            source='INTEGRATED_ACTUAL_INSPECTION', synthetic=False,
            completed_at='2026-10-13T00:00:00Z', publication_status='ACKNOWLEDGED')]
        v = line_view(s, {})
        self.assertEqual(v['verdict'], 'NOT_RUN')
        self.assertEqual(v['last_result']['decision'], 'PASS')
        self.assertFalse(v['last_result']['plc_consumption_confirmed'])

    def test_current_inspection_and_progress_are_not_completed_result(self):
        s = status(); s['line_state'] = 'INSPECTING'
        s['plc'].update(state='INSPECTING', inspection_id='current', plc_request_token='r')
        s['inspection_service']['progress'] = dict(completed_frames=1, required_frames=3)
        v = line_view(s, {})
        self.assertEqual(v['phase'], 'INSPECTING')
        self.assertEqual(v['verdict'], 'PENDING')
        self.assertEqual(v['progress']['completed_frames'], 1)

    def test_camera_loss_and_old_pass_stay_separate(self):
        s = status(); s['latest_frame'] = None; s['stale_observation'] = True
        s['history'] = [dict(decision='PASS', source='INTEGRATED_ACTUAL_INSPECTION', synthetic=False)]
        v = line_view(s, {})
        self.assertFalse(v['camera']['fresh'])
        self.assertEqual(v['phase'], 'WAIT_CAMERA')
        self.assertNotEqual(v['verdict'], 'PASS')

    def test_false_fail_and_review_are_not_hidden(self):
        for d in ('FAIL', 'REVIEW', 'ERROR'):
            s = status()
            s['history'] = [dict(decision=d, source='INTEGRATED_ACTUAL_INSPECTION',
                synthetic=False, inspection_id='real', existing_inspector='PASS',
                assembly_inspector=d, publication_status='NOT_SENT')]
            v = line_view(s, {})
            self.assertEqual(v['last_result']['decision'], d)
            self.assertEqual(v['last_result']['assembly_inspector'], d)
            self.assertEqual(v['last_result']['publication_status'], 'NOT_SENT')

    def test_synthetic_history_is_not_actual_product_result(self):
        s = status(); s['history'] = [dict(decision='PASS', synthetic=True, source='SYNTHETIC_PROTOCOL_TEST')]
        self.assertIsNone(line_view(s, {})['last_result'])

    def test_legacy_readback_does_not_claim_consumption_or_motor_stop(self):
        s = status(); s['plc'].update(publication_status='ACKNOWLEDGED', plc_consumption_confirmed=True)
        v = line_view(s, {})
        self.assertFalse(v['plc']['consumption_confirmed'])
        self.assertEqual(v['motor_feedback'], 'UNVERIFIED')

    def test_withdrawn_request_is_hold_not_testing_or_pass(self):
        s = status(); s['line_state'] = 'LEGACY_REQUEST_WITHDRAWN_RESULT_BLOCKED'
        s['plc']['state'] = 'WAIT_PRODUCT_CLEAR'
        v = line_view(s, {})
        self.assertEqual(v['phase'], 'HOLD')
        self.assertEqual(v['verdict'], 'NOT_RUN')


if __name__ == '__main__':
    unittest.main()
