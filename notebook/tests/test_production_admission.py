"""Real Journal admission with a fake command queue; never opens camera or PLC."""
import copy
import json
import queue
import tempfile
import threading
import time
import unittest
from collections import deque
from pathlib import Path
from types import SimpleNamespace as NS
from dataclasses import FrozenInstanceError
from unittest.mock import Mock, patch

from apps.edge_service.inspection import InspectionService
from src.journal.sqlite import ConflictError, Journal
from src.runtime.health_diagnostics import HealthDiagnostics


class ProductionAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.journal = Journal(Path(self.temp.name), min_free_bytes=0)
        self.addCleanup(self.journal.close)
        self.service = InspectionService.__new__(InspectionService)
        service = self.service
        service.lock = threading.RLock()
        service.production_enabled = True
        service.production_owner = NS(session_id='runtime', inspection_motion_mode='FULL_FRAME',
                                      zone={'fixture': True}, operating=True)
        service.station = dict(cell_id='fixture', station_id='fixture', inspection_timeout_seconds=8,
            fresh_frame=dict(boundary_epsilon_ms=1, max_trigger_to_frame_ms=7000,
                             inspection_window_ms=7000), max_frame_age_seconds=1,
            frame_spacing_seconds=.01)
        service.journal = self.journal
        service.session = self.journal.new_session('fixture')
        self.package = dict(manifest_sha256='sha', manifest={'product_id': 'fixture'})
        service.package = NS(manifest_hash='sha', snapshot=lambda: copy.deepcopy(self.package))
        service.generation = 'worker'
        service.process = NS(is_alive=lambda: True, pid=123)
        service.heartbeat = NS(value=time.monotonic())
        service.preview_received = time.monotonic()
        service.preview = dict(generation='worker', freshness={'camera_epoch': 'camera'})
        service.active = service.storage_pending = service.production_admission_pending = None
        service.state, service.error, service.switching = 'IDLE', None, False
        service.calibration = {'confirmed': True, 'fixture': 'not-field'}
        service.mock = NS(state='IDLE', job=None, status=lambda: {'state': 'IDLE'})
        service.lab = NS(mode='MANUAL', status=lambda: {'mode': 'MANUAL'})
        service.progress = service.backend = service.sender = service.latest_timing = None
        service.recovery = {}
        service.diagnostic_capture = NS(value={})
        service.preview_times = deque()
        service._status_cache = {}
        service.cancellation = threading.Event()
        service.closed = threading.Event()
        service.commands = queue.Queue(maxsize=1)
        service.health_diagnostics = HealthDiagnostics()
        self.binding = dict(runtime_session_id='runtime', camera_epoch='camera',
                            worker_generation='worker', track_id=7, cycle_id=3)

    def prepare(self):
        return self.service.prepare_production_admission(self.binding)

    def persist(self, context):
        job = context.payload()
        request = dict(job['base'], request_id=1, cycle_id=1, attempt=1)
        trigger = dict(job['trigger'], request_id=1, cycle_id=1)
        identifier, created = self.journal.admit(request, job['package'], trigger=trigger)
        return dict(context=context, error=None, durable_monotonic=time.monotonic(),
                    result=dict(request=request, trigger=trigger,
                                row=self.journal.detail(identifier), created=created))

    def test_prepare_does_not_touch_storage_and_reserves_one_admission(self):
        with (patch.object(self.journal, 'capacity', side_effect=AssertionError('disk/SQL')),
              patch.object(self.service, 'status', side_effect=AssertionError('SQL'))):
            context = self.prepare()
        self.assertEqual(self.service.state, 'ADMITTING')
        self.assertTrue(self.service.commands.empty())
        self.assertIs(self.service.production_admission_pending, context)
        self.assertEqual(self.journal.db.execute('SELECT count(*) FROM inspections').fetchone()[0], 0)
        self.binding['track_id'] = 999
        detached = context.payload()
        detached['base']['runtime_binding']['track_id'] = 1000
        self.assertEqual(context.payload()['base']['runtime_binding']['track_id'], 7)
        with self.assertRaises(FrozenInstanceError):
            context.generation = 'forged'
        with self.assertRaisesRegex(ConflictError, 'ADMISSION_PENDING'):
            self.prepare()

    def test_manual_and_package_actions_cannot_take_pending_reservation(self):
        self.prepare()
        for action in (lambda: self.service.allocate_request(),
                       lambda: self.service.submit({}),
                       lambda: self.service.live_control('start'),
                       lambda: self.service.lab_action('mode', {'mode': 'MANUAL'})):
            with self.assertRaises(ConflictError):
                action()
        # A fault must not reopen package switching while the admission write
        # still belongs to the storage Worker.
        self.service.state = 'RECOVERY'
        with patch('apps.edge_service.inspection.load_package', return_value=self.service.package):
            with self.assertRaisesRegex(ConflictError, 'IDLE_REQUIRED'):
                self.service.activate('unused-fixture')

    def test_dispatch_requires_durable_matching_request_and_keeps_trigger_audit(self):
        context = self.prepare()
        saved = self.persist(context)
        row, created = self.service.activate_production_admission(context, saved)
        active = self.service.commands.get_nowait()
        self.assertTrue(created)
        self.assertEqual(row['state'], 'ACCEPTED')
        self.assertEqual(active['inspection_id'], row['inspection_id'])
        self.assertEqual(active['request'], saved['result']['request'])
        self.assertEqual(active['trigger'], saved['result']['trigger'])
        self.assertEqual(active['durable_admission_monotonic'], saved['durable_monotonic'])
        self.assertGreater(active['accepted_monotonic'], saved['durable_monotonic'])
        event = json.loads(self.journal.db.execute("SELECT payload_json FROM events WHERE event_type='TRIGGER_ACCEPTED'").fetchone()[0])
        self.assertEqual(event['payload']['trigger'], active['trigger'])
        self.assertEqual(self.service.state, 'BUSY')
        self.assertIsNone(self.service.production_admission_pending)
        with self.assertRaisesRegex(ConflictError, 'ADMISSION_CONTEXT_MISMATCH'):
            self.service.activate_production_admission(context, saved)

    def test_cancelled_reservation_cannot_dispatch_late_durable_completion(self):
        context = self.prepare()
        self.assertTrue(self.service.release_production_admission(context, 'STOP'))
        saved = self.persist(context)
        with self.assertRaisesRegex(ConflictError, 'ADMISSION_CONTEXT_MISMATCH'):
            self.service.activate_production_admission(context, saved)
        self.assertTrue(self.service.commands.empty())
        self.assertEqual(saved['result']['row']['state'], 'ACCEPTED')
        self.assertFalse(self.service.release_production_admission(context, 'duplicate'))

    def test_identity_and_health_changes_reject_dispatch(self):
        changes = {
            'generation': lambda s: setattr(s, 'generation', 'replacement'),
            'epoch': lambda s: s.preview['freshness'].update(camera_epoch='replacement'),
            'package': lambda s: setattr(s.package, 'manifest_hash', 'replacement'),
            'session': lambda s: setattr(s, 'session', 99),
            'owner': lambda s: setattr(s.production_owner, 'session_id', 'replacement'),
            'camera': lambda s: setattr(s, 'preview_received', 0),
            'worker': lambda s: setattr(s.process, 'is_alive', lambda: False),
            'heartbeat': lambda s: setattr(s.heartbeat, 'value', 0),
            'calibration': lambda s: s.calibration.update(confirmed=False),
            'cancel': lambda s: s.cancellation.set(),
            'state': lambda s: setattr(s, 'state', 'RECOVERY'),
            'error': lambda s: setattr(s, 'error', 'CAMERA_FAILURE'),
            'closed': lambda s: s.closed.set(),
            'switching': lambda s: setattr(s, 'switching', True),
            'control': lambda s: setattr(s.mock, 'state', 'RUNNING'),
        }
        # Each subcase uses its own complete request and state snapshot.
        for name, change in changes.items():
            with self.subTest(name=name):
                case = ProductionAdmissionTests()
                case.setUp()
                try:
                    context = case.prepare()
                    saved = case.persist(context)
                    change(case.service)
                    with case.assertRaises(ConflictError):
                        case.service.activate_production_admission(context, saved)
                    case.assertTrue(case.service.commands.empty())
                finally:
                    case.doCleanups()

    def test_bad_storage_receipts_reject_dispatch(self):
        changes = {
            'error': lambda x: x.update(error='OSError:disk'),
            'future': lambda x: x.update(durable_monotonic=time.monotonic()+100),
            'old': lambda x: x.update(durable_monotonic=0),
            'duplicate': lambda x: x['result'].update(created=False),
            'terminal': lambda x: x['result']['row'].update(state='CANCELLED'),
            'owner': lambda x: x['result']['request']['runtime_binding'].update(track_id=999),
            'trigger': lambda x: x['result']['trigger'].update(capture_epoch='replacement'),
            'row': lambda x: x['result']['row'].update(request={}),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                case = ProductionAdmissionTests()
                case.setUp()
                try:
                    context = case.prepare()
                    saved = case.persist(context)
                    change(saved)
                    with case.assertRaises(ConflictError):
                        case.service.activate_production_admission(context, saved)
                    case.assertTrue(case.service.commands.empty())
                finally:
                    case.doCleanups()

    def test_slow_journal_lock_does_not_block_prepare_or_live_health(self):
        locked, release = threading.Event(), threading.Event()
        def hold_journal():
            with self.journal.lock:
                locked.set()
                release.wait(2)
        thread = threading.Thread(target=hold_journal)
        thread.start()
        self.assertTrue(locked.wait(1))
        try:
            started = time.monotonic()
            self.prepare()
            health = self.service.health()
            self.assertLess(time.monotonic()-started, .15)
            self.assertTrue(health['camera_ready'])
            self.assertFalse(health['ready'])
        finally:
            release.set()
            thread.join(2)

    def test_full_command_queue_never_dispatches_or_synchronously_writes_error(self):
        context = self.prepare()
        saved = self.persist(context)
        self.service.commands.put_nowait({'already': 'occupied'})
        with patch.object(self.journal, 'finish', side_effect=AssertionError('sync write')):
            with self.assertRaisesRegex(ConflictError, 'COMMAND_QUEUE_FULL'):
                self.service.activate_production_admission(context, saved)
        self.assertEqual(self.service.state, 'RECOVERY')
        self.assertIsNone(self.service.active)
        self.assertEqual(self.service.commands.qsize(), 1)

    def test_storage_worker_delay_preserves_health_and_defers_dispatch(self):
        from apps.edge_service.result_storage import ResultStorage
        storage = ResultStorage(self.journal)
        self.addCleanup(storage.close)
        entered = threading.Event()
        original = self.journal.admit
        def slow_admit(*args, **kwargs):
            with self.journal.lock:
                entered.set()
                time.sleep(.55)
                return original(*args, **kwargs)
        context = self.prepare()
        gaps = []
        with patch.object(self.journal, 'admit', side_effect=slow_admit):
            storage.submit_request(context, context.payload())
            self.assertTrue(entered.wait(1))
            previous = time.monotonic()
            while storage.request_completed.empty():
                health = self.service.health()
                current = time.monotonic()
                gaps.append(current-previous)
                previous = current
                self.assertTrue(health['camera_ready'])
                self.assertTrue(self.service.commands.empty())
                self.assertLess(current-context.prepared_monotonic, 2)
                time.sleep(.01)
            saved = storage.request_completed.get_nowait()
        self.assertIsNone(saved['error'])
        self.assertGreaterEqual(saved['duration_ms'], 550)
        self.assertLess(max(gaps), .15)
        self.service.activate_production_admission(context, saved)
        command = self.service.commands.get_nowait()
        self.assertEqual(command['durable_admission_monotonic'], saved['durable_monotonic'])

    def test_status_capacity_wait_does_not_hold_service_lock(self):
        entered, release = threading.Event(), threading.Event()
        values, errors = [], []
        capacity = self.journal.capacity
        def slow_capacity():
            entered.set()
            if not release.wait(2):
                raise TimeoutError('fixture capacity')
            capacity()
        def read_status():
            try:
                values.append(self.service.status())
            except Exception as error:
                errors.append(error)
        with patch.object(self.journal, 'capacity', side_effect=slow_capacity):
            thread = threading.Thread(target=read_status)
            thread.start()
            self.assertTrue(entered.wait(1))
            try:
                started = time.monotonic()
                health = self.service.health()
                self.assertLess(time.monotonic()-started, .15)
                self.assertTrue(health['camera_ready'])
                # Returned UI health must also reflect a state changed while
                # its independent SQL read was waiting.
                with self.service.lock:
                    self.service.state, self.service.error = 'RECOVERY', 'fixture fault'
            finally:
                release.set()
                thread.join(3)
        self.assertFalse(errors)
        self.assertEqual(values[0]['state'], 'RECOVERY')
        self.assertFalse(values[0]['ready'])
        self.assertEqual(values[0]['error'], 'fixture fault')

    def test_disk_health_check_is_measured_without_changing_failure_policy(self):
        with patch('apps.edge_service.inspection.shutil.disk_usage', side_effect=OSError('fixture')):
            health = self.service.health()
        self.assertEqual(health['error'], 'STORAGE_UNAVAILABLE')
        self.assertFalse(health['ready'])
        metric = self.service.health_diagnostics.snapshot()['latest']['HEALTH_DISK_CHECK']
        self.assertGreaterEqual(metric['duration_ms'], 0)

    def active_result(self):
        context = self.prepare()
        saved = self.persist(context)
        self.service.activate_production_admission(context, saved)
        active = self.service.commands.get_nowait()
        floor = active['durable_admission_monotonic']
        frames = [dict(frame_id='camera:'+str(i), sequence=i, camera_epoch='camera',
                       estimated_source_monotonic=floor+i*.002,
                       selected_at_monotonic=floor+i*.002+.0001) for i in range(1, 4)]
        result = dict(decision='PASS', observations=[dict(frame_id=f['frame_id'],
            freshness=dict(f, integrity={'valid': True})) for f in frames],
            fresh_frame=dict(trigger=active['trigger'], source_not_before_monotonic=floor,
                effective_source_not_before_monotonic=max(floor, active['trigger']['trigger_received_monotonic']),
                selected_frames=copy.deepcopy(frames)))
        time.sleep(.01)
        return result

    def test_worker_result_cannot_claim_precommit_or_mismatched_frame_evidence(self):
        valid = self.active_result()
        self.assertIsNone(self.service._result_context_error(valid))
        changes = {
            'missing floor': lambda r: r['fresh_frame'].pop('source_not_before_monotonic'),
            'wrong floor': lambda r: r['fresh_frame'].update(source_not_before_monotonic=0),
            'wrong effective': lambda r: r['fresh_frame'].update(effective_source_not_before_monotonic=0),
            'missing selection': lambda r: r['fresh_frame'].pop('selected_frames'),
            'wrong id': lambda r: r['fresh_frame']['selected_frames'][0].update(frame_id='wrong'),
            'order': lambda r: r['fresh_frame']['selected_frames'].reverse(),
            'wrong sequence': lambda r: r['observations'][0]['freshness'].update(sequence=99),
            'different source': lambda r: r['observations'][0]['freshness'].update(estimated_source_monotonic=0),
            'no observed originals': lambda r: r.update(observations=[]),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                altered = copy.deepcopy(valid)
                change(altered)
                self.assertIsNotNone(self.service._result_context_error(altered))
        altered = copy.deepcopy(valid)
        floor = self.service.active['durable_admission_monotonic']
        for offset in (0, .001):
            altered['fresh_frame']['selected_frames'][0]['estimated_source_monotonic'] = floor+offset
            altered['observations'][0]['freshness']['estimated_source_monotonic'] = floor+offset
            self.assertEqual(self.service._result_context_error(altered),
                             'ADMISSION_FRAME_BEFORE_DURABILITY_OR_OUT_OF_ORDER')

    def test_service_stamps_authoritative_floor_only_after_result_validation(self):
        result = self.active_result()
        result['durable_admission_monotonic'] = -999  # Worker cannot own this field.
        service = self.service
        service.backend = {'backend': 'fixture'}
        service.storage = NS(completed=queue.Queue(), submit=Mock())
        service.results, service.previews = queue.Queue(), queue.Queue()
        service.results.put(dict(type='result', generation=service.generation,
            inspection_id=service.active['inspection_id'], result=result, images=[]))
        service.closed = NS(wait=Mock(side_effect=[False, True]))
        service.lab.tick = Mock()
        service.mock.tick = Mock()
        service._monitor_loop()
        service.storage.submit.assert_called_once()
        message = service.storage.submit.call_args.args[1]
        self.assertEqual(message['result']['durable_admission_monotonic'],
                         service.active['durable_admission_monotonic'])

    def test_legacy_submit_camera_check_does_not_call_status(self):
        self.service.production_owner.operating = False
        request = dict(self.service.allocate_request(), kind='inspect', control_mode='manual',
                       view_assessment={})
        with patch.object(self.service, 'status', side_effect=AssertionError('UI SQL path')):
            row, created = self.service.submit(request)
        self.assertTrue(created)
        self.assertEqual(self.service.commands.get_nowait()['inspection_id'], row['inspection_id'])


if __name__ == '__main__':
    unittest.main()
