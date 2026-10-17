"""Real Journal/final worker/validator/AF_UNIX publication; synthetic inputs only."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
import uuid

from apps.edge_service.result_storage import ResultStorage
from src.control.opener_cyclic import OpenerGateway, CyclicHandshake
from src.journal.sqlite import Journal
from src.runtime.standalone import StandaloneRuntime


@unittest.skipUnless(os.environ.get('SUPERVISED_IPC_FIXTURE'), 'requires AF_UNIX-only C fixture')
class CompletedPublicationNative(unittest.TestCase):
    def test_stored_three_frames_publish_once_despite_absent_preview(self):
        import cv2
        import numpy as np
        with tempfile.TemporaryDirectory(prefix='eai-final-') as folder:
            root=Path(folder); os.chmod(root,0o700)
            process=subprocess.Popen([os.environ['SUPERVISED_IPC_FIXTURE'],str(root/'ipc'),'automatic'],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            gateway=journal=storage=None
            try:
                until=time.monotonic()+3
                while not (root/'ipc').exists() and time.monotonic()<until: time.sleep(.01)
                gateway=OpenerGateway(root/'ipc',writes_enabled=True)
                handshake=CyclicHandshake(gateway,lambda event:None)
                def wait(predicate):
                    until=time.monotonic()+3
                    while time.monotonic()<until:
                        gateway.health_update(True,False,time.monotonic())
                        snapshot=gateway.read_snapshot(time.monotonic())
                        if snapshot and predicate(snapshot): return snapshot
                        time.sleep(.01)
                    self.fail(str(snapshot))
                wait(lambda s:s['connected'] and s['fresh'])
                journal=Journal(root/'data',min_free_bytes=0); storage=ResultStorage(journal)
                r=StandaloneRuntime.__new__(StandaloneRuntime)
                r.service=NS(journal=journal,storage=storage,generation='g',package=NS(manifest_hash='sha'),
                    health=lambda:dict(error=None,camera_ready=True,state='IDLE',worker_alive=True,camera_epoch='e'))
                r.gateway=gateway; r.handshake=handshake; r.epoch='e'; r.session_id='s'
                r._automatic_policy=lambda:True; r._supervised_policy=lambda:False; r._full_frame_policy=lambda:True
                r.operating=True; r.error=None; r.cycle_issue=None; r.final_pending=None
                r.published_ids=set(); r.request_product_separation=None
                published=[]
                def publish(identifier, final, binding):
                    # The real final worker must have committed before IPC.
                    self.assertIsNotNone(journal.db.execute('SELECT value FROM service_state WHERE key=?',
                        ('integrated_decision:'+identifier,)).fetchone())
                    handshake.publish(identifier,final['decision'],True,time.monotonic())
                    self.assertEqual(handshake.publication,'IPC_QUEUED')
                    r.published_ids.add(identifier); published.append(identifier)
                r._publish_committed=publish
                process.stdin.write('S'); process.stdin.flush()
                for number,decision in enumerate(('PASS','FAIL'),1):
                    wait(lambda s:s['phase']=='IDLE')
                    process.stdin.write('R'); process.stdin.flush()
                    wait(lambda s:s['phase']=='REQUEST_RECEIVED')
                    handshake.poll(time.monotonic())
                    accepted=handshake.accepted_at; trigger=time.monotonic()
                    cycle=uuid.uuid4().hex
                    binding=dict(runtime_session_id='s',worker_generation='g',camera_epoch='e',
                        cycle_id=cycle,track_id=number,plc_request_token=handshake.token,
                        package_manifest_sha='sha',monotonic_s=trigger,sequence=0)
                    request=dict(cell_id='fixture',plc_session_id=1,request_id=number,cycle_id=number,
                        attempt=1,package_sha256='sha',runtime_binding=binding)
                    identifier,_=journal.admit(request,{'fixture':True})
                    handshake.bind(identifier)
                    images=[]; observations=[]; checks=[]
                    for index in range(3):
                        pixels=np.full((8,8,3),number*20+index,np.uint8)
                        frame_id=identifier+':'+str(index); source=time.monotonic()
                        images.append(dict(kind='raw',data=cv2.imencode('.png',pixels)[1].tobytes(),
                            frame_id=frame_id,width=8,height=8))
                        observations.append(dict(frame_id=frame_id,input_pixel_sha256=hashlib.sha256(pixels.tobytes()).hexdigest(),
                            freshness=dict(frame_id=frame_id,camera_epoch='e',sequence=index+1,
                                estimated_source_monotonic=source,integrity={'valid':True})))
                        checks.append(dict(frame_id=frame_id,failed_conditions=[]))
                    journal.finish(identifier,dict(decision=decision,reason='SYNTHETIC_ONLY',
                        execution={'source':'mock','worker_generation':'g'},observations=observations,
                        production_frame_checks=checks,production_identity=dict(binding,inspection_id=identifier)),images)
                    r.coordinator=NS(active_cycle=NS(cycle_id=cycle),_tracker=NS(_track_id=number))
                    r.latest_packet=dict(provider={'status':'NO_FOREGROUND','observations':[]})
                    r._automatic_cycle_evidence={'start_counters':{key:number-1 for key in ('result_count','done_count','completed_count')}}
                    r._commit_and_publish(identifier,{'decision':decision},time.monotonic())
                    until=time.monotonic()+3
                    while r.final_pending and time.monotonic()<until:
                        gateway.health_update(True,False,time.monotonic())
                        with journal.lock:
                            r._poll_final_commit(time.monotonic())
                        time.sleep(.01)
                    self.assertIsNone(r.final_pending)
                    snapshot=wait(lambda s:s['completed_count']==number and s['phase'] in ('READY_NEXT','IDLE'))
                    self.assertEqual(tuple(snapshot[key] for key in ('result_count','done_count','completed_count')),(number,)*3)
                    self.assertEqual(len(published),number)
                    self.assertEqual(snapshot['raw100'],'00000000')
            finally:
                if storage: storage.close()
                if journal: journal.close()
                if gateway: gateway.close()
                process.stdin.write('Q'); process.stdin.flush()
                process.communicate(timeout=3)
                self.assertEqual(process.returncode,0)
