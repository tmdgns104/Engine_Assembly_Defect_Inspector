"""Request durability tests use temporary SQLite only; no camera or PLC."""
import json
from contextlib import closing
from pathlib import Path
import queue
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'jetson'))
from apps.edge_service.result_storage import ResultStorage
from src.journal.sqlite import Journal


class FailingCommit:
    """Real SQLite writes, with one selected transaction failing before commit."""
    def __init__(self, connection, fail_at):
        self.connection, self.fail_at, self.transactions = connection, fail_at, 0

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, kind, error, traceback):
        self.transactions += 1
        if kind is None and self.transactions == self.fail_at:
            self.connection.rollback()
            raise OSError('injected_commit_failure')
        return self.connection.__exit__(kind, error, traceback)


class IntegrityProbe(FailingCommit):
    def __init__(self, connection, *, delay=0, corrupt=False):
        super().__init__(connection, fail_at=-1)
        self.delay, self.corrupt = delay, corrupt
        self.entered = threading.Event()

    def execute(self, statement, *args):
        if statement == 'PRAGMA quick_check':
            self.entered.set()
            time.sleep(self.delay)
            if self.corrupt:
                return self.connection.execute("SELECT 'injected_integrity_failure'")
        return self.connection.execute(statement, *args)


class RequestStartStorage(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.journal = Journal(self.folder.name, min_free_bytes=0)
        self.storage = ResultStorage(self.journal)
        self.addCleanup(self.folder.cleanup)
        self.addCleanup(self.journal.close)
        self.addCleanup(self.storage.close)
        self.context = object()

    def admit_job(self):
        return dict(kind='admit', base=dict(cell_id='cell', plc_session_id=1,
            package_sha256='package', kind='inspect', control_mode='production'),
            package=dict(package_sha256='package'), trigger=dict(trigger_id='trigger',
            cell_id='placeholder', plc_session_id=99, request_id=1, cycle_id=1,
            trigger_received_monotonic=10., capture_epoch='camera'))

    def execute(self, job):
        self.storage.submit_request(self.context, job)
        result = self.storage.request_completed.get(timeout=3)
        self.assertIs(result['context'], self.context)
        return result

    def admitted(self):
        result = self.execute(self.admit_job())
        self.assertIsNone(result['error'])
        return result['result']

    def test_550ms_event_delay_does_not_block_caller_or_report_early_durable(self):
        entered = threading.Event()
        original = self.journal._event
        def delayed(*args):
            entered.set()
            time.sleep(.55)
            return original(*args)
        with patch.object(self.journal, '_event', side_effect=delayed):
            before = time.monotonic()
            self.storage.submit_request(self.context, dict(kind='events', events=[{'event':'START'}]))
            self.assertLess(time.monotonic() - before, .2)
            self.assertTrue(entered.wait(1))
            self.assertTrue(self.storage.request_completed.empty())
            ticks = 0
            while time.monotonic() - before < .35:
                ticks += 1
                time.sleep(.02)
                self.assertTrue(self.storage.request_completed.empty())
            self.assertGreaterEqual(ticks, 5)
            result = self.storage.request_completed.get(timeout=2)
        self.assertIsNone(result['error'])
        self.assertGreaterEqual(result['duration_ms'], 500)
        self.assertGreaterEqual(result['durable_monotonic'], before + .5)
        self.assertIn('events_commit_ms', result['timings'])

    def test_event_batch_preserves_order_and_only_identified_publication(self):
        events = [dict(event='REQUEST_SEEN'), dict(event='ADMITTED',inspection_id='i'),
                  dict(event='BOUND',inspection_id='i')]
        result = self.execute(dict(kind='events', events=events))
        self.assertIsNone(result['error'])
        stored = self.journal.db.execute('SELECT event_type FROM events ORDER BY producer_seq').fetchall()
        self.assertEqual([r[0] for r in stored], ['REQUEST_SEEN','ADMITTED','BOUND'])
        rows = self.journal.db.execute("SELECT key,value FROM service_state WHERE key LIKE 'production_publication:%'").fetchall()
        self.assertEqual([(r[0], json.loads(r[1])) for r in rows], [('production_publication:i',events[-1])])

    def test_event_batch_failure_rolls_back_events_outbox_and_publication(self):
        original = self.journal._event
        def fail_second(name, payload):
            if name == 'SECOND':
                raise OSError('disk_full')
            return original(name, payload)
        with patch.object(self.journal, '_event', side_effect=fail_second):
            result = self.execute(dict(kind='events',events=[
                dict(event='FIRST',inspection_id='i'),dict(event='SECOND')]))
        self.assertIn('disk_full', result['error'])
        self.assertIsNone(result['durable_monotonic'])
        for table in ('events','outbox','service_state'):
            self.assertEqual(self.journal.db.execute('SELECT count(*) FROM '+table).fetchone()[0], 0)

    def test_admission_uses_durable_counter_and_trigger_identity(self):
        first = self.admitted()
        self.execute(dict(kind='cancel',inspection_id=first['inspection_id'],reason='STOP'))
        second = self.admitted()
        self.assertEqual(second['request']['request_id'], 2)
        self.assertEqual(second['request']['cycle_id'], 2)
        self.assertEqual(second['request']['attempt'], 1)
        self.assertEqual(second['row']['state'], 'ACCEPTED')
        for key in ('cell_id','plc_session_id','request_id','cycle_id'):
            self.assertEqual(second['trigger'][key], second['request'][key])
        event = self.journal.db.execute("SELECT payload_json FROM events WHERE event_type='TRIGGER_ACCEPTED' ORDER BY producer_seq DESC LIMIT 1").fetchone()[0]
        self.assertEqual(json.loads(event)['payload']['trigger'], second['trigger'])

    def test_admission_events_commit_in_order_before_admit_and_completion(self):
        entered, release = threading.Event(), threading.Event()
        original_event, original_admit = self.journal._event, self.journal.admit
        def delayed_event(name, payload):
            value = original_event(name, payload)
            if name == 'REQUEST_BOUND':
                entered.set()
                if not release.wait(2):
                    raise TimeoutError('fixture')
            return value
        def admit_after_committed_events(*args, **kwargs):
            with closing(sqlite3.connect(Path(self.folder.name)/'journal.sqlite3')) as probe:
                rows = probe.execute('SELECT event_type FROM events ORDER BY producer_seq').fetchall()
                self.assertEqual(rows, [('REQUEST_SEEN',), ('REQUEST_BOUND',)])
            return original_admit(*args, **kwargs)
        job = self.admit_job()
        job['events'] = [dict(event='REQUEST_SEEN'), dict(event='REQUEST_BOUND')]
        try:
            with patch.object(self.journal,'_event',side_effect=delayed_event), \
                    patch.object(self.journal,'admit',side_effect=admit_after_committed_events):
                self.storage.submit_request(self.context, job)
                self.assertTrue(entered.wait(1))
                self.assertTrue(self.storage.request_completed.empty())
                with closing(sqlite3.connect(Path(self.folder.name)/'journal.sqlite3')) as probe:
                    self.assertEqual(probe.execute('SELECT count(*) FROM inspections').fetchone()[0], 0)
                    self.assertEqual(probe.execute("SELECT count(*) FROM service_state WHERE key='request_counter:1'").fetchone()[0], 0)
                release.set()
                result = self.storage.request_completed.get(timeout=2)
        finally:
            release.set()
        self.assertIsNone(result['error'])
        self.assertIn('events_commit_ms',result['timings'])
        rows = self.journal.db.execute('SELECT event_type FROM events ORDER BY producer_seq').fetchall()
        self.assertEqual([r[0] for r in rows], ['REQUEST_SEEN','REQUEST_BOUND','TRIGGER_ACCEPTED'])

    def test_failed_admission_event_batch_is_not_retried_or_admitted(self):
        original = self.journal._event
        calls = []
        def fail(name, payload):
            calls.append(name)
            if name == 'REQUEST_BOUND':
                raise OSError('request_event_commit_failed')
            return original(name, payload)
        job = self.admit_job()
        job['events'] = [dict(event='REQUEST_SEEN'),dict(event='REQUEST_BOUND')]
        with patch.object(self.journal,'_event',side_effect=fail):
            result = self.execute(job)
        self.assertIn('request_event_commit_failed',result['error'])
        self.assertEqual(calls,['REQUEST_SEEN','REQUEST_BOUND'])
        for table in ('events','outbox','inspections','service_state'):
            self.assertEqual(self.journal.db.execute('SELECT count(*) FROM '+table).fetchone()[0],0)

    def test_admit_commit_failure_keeps_spent_counter_but_no_admission(self):
        self.journal.db = FailingCommit(self.journal.db, fail_at=2)
        result = self.execute(self.admit_job())
        self.assertIn('injected_commit_failure', result['error'])
        self.assertIsNone(result['durable_monotonic'])
        self.assertEqual(self.journal.db.execute('SELECT count(*) FROM inspections').fetchone()[0], 0)
        self.assertEqual(self.journal.db.execute("SELECT value FROM service_state WHERE key='request_counter:1'").fetchone()[0], '1')
        self.assertEqual(self.admitted()['request']['request_id'], 2)

    def test_failed_detail_preserves_exact_admission_for_cancellation(self):
        with patch.object(self.journal,'detail',side_effect=OSError('read_failed')):
            failed = self.execute(self.admit_job())
        self.assertIn('read_failed', failed['error'])
        identifier = failed['result']['inspection_id']
        self.assertEqual(self.journal.detail(identifier)['state'], 'ACCEPTED')
        cancelled = self.execute(dict(kind='cancel',inspection_id=identifier,reason='ADMISSION_READ_FAILED'))
        self.assertEqual(cancelled['result']['row']['state'], 'CANCELLED')

    def test_cancel_before_dispatch_keeps_durable_blocked_cycle_evidence(self):
        identifier = self.admitted()['inspection_id']
        cancelled = self.execute(dict(kind='cancel', inspection_id=identifier, reason='PHYSICAL_STOP'))
        self.assertIsNone(cancelled['error'])
        self.assertEqual(cancelled['result']['row']['state'], 'CANCELLED')
        events = self.journal.db.execute("SELECT payload_json FROM events "
            "WHERE event_type='LINE_CANCELLED_RESULT_BLOCKED'").fetchall()
        self.assertEqual(len(events), 1)
        payload = json.loads(events[0][0])['payload']
        self.assertEqual(payload['inspection_id'], identifier)
        self.assertEqual(payload['reason'], 'PHYSICAL_STOP')
        self.assertEqual(self.journal.db.execute('SELECT count(*) FROM frame_assets').fetchone()[0], 0)

    def test_failed_blocked_event_does_not_report_cancel_completion_or_change_original(self):
        identifier = self.admitted()['inspection_id']
        original = self.journal._event
        def fail_blocked(name, payload):
            if name == 'LINE_CANCELLED_RESULT_BLOCKED':
                raise OSError('blocked_event_commit_failed')
            return original(name, payload)
        with patch.object(self.journal, '_event', side_effect=fail_blocked):
            cancelled = self.execute(dict(kind='cancel', inspection_id=identifier, reason='PHYSICAL_STOP'))
        self.assertIn('blocked_event_commit_failed', cancelled['error'])
        self.assertIsNone(cancelled['durable_monotonic'])
        self.assertEqual(self.journal.detail(identifier)['state'], 'CANCELLED')

    def test_pending_or_unsettled_production_blocks_next_admission(self):
        first = self.admitted()
        failed = self.execute(self.admit_job())
        self.assertIn('JOURNAL_UNFINISHED_INSPECTION', failed['error'])
        self.assertEqual(self.journal.db.execute("SELECT value FROM service_state WHERE key='request_counter:1'").fetchone()[0], '1')
        self.journal.finish(first['inspection_id'], dict(decision='ERROR', reason='fixture'))
        failed = self.execute(self.admit_job())
        self.assertIn('JOURNAL_UNFINISHED_INSPECTION', failed['error'])

    def test_unfinished_mock_cycle_blocks_even_after_completed_raw(self):
        request = dict(self.admit_job()['base'], control_mode='mock', request_id=22,cycle_id=22,attempt=1)
        identifier,_ = self.journal.admit(request, {})
        self.journal.finish(identifier, dict(decision='ERROR',reason='fixture'))
        result = self.execute(self.admit_job())
        self.assertIn('UNFINISHED_CYCLE_RECOVERY_REQUIRED', result['error'])

    def test_readiness_returns_previous_evidence_without_mutating_journal(self):
        admitted = self.admitted()
        identifier = admitted['inspection_id']
        self.journal.finish(identifier, dict(decision='ERROR',reason='fixture'))
        final = dict(request_token='token',decision='ERROR')
        with self.journal.db:
            self.journal.db.execute('INSERT INTO service_state VALUES (?,?)',
                                    ('integrated_decision:'+identifier,json.dumps(final)))
        changes = self.journal.db.total_changes
        result = self.execute(dict(kind='readiness',previous_identifier=identifier,previous_token='token'))
        self.assertEqual(result['result']['unfinished'], 0)
        self.assertEqual(result['result']['previous_final'], final)
        self.assertEqual(result['result']['previous_row']['inspection_id'],identifier)
        self.assertEqual(self.journal.db.total_changes, changes)
        result['result']['previous_final']['decision'] = 'PASS'
        self.assertEqual(json.loads(self.journal.db.execute('SELECT value FROM service_state WHERE key=?',
            ('integrated_decision:'+identifier,)).fetchone()[0]), final)

    def test_cancel_does_not_overwrite_completed_result_or_another_request(self):
        admitted = self.admitted()
        identifier = admitted['inspection_id']
        self.journal.finish(identifier, dict(decision='ERROR',reason='original_failure'))
        before = self.journal.detail(identifier)
        result = self.execute(dict(kind='cancel',inspection_id=identifier,reason='late_STOP'))
        self.assertEqual(result['result']['row'], before)
        self.assertEqual(self.journal.detail(identifier), before)
        missing = self.execute(dict(kind='cancel',inspection_id='different',reason='STOP'))
        self.assertIn('CANCEL_INSPECTION_NOT_FOUND', missing['error'])
        self.assertEqual(self.journal.detail(identifier), before)

    def test_unknown_job_never_falls_through_to_raw_finish(self):
        with patch.object(self.journal, 'finish') as finish:
            with self.assertRaisesRegex(ValueError,'UNKNOWN_REQUEST_STORAGE_JOB'):
                self.storage.submit_request(self.context, {'kind':'typo'})
            self.storage.jobs.put_nowait(('typo',self.context,{}))
            result = self.storage.request_completed.get(timeout=2)
            self.assertIn('UNKNOWN_STORAGE_JOB_KIND',result['error'])
            finish.assert_not_called()
            self.assertTrue(self.storage.thread.is_alive())

    def test_no_input_records_only_error_without_capture_assets_or_trigger(self):
        job = self.admit_job()
        job.update(kind='no_input', trigger=None, no_input_result=dict(
            decision='ERROR',reason='NO_CURRENT_PRODUCT',observations=[],
            production_identity=dict(plc_request_token='token'),
            execution=dict(source='not_executed',control='production')))
        result = self.execute(job)
        self.assertIsNone(result['error'])
        identifier = result['result']['inspection_id']
        row = result['result']['row']
        self.assertEqual(row['state'],'COMPLETE')
        self.assertEqual(row['result']['decision'],'ERROR')
        self.assertEqual(row['result']['assets'],[])
        self.assertEqual(row['result']['production_identity']['inspection_id'],identifier)
        self.assertEqual(self.journal.db.execute('SELECT count(*) FROM frame_assets').fetchone()[0],0)
        self.assertEqual(self.journal.db.execute("SELECT count(*) FROM events WHERE event_type='TRIGGER_ACCEPTED'").fetchone()[0],0)

    def test_no_input_finish_failure_retains_exact_admission_and_does_not_retry(self):
        job = self.admit_job()
        job.update(kind='no_input',trigger=None,no_input_result=dict(decision='ERROR',reason='NO_CURRENT_PRODUCT'))
        with patch.object(self.journal,'finish',side_effect=OSError('finish_failed')) as finish:
            result = self.execute(job)
            finish.assert_called_once()
        self.assertIn('finish_failed',result['error'])
        self.assertIsNone(result['durable_monotonic'])
        identifier = result['result']['inspection_id']
        self.assertEqual(result['result']['row']['state'],'ACCEPTED')
        self.assertEqual(self.journal.detail(identifier)['state'],'ACCEPTED')
        cancelled = self.execute(dict(kind='cancel',inspection_id=identifier,reason='NO_INPUT_STORAGE_FAILED'))
        self.assertEqual(cancelled['result']['row']['state'],'CANCELLED')

    def test_no_input_cannot_create_pass_or_capture_trigger(self):
        for decision, trigger in (('PASS',None),('ERROR',dict(trigger_id='forbidden'))):
            with self.subTest(decision=decision,trigger=trigger):
                job = self.admit_job()
                job.update(kind='no_input',trigger=trigger,no_input_result=dict(decision=decision))
                result = self.execute(job)
                self.assertIn('NO_INPUT_REQUIRES_ERROR',result['error'])
                self.assertEqual(self.journal.db.execute('SELECT count(*) FROM inspections').fetchone()[0],0)

    def test_readiness_and_admit_integrity_failure_never_admit_or_renew(self):
        self.journal.db = IntegrityProbe(self.journal.db, corrupt=True)
        for job in (dict(kind='readiness'), self.admit_job()):
            with self.subTest(kind=job['kind']):
                result = self.execute(job)
                self.assertIn('JOURNAL_INTEGRITY_FAILED',result['error'])
                self.assertIsNone(result['durable_monotonic'])
                self.assertIsNone(result['result'])
                self.assertIn('integrity_check_ms',result['timings'])
                self.assertEqual(self.journal.db.execute('SELECT count(*) FROM inspections').fetchone()[0],0)
                self.assertEqual(self.journal.db.execute('SELECT count(*) FROM service_state').fetchone()[0],0)

    def test_slow_integrity_checks_stay_in_worker_and_gate_completion(self):
        self.journal.db = IntegrityProbe(self.journal.db, delay=.55)
        for job in (dict(kind='readiness'), self.admit_job()):
            with self.subTest(kind=job['kind']):
                self.journal.db.entered.clear()
                before = time.monotonic()
                self.storage.submit_request(self.context,job)
                self.assertLess(time.monotonic()-before,.2)
                self.assertTrue(self.journal.db.entered.wait(1))
                self.assertTrue(self.storage.request_completed.empty())
                result = self.storage.request_completed.get(timeout=2)
                self.assertIsNone(result['error'])
                self.assertGreaterEqual(result['timings']['integrity_check_ms'],500)
                self.assertGreaterEqual(result['durable_monotonic'],before+.5)


if __name__ == '__main__':
    unittest.main()
