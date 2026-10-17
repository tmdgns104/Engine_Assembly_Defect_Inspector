"""Post-publication audit isolation. Synthetic controls; no PLC or camera."""
import json
import queue
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'jetson'))
from apps.edge_service.result_storage import ResultStorage
from src.journal.sqlite import Journal
from src.runtime.standalone import StandaloneRuntime


class CompletionAuditStorage(unittest.TestCase):
    def test_slow_audit_is_async_and_preserves_event_and_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            journal=Journal(folder,min_free_bytes=0)
            store=ResultStorage(journal)
            entered,release=threading.Event(),threading.Event()
            original=journal._event
            payload=dict(event='INTEGRATED_INSPECTION_COMPLETED',inspection_id='i',decision='REVIEW')
            context={'inspection_id':'i'}
            def delayed(*args):
                entered.set()
                if not release.wait(2):raise TimeoutError('fixture')
                return original(*args)
            try:
                with patch.object(journal,'_event',delayed):
                    store.submit_audit(context,payload)
                    self.assertTrue(entered.wait(1))
                    self.assertTrue(store.audit_completed.empty())
                    release.set()
                    result=store.audit_completed.get(timeout=2)
                self.assertIs(result['context'],context)
                self.assertIsNone(result['error'])
                row=journal.db.execute("SELECT value FROM service_state WHERE key='production_publication:i'").fetchone()
                self.assertEqual(json.loads(row[0]),payload)
                self.assertEqual(journal.db.execute('SELECT count(*) FROM events').fetchone()[0],1)
            finally:
                release.set();store.close();journal.close()

    def test_failed_audit_is_reported_without_success(self):
        journal=NS(lock=threading.RLock(),db=MagicMock())
        journal.db.__enter__=Mock(side_effect=OSError('disk failure'))
        store=ResultStorage(journal)
        try:
            store.submit_audit({'inspection_id':'i'}, {'event':'INTEGRATED_INSPECTION_COMPLETED'})
            result=store.audit_completed.get(timeout=2)
            self.assertIn('disk failure',result['error'])
        finally:store.close()


class CompletionAuditHealth(unittest.TestCase):
    def setUp(self):
        self.now=100.
        self.snapshot=dict(boot=1,connection=2,request_id=3,phase='READY_NEXT',
            connected=True,fresh=True,run_idle=True,bool_valid=True,generated=99.99,received=99.99,
            result_count=4,done_count=4,completed_count=4,raw100='00000000',
            controls=dict(Mc_Run=True,EStop_OK=True,Stop_PB=True,Inspection_Request=False))
        self.health=dict(error=None,camera_ready=True,state='IDLE',camera_epoch='e')
        self.r=StandaloneRuntime.__new__(StandaloneRuntime)
        r=self.r
        r.audit_pending=dict(inspection_id='i',request_token='0000000000000001:2:3',
            generation='g',camera_epoch='e',started=99.,deadline=110.,
            start_counters=dict(result_count=3,done_count=3,completed_count=3))
        r.audit_error=None;r.operating=True;r.error=None;r.initial_approval=None
        r._profile_ready=lambda:True;r.assembly=NS(ready=True)
        r.service=NS(generation='g',health=lambda:dict(self.health),
            storage=NS(thread=NS(is_alive=lambda:True),audit_completed=queue.Queue()),
            health_diagnostics=NS(record=Mock()))
        r.handshake=NS(token=r.audit_pending['request_token'],cancelled=False)
        r.gateway=NS(read_snapshot=lambda now:self.snapshot,health_update=Mock(),cancel=Mock())
        r.published_ids={'i'}

    def ready(self):
        self.r._completion_audit_health(self.now)
        return self.r.gateway.health_update.call_args.args[0]

    def test_settled_same_request_remains_healthy_while_audit_pending(self):
        self.assertTrue(self.ready())

    def test_next_request_can_wait_without_admission_only_after_previous_done(self):
        self.snapshot.update(request_id=4,phase='REQUEST_RECEIVED')
        self.snapshot['controls']['Inspection_Request']=True
        self.assertTrue(self.ready())
        self.snapshot['done_count']=3
        self.assertFalse(self.ready())

    def test_stop_epoch_stale_reconnect_and_timeout_revoke_readiness(self):
        for key in ('Mc_Run','EStop_OK','Stop_PB'):
            self.snapshot['controls'][key]=False
            self.assertFalse(self.ready())
            self.snapshot['controls'][key]=True
        self.health['camera_epoch']='other';self.assertFalse(self.ready());self.health['camera_epoch']='e'
        self.snapshot['received']=99.;self.assertFalse(self.ready());self.snapshot['received']=99.99
        self.snapshot['connection']=3;self.assertFalse(self.ready());self.snapshot['connection']=2
        self.now=111.;self.assertFalse(self.ready())

    def test_disarmed_missing_camera_and_unpublished_identity_never_renew(self):
        self.snapshot['phase']='DISARMED';self.assertFalse(self.ready())
        self.snapshot['phase']='READY_NEXT';self.health['camera_ready']=False;self.assertFalse(self.ready())
        self.health['camera_ready']=True;self.r.published_ids.clear();self.assertFalse(self.ready())

    def test_completion_failure_revokes_health_and_retains_failure_context(self):
        self.r.service.storage.audit_completed.put(dict(context=self.r.audit_pending,error='disk failure'))
        self.assertTrue(self.r._poll_completion_audit(self.now))
        self.assertIn('disk failure',self.r.audit_error)
        self.assertFalse(self.r.gateway.health_update.call_args.args[0])
        self.r.gateway.cancel.assert_called_once()
        self.assertIsNotNone(self.r.audit_pending)

    def test_success_clears_only_matching_pending_context(self):
        self.r.service.storage.audit_completed.put(dict(context=self.r.audit_pending,error=None))
        self.assertFalse(self.r._poll_completion_audit(self.now))
        self.assertIsNone(self.r.audit_pending)

    def test_wrong_completion_cannot_release_admission(self):
        self.r.service.storage.audit_completed.put(dict(context=dict(self.r.audit_pending),error=None))
        self.assertTrue(self.r._poll_completion_audit(self.now))
        self.assertIn('CONTEXT_CHANGED',self.r.audit_error)

    def test_storage_hang_is_bounded_and_revokes_readiness(self):
        self.assertTrue(self.r._poll_completion_audit(111.))
        self.assertEqual(self.r.audit_error,'COMPLETION_AUDIT_TIMEOUT_OR_OWNER_LOST')
        self.assertFalse(self.r.gateway.health_update.call_args.args[0])

    def test_snapshot_published_after_loop_clock_uses_atomic_observation_time(self):
        self.snapshot.update(generated=100.001,received=100.001,observed_at=100.002)
        self.assertTrue(self.ready())

    def test_health_exception_is_fail_closed_without_killing_runtime_loop(self):
        self.r.service.health=Mock(side_effect=RuntimeError('health unavailable'))
        self.assertTrue(self.r._poll_completion_audit(self.now))
        self.assertIn('HEALTH_CHECK',self.r.audit_error)
        self.assertFalse(self.r.gateway.health_update.call_args.args[0])


if __name__=='__main__':unittest.main()
