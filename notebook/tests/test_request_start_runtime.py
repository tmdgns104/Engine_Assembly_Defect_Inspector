"""Control/admission integration with real SQLite; no physical PLC or camera."""
import copy
import queue
import threading
import time
import unittest
import sys
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
from contextlib import ExitStack

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'jetson'))
from notebook.tests import test_production_admission as admission_fixture
from apps.edge_service.result_storage import ResultStorage
from src.runtime.request_start import RequestStart
from notebook.tests.test_full_frame_request import packet


class RequestStartRuntimeTests(unittest.TestCase):
    def setUp(self):
        fixture = admission_fixture.ProductionAdmissionTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture, self.service, self.journal = fixture, fixture.service, fixture.journal
        self.service.storage = ResultStorage(self.journal)
        self.addCleanup(self.service.storage.close)
        self.service.products = queue.Queue()
        self.controls = dict(Inspection_Request=True, Mc_Run=True, EStop_OK=True, Stop_PB=True)
        self.connection, self.request_id = 1, 1
        self.phase = 'REQUEST_RECEIVED'
        self.health_updates = []
        self.connected = True
        self.r = NS(service=self.service, session_id='runtime', epoch='camera',
            operating=True, error=None, final_pending=None, audit_pending=None,
            cycle_issue=None, automatic_identity_block=None, aborted_inspection=None,
            bridge=NS(inspection_id=None), published_ids=set(), _automatic_previous=None,
            _diagnostic_events=None, inspected_tracks=set(),
            line_profile=dict(arrival_deadline_s=4),
            coordinator=NS(active_cycle=NS(cycle_id=3),_tracker=NS(_track_id=7)),
            assembly=NS(ready=True,status=lambda:dict(active_identifier=None,pending=None,outstanding=None)),
            _profile_ready=lambda:True, _commit_and_publish=Mock())
        self.r.gateway = NS(read_snapshot=self.snapshot,health_update=self.health_update,
                            contract_version='fixture',ready_reason=None)
        self.r.handshake = NS(token='0000000000000001:1:1',inspection_id=None,
            state='REQUEST_LATCHED',cancelled=False,cycle_id=3,session_id='line',
            accepted_at=time.monotonic()-.1)
        self.r.latest_packet = dict(packet(1,time.monotonic()-.02),camera_epoch='camera',generation='worker')
        self.r.handshake.bind = Mock(side_effect=self.bind)
        self.r.handshake.fault = Mock(side_effect=self.handshake_fault)
        self.r._fault = Mock(side_effect=self.runtime_fault)
        self.controller = RequestStart(self.r)
        self.r._event = Mock(side_effect=self.controller.event)
        self.binding = dict(fixture.binding,plc_request_token=self.r.handshake.token)

    def snapshot(self, now=None):
        now = time.monotonic()
        return dict(boot=1,connection=self.connection,request_id=self.request_id,
            connected=self.connected,fresh=True,run_idle=True,bool_valid=True,
            generated=now,received=now,phase=self.phase,controls=dict(self.controls))

    def health_update(self, ready, clear, now):
        self.health_updates.append((now,ready,clear))

    def bind(self, identifier):
        self.r.handshake.inspection_id = identifier
        self.r.handshake.state = 'INSPECTING'

    def handshake_fault(self, reason):
        self.r.handshake.cancelled = True
        self.r.handshake.state = 'RESYNC_REQUIRED'

    def runtime_fault(self, reason):
        self.r.error = reason
        self.service.cancellation.set()

    def tick(self):
        self.assertTrue(self.controller.tick(time.monotonic()))

    def drain_pending(self, timeout=3):
        deadline = time.monotonic()+timeout
        while self.controller.pending:
            self.assertLess(time.monotonic(),deadline,'controller job did not complete')
            self.tick()
            time.sleep(.005)

    def delay_admission(self, seconds):
        original = self.journal.admit
        entered = threading.Event()
        def delayed(*args,**kwargs):
            entered.set()
            time.sleep(seconds)
            return original(*args,**kwargs)
        with patch.object(self.journal,'admit',side_effect=delayed):
            self.controller.begin(self.binding,time.monotonic())
            self.assertTrue(entered.wait(1))
            deadline = time.monotonic()+seconds-.05
            while time.monotonic()<deadline:
                self.tick()
                self.assertTrue(self.service.commands.empty())
                self.assertEqual(self.r.handshake.bind.call_count,0)
                time.sleep(.02)
            self.drain_pending()
        self.assertIsNone(self.r.error, self.service.health_diagnostics.snapshot())
        command = self.service.commands.get_nowait()
        self.assertGreaterEqual(command['accepted_monotonic'],command['durable_admission_monotonic'])
        self.assertEqual(self.journal.detail(command['inspection_id'])['state'],'ACCEPTED')
        self.assertEqual(self.r.handshake.bind.call_count,1)
        live = [value for value in self.health_updates if value[1]]
        self.assertGreaterEqual(len(live),10)
        self.assertTrue(all(not clear for _,_,clear in self.health_updates))
        gaps = [b[0]-a[0] for a,b in zip(self.health_updates,self.health_updates[1:])]
        self.assertLess(max(gaps),.4,'control renewal exceeded unchanged 400ms lease')
        self.assertIsNone(self.r.error)

    def test_550ms_storage_delay_keeps_live_checks_without_early_dispatch(self):
        self.delay_admission(.55)

    def test_1000ms_storage_delay_keeps_live_checks_without_early_dispatch(self):
        self.delay_admission(1.)

    def wait_for_admission_receipt_with_preview_miss(self):
        """An actual SQLite receipt may arrive during one missing preview."""
        self.controller.begin(self.binding, time.monotonic())
        original_deadline = self.controller.pending['deadline']
        self.saved_trigger_deadline = self.controller.pending['reservation'].payload()['trigger']['deadline_monotonic']
        self.r.latest_packet['provider'] = dict(status='NO_FOREGROUND', observations=[])
        deadline = time.monotonic() + 2
        while not self.controller.pending.get('activation_receipt'):
            self.assertLess(time.monotonic(), deadline)
            self.tick()
            self.assertIsNone(self.r.error)
            self.assertTrue(self.service.commands.empty())
            time.sleep(.005)
        self.assertEqual(self.controller.pending['deadline'], original_deadline)
        return original_deadline

    def test_saved_admission_waits_for_current_frame_without_second_SQL_or_dispatch(self):
        original_deadline = self.wait_for_admission_receipt_with_preview_miss()
        row = self.journal.db.execute('SELECT inspection_id,state FROM inspections').fetchone()
        self.assertEqual(row['state'], 'ACCEPTED')
        with patch.object(self.journal, 'admit', side_effect=AssertionError('duplicate SQL')):
            for _ in range(3):
                self.tick()
                self.assertEqual(self.controller.pending['deadline'], original_deadline)
                self.assertIsNone(self.r.error)
                self.assertTrue(self.health_updates[-1][1])
                self.assertTrue(self.service.commands.empty())
            self.r.latest_packet = dict(packet(2, time.monotonic()-.001),
                                       camera_epoch='camera', generation='worker')
            self.drain_pending()
        command = self.service.commands.get_nowait()
        self.assertEqual(command['inspection_id'], row['inspection_id'])
        self.assertEqual(command['deadline'], self.saved_trigger_deadline)
        self.assertTrue(self.service.commands.empty())
        self.r.handshake.bind.assert_called_once()

    def test_STOP_while_saved_admission_waits_cancels_once_without_capture(self):
        self.wait_for_admission_receipt_with_preview_miss()
        self.controls['Mc_Run'] = False
        with patch.object(self.journal, 'cancel', wraps=self.journal.cancel) as cancel:
            self.drain_pending()
            cancel.assert_called_once()
        self.assertTrue(self.service.commands.empty())
        self.r.handshake.bind.assert_not_called()
        self.assertEqual(self.journal.db.execute('SELECT state FROM inspections').fetchone()[0], 'CANCELLED')

    def test_saved_admission_wait_never_restarts_deadline(self):
        self.wait_for_admission_receipt_with_preview_miss()
        self.controller.pending['deadline'] = time.monotonic()-1
        self.drain_pending()
        self.assertIn('REQUEST_STORAGE_DEADLINE_EXCEEDED', self.r.error)
        self.assertTrue(self.service.commands.empty())
        self.r.handshake.bind.assert_not_called()

    def test_changed_track_while_saved_admission_waits_remains_a_fault(self):
        self.wait_for_admission_receipt_with_preview_miss()
        self.r.coordinator._tracker._track_id += 1
        self.drain_pending()
        self.assertEqual(self.r.error, 'ADMISSION_CURRENT_TRACK_OR_REQUEST_CHANGED')
        self.assertTrue(self.service.commands.empty())
        self.r.handshake.bind.assert_not_called()

    def test_saved_admission_wait_keeps_live_owner_fault_checks(self):
        mutations = {
            'request_changed': lambda case: setattr(case, 'request_id', 2),
            'PLC_disconnected': lambda case: setattr(case, 'connected', False),
            'E_STOP': lambda case: case.controls.update(EStop_OK=False),
            'camera_lost': lambda case: setattr(case.service, 'preview_received', 0),
            'worker_changed': lambda case: setattr(case.service, 'generation', 'replacement'),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                case = RequestStartRuntimeTests()
                case.setUp()
                try:
                    case.wait_for_admission_receipt_with_preview_miss()
                    mutate(case)
                    case.drain_pending()
                    self.assertIsNotNone(case.r.error)
                    self.assertTrue(case.service.commands.empty())
                    case.r.handshake.bind.assert_not_called()
                    self.assertEqual(case.journal.db.execute('SELECT state FROM inspections').fetchone()[0], 'CANCELLED')
                finally:
                    case.doCleanups()

    def test_STOP_during_admit_cancels_one_late_row_and_never_dispatches(self):
        original, entered, release = self.journal.admit, threading.Event(), threading.Event()
        def blocked(*args,**kwargs):
            entered.set()
            if not release.wait(2):raise TimeoutError('fixture')
            return original(*args,**kwargs)
        try:
            with patch.object(self.journal,'admit',side_effect=blocked), \
                    patch.object(self.journal,'cancel',wraps=self.journal.cancel) as cancel:
                self.controller.begin(self.binding,time.monotonic())
                self.assertTrue(entered.wait(1))
                self.controls['Mc_Run'] = False
                self.tick()
                self.assertTrue(self.controller.pending['aborted'])
                self.assertFalse(self.health_updates[-1][1])
                release.set()
                self.drain_pending()
                self.assertEqual(cancel.call_count,1)
        finally:release.set()
        rows = self.journal.db.execute('SELECT state FROM inspections').fetchall()
        self.assertEqual([row[0] for row in rows],['CANCELLED'])
        self.assertTrue(self.service.commands.empty())
        self.r.handshake.bind.assert_not_called()
        self.assertIsNone(self.service.production_admission_pending)

    def test_foreign_completion_never_activates_pending_request(self):
        original, entered, release = self.journal.admit, threading.Event(), threading.Event()
        def blocked(*args,**kwargs):
            entered.set()
            if not release.wait(2):raise TimeoutError('fixture')
            return original(*args,**kwargs)
        try:
            with patch.object(self.journal,'admit',side_effect=blocked):
                self.controller.begin(self.binding,time.monotonic())
                self.assertTrue(entered.wait(1))
                pending = self.controller.pending
                self.service.storage.request_completed.put_nowait(dict(context=object(),error=None,result={}))
                self.tick()
                self.assertIs(self.controller.pending,pending)
                self.assertEqual(pending['aborted'],'REQUEST_STORAGE_COMPLETION_IDENTITY_MISMATCH')
                self.assertTrue(self.service.commands.empty())
                release.set()
                self.drain_pending()
        finally:release.set()
        self.assertTrue(self.service.commands.empty())
        self.r.handshake.bind.assert_not_called()
        self.assertEqual(self.journal.db.execute("SELECT count(*) FROM inspections WHERE state='CANCELLED'").fetchone()[0],1)

    def test_camera_loss_during_pending_storage_revokes_health_and_cancels(self):
        original, entered, release = self.journal.admit, threading.Event(), threading.Event()
        def blocked(*args,**kwargs):
            entered.set()
            if not release.wait(2):raise TimeoutError('fixture')
            return original(*args,**kwargs)
        try:
            with patch.object(self.journal,'admit',side_effect=blocked):
                self.controller.begin(self.binding,time.monotonic())
                self.assertTrue(entered.wait(1))
                self.service.preview_received = 0
                self.tick()
                self.assertIn('CAMERA',self.controller.pending['aborted'])
                self.assertFalse(self.health_updates[-1][1])
                release.set()
                self.drain_pending()
        finally:release.set()
        self.assertTrue(self.service.commands.empty())
        self.r.handshake.bind.assert_not_called()

    def test_pending_admission_current_context_fault_matrix(self):
        mutations = {
            'request_low': (lambda c: c.controls.update(Inspection_Request=False), 'CONTROL_CANCELLED'),
            'request_id': (lambda c: setattr(c,'request_id',2), 'CONTROL_CANCELLED'),
            'connection': (lambda c: setattr(c,'connection',2), 'OWNER_CHANGED'),
            'runtime_session': (lambda c: setattr(c.r,'session_id','replacement'), 'OWNER_CHANGED'),
            'package': (lambda c: setattr(c.service.package,'manifest_hash','replacement'), 'OWNER_CHANGED'),
            'generation': (lambda c: setattr(c.service,'generation','replacement'), 'OWNER_CHANGED'),
            'camera_epoch': (lambda c: c.service.preview['freshness'].update(camera_epoch='replacement'), 'OWNER_UNAVAILABLE'),
            'deadline': (lambda c: c.controller.pending.update(deadline=time.monotonic()-1), 'DEADLINE_EXCEEDED'),
            'storage_owner_dead': (lambda c: None, 'OWNER_UNAVAILABLE'),
            'PLC_disconnected': (lambda c: setattr(c,'connected',False), 'PLC_UNAVAILABLE'),
            'E_STOP': (lambda c: c.controls.update(EStop_OK=False), 'CONTROL_CANCELLED'),
            'STOP_PB': (lambda c: c.controls.update(Stop_PB=False), 'CONTROL_CANCELLED'),
        }
        for name,(mutate,expected) in mutations.items():
            with self.subTest(fault=name):
                case = RequestStartRuntimeTests()
                case.setUp()
                entered, release = threading.Event(), threading.Event()
                original = case.journal.admit
                def blocked(*args,**kwargs):
                    entered.set()
                    if not release.wait(2):raise TimeoutError('fixture')
                    return original(*args,**kwargs)
                try:
                    with ExitStack() as stack:
                        stack.enter_context(patch.object(case.journal,'admit',side_effect=blocked))
                        cancel = stack.enter_context(patch.object(case.journal,'cancel',wraps=case.journal.cancel))
                        case.controller.begin(case.binding,time.monotonic())
                        self.assertTrue(entered.wait(1))
                        mutate(case)
                        if name == 'storage_owner_dead':
                            stack.enter_context(patch.object(case.service.storage.thread,'is_alive',return_value=False))
                        before = time.monotonic()
                        case.tick()
                        self.assertLess(time.monotonic()-before,.15)
                        self.assertFalse(case.health_updates[-1][1])
                        self.assertIn(expected,case.controller.pending['aborted'])
                        self.assertTrue(case.service.commands.empty())
                        release.set()
                        case.drain_pending()
                        cancel.assert_called_once()
                    rows = case.journal.db.execute('SELECT inspection_id,state FROM inspections').fetchall()
                    self.assertEqual(len(rows),1)
                    self.assertEqual(rows[0]['state'],'CANCELLED')
                    self.assertEqual(cancel.call_args.args[0],rows[0]['inspection_id'])
                    self.assertTrue(case.service.commands.empty())
                    case.r.handshake.bind.assert_not_called()
                    self.assertIsNone(case.service.production_admission_pending)
                finally:
                    release.set()
                    case.doCleanups()

    def test_STOP_after_dispatch_during_bound_event_sets_cancellation_without_SQL(self):
        original = self.journal._event
        entered, release = threading.Event(), threading.Event()
        def blocked(name,payload):
            if name == 'PRODUCTION_INSPECTION_BOUND':
                entered.set()
                if not release.wait(2):raise TimeoutError('fixture')
            return original(name,payload)
        try:
            with patch.object(self.journal,'_event',side_effect=blocked):
                self.controller.begin(self.binding,time.monotonic())
                deadline = time.monotonic()+1
                while not entered.is_set():
                    self.assertLess(time.monotonic(),deadline)
                    self.tick()
                    time.sleep(.005)
                self.assertEqual(self.controller.pending['kind'],'events')
                self.assertIsNotNone(self.service.active)
                self.assertEqual(self.service.commands.qsize(),1)
                self.assertFalse(self.service.cancellation.is_set())
                self.r._fault = Mock()  # No fixture side effect can set the flag.
                self.controls['Mc_Run'] = False
                with ExitStack() as stack:
                    for method in ('finish','cancel','detail','capacity'):
                        stack.enter_context(patch.object(self.journal,method,
                            side_effect=AssertionError('CONTROL_THREAD_SQL_'+method)))
                    before = time.monotonic()
                    self.tick()
                    self.assertLess(time.monotonic()-before,.15)
                self.assertTrue(self.service.cancellation.is_set())
                self.assertFalse(self.health_updates[-1][1])
                self.r._fault.assert_called_once()
                release.set()
                self.drain_pending()
        finally:release.set()
        self.assertEqual(self.service.commands.qsize(),1)
        self.assertEqual(self.r.handshake.bind.call_count,1)

    def test_no_input_stores_ERROR_then_supplies_same_durable_row_without_capture(self):
        self.controller.no_input('ERROR','NO_CURRENT_PRODUCT',time.monotonic())
        self.drain_pending()
        self.assertTrue(self.service.commands.empty())
        self.r._commit_and_publish.assert_called_once()
        call = self.r._commit_and_publish.call_args
        identifier, final = call.args[:2]
        row = call.kwargs['durable_row']
        self.assertEqual(row['inspection_id'],identifier)
        self.assertEqual(row['result']['decision'],'ERROR')
        self.assertTrue(row['result']['storage_success'])
        self.assertEqual(row['result']['assets'],[])
        self.assertEqual(final['policy'],'NO_INPUT_IS_NEVER_PASS')
        self.assertEqual(self.journal.detail(identifier),row)

    def test_initial_readiness_never_renews_before_worker_evidence_is_complete(self):
        self.r.handshake.token = None
        self.r.handshake.state = 'IDLE'
        self.phase = 'IDLE'
        self.controls['Inspection_Request'] = False
        original, entered, release = self.journal.capacity, threading.Event(), threading.Event()
        def blocked():
            entered.set()
            if not release.wait(2):raise TimeoutError('fixture')
            return original()
        try:
            with patch.object(self.journal,'capacity',side_effect=blocked):
                self.controller._request_readiness(self.snapshot())
                self.assertTrue(entered.wait(1))
                for _ in range(3):
                    self.tick()
                    self.assertFalse(self.health_updates[-1][1])
                    self.assertFalse(self.controller.ready(self.snapshot()))
                release.set()
                self.drain_pending()
        finally:release.set()
        self.assertTrue(self.controller.ready(self.snapshot()))
        self.assertTrue(self.service.commands.empty())
        self.assertEqual(self.journal.db.execute('SELECT count(*) FROM inspections').fetchone()[0],0)

    def test_STOP_during_no_input_commit_preserves_ERROR_but_never_publishes(self):
        self.r.gateway.contract_version = 'OPENER_CYCLIC'
        original, entered, release = self.journal.finish, threading.Event(), threading.Event()
        def blocked(*args,**kwargs):
            entered.set()
            if not release.wait(2):raise TimeoutError('fixture')
            return original(*args,**kwargs)
        try:
            with patch.object(self.journal,'finish',side_effect=blocked):
                self.controller.no_input('ERROR','NO_CURRENT_PRODUCT',time.monotonic())
                self.assertTrue(entered.wait(1))
                self.controls['Mc_Run'] = False
                self.tick()
                release.set()
                self.drain_pending()
        finally:release.set()
        self.r._commit_and_publish.assert_not_called()
        self.r.handshake.bind.assert_not_called()
        self.assertTrue(self.service.commands.empty())
        rows = self.journal.db.execute('SELECT state,decision FROM inspections').fetchall()
        self.assertEqual([tuple(row) for row in rows],[('COMPLETE','ERROR')])
        from src.runtime.standalone import StandaloneRuntime
        restored = StandaloneRuntime.__new__(StandaloneRuntime)
        restored.service = self.service
        restored.aborted_inspection = None
        StandaloneRuntime._restore_aborted_inspection(restored)
        self.assertEqual(restored.aborted_inspection['inspection_id'],
                         self.r.aborted_inspection['inspection_id'])
        self.assertEqual(restored.aborted_inspection['request_token'], self.r.handshake.token)

    def test_restored_unresolved_abort_never_advertises_ready(self):
        self.r.handshake.token = None
        self.r.handshake.state = 'IDLE'
        self.phase = 'SYNC_LOW'
        self.controls.update(Inspection_Request=False, Mc_Run=False)
        self.r.aborted_inspection = dict(inspection_id='previous-cancelled', reason='STOP')
        self.controller._request_readiness(self.snapshot())
        self.drain_pending()
        self.assertFalse(self.controller.ready(self.snapshot()))
        self.assertEqual(self.controller.settlement()['reason'], 'UNRESOLVED_CANCELLED_REQUEST')
        self.assertTrue(all(not ready for _, ready, _ in self.health_updates))

    def test_full_storage_queue_releases_reservation_without_creating_inspection(self):
        entered, release = threading.Event(), threading.Event()
        original = self.journal._event
        def blocked(name,payload):
            if name == 'HOLD_STORAGE':
                entered.set()
                if not release.wait(2):raise TimeoutError('fixture')
            return original(name,payload)
        try:
            with patch.object(self.journal,'_event',side_effect=blocked):
                self.service.storage.submit_audit({'inspection_id':'fixture'},dict(event='HOLD_STORAGE'))
                self.assertTrue(entered.wait(1))
                self.service.storage.submit_final({},dict(inspection_id='not-an-inspection'))
                with self.assertRaises(queue.Full):
                    self.controller.begin(self.binding,time.monotonic())
                self.assertIsNone(self.service.production_admission_pending)
                self.assertIsNone(self.controller.pending)
                self.assertTrue(self.service.commands.empty())
                release.set()
                self.service.storage.audit_completed.get(timeout=2)
                self.service.storage.final_completed.get(timeout=2)
        finally:release.set()
        self.assertEqual(self.journal.db.execute('SELECT count(*) FROM inspections').fetchone()[0],0)


if __name__ == '__main__':
    unittest.main()
