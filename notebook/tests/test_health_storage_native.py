"""Real software owners with synthetic camera and model boundaries.

AF_UNIX-only C fixture cannot open any PLC socket. Does not claim field AI.
Recorded field PNG bytes are checked separately in test_health_storage.
"""
import hashlib
import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

from notebook.tests.runtime_fixtures import fixture_documents, write_package
from notebook.tests.opener_worker_initial_fixture import worker, AssemblyModels
from apps.edge_service.inspection import InspectionService
from src.control.opener_cyclic import OpenerGateway
from src.runtime.standalone import StandaloneRuntime
from src.runtime.production_profile import tracker_config
from src.runtime.vision_coordinator import VisionRuntimeCoordinator
from src.runtime.auto_adapters import WorkerObservationSource, LocalResultOutput
from src.runtime.cell_supervisor import FaultPolicy
from src.runtime.logging_support import RuntimeLog
from src.runtime.initial_approval import atomic_json
from src.vision.assembly_inspection import AssemblyInspector


@unittest.skipUnless(os.environ.get('SUPERVISED_IPC_FIXTURE'), 'requires AF_UNIX C fixture')
class StoredWorkerNative(unittest.TestCase):
    def test_four_decisions_through_real_worker_storage_assembly_ipc(self):
        from live_observation import ThreeFrameObservation
        reports = []
        for decision, expected in [('PASS_CANDIDATE','PASS'),('FAIL_CANDIDATE','FAIL'),('REVIEW','REVIEW'),('ERROR','ERROR')]:
            with self.subTest(decision=decision), tempfile.TemporaryDirectory(prefix='eai19-') as folder:
                root = Path(folder); os.chmod(root, 0o700)
                docs = fixture_documents()
                docs['recipe'].update(alignment_mode='engine_affine', engine_pose=dict(path='fixture',sha256='0'*64,
                    envelope_package='fixture',envelope_manifest_sha256='0'*64))
                write_package(root/'package',docs)
                station=dict(station_id='isolated',cell_id='isolated',camera_device='NO_HARDWARE',
                    inspection_timeout_seconds=12,startup_timeout_seconds=8,max_frame_age_seconds=.35,
                    frame_spacing_seconds=.15,quality=dict(min_mean_brightness=1,max_mean_brightness=254,min_blur_variance=0),
                    fresh_frame=dict(boundary_epsilon_ms=0,max_trigger_to_frame_ms=3000,inspection_window_ms=9000))
                service=InspectionService(root/'package',station,root/'data',worker_target=worker,production=True)
                model=AssemblyModels(decision)
                assembly=AssemblyInspector(root/'data',root/'assembly',loader=lambda:(model,NS,ThreeFrameObservation))
                process=subprocess.Popen([os.environ['SUPERVISED_IPC_FIXTURE'],str(root/'ipc'),'initial'],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                runtime=gateway=None;case_completed=False
                try:
                    self.wait(lambda: (root/'ipc').exists() and service.status()['camera_ready'])
                    service.calibration={'confirmed':True,'coordinate_space':'normalized_image','slots':{}}
                    gateway=OpenerGateway(root/'ipc',writes_enabled=True)
                    zone=dict(version='fixture',entry_policy='product_center',confirmed=False,calibration_sha=None,
                        polygon_normalized=[[.2,.65],[.8,.65],[.8,.9],[.2,.9]])
                    cfg=tracker_config(zone,wait_area_clear=True,plc_request_tracking=True)
                    profile=dict(mode='EXISTING_PLC_INSPECTION',min_free_bytes=0,field_profile_verified=False,
                        arrival_deadline_s=8,assembly_deadline_s=10,inspection_start_policy='PLC_REQUEST_TRACKED_FULL_FRAME',
                        cycle_admission='FIRST_PRODUCT_ONLY',initial_authorization='EXPLICIT_ONE_SHOT_V1',
                        request_start_qualification={'verified':False},clearance_qualification={'verified':False})
                    runtime=StandaloneRuntime(service,VisionRuntimeCoordinator(uuid.uuid4().hex,cfg),
                        WorkerObservationSource(),LocalResultOutput(),RuntimeLog(root/'runtime-log'),cfg,FaultPolicy(),
                        zone=zone,area_config_version=None,area_reference_required=False,gateway=gateway,
                        line_profile=profile,assembly=assembly,inspection_motion_mode='STATIONARY')
                    path=runtime.initial_approval.root/'challenge.json'
                    def challenge():
                        if not path.exists(): return None
                        c=json.loads(path.read_text()); return c if c['eligible'] else None
                    c=self.wait(challenge)
                    atomic_json(runtime.initial_approval.root/'request.json',dict(approval_id=uuid.uuid4().hex,
                        binding=c['binding'],policy=c['policy'],created=time.monotonic(),
                        confirmations=['PHYSICAL_STOP','SUPERVISED','NO_UNFINISHED_PRODUCT','REAL_AI_OUTPUT']))
                    self.wait(lambda: self.phase(gateway)=='SYNC_LOW')
                    process.stdin.write('S'); process.stdin.flush()
                    self.wait(lambda: self.phase(gateway)=='IDLE')
                    from src.journal.sqlite import atomic_write
                    event = service.journal._event
                    def slow_asset(path, data):
                        time.sleep(.10)
                        return atomic_write(path,data)
                    def slow_commit(kind,payload):
                        if kind in ('INSPECTION_COMPLETED','INTEGRATED_FINAL_DURABLE'): time.sleep(.55)
                        return event(kind,payload)
                    poll_stop=threading.Event();poll_errors=[]
                    def poll_ui():
                        while not poll_stop.wait(.03):
                            try: runtime.status()
                            except Exception as error: poll_errors.append(repr(error));return
                    polling=threading.Thread(target=poll_ui,daemon=True)
                    polling.start()
                    try:
                        with patch('src.journal.sqlite.atomic_write',slow_asset), patch.object(service.journal,'_event',slow_commit):
                            process.stdin.write('R'); process.stdin.flush()
                            self.wait(lambda: runtime.history, timeout=15, diagnostic=lambda:dict(
                                error=runtime.error,plc=runtime.handshake.status(),service=service.health()))
                    finally:
                        poll_stop.set();polling.join(3)
                    self.assertFalse(polling.is_alive(),'UI status held a shared lock')
                    self.assertEqual(poll_errors,[])
                    final=runtime.history[0]
                    self.assertEqual(final['decision'],expected)
                    self.assertEqual(final['plc_result_value'],int(expected!='PASS'))
                    self.wait(lambda: self.phase(gateway)=='READY_NEXT')
                    s=gateway.read_snapshot(time.monotonic())
                    self.assertEqual((s['result_count'],s['done_count'],s['completed_count']),(1,1,1))
                    row=service.journal.detail(final['inspection_id'])
                    self.assertEqual(row['state'],'COMPLETE')
                    raws=[x for x in row['result']['assets'] if x['kind']=='raw']
                    self.assertEqual(len({x['frame_id'] for x in raws}),3)
                    for asset in raws:
                        self.assertEqual(hashlib.sha256((service.journal.root/asset['relative_path']).read_bytes()).hexdigest(),asset['sha256'])
                    self.assertGreater(service.latest_timing['storage_commit_ms'],800)
                    self.assertEqual(runtime.bridge.phase,'INSPECTION_DURABLE')
                    self.assertIsNone(service.error)
                    self.assertEqual(model.resets,1)
                    # Same request held/repeated cannot create another final.
                    process.stdin.write('R'); process.stdin.flush(); time.sleep(.15)
                    self.assertEqual(len(runtime.history),1)
                    reports.append(dict(decision=expected,timing=service.latest_timing,raw_sizes=[x['bytes'] for x in raws],
                        health=gateway.diagnostics.snapshot(),journal_timing=service.journal.diagnostics.snapshot(),
                        service_timing=service.health_diagnostics.snapshot()))
                    case_completed=True
                finally:
                    if runtime and gateway and os.environ.get('HEALTH_STORAGE_REPORT'):
                        evidence=dict(decision=expected,success=case_completed,health=gateway.diagnostics.snapshot(),
                            service=service.health_diagnostics.snapshot(),journal=service.journal.diagnostics.snapshot(),
                            pending=runtime.final_pending,raw_pending=bool(service.storage_pending))
                        path=Path(os.environ['HEALTH_STORAGE_REPORT']).with_name('CASE_'+expected+'.json')
                        path.write_text(json.dumps(evidence,indent=2))
                    if runtime: runtime.close()
                    else: assembly.close();service.close()
                    if gateway and not runtime: gateway.close()
                    process.stdin.write('Q');process.stdin.flush()
                    stdout,stderr=process.communicate(timeout=3)
                    self.assertEqual(process.returncode,0,stderr)
                    import re
                    seq=re.search(r'result_sequence=(\d+) done_sequence=(\d+)',stdout)
                    if case_completed and seq:self.assertEqual(int(seq[2]),int(seq[1])+1)
        if os.environ.get('HEALTH_STORAGE_REPORT'):
            Path(os.environ['HEALTH_STORAGE_REPORT']).write_text(json.dumps(reports,indent=2))

    def wait(self,predicate,timeout=10,diagnostic=lambda:None):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            value=predicate()
            if value:return value
            time.sleep(.02)
        self.fail(str(diagnostic()))

    def phase(self,gateway):
        s=gateway.read_snapshot(time.monotonic());return s['phase'] if s else None
