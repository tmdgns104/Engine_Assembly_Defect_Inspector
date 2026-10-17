"""ARM64 C/Python IPC and real SQLite; synthetic PLC and camera health only."""
import os
import subprocess
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from src.control.opener_cyclic import OpenerGateway, CyclicHandshake
from src.runtime.standalone import StandaloneRuntime
from src.runtime.health_diagnostics import HealthDiagnostics
from src.journal.sqlite import Journal
from apps.edge_service.result_storage import ResultStorage


@unittest.skipUnless(os.environ.get('SUPERVISED_IPC_FIXTURE'), 'native AF_UNIX fixture required')
class NativeCompletionAudit(unittest.TestCase):
    def test_four_outcomes_with_slow_postpublication_and_done_audits(self):
        with tempfile.TemporaryDirectory(prefix='audit-ipc-') as folder:
            root=Path(folder);os.chmod(root,0o700)
            process=subprocess.Popen([os.environ['SUPERVISED_IPC_FIXTURE'],str(root/'ipc'),'automatic'],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            gateway=None;journal=None;store=None
            try:
                until=time.monotonic()+3
                while not (root/'ipc').exists() and time.monotonic()<until:time.sleep(.01)
                gateway=OpenerGateway(root/'ipc',writes_enabled=True)
                handshake=CyclicHandshake(gateway,lambda event:None)
                def wait(predicate):
                    until=time.monotonic()+3
                    while time.monotonic()<until:
                        gateway.health_update(True,False,time.monotonic())
                        snapshot=gateway.read_snapshot(time.monotonic())
                        if snapshot and predicate(snapshot):return snapshot
                        time.sleep(.02)
                    self.fail(str(snapshot))
                wait(lambda s:s['connected'] and s['fresh'])
                journal=Journal(root/'data',min_free_bytes=0);store=ResultStorage(journal)
                r=StandaloneRuntime.__new__(StandaloneRuntime)
                r.service=NS(journal=journal,storage=store,generation='fixture',
                    health=lambda:dict(error=None,camera_ready=True,state='IDLE',camera_epoch='fixture'),
                    health_diagnostics=HealthDiagnostics())
                r.gateway=gateway;r.handshake=handshake;r.epoch='fixture';r.session_id='fixture'
                r.operating=True;r.error=None;r.audit_error=None;r.audit_pending=None;r.initial_approval=None
                r._profile_ready=lambda:True;r._automatic_policy=lambda:True;r.assembly=NS(ready=True)
                r.line_profile={'arrival_deadline_s':8};r.published_ids=set()
                original=journal._event
                def delayed(kind,payload):
                    time.sleep(.55)
                    return original(kind,payload)
                process.stdin.write('S');process.stdin.flush()
                with patch.object(journal,'_event',delayed):
                    for number,decision in enumerate(('PASS','FAIL','REVIEW','ERROR'),1):
                        wait(lambda s:s['phase']=='IDLE')
                        process.stdin.write('R');process.stdin.flush()
                        s=wait(lambda s:s['phase']=='REQUEST_RECEIVED')
                        handshake.poll(time.monotonic())
                        identifier=uuid.uuid4().hex  # Actual IPC contract requires 32 hex characters.
                        handshake.bind(identifier);r.published_ids.add(identifier)
                        r._automatic_cycle_evidence={'start_counters':{k:number-1 for k in ('result_count','done_count','completed_count')}}
                        handshake.publish(identifier,decision,True,time.monotonic())
                        for event in ('INTEGRATED_INSPECTION_COMPLETED','PLC_CYCLIC_COMPLETION_OBSERVED'):
                            r._completion_event(dict(event=event,inspection_id=identifier,request_token=handshake.token,decision=decision))
                            until=time.monotonic()+2
                            while r._poll_completion_audit(time.monotonic()):
                                self.assertIsNone(r.audit_error)
                                self.assertLess(time.monotonic(),until)
                                s=gateway.read_snapshot(time.monotonic())
                                self.assertIsNotNone(s,dict(error=gateway.error,diagnostics=gateway.diagnostics.snapshot()))
                                self.assertNotEqual(s['phase'],'DISARMED',dict(snapshot=s,diagnostics=gateway.diagnostics.snapshot()))
                                time.sleep(.02)
                            s=wait(lambda s:s['completed_count']==number and s['phase'] in ('READY_NEXT','IDLE'))
                        self.assertEqual((s['result_count'],s['done_count'],s['completed_count']),(number,)*3)
                        self.assertEqual(s['raw100'],'00000000')
                self.assertEqual(journal.db.execute('SELECT count(*) FROM events').fetchone()[0],8)
                self.assertFalse(any(e.get('reason')=='HEALTH_LEASE_EXPIRED' for e in gateway.diagnostics.snapshot()['events']))
            finally:
                if store:store.close()
                if journal:journal.close()
                if gateway:gateway.close()
                process.stdin.write('Q');process.stdin.flush()
                process.communicate(timeout=3)
                self.assertEqual(process.returncode,0)


if __name__=='__main__':unittest.main()
