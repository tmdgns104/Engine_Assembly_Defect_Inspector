"""Completed raw evidence owns publication; preview is not a second inspection."""
import copy
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch

from notebook.tests import test_automatic_runtime as fixture
from notebook.tests.test_full_frame_request import packet
from src.runtime.completed_evidence import validate_completed_evidence


class CompletedPublicationTests(unittest.TestCase):
    setUp = fixture.AutomaticRuntimeTests.setUp
    observe = fixture.AutomaticRuntimeTests.observe
    trigger = fixture.AutomaticRuntimeTests.trigger
    complete = fixture.AutomaticRuntimeTests.complete
    frame = fixture.AutomaticRuntimeTests.frame
    poll = fixture.AutomaticRuntimeTests.poll
    request_and_complete = fixture.AutomaticRuntimeTests.request_and_complete

    def test_durable_PASS_and_FAIL_survive_preview_miss_and_publish_once(self):
        original = self.j.commit_integrated
        def commit(final):
            original(final)
            # Same request/track and fresh stream, one absent envelope detection
            # between final fsync and the Runtime polling its completion.
            self.r.latest_packet = packet(999, self.now+self.at+.04, count=0)
        with patch.object(self.j, 'commit_integrated', side_effect=commit):
            for number, decision in enumerate(('PASS', 'FAIL'), 1):
                identifier = self.request_and_complete(number, decision)
                self.assertEqual(self.r.history[0]['inspection_id'], identifier)
                self.assertEqual(self.r.history[0]['decision'], decision)
                self.r._poll_result(self.now+self.at+.1)
                self.assertEqual(self.g.result.call_count, number)

    def test_current_camera_failure_still_blocks_after_final_storage(self):
        original = self.j.commit_integrated
        def commit(final):
            original(final)
            self.service.health = lambda: dict(ready=False,camera_ready=False,state='IDLE',error=None)
        with patch.object(self.j, 'commit_integrated', side_effect=commit):
            with self.assertRaisesRegex(ValueError, 'CAMERA'):
                self.request_and_complete(1, 'PASS')
        self.g.result.assert_not_called()

    def test_durable_result_with_missing_raw_frame_never_publishes(self):
        original = self.j.detail
        def detail(identifier):
            row = original(identifier)
            if row and row['state'] == 'COMPLETE':
                row = copy.deepcopy(row)
                row['result']['assets'] = row['result']['assets'][:2]
            return row
        with patch.object(self.j, 'detail', side_effect=detail):
            with self.assertRaisesRegex(ValueError, 'COMPLETED_EVIDENCE'):
                self.request_and_complete(1, 'PASS')
        self.g.result.assert_not_called()

    def test_preview_gap_after_durable_inspection_is_diagnostic(self):
        original = self.j.commit_integrated
        def commit(final):
            original(final)
            self.r.latest_packet = packet(999, self.now+self.at+.04, count=0)
            self.r._observation_issue('PRODUCT_OBSERVATION_GAP')
        with patch.object(self.j, 'commit_integrated', side_effect=commit):
            self.request_and_complete(1, 'PASS')
        self.assertIsNone(self.r.cycle_issue)
        self.assertEqual(self.r.issue['scope'], 'COMPLETED_INSPECTION_PREVIEW')
        self.assertEqual(self.g.result.call_count, 1)

    def test_evidence_identity_order_integrity_and_duplicates_fail_closed(self):
        identifier = self.request_and_complete(1, 'PASS')
        original = self.j.detail(identifier)
        binding = original['request']['runtime_binding']
        mutators = {
            'wrong inspection': lambda r: r['result'].update(inspection_id='other'),
            'wrong request': lambda r: r['result']['production_identity'].update(plc_request_token='other'),
            'wrong generation': lambda r: r['result']['execution'].update(worker_generation='other'),
            'wrong package': lambda r: r['request'].update(package_sha256='other'),
            'not durable': lambda r: r['result'].update(storage_success=False),
            'missing frame': lambda r: r['result']['observations'].pop(),
            'prior frame': lambda r: r['result']['observations'][0]['freshness'].update(estimated_source_monotonic=0.),
            'changed epoch': lambda r: r['result']['observations'][0]['freshness'].update(camera_epoch='other'),
            'corrupt frame': lambda r: r['result']['observations'][0]['freshness']['integrity'].update(valid=False),
            'duplicate pixels': lambda r: r['result']['observations'][1].update(input_pixel_sha256=r['result']['observations'][0]['input_pixel_sha256']),
            'duplicate source': lambda r: r['result']['assets'][1].update(sha256=r['result']['assets'][0]['sha256']),
            'wrong asset owner': lambda r: r['result']['assets'][0].update(inspection_id='other'),
            'failed association': lambda r: r['result']['production_frame_checks'][0].update(failed_conditions=['WRONG_PRODUCT']),
        }
        for name, mutate in mutators.items():
            with self.subTest(name=name):
                row = copy.deepcopy(original); mutate(row)
                with self.assertRaisesRegex(ValueError, 'COMPLETED_EVIDENCE'):
                    validate_completed_evidence(row, binding, identifier,
                        binding['request_accepted_monotonic'], self.now+self.at+1, 'sha')

    def test_post_storage_request_or_identity_changes_cannot_send(self):
        mutators = {
            'cancel': lambda: setattr(self.r.handshake, 'cancelled', True),
            'token': lambda: setattr(self.r.handshake, 'token', 'other'),
            'generation': lambda: setattr(self.service, 'generation', 'other'),
            'epoch': lambda: setattr(self.r, 'epoch', 'other'),
            'health epoch': lambda: setattr(self.service, 'health', lambda: dict(
                camera_ready=True,worker_alive=True,camera_epoch='other',state='IDLE')),
            'dead worker': lambda: setattr(self.service, 'health', lambda: dict(
                camera_ready=True,worker_alive=False,camera_epoch='e',state='IDLE')),
            'cycle': lambda: setattr(self.r, 'coordinator', NS(active_cycle=None,
                _tracker=self.r.coordinator._tracker)),
            'track': lambda: setattr(self.r.coordinator._tracker, '_track_id', 777),
            'stop': lambda: self.g.s['controls'].update(Mc_Run=False),
            'estop': lambda: self.g.s['controls'].update(EStop_OK=False),
            'disconnect': lambda: self.g.s.update(connected=False),
            'stale': lambda: self.g.s.update(fresh=False),
            'boot': lambda: self.g.s.update(boot=99),
        }
        for name, mutate in mutators.items():
            with self.subTest(name=name):
                self.setUp()
                original = self.j.commit_integrated
                def commit(final):
                    original(final); mutate()
                with patch.object(self.j, 'commit_integrated', side_effect=commit) as committed:
                    try:
                        self.request_and_complete(1, 'PASS')
                    except ValueError as error:
                        expected = ('CYCLIC_FINAL_CONTEXT_MISMATCH' if name in ('generation','epoch') else
                            'CYCLIC_FINAL_CAMERA_UNAVAILABLE' if name in ('health epoch','dead worker') else
                            'CYCLIC_FINAL_PRODUCT_CHANGED' if name in ('cycle','track') else
                            'CYCLIC_FINAL_CONTROL_CONTEXT_INVALID')
                        self.assertEqual(str(error),expected)
                    self.assertEqual(committed.call_count, 1, 'Fixture must reach final durability')
                self.g.result.assert_not_called()


if __name__ == '__main__':
    unittest.main()
