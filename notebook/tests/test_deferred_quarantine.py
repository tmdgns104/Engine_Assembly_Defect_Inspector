"""Real monitor/SQLite isolation; no camera, PLC or inference execution."""
import json
import queue
import threading
import time
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from notebook.tests import test_request_start_runtime as runtime_fixture


class DeferredQuarantineTests(unittest.TestCase):
    def setUp(self):
        self.case = runtime_fixture.RequestStartRuntimeTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.service, self.journal = self.case.service, self.case.journal
        self.controller = self.case.controller
        self.service.production_owner.request_start = self.controller
        self.service.results, self.service.previews = queue.Queue(), queue.Queue()
        self.service.lab.tick = Mock()
        self.service.mock.tick = Mock()

    def message(self, identifier):
        return dict(type='result', generation=self.service.generation,
            inspection_id=identifier, result={'decision': 'PASS'}, images=[])

    def monitor_once(self):
        with patch.object(self.service.closed, 'wait', side_effect=[False, True]):
            self.service._monitor_loop()

    def drain(self):
        until = time.monotonic() + 3
        while (self.controller.pending or self.controller.events
                or not self.service.deferred_quarantine_audits.empty()
                or self.service.deferred_quarantine_overflow is not None):
            self.assertLess(time.monotonic(), until, 'deferred audit did not settle')
            with self.service.lock:
                self.controller.tick(time.monotonic())
            time.sleep(.005)

    def test_real_monitor_late_result_does_not_block_STOP_during_admit(self):
        entered, release, monitor_done = threading.Event(), threading.Event(), threading.Event()
        original_admit = self.journal.admit
        errors = []
        previous = json.dumps({'event': 'PLC_CYCLIC_COMPLETION_OBSERVED', 'inspection_id': 'previous'})
        with self.journal.lock, self.journal.db:
            self.journal.db.execute('INSERT INTO service_state VALUES (?,?)',
                ('production_publication:previous', previous))

        def blocked_admit(*args, **kwargs):
            entered.set()
            if not release.wait(3):
                raise TimeoutError('fixture admission release')
            return original_admit(*args, **kwargs)

        def run_monitor():
            try:
                self.monitor_once()
            except Exception as error:
                errors.append(error)
            finally:
                monitor_done.set()

        thread = threading.Thread(target=run_monitor, daemon=True)
        try:
            with patch.object(self.journal, 'admit', side_effect=blocked_admit):
                self.controller.begin(self.case.binding, time.monotonic())
                self.assertTrue(entered.wait(1))
                self.service.results.put(self.message('previous'))
                thread.start()
                self.assertTrue(monitor_done.wait(.15), 'monitor held Service.lock waiting for Journal')
                self.assertEqual(errors, [])
                self.assertTrue(self.service._status_snapshot()['production_admission_pending'])
                self.case.controls['Mc_Run'] = False
                started = time.monotonic()
                with self.service.lock:
                    self.case.tick()
                self.assertLess(time.monotonic()-started, .15)
                self.assertFalse(self.case.health_updates[-1][1])
                self.assertTrue(self.controller.pending['aborted'])
                self.assertTrue(self.service.commands.empty())
                release.set()
                self.drain()
        finally:
            release.set()
            if thread.ident is not None:
                thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertFalse(self.service._status_snapshot()['production_admission_pending'])
        self.assertEqual(self.journal.db.execute('SELECT state FROM inspections').fetchone()[0], 'CANCELLED')
        audit = self.journal.db.execute(
            "SELECT payload_json FROM events WHERE event_type='LATE_RESULT_QUARANTINED'").fetchall()
        self.assertEqual(len(audit), 1)
        self.assertEqual(json.loads(audit[0][0])['payload']['inspection_id'], 'previous')
        self.assertEqual(self.journal.db.execute('SELECT value FROM service_state WHERE key=?',
            ('production_publication:previous',)).fetchone()[0], previous)

    def test_bounded_overflow_preserves_received_audit_and_fails_closed_without_SQL(self):
        for number in range(66):
            self.service.results.put(self.message('late:'+str(number)))
        with patch.object(self.journal, '_event', side_effect=AssertionError('monitor SQL forbidden')):
            self.monitor_once()
        self.assertEqual(self.service.state, 'RECOVERY')
        self.assertEqual(self.service.error, 'DEFERRED_QUARANTINE_AUDIT_OVERFLOW')
        self.assertTrue(self.service.cancellation.is_set())
        self.assertEqual(self.service.deferred_quarantine_audits.qsize(), 64)
        self.assertEqual(self.service.deferred_quarantine_overflow['inspection_id'], 'late:64')
        self.assertEqual(self.service.results.qsize(), 1)  # Unconsumed message remains owned by its queue.
        self.monitor_once()
        self.assertEqual(self.service.results.qsize(), 1)
        self.drain()
        stored = self.journal.db.execute(
            "SELECT payload_json FROM events WHERE event_type='LATE_RESULT_QUARANTINED' ORDER BY rowid").fetchall()
        self.assertEqual([json.loads(row[0])['payload']['inspection_id'] for row in stored],
                         ['late:'+str(number) for number in range(65)])
        self.assertEqual(self.service.error, 'DEFERRED_QUARANTINE_AUDIT_OVERFLOW')
        self.assertFalse(self.service.health()['ready'])
        self.assertTrue(self.service.commands.empty())

    def test_quarantine_does_not_redispatch_current_result(self):
        result = self.case.fixture.active_result()
        self.service.backend = {'backend': 'fixture'}
        self.service.storage = NS(completed=queue.Queue(), submit=Mock())
        self.service.results.put(self.message('older'))
        current = self.message(self.service.active['inspection_id'])
        current['result'] = result
        self.service.results.put(current)
        self.monitor_once()
        self.service.storage.submit.assert_called_once()
        self.assertEqual(self.service.storage.submit.call_args.args[1]['inspection_id'],
                         self.service.active['inspection_id'])
        self.assertEqual(self.service.deferred_quarantine_audits.get_nowait()['inspection_id'], 'older')
        self.assertIsNone(self.service.error)

    def test_nonautomatic_owner_preserves_existing_immediate_quarantine(self):
        self.service.production_owner.request_start = None
        self.service.results.put(self.message('legacy'))
        self.monitor_once()
        rows = self.journal.db.execute(
            "SELECT payload_json FROM events WHERE event_type='LATE_RESULT_QUARANTINED'").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(json.loads(rows[0][0])['payload'],
                         dict(inspection_id='legacy', reason='NO_MATCHING_ACTIVE_TRIGGER'))


if __name__ == '__main__':
    unittest.main()
