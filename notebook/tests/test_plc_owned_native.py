"""Actual Worker/Runtime/Journal/Assembly/IPC owners; synthetic devices only.

C fixture only opens AF_UNIX. Products are encoded in synthetic images and
read by a test detector. Neither exit proof nor final outcomes are injected
into Runtime. No grant API, challenge file or approval ledger is used.
"""
import hashlib
import json
import os
import subprocess
import tempfile
import time
import unittest
import uuid
import ctypes
import multiprocessing as mp
from functools import partial
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from notebook.tests import test_health_storage_native as storage_base
from notebook.tests.opener_worker_initial_fixture import passage_worker, AssemblyModels
from notebook.tests.runtime_fixtures import fixture_documents, write_package
from apps.edge_service.inspection import InspectionService
from src.control.opener_cyclic import OpenerGateway
from src.runtime.standalone import StandaloneRuntime, AUTO_POLICY
from src.runtime.production_profile import tracker_config, calibration_sha
from src.runtime.vision_coordinator import VisionRuntimeCoordinator
from src.runtime.auto_adapters import WorkerObservationSource, LocalResultOutput
from src.runtime.cell_supervisor import FaultPolicy
from src.runtime.logging_support import RuntimeLog
from src.vision.assembly_process import ProcessAssemblyInspector


class ProcessModel(AssemblyModels):
    """Test-only shared decisions; native call holds only the child's GIL."""
    choices=('PASS_CANDIDATE','REVIEW','FAIL_CANDIDATE')
    def __init__(self, decision, resets):
        self.shared_decision,self.shared_resets=decision,resets
        self.processor=NS(guard=NS(reset=self.reset))
    @property
    def decision(self):return self.choices[self.shared_decision.value]
    @decision.setter
    def decision(self,value):self.shared_decision.value=self.choices.index(value)
    @property
    def resets(self):return self.shared_resets.value
    def reset(self):self.shared_resets.value+=1
    def process(self,image,context):
        ctypes.PyDLL(None).usleep(550_000)
        return super().process(image,context)


def load_process_model(decision,resets):
    from live_observation import ThreeFrameObservation
    return ProcessModel(decision,resets),NS,ThreeFrameObservation

@unittest.skipUnless(os.environ.get('SUPERVISED_IPC_FIXTURE'),'native AF_UNIX fixture required')
class PlcOwnedNative(unittest.TestCase):
    wait=storage_base.StoredWorkerNative.wait
    phase=storage_base.StoredWorkerNative.phase

    def test_three_products_real_software_owners_without_any_grant(self):
        from live_observation import ThreeFrameObservation
        with tempfile.TemporaryDirectory(prefix='eai20-') as folder:
            root=Path(folder);os.chmod(root,0o700)
            scene=root/'scene.json'
            def set_box(box):
                temp=scene.with_suffix('.tmp');temp.write_text(json.dumps(dict(box=box)));temp.replace(scene)
            set_box([10,20,70,100])
            docs=fixture_documents()
            docs['recipe'].update(alignment_mode='engine_affine',engine_pose=dict(path='fixture',sha256='0'*64,
                envelope_package='fixture',envelope_manifest_sha256='0'*64))
            write_package(root/'package',docs)
            station=dict(station_id='isolated',cell_id='isolated',camera_device='NO_HARDWARE',
                fixture_passage_path=str(scene),inspection_timeout_seconds=12,startup_timeout_seconds=8,
                max_frame_age_seconds=.35,frame_spacing_seconds=.15,
                quality=dict(min_mean_brightness=1,max_mean_brightness=254,min_blur_variance=0),
                fresh_frame=dict(boundary_epsilon_ms=0,max_trigger_to_frame_ms=3000,inspection_window_ms=9000))
            service=InspectionService(root/'package',station,root/'data',worker_target=passage_worker,production=True)
            context=mp.get_context('spawn')
            decision_value,resets=context.Value('i',0),context.Value('i',0)
            model=ProcessModel(decision_value,resets)
            assembly=ProcessAssemblyInspector(root/'data',root/'assembly',
                loader=partial(load_process_model,decision_value,resets))
            process=subprocess.Popen([os.environ['SUPERVISED_IPC_FIXTURE'],str(root/'ipc'),'automatic'],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            runtime=gateway=None
            report=[]
            try:
                self.wait(lambda:(root/'ipc').exists() and service.status()['camera_ready'])
                service.calibration={'confirmed':True,'coordinate_space':'normalized_image','slots':{}}
                gateway=OpenerGateway(root/'ipc',writes_enabled=True)
                zone=dict(version='fixture',entry_policy='product_center',confirmed=False,calibration_sha=None,
                    polygon_normalized=[[.2,.65],[.8,.65],[.8,.9],[.2,.9]])
                cfg=tracker_config(zone,wait_area_clear=True,plc_request_tracking=True)
                qualification=dict(verified=True,policy=AUTO_POLICY,calibration_sha=calibration_sha(service.calibration),
                    evidence='SYNTHETIC_ONLY_NOT_FIELD',exit_edge='right',passage_policy='PRODUCT_TRAJECTORY_AND_EXIT_STRIP',
                    unoccluded_exit_verified=True,sensor_cycle_source='QUALIFIED_PLC_REQUEST_LATCH',
                    plc_logic_sha256='a'*64,plc_online_equivalence_verified=True,plc_timeout_stop_recovery_verified=True)
                profile=dict(mode='EXISTING_PLC_INSPECTION',min_free_bytes=0,field_profile_verified=True,
                    arrival_deadline_s=8,assembly_deadline_s=10,inspection_start_policy='PLC_REQUEST_TRACKED_FULL_FRAME',
                    cycle_admission=AUTO_POLICY,automatic_operation_qualification=qualification,
                    request_start_qualification=dict(verified=True,policy='PLC_REQUEST_TRACKED_FULL_FRAME',
                        calibration_sha=calibration_sha(service.calibration),evidence='SYNTHETIC_ONLY'),
                    clearance_qualification={'verified':False})
                runtime=StandaloneRuntime(service,VisionRuntimeCoordinator(uuid.uuid4().hex,cfg),
                    WorkerObservationSource(),LocalResultOutput(),RuntimeLog(root/'runtime-log'),cfg,FaultPolicy(),
                    zone=zone,area_config_version=None,area_reference_required=False,gateway=gateway,
                    line_profile=profile,assembly=assembly,inspection_motion_mode='STATIONARY')
                def diag():
                    return dict(error=runtime.error,plc=runtime.handshake.status(),service=service.health(),
                        passage=runtime.product_passage.status() if runtime.product_passage else None,
                        cycle=runtime.plc_cycle,issue=runtime.issue)
                self.wait(lambda:self.phase(gateway)=='SYNC_LOW',diagnostic=diag)
                self.assertIsNone(runtime.initial_approval)
                self.assertFalse(hasattr(gateway,'automatic_arm'))
                self.assertFalse((root/'data/first-product-approval').exists())
                process.stdin.write('S');process.stdin.flush()
                for number,decision in enumerate(('PASS_CANDIDATE','REVIEW','FAIL_CANDIDATE'),1):
                    self.wait(lambda:self.phase(gateway)=='IDLE',diagnostic=diag)
                    model.decision=decision
                    event=service.journal._event
                    def slow_commit(kind,payload):
                        if kind in ('INSPECTION_COMPLETED','INTEGRATED_FINAL_DURABLE'):time.sleep(.55)
                        return event(kind,payload)
                    with patch.object(service.journal,'_event',slow_commit):
                        process.stdin.write('R');process.stdin.flush()
                        self.wait(lambda:len(runtime.history)==number,timeout=15,diagnostic=diag)
                    final=runtime.history[0]
                    self.wait(lambda:(gateway.read_snapshot(time.monotonic()) or {}).get('completed_count')==number,
                        diagnostic=diag)
                    row=service.journal.detail(final['inspection_id'])
                    self.assertEqual(row['state'],'COMPLETE')
                    self.assertEqual(final['decision'],{'PASS_CANDIDATE':'PASS','REVIEW':'REVIEW','FAIL_CANDIDATE':'FAIL'}[decision])
                    self.assertNotIn('automatic_admission_id',final)
                    self.assertFalse(final['software_permission_required'])
                    raw=[a for a in row['result']['assets'] if a['kind']=='raw']
                    self.assertEqual(len({a['frame_id'] for a in raw}),3)
                    for a in raw:self.assertEqual(hashlib.sha256((service.journal.root/a['relative_path']).read_bytes()).hexdigest(),a['sha256'])
                    snap=gateway.read_snapshot(time.monotonic())
                    self.assertEqual((snap['result_count'],snap['done_count'],snap['completed_count']),(number,number,number))
                    self.assertEqual(snap['approval_id'],'')
                    report.append(dict(inspection_id=final['inspection_id'],request_token=final['request_token'],
                        track=row['request']['runtime_binding'],decision=final['decision'],raw_ids=[a['frame_id'] for a in raw],
                        timings=service.latest_timing,health=gateway.diagnostics.snapshot()))
                    if number<3:
                        # Real consecutive worker frames traverse the exit; never
                        # fabricate product_separation or reset a Track manually.
                        for left,right in ((20,80),(30,90),(40,100),(50,100),(60,100),(70,100),(80,100),(90,100)):
                            before=runtime.last_sequence
                            set_box([left,20,right,100])
                            self.wait(lambda:runtime.last_sequence>before and runtime.latest_packet['provider']['observations']
                                and abs(runtime.latest_packet['provider']['observations'][0]['bbox']['x1']-left/100)<.001,
                                diagnostic=diag)
                        set_box([10,20,70,100])
                        self.wait(lambda:runtime.product_separation,timeout=5,diagnostic=diag)
                        self.wait(lambda:runtime.eligible,diagnostic=diag)
                self.assertEqual(len({r['inspection_id'] for r in report}),3)
                self.assertEqual(len({r['request_token'] for r in report}),3)
                self.assertEqual(model.resets,3)
                self.assertLess(gateway.diagnostics.snapshot()['latest']['HEALTH_UPDATE']['max_interval_ms'],400)
                self.assertFalse((root/'data/first-product-approval').exists())
            finally:
                if os.environ.get('PLC_OWNED_REPORT'):
                    Path(os.environ['PLC_OWNED_REPORT']).write_text(json.dumps(dict(cycles=report,
                        state=diag() if runtime else None),indent=2))
                if runtime:runtime.close()
                else:assembly.close();service.close()
                process.stdin.write('Q');process.stdin.flush()
                out,err=process.communicate(timeout=3)
                self.assertEqual(process.returncode,0,err)
                print(out)
