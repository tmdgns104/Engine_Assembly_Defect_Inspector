"""Control isolation for request-event writes; no camera, PLC or inference.

These tests cover SQLite ownership, not arbitrary filesystem stalls. Existing
health.disk_usage and Assembly result file reads remain synchronous and are
outside the claims made by these checks.
"""
import queue
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from src.journal.sqlite import Journal
from src.runtime.request_start import RequestStart
from src.runtime.standalone import StandaloneRuntime


class RequestControlIsolation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.journal = Journal(Path(self.temp.name), min_free_bytes=0)
        self.addCleanup(self.journal.close)
        self.identifier, _ = self.journal.admit(dict(cell_id='fixture', plc_session_id=1,
            request_id=1, cycle_id=1, attempt=1), {})
        runtime = self.runtime = StandaloneRuntime.__new__(StandaloneRuntime)
        runtime.service = NS(journal=self.journal, generation='fixture-generation',
            cancellation=threading.Event(), state='BUSY',
            active={'inspection_id': self.identifier}, storage_pending=None,
            products=queue.Queue(),
            cancel=Mock(side_effect=AssertionError('Synchronous Journal cancel is forbidden')))
        runtime.gateway = NS(health_update=Mock())
        runtime.handshake = NS(token='0000000000000001:1:1',
            state='INSPECTING', publication='NOT_PUBLISHED', fault=Mock())
        runtime.bridge = NS(inspection_id=self.identifier, phase='INSPECTION_REQUESTED')
        runtime.session_id = 'fixture-runtime'
        runtime._diagnostic_events = None
        runtime._automatic_policy = lambda: True
        runtime.published_ids = set()
        runtime.final_pending = None
        runtime.arrival = {'fixture': True}
        runtime.operating, runtime.error, runtime.cycle_issue = True, None, None
        runtime.product_passage = None
        runtime.request_start = RequestStart(runtime)
        runtime.request_start.capture_events = True
        runtime.request_start.pending = {'kind': 'events', 'reservation': None}

    def with_journal_busy(self, action):
        acquired, release = threading.Event(), threading.Event()
        def writer():
            with self.journal.lock:
                acquired.set()
                release.wait(2)
        thread = threading.Thread(target=writer)
        thread.start()
        self.assertTrue(acquired.wait(1))
        try:
            started = time.monotonic()
            action()
            self.assertLess(time.monotonic()-started, .15)
        finally:
            release.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())

    def assert_immediate_withdrawal(self, reason):
        runtime = self.runtime
        self.assertTrue(runtime.service.cancellation.is_set())
        self.assertEqual(runtime.service.state, 'CANCELLING')
        self.assertEqual(runtime.gateway.health_update.call_args.args[:2], (False, False))
        runtime.handshake.fault.assert_called_with(reason)
        runtime.service.cancel.assert_not_called()
        # Cancellation signaling is not a claim of durable cancellation. The
        # existing storage/Worker completion path still owns that later write.
        self.assertEqual(self.journal.detail(self.identifier)['state'], 'ACCEPTED')

    def test_stop_during_request_audit_withdraws_without_waiting_for_sqlite(self):
        self.with_journal_busy(lambda: self.runtime._cancel_pending('PHYSICAL_STOP'))
        self.assert_immediate_withdrawal('PHYSICAL_STOP')
        self.assertIsNone(self.runtime.arrival)
        self.assertIn(self.identifier, self.runtime.published_ids)
        self.assertEqual(self.runtime.aborted_inspection['request_token'], self.runtime.handshake.token)
        self.assertEqual(self.runtime.request_start.events[-1]['event'], 'LINE_CANCELLED_RESULT_BLOCKED')

    def test_observation_fault_during_audit_signals_cancel_without_journal(self):
        reason = 'TRACK_ASSOCIATION_OR_GAP_LOST'
        self.with_journal_busy(lambda: self.runtime._observation_issue(reason))
        self.assert_immediate_withdrawal(reason)
        self.assertEqual(self.runtime.cycle_issue['reason'], reason)
        self.assertEqual(self.runtime.request_start.events[-1]['event'], 'LINE_OBSERVATION_ISSUE')

    def test_raw_final_and_unpublished_durable_rows_defer_observation_sql(self):
        runtime = self.runtime
        packet = {'frame_id': 'fixture:1'}
        runtime.service.products.put(packet)
        runtime._packet = Mock(side_effect=AssertionError('May read Journal through completed-preview guard'))
        for stage in ('raw', 'final', 'unpublished-durable'):
            with self.subTest(stage=stage):
                runtime.service.storage_pending = {'fixture': True} if stage == 'raw' else None
                runtime.final_pending = {'fixture': True} if stage == 'final' else None
                runtime.bridge.phase = 'INSPECTION_DURABLE' if stage == 'unpublished-durable' else 'INSPECTION_REQUESTED'
                self.with_journal_busy(runtime.request_start._observations)
                self.assertEqual(runtime.service.products.qsize(), 1)
                runtime._packet.assert_not_called()
        runtime.service.storage_pending = runtime.final_pending = None
        runtime.bridge.phase = 'INSPECTION_REQUESTED'
        runtime._packet = Mock()
        runtime.request_start._observations()
        runtime._packet.assert_called_once_with(packet)
        self.assertTrue(runtime.service.products.empty())

    def test_published_preview_gap_does_not_read_the_previous_journal_row(self):
        runtime = self.runtime
        runtime.bridge.phase = 'INSPECTION_DURABLE'
        runtime.published_ids.add(self.identifier)
        with self.journal.lock:
            original = self.journal.detail
            self.journal.detail = Mock(side_effect=AssertionError('Unneeded prior-row SQL'))
            try:
                self.assertFalse(runtime._completed_preview_issue('PRODUCT_OBSERVATION_GAP'))
                self.journal.detail.assert_not_called()
            finally:
                self.journal.detail = original
        # Published-cycle diagnostics remain consumable after the write owner
        # is gone; deferral must not permanently freeze the queue.
        runtime.service.products.put({'frame_id': 'fixture:2'})
        runtime._packet = Mock()
        runtime.request_start._observations()
        runtime._packet.assert_called_once()

    def test_other_modes_keep_existing_cancellation_owner(self):
        runtime = self.runtime
        runtime.request_start.capture_events = False
        runtime.service.cancel = Mock()
        runtime._cancel_active_inspection('legacy')
        runtime.service.cancel.assert_called_once_with(self.identifier)
        runtime.gateway.health_update.assert_not_called()


class LateResultAuditIsolation(unittest.TestCase):
    def fixture(self):
        from notebook.tests import test_request_start_runtime as fixtures
        fixture = fixtures.RequestStartRuntimeTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        service, runtime = fixture.service, fixture.r
        runtime.request_start = fixture.controller
        runtime.inspection_motion_mode, runtime.zone = 'FULL_FRAME', {'fixture': True}
        service.production_owner = runtime
        service.results, service.previews = queue.Queue(), queue.Queue()
        service.lab.tick = Mock()
        service.mock.tick = Mock()
        service._fault = Mock(side_effect=AssertionError('Unexpected monitor fault'))
        return fixture

    def monitor(self, fixture):
        thread = threading.Thread(target=fixture.service._monitor_loop)
        thread.start()
        def stop():
            fixture.service.closed.set()
            thread.join(2)
            self.assertFalse(thread.is_alive())
        self.addCleanup(stop)
        return thread

    def test_real_monitor_late_result_does_not_wait_on_admission_sql(self):
        fixture = self.fixture()
        service, controller, journal = fixture.service, fixture.controller, fixture.journal
        previous = dict(event='PLC_CYCLIC_COMPLETION_OBSERVED', inspection_id='prior', decision='PASS')
        with journal.db:
            journal.db.execute('INSERT INTO service_state VALUES (?,?)',
                ('production_publication:prior', json.dumps(previous)))
        original, entered, release = journal.admit, threading.Event(), threading.Event()
        def blocked(*args, **kwargs):
            entered.set()
            if not release.wait(2): raise TimeoutError('test writer timeout')
            return original(*args, **kwargs)
        self.monitor(fixture)
        try:
            with patch.object(journal, 'admit', side_effect=blocked):
                controller.begin(fixture.binding, time.monotonic())
                self.assertTrue(entered.wait(1))
                service.results.put(dict(generation=service.generation, type='result',
                    inspection_id='prior', result={'decision':'PASS'}))
                until = time.monotonic()+.55
                turns = 0
                while time.monotonic() < until:
                    self.assertTrue(service.lock.acquire(timeout=.1), 'Monitor held Service while waiting for SQLite')
                    try:
                        fixture.tick()
                        self.assertTrue(service.commands.empty())
                    finally: service.lock.release()
                    turns += 1
                    time.sleep(.02)
                self.assertGreater(turns, 10)
                self.assertTrue(service.results.empty())
                release.set()
                fixture.drain_pending()
        finally: release.set()
        service._fault.assert_not_called()
        gaps = [b[0]-a[0] for a,b in zip(fixture.health_updates, fixture.health_updates[1:])]
        self.assertLess(max(gaps), .4)
        self.assertTrue(any(ready for _,ready,_ in fixture.health_updates))
        with journal.lock:
            saved = journal.db.execute("SELECT payload_json FROM events WHERE event_type='LATE_RESULT_QUARANTINED'").fetchall()
            self.assertEqual(len(saved), 1)
            self.assertEqual(json.loads(saved[0][0])['payload']['inspection_id'], 'prior')
            value = journal.db.execute("SELECT value FROM service_state WHERE key='production_publication:prior'").fetchone()[0]
            self.assertEqual(json.loads(value), previous)

    def test_full_audit_queue_retains_worker_message_and_withdraws_ready(self):
        fixture = self.fixture()
        service, controller = fixture.service, fixture.controller
        for number in range(32):
            controller.defer_event(dict(event='LATE_RESULT_QUARANTINED', inspection_id=str(number), event_only=True))
        service.results.put(dict(generation=service.generation, type='result', inspection_id='not-dropped', result={'decision':'PASS'}))
        self.monitor(fixture)
        until = time.monotonic()+.5
        while service.error is None and time.monotonic()<until: time.sleep(.01)
        self.assertEqual(service.error, 'LATE_RESULT_AUDIT_BACKPRESSURE')
        self.assertEqual(service.results.qsize(), 1)
        self.assertTrue(service.cancellation.is_set())
        self.assertFalse(fixture.health_updates[-1][1])
        self.assertEqual(controller.deferred_events.qsize(), 32)


if __name__ == '__main__':
    unittest.main()
