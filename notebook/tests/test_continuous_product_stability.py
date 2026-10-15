"""Replay-shaped gaps and Request/proof ordering; no hardware qualification."""
import unittest
import threading
from types import SimpleNamespace
from unittest.mock import patch

from notebook.tests import test_automatic_runtime as automatic
from notebook.tests import test_product_passage_field as field
from notebook.tests.test_line_presentation import status
from src.runtime.standalone_web import line_view
from src.runtime.consumed_frames import ConsumedFrames
from src.runtime.standalone import StandaloneRuntime


class EntryContinuityTests(unittest.TestCase):
    def passage(self):
        f = field.FieldPassageTests()
        f.setUp()
        f.outbound()
        for _ in range(20):
            f.frame(None)
        return f

    def test_one_missing_observation_does_not_relabel_entry_as_old_product(self):
        for mode in ('queue_gap', 'detector_miss'):
            with self.subTest(mode=mode):
                f = self.passage()
                f.frame((.85,.24,1.,.86))
                f.frame((.80,.24,.99,.86))
                if mode == 'detector_miss': f.frame(None)
                f.frame((.73,.24,.96,.86), gap=2 if mode=='queue_gap' else 1)
                self.assertFalse(f.p.invalid, f.p.reason)
                self.assertIsNone(f.p.proof)
                proof = None
                for i in range(15):
                    proof = f.frame((.72-.01*i,.24,.95-.01*i,.86)) or proof
                    if proof: break
                self.assertIsNotNone(proof, f.p.status())
                self.assertFalse(proof['product_exit_claimed'])

    def test_missing_entry_cannot_be_replaced_by_a_middle_box(self):
        f = self.passage()
        f.frame((.85,.24,1.,.86))
        for _ in range(14): f.frame(None)
        for _ in range(15): f.frame((.35,.24,.65,.86))
        self.assertIsNone(f.p.proof)


class RequestOrderingTests(unittest.TestCase):
    setUp = automatic.AutomaticRuntimeTests.setUp
    observe = automatic.AutomaticRuntimeTests.observe
    trigger = automatic.AutomaticRuntimeTests.trigger
    complete = automatic.AutomaticRuntimeTests.complete
    frame = automatic.AutomaticRuntimeTests.frame
    poll = automatic.AutomaticRuntimeTests.poll
    request_and_complete = automatic.AutomaticRuntimeTests.request_and_complete
    next_request = automatic.AutomaticRuntimeTests.next_request

    def outbound_and_entry(self):
        self.first = self.request_and_complete(1,'PASS')
        # Outbound body crosses the right edge but has no shrinking tail.
        for left,right in ((.2,.8),(.3,.9),(.4,1.),(.5,1.),(.6,1.),(.7,1.)):
            self.frame(box=dict(x1=left,y1=.1,x2=right,y2=.6))
            self.poll()
        for _ in range(8):
            self.frame(count=0)
            self.poll()
        # A new engine visibly enters the left edge before Request rises.
        self.frame(box=dict(x1=0.,y1=.1,x2=.15,y2=.6))
        self.poll()

    def finish_entry(self):
        for right in (.18,.21,.24,.27):
            self.frame(box=dict(x1=0.,y1=.1,x2=right,y2=.6))
            self.poll()
        self.frame(box=dict(x1=.02,y1=.1,x2=.29,y2=.6))
        self.poll()

    def test_request_can_wait_for_same_entry_proof_then_inspect_once(self):
        self.outbound_and_entry()
        self.next_request()
        self.assertEqual(len(self.submitted),1)
        self.finish_entry()
        self.trigger(self.at+.1)
        self.assertEqual(len(self.submitted),2, self.r.automatic_identity_block)
        self.assertIsNone(self.r.automatic_identity_block)
        proof = self.r.request_product_separation
        self.assertEqual(proof['inspection_id'],self.first)
        self.assertLessEqual(proof['upstream_entry']['first_time'],self.r.handshake.accepted_at)
        self.assertNotEqual(self.submitted[0]['runtime_binding']['cycle_id'],
                            self.submitted[1]['runtime_binding']['cycle_id'])
        self.trigger(self.at+.12)
        self.assertEqual(len(self.submitted),2)
        self.assertEqual(self.g.result.call_count,1)
        self.g.automatic_arm.assert_not_called()

    def test_new_product_first_seen_after_request_cannot_inherit_it(self):
        self.request_and_complete(1,'PASS')
        self.next_request()
        for left,right in ((.2,.8),(.3,.9),(.4,1.),(.5,1.),(.6,1.),(.7,1.)):
            self.frame(box=dict(x1=left,y1=.1,x2=right,y2=.6)); self.poll()
        for _ in range(8): self.frame(count=0); self.poll()
        self.frame(box=dict(x1=0.,y1=.1,x2=.15,y2=.6)); self.poll()
        self.finish_entry()
        self.trigger(self.at+.1)
        self.assertEqual(len(self.submitted),1)

    def test_stop_or_connection_change_cannot_resolve_pending_request(self):
        for cause in ('stop','connection'):
            with self.subTest(cause=cause):
                if cause=='connection': self.setUp()
                self.outbound_and_entry()
                self.next_request()
                if cause=='stop':
                    self.g.s.update(phase='DISARMED',reason='PLC_CONTROL_INHIBIT')
                    self.g.s['controls']['Mc_Run']=False
                else:
                    self.g.s.update(connection=2)
                self.poll()
                self.finish_entry()
                self.trigger(self.at+.1)
                self.assertEqual(len(self.submitted),1)
                self.assertEqual(self.g.result.call_count,1)

    def test_pending_entry_does_not_bypass_epoch_storage_or_expired_request(self):
        for cause in ('epoch', 'storage_error', 'deadline'):
            with self.subTest(cause=cause):
                if cause != 'epoch': self.setUp()
                self.outbound_and_entry()
                self.next_request()
                if cause == 'epoch':
                    self.r.arrival['epoch'] = 'changed-camera'
                elif cause == 'storage_error':
                    self.r.error = 'JOURNAL_COMMIT_FAILED'
                else:
                    self.r.handshake.accepted_at -= 20
                self.finish_entry()
                self.trigger(self.at+.1)
                self.assertEqual(len(self.submitted), 1)
                if cause == 'deadline':
                    # Preserve the existing durable no-AI ERROR -> NG policy.
                    self.assertEqual(self.g.result.call_count, 2)
                    self.assertEqual(self.r.history[0]['decision'], 'ERROR')
                else:
                    self.assertEqual(self.g.result.call_count, 1)


class ConsumedCheckpointTests(unittest.TestCase):
    def test_diagnostic_copy_does_not_hold_runtime_control_lock(self):
        runtime = SimpleNamespace(lock=threading.RLock(), consumed_frames=ConsumedFrames())
        copying = threading.Event()
        release = threading.Event()
        errors = []
        def slow_copy(value):
            copying.set()
            release.wait(2)
            return value
        def read():
            try: StandaloneRuntime.consumed_frame_snapshot(runtime)
            except Exception as error: errors.append(error)
        # Large copies represent a diagnostic reader, never a hardware worker.
        with patch('src.runtime.consumed_frames.deepcopy', side_effect=slow_copy):
            thread = threading.Thread(target=read)
            thread.start()
            try:
                self.assertTrue(copying.wait(1))
                acquired = runtime.lock.acquire(timeout=.1)
                if acquired: runtime.lock.release()
                self.assertTrue(acquired, 'diagnostic copy blocks the control/health loop')
            finally:
                release.set()
                thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])

    def test_checkpoint_is_bounded_independent_and_excluded_from_regular_status(self):
        frames = ConsumedFrames()
        state = dict(invalid=False, entry=dict(samples=1))
        for sequence in range(1200):
            frames.record(dict(frame_id=f'e:{sequence}', sequence=sequence,
                camera_epoch='e', generation='g', integrity=dict(valid=True)),
                consumed_at=sequence, passage_state=state)
            if sequence > 1180: frames.checkpoint('test', state)
        state['entry']['samples'] = 99
        result = frames.snapshot(4)
        self.assertEqual(result['retained'], 1024)
        self.assertEqual(len(result['frames']), 4)
        self.assertEqual(result['checkpoints'], [])
        recorded = frames.snapshot(include_checkpoints=True)
        self.assertEqual(len(recorded['checkpoints']), 4)
        self.assertEqual(len(recorded['checkpoints'][0]['frames']), 128)
        self.assertEqual(recorded['frames'][-1]['passage_state']['entry']['samples'], 1)
        recorded['checkpoints'][0]['context']['entry']['samples'] = 100
        self.assertEqual(frames.snapshot(include_checkpoints=True)['checkpoints'][0]['context']['entry']['samples'], 1)


class PassagePresentationTests(unittest.TestCase):
    def test_idle_observation_is_not_a_failed_request(self):
        s=status();s['line_state']='WAIT_PLC_REQUEST'
        s['plc'].update(contract_version='OPENER_CYCLIC',network_plc_writes_enabled=True)
        s['plc_cycle']=dict(reason='WAIT_PLC_REQUEST',product_identity_reason='WAIT_OUTBOUND_PRODUCT_TRAJECTORY',
                           product_passage=dict(invalid=False))
        v=line_view(s,{})
        self.assertEqual(v['title'],'다음 제품 준비 중 — 이전 제품 이동 관찰')
        self.assertEqual(v['phase'],'WAIT_PRODUCT_MOVEMENT')
        self.assertEqual(v['verdict'],'NOT_RUN')
        s['plc'].update(state='REQUEST_LATCHED',Inspection_Request=True)
        s['plc_cycle']['request_identity_block']='PREVIOUS_PRODUCT_IDENTITY_OR_EXIT_UNPROVEN'
        v=line_view(s,{})
        self.assertEqual(v['title'],'새 제품 식별 실패 — 검사 미실행')
        self.assertEqual(v['verdict'],'NOT_RUN')


if __name__=='__main__': unittest.main()
