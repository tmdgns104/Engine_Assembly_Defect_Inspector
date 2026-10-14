"""Diagnostic observations must not fsync on the PLC health owner."""
import json
import tempfile
import time
import unittest
from contextlib import contextmanager
from types import SimpleNamespace as NS
from unittest.mock import patch

from src.journal.sqlite import Journal
from src.runtime.health_diagnostics import HealthDiagnostics
from src.runtime.standalone import StandaloneRuntime, AUTO_POLICY
from src.runtime.inspection_start import FULL_FRAME


@contextmanager
def saved_journal():
    with tempfile.TemporaryDirectory() as root:
        journal = Journal(root, min_free_bytes=0)
        try:
            yield journal
        finally:
            journal.close()


class ObservationIO(unittest.TestCase):
    def owner(self, journal):
        owner = object.__new__(StandaloneRuntime)
        owner.line_profile = {'cycle_admission': AUTO_POLICY, 'inspection_start_policy': FULL_FRAME}
        owner.gateway = NS(contract_version='OPENER_CYCLIC')
        owner.session_id = 'runtime-test'
        owner._diagnostic_events = None
        owner.service = NS(journal=journal, generation='worker-test',
                           health_diagnostics=HealthDiagnostics())
        return owner

    def test_tracking_diagnostics_never_wait_for_slow_sqlite_commit(self):
        with saved_journal() as journal:
            owner = self.owner(journal)
            original = journal._event
            def slow(*args):
                time.sleep(.5)  # Reproduce a normal slow fsync/checkpoint.
                return original(*args)
            start = time.monotonic()
            with patch.object(journal, '_event', side_effect=slow) as save:
                for event in ('VISION_PASSAGE_STARTED', 'PRODUCTION_TRACK_STATE',
                              'PRODUCTION_DEPARTURE_EDGE_ASSESSED'):
                    owner._event(dict(event=event, frame_id='frame-7', sequence=7))
            self.assertLess(time.monotonic()-start, .1)
            self.assertEqual(save.call_count, 0)
            self.assertEqual(journal.db.execute('SELECT count(*) FROM events').fetchone()[0], 0)
            trace = owner.service.health_diagnostics.snapshot()
            self.assertEqual(len(trace['events']), 3)
            self.assertEqual(trace['events'][-1]['frame_id'], 'frame-7')

    def test_request_result_exit_and_abort_evidence_remain_durable(self):
        with saved_journal() as journal:
            owner = self.owner(journal)
            events = ('PLC_REQUEST_TRACK_FROZEN', 'INTEGRATED_INSPECTION_COMPLETED',
                      'AUTOMATIC_PRODUCT_SEPARATED', 'LINE_CANCELLED_RESULT_BLOCKED')
            for event in events:
                owner._event(dict(event=event, inspection_id='inspection-test'))
            rows = journal.db.execute('SELECT event_type,payload_json FROM events ORDER BY rowid').fetchall()
            self.assertEqual(tuple(row[0] for row in rows), events)
            self.assertTrue(all(json.loads(row[1])['payload']['inspection_id']=='inspection-test' for row in rows))

    def test_observation_memory_is_bounded_and_capture_keeps_same_event(self):
        with saved_journal() as journal:
            owner = self.owner(journal)
            owner._diagnostic_events = []
            value = dict(event='PRODUCTION_TRACK_STATE', frame_id='frame-1', sequence=1)
            owner._event(value)
            self.assertEqual(owner._diagnostic_events, [value])
            owner._diagnostic_events = None
            for sequence in range(100):
                owner._event(dict(event='PRODUCTION_TRACK_STATE', sequence=sequence))
            self.assertEqual(len(owner.service.health_diagnostics.snapshot()['events']), 64)


if __name__ == '__main__':
    unittest.main()
