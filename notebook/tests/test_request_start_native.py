"""Real AF_UNIX C/health/admission/storage path; synthetic frames and AI only.

The C fixture does not link EtherNet/IP or open a PLC network socket. Runtime
owns every health renewal: the test never sends an unconditional READY pulse.
"""
from contextlib import contextmanager
import copy
import hashlib
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'jetson'))
from apps.edge_service.result_storage import ResultStorage
from notebook.tests.test_full_frame_request import FakeC, ZONE, packet
from notebook.tests import test_production_admission as admission_fixture
from src.control.opener_cyclic import OpenerGateway
from src.runtime.auto_adapters import LocalResultOutput, WorkerObservationSource
from src.runtime.cell_supervisor import FaultPolicy
from src.runtime.inspection_start import FULL_FRAME
from src.runtime.production_profile import calibration_sha, tracker_config
from src.runtime.standalone import AUTO_POLICY, StandaloneRuntime
from src.runtime.vision_coordinator import VisionRuntimeCoordinator
import src.journal.request_start as journal_start


def make_service(test):
    fixture = admission_fixture.ProductionAdmissionTests()
    fixture.setUp()
    test.addCleanup(fixture.doCleanups)
    service, journal = fixture.service, fixture.journal
    service.generation = 'g'
    service.package = NS(manifest_hash='sha', snapshot=lambda: {
        'manifest_sha256': 'sha', 'manifest': {'product_id': 'synthetic', 'release_id': 'fixture'}})
    service.products = queue.Queue(maxsize=16)
    service.production_tracking = threading.Event()
    service.storage = ResultStorage(journal)
    test.addCleanup(service.storage.close)
    service.preview.update(generation='g', freshness={'camera_epoch': 'e'})
    return service, journal


def make_runtime(service, gateway):
    profile = dict(mode='EXISTING_PLC_INSPECTION', min_free_bytes=0,
        field_profile_verified=False, arrival_deadline_s=8, assembly_deadline_s=30,
        inspection_start_policy=FULL_FRAME, cycle_admission=AUTO_POLICY,
        initial_authorization=AUTO_POLICY,
        request_start_qualification=dict(verified=True, policy=FULL_FRAME,
            calibration_sha=calibration_sha(service.calibration), evidence='SYNTHETIC_FIXTURE_ONLY'),
        automatic_operation_qualification=dict(policy=AUTO_POLICY,
            calibration_sha=calibration_sha(service.calibration), exit_edge='right',
            passage_policy='PRODUCT_TRAJECTORY_AND_EXIT_STRIP'),
        clearance_qualification={'verified': False})
    cfg = tracker_config(ZONE, wait_area_clear=True, plc_request_tracking=True)
    coordinator = VisionRuntimeCoordinator('a'*32, cfg)
    assembly = NS(ready=True, status=lambda: dict(ready=True, outstanding=0,
        pending=None, active_identifier=None))
    with patch('threading.Thread.start'):
        return StandaloneRuntime(service, coordinator, WorkerObservationSource(),
            LocalResultOutput(), NS(), cfg, FaultPolicy(), zone=copy.deepcopy(ZONE),
            area_config_version='synthetic', area_reference_required=False,
            gateway=gateway, line_profile=profile, assembly=assembly)


class RequestStartFixtureConstructionTests(unittest.TestCase):
    def test_native_fixture_profile_constructs_actual_runtime_without_IPC(self):
        service, _ = make_service(self)
        gateway = FakeC()
        gateway.set(time.monotonic(), 'DISARMED', number=0, request=False, Mc_Run=False)
        runtime = make_runtime(service, gateway)
        self.assertIs(service.production_owner, runtime)
        self.assertIsNotNone(runtime.request_start)
        self.assertTrue(runtime._profile_ready())
        self.assertFalse(runtime._automatic_readiness()['unattended_recovery_verified'])


@unittest.skipUnless(os.environ.get('SUPERVISED_IPC_FIXTURE'), 'native AF_UNIX fixture required')
class RequestStartNativeTests(unittest.TestCase):
    def test_single_START_three_cycles_survive_each_slow_request_stage(self):
        self._exercise_native()

    def test_STOP_during_admit_cancels_late_commit_without_camera_or_result(self):
        self._exercise_native(stop_during_admit=True)

    def test_single_START_twelve_cycles_delay_matrix_has_no_accumulating_pending_work(self):
        self._exercise_native(delay_matrix=True)

    def test_admitted_request_waits_for_current_frame_without_duplicate_dispatch(self):
        self._exercise_native(frame_wait=True)

    def test_observation_timeout_ERROR_then_PASS_FAIL_on_one_START(self):
        self._exercise_native(observation_timeout=True)

    def _exercise_native(self, *, stop_during_admit=False, delay_matrix=False, frame_wait=False,
                         observation_timeout=False):
        import cv2
        import numpy as np
        from src.vision.inspection_worker import put_latest
        service, journal = make_service(self)
        if observation_timeout:
            service.station['fresh_frame']['inspection_window_ms'] = 3000
        renewals = []
        # AF_UNIX sockaddr_un has a small path limit. Deployment verification
        # may set TMPDIR to a deeply nested release path, so do not inherit it.
        with tempfile.TemporaryDirectory(prefix='eai-admission-', dir='/tmp') as folder:
            root = Path(folder)
            os.chmod(root, 0o700)
            self.assertLess(len(os.fsencode(root / 'ipc')), 108)
            process = subprocess.Popen([os.environ['SUPERVISED_IPC_FIXTURE'], str(root/'ipc'), 'automatic'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            gateway = None
            try:
                deadline = time.monotonic() + 3
                while not (root/'ipc').exists() and time.monotonic() < deadline and process.poll() is None:
                    time.sleep(.01)
                if process.poll() is not None:
                    stdout, stderr = process.communicate(timeout=1)
                    self.fail(str(dict(reason='native fixture exited before IPC bind',
                        returncode=process.returncode, ipc=str(root/'ipc'), stdout=stdout, stderr=stderr)))
                self.assertTrue((root/'ipc').exists(), str(root/'ipc'))
                gateway = OpenerGateway(root/'ipc', writes_enabled=True)
                actual_health = gateway.health_update

                def record_health(ready, clear, now):
                    renewals.append((now, ready, clear))
                    actual_health(ready, clear, now)

                gateway.health_update = record_health
                # A connected snapshot is observed read-only before Runtime
                # initialization. No test-generated heartbeat or START occurs.
                deadline = time.monotonic() + 3
                while not gateway.read_snapshot(time.monotonic()) and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertIsNotNone(gateway.read_snapshot(time.monotonic()))
                runtime = make_runtime(service, gateway)
                # AI/assembly is supplied below as explicit synthetic raw
                # results; request/track admission and final publication are real.
                runtime._poll_result = lambda now: None
                sequence = 0
                feed = False
                cycle_number = 0
                frame_wait_injected = False
                qualification_misses = 0
                frame_wait_receipts = []

                original_completion = service.storage.request_completed.get_nowait

                def completed_receipt():
                    nonlocal sequence, frame_wait_injected, qualification_misses
                    saved = original_completion()
                    pending = runtime.request_start.pending
                    if ((frame_wait or observation_timeout) and not frame_wait_injected
                            and cycle_number == (1 if observation_timeout else 3)
                            and pending and pending['kind'] == 'admit'):
                        # Inject after an actual durable receipt is retrieved,
                        # not a racy queue.empty() check before writer completion.
                        # Use the same observation consumer as the real Runtime.
                        frame_wait_injected = True
                        qualification_misses = 10000 if observation_timeout else 3
                        sequence += 1
                        now = time.monotonic()
                        observation = packet(sequence, now-.002, count=0)
                        observation['processed_monotonic'] = now
                        runtime._packet(observation)
                    return saved

                service.storage.request_completed.get_nowait = completed_receipt

                def step():
                    nonlocal sequence, frame_wait_injected, qualification_misses
                    now = time.monotonic()
                    service.heartbeat.value = now
                    service.preview_received = now
                    service.preview = dict(generation='g', freshness={'camera_epoch': 'e'})
                    sequence += 1
                    observation = packet(sequence, now - .002,
                        count=0 if qualification_misses else int(feed))
                    if qualification_misses:
                        qualification_misses -= 1
                    observation['processed_monotonic'] = now
                    # Match the real camera's bounded latest-preview channel.
                    # Persistence may temporarily defer consumption; a preview
                    # overflow replaces its oldest item instead of raising.
                    put_latest(service.products, observation)
                    with runtime.lock, service.lock:
                        service._storage_completions()
                        if runtime._poll_completion_audit(time.monotonic()):
                            return
                        if runtime.request_start.tick(time.monotonic()):
                            pending = runtime.request_start.pending
                            if frame_wait and pending and pending.get('activation_receipt'):
                                receipt = pending['activation_receipt']
                                frame_wait_receipts.append(receipt)
                                self.assertIs(receipt, frame_wait_receipts[0])
                                self.assertEqual(service.state, 'ADMITTING')
                                self.assertTrue(service.commands.empty())
                                self.assertIsNone(runtime.handshake.inspection_id)
                            return
                        if not journal.lock.acquire(blocking=False):
                            runtime._storage_wait_health(time.monotonic())
                            return
                        try:
                            runtime._acquisition(time.monotonic())
                            runtime._poll_plc(time.monotonic())
                            if runtime.audit_pending:
                                return
                            while True:
                                try:
                                    runtime._packet(service.products.get_nowait())
                                except queue.Empty:
                                    break
                            runtime._poll_final_commit(time.monotonic())
                            if not runtime.audit_pending:
                                runtime._trigger(time.monotonic())
                        finally:
                            journal.lock.release()

                def wait(predicate, *, timeout=5, allow_error=False):
                    until = time.monotonic() + timeout
                    while time.monotonic() < until:
                        step()
                        if not allow_error:
                            self.assertIsNone(runtime.error, dict(error=runtime.error,
                                phase=runtime.phase, pending=runtime.request_start.pending,
                                line_wait=runtime.line_wait, snapshot=gateway.read_snapshot(time.monotonic())))
                        snapshot = gateway.read_snapshot(time.monotonic())
                        if snapshot and predicate(snapshot):
                            return snapshot
                        time.sleep(.01)
                    self.fail(str(dict(snapshot=gateway.read_snapshot(time.monotonic()),
                        phase=runtime.phase, pending=runtime.request_start.pending,
                        handshake=runtime.handshake.status(), ready=runtime.request_start.readiness,
                        issue=runtime.issue)))

                # Python's queued health value is not C's stopped-baseline
                # acknowledgement. START must follow the actual C transition.
                wait(lambda s: runtime.request_start.ready(s) and gateway.health[0]
                    and s['phase'] == 'SYNC_LOW' and s['reason'] == 'WAIT_PLC_RUN_AND_REQUEST_LOW'
                    and s['controls'] == dict(Inspection_Request=False, Mc_Run=False,
                        EStop_OK=True, Stop_PB=True))
                process.stdin.write('S')
                process.stdin.flush()
                wait(lambda s: s['phase'] == 'IDLE')

                original_event, original_admit = journal._event, journal.admit
                original_finish, original_final = journal.finish, journal.commit_integrated
                original_transaction = journal_start.transaction
                delayed = []
                cases = [(stage, delay) for stage in ('admit', 'raw', 'final')
                         for delay in (.350, .450, .600, 1.)] if delay_matrix else []
                stage_times = []
                def inject(stage):
                    if not cases or not cycle_number:
                        return
                    wanted, delay = cases[cycle_number-1]
                    marker = (cycle_number, stage)
                    if wanted == stage and marker not in delayed:
                        delayed.append(marker)
                        before = time.monotonic()
                        time.sleep(delay)
                        stage_times.append(dict(cycle=cycle_number, stage=stage,
                            injected_ms=delay*1000, observed_ms=(time.monotonic()-before)*1000))

                def slow_event(name, payload):
                    if not delay_matrix and cycle_number == 1 and name == 'OPENER_AI_REQUEST_ACCEPTED' and 'event' not in delayed:
                        delayed.append('event')
                        time.sleep(.55)
                    return original_event(name, payload)

                @contextmanager
                def slow_transaction(target, timings, stage):
                    with original_transaction(target, timings, stage):
                        yield
                        if not delay_matrix and cycle_number == 2 and stage == 'counter' and 'counter' not in delayed:
                            delayed.append('counter')
                            time.sleep(.55)

                def slow_admit(*args, **kwargs):
                    inject('admit')
                    if not delay_matrix and cycle_number == 3 and 'admit' not in delayed:
                        delayed.append('admit')
                        time.sleep(.55)
                    return original_admit(*args, **kwargs)

                def slow_finish(*args, **kwargs):
                    inject('raw')
                    return original_finish(*args, **kwargs)

                def slow_final(*args, **kwargs):
                    inject('final')
                    return original_final(*args, **kwargs)

                with patch.object(journal, '_event', side_effect=slow_event), \
                        patch.object(journal, 'admit', side_effect=slow_admit), \
                        patch.object(journal, 'finish', side_effect=slow_finish), \
                        patch.object(journal, 'commit_integrated', side_effect=slow_final), \
                        patch.object(journal_start, 'transaction', slow_transaction):
                    if stop_during_admit:
                        entered, release = threading.Event(), threading.Event()

                        def blocked_admit(*args, **kwargs):
                            entered.set()
                            if not release.wait(3):
                                raise TimeoutError('native STOP fixture admission release')
                            return original_admit(*args, **kwargs)

                        try:
                            with patch.object(journal, 'admit', side_effect=blocked_admit), \
                                    patch.object(journal, 'cancel', wraps=journal.cancel) as cancel:
                                feed = True
                                process.stdin.write('R')
                                process.stdin.flush()
                                wait(lambda s: entered.is_set())
                                pending = runtime.request_start.pending
                                request_token = pending['token']
                                reservation = service.production_admission_pending
                                self.assertIsNotNone(reservation)
                                self.assertTrue(service.commands.empty())
                                process.stdin.write('T')
                                process.stdin.flush()
                                wait(lambda s: pending['aborted'] is not None, allow_error=True)
                                self.assertIsNotNone(runtime.error)
                                self.assertFalse(gateway.health[0])
                                self.assertIs(service.production_admission_pending, reservation)
                                self.assertIsNone(service.active)
                                self.assertTrue(service.commands.empty())
                                release.set()
                                snapshot = wait(lambda s: runtime.request_start.pending is None
                                    and service.production_admission_pending is None, allow_error=True)
                                self.assertEqual(cancel.call_count, 1)
                        finally:
                            release.set()
                        self.assertEqual([row[0] for row in journal.db.execute(
                            'SELECT state FROM inspections').fetchall()], ['CANCELLED'])
                        self.assertIsNone(service.active)
                        self.assertTrue(service.commands.empty())
                        self.assertIsNone(runtime.handshake.inspection_id)
                        self.assertEqual(runtime.aborted_inspection['request_token'], request_token)
                        self.assertEqual(tuple(snapshot[key] for key in
                            ('result_count', 'done_count', 'completed_count')), (0, 0, 0))
                    decisions = (('ERROR', 'PASS', 'FAIL') if observation_timeout else
                        ('PASS', 'REVIEW', 'FAIL') * 4 if delay_matrix else ('PASS', 'FAIL', 'PASS'))
                    cycles = () if stop_during_admit else enumerate(decisions, 1)
                    for cycle_number, decision in cycles:
                        wait(lambda s: s['phase'] == 'IDLE' and runtime.request_start.ready(s))
                        feed = True
                        process.stdin.write('R')
                        process.stdin.flush()
                        if observation_timeout and cycle_number == 1:
                            snapshot = wait(lambda s: s['completed_count'] == cycle_number,
                                            timeout=6)
                            self.assertTrue(service.commands.empty())
                            rows = journal.db.execute('SELECT inspection_id,state FROM inspections').fetchall()
                            self.assertEqual(len(rows), 1)
                            row = journal.detail(rows[0]['inspection_id'])
                            self.assertEqual(row['state'], 'COMPLETE')
                            self.assertEqual(row['result']['decision'], 'ERROR')
                            self.assertEqual(row['result']['reason_code'],
                                             'ADMISSION_OBSERVATION_DEADLINE_EXCEEDED')
                            self.assertEqual(row['result']['observations'], [])
                            self.assertEqual(row['result']['assets'], [])
                            self.assertEqual(tuple(snapshot[key] for key in
                                ('result_count', 'done_count', 'completed_count')), (1, 1, 1))
                            self.assertEqual(runtime.history[0]['inspection_id'], row['inspection_id'])
                            self.assertEqual(runtime.history[0]['decision'], 'ERROR')
                            qualification_misses = 0
                            wait(lambda s: s['phase'] == 'IDLE' and runtime.request_start.ready(s)
                                 and not runtime.request_start.pending and not runtime.audit_pending)
                            continue
                        wait(lambda s: not service.commands.empty())
                        command = service.commands.get_nowait()
                        identifier = command['inspection_id']
                        self.assertEqual(journal.detail(identifier)['state'], 'ACCEPTED')
                        self.assertGreaterEqual(command['accepted_monotonic'], command['durable_admission_monotonic'])
                        self.assertEqual(runtime.handshake.inspection_id, identifier)
                        # Drain the BOUND audit via the same health owner; no
                        # test pulse can mask its write latency or a stale lease.
                        wait(lambda s: runtime.request_start.pending is None and not runtime.request_start.events)
                        observations, images, checks = [], [], []
                        for index in range(3):
                            time.sleep(.003)
                            source = time.monotonic()
                            pixels = np.full((8, 8, 3), cycle_number*20+index, np.uint8)
                            frame_id = identifier + ':' + str(index)
                            fresh = dict(frame_id=frame_id, camera_epoch='e', sequence=sequence+index+1,
                                estimated_source_monotonic=source, selected_at_monotonic=time.monotonic(),
                                integrity={'valid': True})
                            observations.append(dict(frame_id=frame_id, freshness=fresh,
                                input_pixel_sha256=hashlib.sha256(pixels.tobytes()).hexdigest()))
                            images.append(dict(kind='raw', data=cv2.imencode('.png', pixels)[1].tobytes(),
                                frame_id=frame_id, width=8, height=8))
                            checks.append(dict(frame_id=frame_id, failed_conditions=[]))
                        sequence += 3
                        raw = dict(decision=decision, reason='SYNTHETIC_NATIVE_FIXTURE',
                            observations=observations, production_frame_checks=checks,
                            production_identity=command['production_binding'],
                            execution={'source': 'mock', 'worker_generation': 'g'},
                            fresh_frame=dict(trigger=command['trigger'],
                                source_not_before_monotonic=command['durable_admission_monotonic'],
                                effective_source_not_before_monotonic=command['durable_admission_monotonic'],
                                selected_frames=[copy.deepcopy(item['freshness']) for item in observations]))
                        self.assertIsNone(service._result_context_error(raw))
                        raw['durable_admission_monotonic'] = command['durable_admission_monotonic']
                        service.storage_pending = dict(active=service.active, generation='g',
                            camera_epoch='e', inspection_id=identifier, started=time.monotonic())
                        service.storage.submit(service.storage_pending,
                            dict(inspection_id=identifier, result=raw, images=images))
                        wait(lambda s: service.storage_pending is None)
                        with runtime.lock, service.lock:
                            runtime.bridge.poll()
                            runtime._commit_and_publish(identifier, {'decision': decision}, time.monotonic())
                        snapshot = wait(lambda s: s['completed_count'] == cycle_number
                            and s['phase'] in ('READY_NEXT', 'IDLE'))
                        self.assertEqual(tuple(snapshot[key] for key in
                            ('result_count', 'done_count', 'completed_count')), (cycle_number,)*3)
                        self.assertEqual(snapshot['raw100'], '00000000')
                        self.assertEqual(runtime.history[0]['inspection_id'], identifier)
                        self.assertEqual(runtime.history[0]['decision'], decision)
                        wait(lambda s: s['phase'] == 'IDLE' and runtime.request_start.ready(s)
                             and not runtime.request_start.pending and not runtime.audit_pending)
                        self.assertIsNone(service.storage_pending)
                        self.assertIsNone(runtime.final_pending)
                        self.assertTrue(service.storage.jobs.empty())
                        self.assertEqual(journal.db.execute(
                            "SELECT count(*) FROM inspections WHERE state NOT IN ('COMPLETE','CANCELLED')").fetchone()[0], 0)
                if not stop_during_admit:
                    self.assertEqual(len(delayed), 12 if delay_matrix else 3)
                    if not delay_matrix:
                        self.assertEqual(delayed, ['event', 'counter', 'admit'])
                    self.assertEqual(journal.db.execute('SELECT count(*) FROM inspections').fetchone()[0], len(decisions))
                if frame_wait:
                    self.assertTrue(frame_wait_injected)
                    self.assertGreaterEqual(len(frame_wait_receipts), 2)
                    self.assertEqual(journal.db.execute(
                        "SELECT count(*) FROM inspections WHERE state='COMPLETE'").fetchone()[0], 3)
                gaps = [current[0]-previous[0] for previous, current in zip(renewals, renewals[1:])]
                self.assertLess(max(gaps), .4, dict(max_renewal_gap=max(gaps),
                    diagnostics=gateway.diagnostics.snapshot()))
                self.assertFalse(any(row.get('reason') == 'HEALTH_LEASE_EXPIRED'
                    for row in gateway.diagnostics.snapshot()['events']))
                self.assertTrue(all(not clear for _, _, clear in renewals))
                self.measurements = dict(
                    actual_field_plc=False, source='AF_UNIX_SYNTHETIC_PLC_WITH_REAL_RUNTIME',
                    injected_storage_delay_ms=550 if not stop_during_admit else None,
                    health_lease_ms=400, renewal_intervals=len(gaps),
                    renewal_gap_max_ms=max(gaps)*1000,
                    renewal_gap_p95_ms=float(np.percentile(gaps,95))*1000,
                    renewal_gap_p99_ms=float(np.percentile(gaps,99))*1000,
                    stage_delays=stage_times,
                    admission_frame_wait_ticks=len(frame_wait_receipts),
                    completed_cycles=0 if stop_during_admit else len(decisions))
            finally:
                failure_in_progress = sys.exc_info()[0] is not None
                if gateway:
                    gateway.close()
                if process.poll() is None:
                    try:
                        process.stdin.write('Q')
                        process.stdin.flush()
                    except BrokenPipeError:
                        pass
                stdout, stderr = process.communicate(timeout=3)
                if not failure_in_progress:
                    self.assertEqual(process.returncode, 0, stderr)
            self.assertIn('completed=' + ('0' if stop_during_admit else str(len(decisions))), stdout)


if __name__ == '__main__':
    unittest.main()
