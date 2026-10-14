"""Storage concurrency regression; no camera, network or PLC access."""
import threading
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
import os
from types import SimpleNamespace as NS
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'jetson'))
from src.journal.sqlite import Journal
from src.runtime.standalone import StandaloneRuntime
from apps.edge_service.inspection import InspectionService
from apps.edge_service.result_storage import ResultStorage


class JournalStorageConcurrency(unittest.TestCase):
    def test_asset_io_does_not_hold_journal_lock_and_cancel_wins(self):
        with tempfile.TemporaryDirectory() as root:
            journal = Journal(root, min_free_bytes=0)
            identifier, _ = journal.admit(dict(cell_id='t', plc_session_id=1,
                cycle_id=1, request_id=1, attempt=1), {})
            entered, release = threading.Event(), threading.Event()
            from src.journal.sqlite import atomic_write
            def slow(path, data):
                entered.set()
                if not release.wait(2): raise TimeoutError('test release')
                atomic_write(path, data)
            returned = []
            with patch('src.journal.sqlite.atomic_write', slow):
                worker = threading.Thread(target=lambda: returned.append(journal.finish(identifier,
                    dict(decision='REVIEW', reason='real result preserved'),
                    [dict(kind='raw',data=b'fixture',width=1,height=1)])))
                worker.start()
                self.assertTrue(entered.wait(1))
                acquired = journal.lock.acquire(timeout=.05)
                try:
                    if acquired: journal.cancel(identifier, 'STOP')
                finally:
                    if acquired: journal.lock.release()
                    release.set(); worker.join(3)
                self.assertTrue(acquired, 'image fsync held the Journal lock')
            self.assertEqual(returned, [None])
            self.assertEqual(journal.detail(identifier)['state'], 'CANCELLED')
            events = journal.db.execute("SELECT payload_json FROM events WHERE event_type='LATE_RESULT_QUARANTINED'").fetchall()
            self.assertIn('real result preserved', str(events[0][0]))
            journal.close()

    @unittest.skipUnless(os.environ.get('FIELD_PNG_DIR'), 'private recorded evidence is not in Git')
    def test_actual_three_png_bytes_survive_slow_storage(self):
        import cv2
        import numpy as np
        images=[]
        for path in sorted(Path(os.environ['FIELD_PNG_DIR']).glob('*.png')):
            data=path.read_bytes();image=cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_COLOR)
            self.assertEqual(image.shape,(720,1280,3))
            images.append(dict(kind='raw',data=data,width=1280,height=720))
        self.assertEqual(sorted(len(i['data']) for i in images),[1475748,1584248,1646397])
        with tempfile.TemporaryDirectory() as root:
            journal=Journal(root,min_free_bytes=0)
            store=ResultStorage(journal)
            try:
                identifier,_=journal.admit(dict(cell_id='t',plc_session_id=1,cycle_id=1,request_id=1,attempt=1),{})
                from src.journal.sqlite import atomic_write
                def slow(path,data):
                    time.sleep(.2);atomic_write(path,data)
                accepted = time.monotonic()
                context=dict(active={'accepted_monotonic':accepted, 'production_binding':dict(
                    inspection_motion_mode='CONVEYOR_MOTION_PLC_BENCH', request_accepted_monotonic=accepted)})
                with patch('src.journal.sqlite.atomic_write',slow):
                    store.submit(context,dict(inspection_id=identifier,
                        result=dict(decision='REVIEW',execution={'source':'RECORDED_FIELD_FIXTURE'}),images=images))
                    ticks=0
                    while store.completed.empty():
                        acquired=journal.lock.acquire(timeout=.01)
                        if acquired:journal.lock.release();ticks+=1
                        time.sleep(.02)
                    completion=store.completed.get()
                self.assertIsNone(completion['error'])
                self.assertGreater(completion['timing']['storage_commit_ms'],600)
                self.assertGreater(completion['timing']['plc_request_to_durable_result_ms'],600)
                self.assertGreater(ticks,10)
                self.assertEqual([i['sha256'] for i in completion['result']['assets']],
                    [__import__('hashlib').sha256(i['data']).hexdigest() for i in images])
            finally:store.close();journal.close()


class StorageHealthFaults(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.now=time.monotonic()
        self.service=InspectionService.__new__(InspectionService)
        s=self.service
        from src.runtime.health_diagnostics import HealthDiagnostics
        s.health_diagnostics=HealthDiagnostics()
        s.lock=threading.RLock();s.process=NS(is_alive=lambda:True,pid=1)
        s.preview={'freshness':{'camera_epoch':'e'}};s.preview_received=self.now
        s.heartbeat=NS(value=self.now);s.error=None;s.state='BUSY';s.generation='g'
        s.calibration={};s.switching=False
        s.journal=NS(root=Path(self.temp.name),min_free_bytes=0)
        s.active=dict(inspection_id='i',deadline=self.now+5)
        s.storage_pending=dict(inspection_id='i',active=s.active,generation='g',camera_epoch='e')
        s.storage=NS(thread=NS(is_alive=lambda:True))
        r=self.r=StandaloneRuntime.__new__(StandaloneRuntime)
        r.service=s;r.bridge=NS(inspection_id='i');r.handshake=NS(token='0000000000000001:1:1',cancelled=False)
        r.operating=True;r.error=None;r.initial_approval=NS(failed=False,state='ACCEPTED')
        r.assembly=NS(ready=True);r._profile_ready=lambda:True
        self.snapshot=dict(boot=1,connection=1,request_id=1,phase='REQUEST_RECEIVED',connected=True,
            fresh=True,run_idle=True,bool_valid=True,controls=dict(Mc_Run=True,EStop_OK=True,Stop_PB=True,Inspection_Request=True))
        self.updates=[]
        r.gateway=NS(contract_version='OPENER_CYCLIC',read_snapshot=lambda t:self.snapshot,
            health_update=lambda ready,clear,t:self.updates.append((ready,clear,t)))

    def test_busy_storage_is_healthy_but_each_real_fault_revokes(self):
        self.r._storage_wait_health(self.now)
        self.assertTrue(self.updates[-1][0])
        for target,key,value in [(self.service,'error','DB_STORAGE_FAILED'),
            (self.service,'preview_received',self.now-3),
            (self.service.heartbeat,'value',self.now-6),
            (self.service,'generation','different')]:
            old=getattr(target,key);setattr(target,key,value)
            self.r._storage_wait_health(self.now);self.assertFalse(self.updates[-1][0],key)
            setattr(target,key,old)
        self.service.process.is_alive=lambda:False
        self.r._storage_wait_health(self.now);self.assertFalse(self.updates[-1][0])

    def test_stop_ipc_loss_and_missing_storage_context_are_not_masked(self):
        for key in ('Mc_Run','EStop_OK','Stop_PB'):
            self.snapshot['controls'][key]=False
            self.r._storage_wait_health(self.now);self.assertFalse(self.updates[-1][0])
            self.snapshot['controls'][key]=True
        self.r.gateway.read_snapshot=lambda t:None
        self.r._storage_wait_health(self.now);self.assertFalse(self.updates[-1][0])

    def test_camera_epoch_and_storage_deadline_are_not_masked(self):
        self.service.preview['freshness']['camera_epoch']='new-camera'
        self.r._storage_wait_health(self.now);self.assertFalse(self.updates[-1][0])
        self.service.preview['freshness']['camera_epoch']='e'
        self.service.active['deadline']=self.now-1
        self.r._storage_wait_health(self.now);self.assertFalse(self.updates[-1][0])

    def test_unrelated_journal_reader_neither_revokes_nor_renews_health(self):
        self.service.storage_pending = None
        self.r.final_pending = None
        self.r._storage_wait_health(self.now)
        self.assertEqual(self.updates, [])

    def test_late_completion_cannot_clear_replaced_active_context(self):
        import queue
        from unittest.mock import Mock
        s=self.service
        s.storage.completed=queue.Queue()
        context=s.storage_pending
        s.active=dict(inspection_id='different')
        s._fault=Mock()
        s.storage.completed.put(dict(context=context,result={},error=None,timing={}))
        s._storage_completions()
        s._fault.assert_called_once_with('STORAGE_COMPLETION_CONTEXT_CHANGED')
        self.assertEqual(s.active['inspection_id'],'different')

    def test_storage_hang_still_stops_camera_without_closing_owned_database(self):
        from unittest.mock import Mock
        s=self.service
        s.close_complete=False;s.sender=None;s.closed=threading.Event()
        s.monitor=NS(join=lambda timeout:None,is_alive=lambda:False)
        s.cancellation=threading.Event();s._stop_worker=Mock()
        s.storage.close=Mock(side_effect=RuntimeError('RESULT_STORAGE_STOP_UNCONFIRMED'))
        s.journal.close=Mock();s.diagnostic_capture=NS(close=Mock())
        s.manager=NS(shutdown=Mock())
        with self.assertRaisesRegex(RuntimeError,'RESULT_STORAGE_STOP_UNCONFIRMED'):
            s.close()
        s._stop_worker.assert_called_once()
        s.journal.close.assert_not_called()
        self.assertFalse(s.close_complete)

    def test_storage_exception_does_not_produce_completion(self):
        from unittest.mock import Mock
        store=ResultStorage(NS(finish=Mock(side_effect=OSError('DB full'))))
        try:
            store.submit(dict(active={'accepted_monotonic':time.monotonic()}),dict(
                inspection_id='i',result={},images=[]))
            value=store.completed.get(timeout=1)
            self.assertIsNone(value['result']);self.assertIn('DB full',value['error'])
        finally:store.close()

class FinalCommitConcurrency(unittest.TestCase):
    def setUp(self):
        from notebook.tests.test_opener_guards import DurableIdentityGuards
        self.fixture=DurableIdentityGuards()
        self.fixture.setUp();self.addCleanup(self.fixture.tearDown)
        self.identifier=self.fixture.candidate()
        self.r=self.fixture.r
        self.r._cancel_pending=lambda reason:self.r.published_ids.add(self.identifier)

    def test_final_slow_commit_cannot_publish_before_durability_or_after_STOP(self):
        entered,release=threading.Event(),threading.Event()
        commit=self.fixture.journal.commit_integrated
        def slow(final):
            entered.set()
            if not release.wait(2):raise TimeoutError('release')
            commit(final)
        with patch.object(self.fixture.journal,'commit_integrated',slow):
            try:
                StandaloneRuntime._commit_and_publish(self.r,self.identifier,{'decision':'REVIEW'},5)
                self.assertTrue(entered.wait(1))
                self.r._poll_final_commit(5.1)
                self.fixture.h.publish.assert_not_called()
                self.fixture.h.cancelled=True
            finally:release.set()
            saved=self.fixture.storage.final_completed.get(timeout=2)
            self.fixture.storage.final_completed.put(saved)
            self.r._poll_final_commit(5.6)
        self.fixture.h.publish.assert_not_called()
        self.assertIn(self.identifier,self.r.published_ids)
        self.assertIsNotNone(self.fixture.journal.db.execute(
            "SELECT value FROM service_state WHERE key=?",('integrated_decision:'+self.identifier,)).fetchone())

    def test_final_commit_failure_cannot_publish(self):
        with patch.object(self.fixture.journal,'commit_integrated',side_effect=OSError('DB fsync failed')):
            StandaloneRuntime._commit_and_publish(self.r,self.identifier,{'decision':'REVIEW'},5)
            saved=self.fixture.storage.final_completed.get(timeout=2)
            self.fixture.storage.final_completed.put(saved)
            with self.assertRaisesRegex(ValueError,'FINAL_STORAGE_FAILED'):
                self.r._poll_final_commit(5.1)
        self.fixture.h.publish.assert_not_called()


if __name__ == '__main__': unittest.main()
