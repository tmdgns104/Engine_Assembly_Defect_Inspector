"""Synthetic-only request/Track regression through the real runtime and Journal."""
import copy
import json
import logging
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from src.journal.sqlite import Journal
from src.runtime.standalone import StandaloneRuntime, arrival_evidence
from src.runtime.inspection_start import FULL_FRAME, start_policy, tracked_frame_evidence
from src.runtime.production_profile import tracker_config, calibration_sha
from src.runtime.vision_coordinator import VisionRuntimeCoordinator
from src.runtime.auto_adapters import WorkerObservationSource, LocalResultOutput
from src.runtime.cell_supervisor import FaultPolicy
from src.runtime.health_diagnostics import HealthDiagnostics
from src.tracking.contracts import TrackState
from src.vision.production_binding import verify_observations

ZONE = dict(version='fixture', entry_policy='product_center', confirmed=False,
            calibration_sha=None, polygon_normalized=[[.2,.65],[.8,.65],[.8,.9],[.2,.9]])
BOX = dict(x1=.1, y1=.1, x2=.7, y2=.6)


def packet(sequence, at, box=BOX, *, count=1, stable=False):
    observations = ([dict(bbox=dict(box), source='PACKAGE_CARRIER_DETECTOR')] if count == 1 else [])
    return dict(frame_id=f'e:{sequence}',sequence=sequence,monotonic_s=at,
        processed_monotonic=at+.01,camera_epoch='e',generation='g',package_sha256='sha',
        stable=stable, integrity={'valid':True},
        provider=dict(observations=observations,
            status='PRODUCT_OBSERVED' if count==1 else 'NO_FOREGROUND' if count==0 else 'AMBIGUOUS_FOREGROUND',
            reason=None if count<2 else 'MULTIPLE_FOREGROUND_COMPONENTS',total_components=count),
        area_occupancy=None)


class FakeC:
    backend = contract_version = 'OPENER_CYCLIC'
    runtime_session = 'a'*32
    writes_enabled = False  # This fixture can never open IPC or PLC sockets.
    def __init__(self):
        self.s = None
        self.health = None
        self.result = Mock()
    def read_snapshot(self, now): return copy.deepcopy(self.s)
    def cancel(self): self.health=(False,False,0)
    def health_update(self, *values): self.health=values
    def close(self): pass
    def set(self, now, phase, number=1, request=True, **controls):
        self.s=dict(boot=1,connection=1,request_id=number,generated=now,
            received=now,accepted_at=now,connected=True,fresh=True,run_idle=True,
            bool_valid=True,phase=phase,raw100='00000000',reason='fixture',
            controls=dict(Inspection_Request=request,EStop_OK=True,Mc_Run=True,Stop_PB=True))
        self.s['controls'].update(controls)


class RuntimeFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.j = Journal(Path(self.temp.name), min_free_bytes=0)
        self.addCleanup(self.j.close)
        self.g = FakeC()
        self.serial = 0
        self.submitted = []
        calibration = {'fixture':'not-field'}
        self.service = NS(journal=self.j, generation='g', calibration=calibration,
            health_diagnostics=HealthDiagnostics(),
            lock=threading.RLock(), production_tracking=threading.Event(),active=None,
            error=None,state='IDLE', session=1,
            package=NS(manifest_hash='sha',snapshot=lambda:{'manifest':{'product_id':'fixture','release_id':'fixture'}}),
            cancel=Mock(), health=lambda:dict(ready=True,camera_ready=True,state='IDLE',
                worker_alive=True,camera_epoch='e'),
            status=lambda:dict(ready=True,camera_ready=True,state='IDLE'))
        def allocate():
            self.serial += 1
            return dict(cell_id='fixture',plc_session_id=1,request_id=self.serial,cycle_id=self.serial,
                        attempt=1,package_sha256='sha')
        def submit(req, **kwargs):
            identifier,created=self.j.admit(req,self.service.package.snapshot())
            self.submitted.append(req)
            return self.j.detail(identifier),created
        self.service.allocate_request=allocate
        self.service.submit=submit
        profile=dict(mode='EXISTING_PLC_INSPECTION', min_free_bytes=0,field_profile_verified=False,
            arrival_deadline_s=8,assembly_deadline_s=30,inspection_start_policy=FULL_FRAME,
            cycle_admission='FIRST_PRODUCT_ONLY',request_start_qualification=dict(verified=True,
                policy=FULL_FRAME,calibration_sha=calibration_sha(calibration),evidence='SYNTHETIC_FIXTURE_ONLY'),
            clearance_qualification=dict(verified=False))
        cfg=tracker_config(ZONE,wait_area_clear=True,plc_request_tracking=True)
        coordinator=VisionRuntimeCoordinator('a'*32,cfg)
        with patch('threading.Thread.start'):
            self.r=StandaloneRuntime(self.service,coordinator,WorkerObservationSource(),LocalResultOutput(),
                NS(),cfg,FaultPolicy(),zone=copy.deepcopy(ZONE),area_config_version='area-fixture',
                area_reference_required=False,gateway=self.g,line_profile=profile,
                assembly=NS(ready=True,status=lambda:{'ready':True}))
        self.r.logger=logging.getLogger('fixture')
        self.r.operating=True
        self.r.worker_generation='g'
        from notebook.tests.runtime_fixtures import drain_final_commits
        storage = drain_final_commits(self.r)
        self.addCleanup(storage.close)
        self.service.production_tracking.set()
        self.now=time.monotonic()
    def observe(self, seq, offset, box=BOX, area_class=None, **kwargs):
        p=packet(seq,self.now+offset,box,**kwargs)
        if area_class:
            p['area_occupancy'] = dict(classification=area_class, reason='SYNTHETIC_SURFACE',
                reference_valid=True, config_version='area-fixture', reference_version='surface-fixture',
                **{k:p[k] for k in ('frame_id','sequence','camera_epoch','generation','monotonic_s')})
        with patch('src.runtime.production.time.monotonic',return_value=self.now+offset+.02):
            self.r._apply_packet(p)
        return p
    def request(self, offset=.2, number=1):
        self.g.set(self.now+offset,'REQUEST_RECEIVED',number)
        self.r._poll_cyclic_plc(self.now+offset)
    def trigger(self, offset=.4):
        self.g.s['generated']=self.now+offset
        self.r.handshake.poll(self.now+offset)
        self.r._trigger(self.now+offset)
    def test_engine_outside_zone_submits_without_stability_wait(self):
        self.observe(1,.0); original=self.r.coordinator._tracker._track_id
        self.request(); self.observe(2,.3);self.trigger()
        self.assertEqual(len(self.submitted),1)
        binding=self.submitted[0]['runtime_binding']
        self.assertEqual(binding['track_id'],original)
        self.assertEqual(binding['inspection_start_policy'],FULL_FRAME)
        self.assertEqual(binding['trigger_reason'],'PLC_REQUEST_SAME_TRACK_FRESH_FRAME')
        self.assertEqual(binding['inspection_zone'],ZONE)
        self.assertFalse(self.r.latest_packet['stable'])
    def test_center_engine_submits(self):
        self.observe(1,0,dict(x1=.3,y1=.3,x2=.7,y2=.7))
        self.request();self.observe(2,.3,dict(x1=.3,y1=.3,x2=.7,y2=.7));self.trigger()
        self.assertEqual(len(self.submitted),1)
    def test_bottom_boundary_is_tracking_not_visibility_proof(self):
        box=dict(x1=.1,y1=.2,x2=.9,y2=1.)
        self.observe(1,0,box);self.request();self.observe(2,.3,box);self.trigger()
        binding=self.submitted[0]['runtime_binding']
        self.assertTrue(binding['boundary_contact_possible'])
        self.assertEqual(binding['whole_product_visibility'],'NOT_PROVEN_BY_TRACKING')
        self.assertFalse(arrival_evidence(self.r.latest_packet,self.now+.2,'e','g',ZONE))
    def test_no_new_frame_never_submits(self):
        self.observe(1,0);self.request();self.trigger()
        self.assertEqual(self.submitted,[])
    def test_no_track_at_edge_waits_then_binds_first_valid_track(self):
        self.request();self.observe(1,.3);self.trigger()
        self.assertEqual(len(self.submitted),1)
        self.assertIsNotNone(self.r.arrival['track'])
    def test_two_products_block(self):
        self.observe(1,0,count=2);self.request();self.observe(2,.3,count=2);self.trigger()
        self.assertEqual(self.submitted,[])
    def test_request_track_change_cannot_switch_product(self):
        self.observe(1,0);self.request()
        self.r._finish_without_frames=Mock()
        self.r.coordinator._tracker._track_id += 1
        self.observe(2,.3);self.trigger()
        self.r._finish_without_frames.assert_called_once_with('ERROR','CURRENT_PRODUCT_CHANGED',self.now+.4)
        self.assertEqual(self.submitted,[])
    def test_camera_epoch_and_generation_change_block(self):
        for key,value in [('camera_epoch','new'),('generation','new')]:
            with self.subTest(key=key):
                p=packet(2,self.now+.3);p[key]=value
                self.assertFalse(tracked_frame_evidence(p,self.now+.2,'e','g',self.now+.4))
    def test_duplicate_request_and_same_track_cannot_reinspect(self):
        self.observe(1,0);self.request();self.observe(2,.3);self.trigger()
        for _ in range(10):self.r._poll_cyclic_plc(self.now+.4);self.trigger()
        self.assertEqual(len(self.submitted),1)
        self.request(offset=.5,number=2)
        self.assertEqual(self.r.handshake.reason,'NEXT_PRODUCT_REQUIRES_VERIFIED_CLEARANCE')
        self.assertEqual(self.r.cyclic_admissions,1)
        self.g.result.assert_not_called()
    def test_stop_estop_requestoff_or_link_blocks_submission(self):
        self.observe(1,0);self.request();self.observe(2,.3)
        for key in ('Stop_PB','EStop_OK','Mc_Run','Inspection_Request'):
            with self.subTest(key=key):
                self.g.s['controls'][key]=False
                self.trigger()
                self.assertEqual(self.submitted,[])
                self.g.s['controls'][key]=True
        self.g.s['connected']=False
        self.trigger()
        self.g.result.assert_not_called()
    def test_invalid_or_missing_product_times_out_to_journal_ERROR(self):
        self.request()
        self.trigger(offset=9)
        row=self.j.detail(self.r.history[0]['inspection_id'])
        self.assertEqual(row['decision'],'ERROR')
        self.assertEqual(self.r.history[0]['decision'],'ERROR')
        self.assertEqual(self.r.handshake.publication,'IPC_QUEUED')
        self.assertEqual(self.r.history[0]['plc_result_value'],1)
        self.assertEqual(self.g.result.call_args.args[2],'ERROR')
    def test_start_qualification_does_not_approve_zone_or_field_profile(self):
        self.assertTrue(self.r._profile_ready())
        self.assertFalse(self.r.zone['confirmed'])
        self.assertFalse(self.r.line_profile['field_profile_verified'])
        self.r.line_profile['request_start_qualification']['verified']=False
        self.assertFalse(self.r._profile_ready())
        self.assertFalse(self.r._clear(self.now))
    def test_unknown_or_product_present_cannot_clear(self):
        self.observe(1,0);self.request()
        self.assertFalse(self.r._clear(self.now+.2))
        self.g.set(self.now+.4,'READY_NEXT',request=False)
        self.r._poll_cyclic_plc(self.now+.4)
        self.assertFalse(self.g.health[1])
        self.assertIsNone(self.r.cyclic_rearm_evidence)
    def test_mark_inspected_accepts_same_tracking_id_without_fake_zone_event(self):
        self.observe(1,0)
        c=self.r.coordinator
        self.assertEqual(c._tracker._state,TrackState.TRACKING)
        self.assertIsNone(self.r.window_event)
        c.mark_inspected(c.active_cycle.cycle_id,c._tracker._track_id,'id')
        self.assertEqual(c._tracker._state,TrackState.INSPECTED)
    def test_missing_product_is_not_retired_without_area_evidence(self):
        self.observe(1,0);self.request();self.observe(2,.3);self.trigger()
        self.r.area_config_version=None
        self.observe(3,1.,count=0);self.observe(4,2.,count=0);self.observe(5,3.5,count=0)
        self.assertIsNotNone(self.r.coordinator.active_cycle)
        self.assertIsNone(self.r.last_retirement)

    def complete(self, decision='PASS', offset=.4):
        import cv2
        import numpy as np
        identifier=self.r.bridge.inspection_id
        binding=self.r.bridge.request['runtime_binding']
        import hashlib
        images=[]; observations=[]; checks=[]
        for index in range(3):
            pixels=np.full((8,8,3),120+index,np.uint8)
            raw=cv2.imencode('.png',pixels)[1].tobytes()
            frame_id=identifier+':'+str(index)
            fresh=dict(camera_epoch=binding['camera_epoch'],frame_id=frame_id,
                sequence=binding['sequence']+index+1,
                estimated_source_monotonic=binding['monotonic_s']+.001*(index+1),
                integrity={'valid':True})
            images.append(dict(kind='raw',data=raw,width=8,height=8,frame_id=frame_id))
            observations.append(dict(frame_id=frame_id,freshness=fresh,
                input_pixel_sha256=hashlib.sha256(pixels.tobytes()).hexdigest()))
            checks.append(dict(frame_id=frame_id,failed_conditions=[]))
        self.j.finish(identifier,dict(decision=decision,reason='SYNTHETIC_FIXTURE',
            execution={'source':'mock','worker_generation':'g'},
            observations=observations,production_frame_checks=checks,
            production_identity=dict(binding,inspection_id=identifier)),images)
        self.r.bridge.poll()
        self.r._commit_and_publish(identifier,{'decision':decision},self.now+offset)
        return identifier

    def test_four_outcomes_keep_journal_then_gateway_contract(self):
        self.observe(1,0);self.request();self.observe(2,.3);self.trigger()
        identifier=self.complete(self.OUTCOME if hasattr(self,'OUTCOME') else 'PASS')
        self.assertTrue(self.j.detail(identifier)['result']['storage_success'])
        self.assertEqual(self.g.result.call_count,1)
        self.assertEqual(self.g.result.call_args.args[2],self.r.history[0]['decision'])
        self.assertTrue(self.r.history[0]['synthetic'])
        self.assertEqual(self.r.handshake.publication,'IPC_QUEUED')
        self.assertEqual(self.r.history[0]['plc_result_value'],int(self.r.history[0]['decision']!='PASS'))

    def test_review_outcome_is_plc_ng_actual_review_preserved(self):
        self.OUTCOME='REVIEW';self.test_four_outcomes_keep_journal_then_gateway_contract()
    def test_error_outcome_is_plc_ng_actual_error_preserved(self):
        self.OUTCOME='ERROR';self.test_four_outcomes_keep_journal_then_gateway_contract()
    def test_fail_outcome_is_factually_preserved(self):
        self.OUTCOME='FAIL';self.test_four_outcomes_keep_journal_then_gateway_contract()

    def test_validated_clearance_retires_then_allows_next_track(self):
        self.r.line_profile.update(cycle_admission='VERIFIED_CLEARANCE',
            clearance_qualification=dict(verified=True,config_sha='area-fixture',
                calibration_sha=calibration_sha(self.service.calibration),evidence='SYNTHETIC_ONLY'))
        self.observe(1,0);self.request();self.observe(2,.3);self.trigger();self.complete()
        first_track=self.r.arrival['track']
        self.g.set(self.now+.5,'READY_NEXT',request=False)
        self.r._poll_cyclic_plc(self.now+.5)
        for seq in range(3,19):
            at=.6+(seq-3)*.2
            self.observe(seq,at,count=0,area_class='MATCH')
            self.g.s['generated']=self.now+at+.02
            with patch('src.runtime.standalone.time.monotonic',return_value=self.now+at+.02):
                self.r._poll_cyclic_plc(self.now+at+.02)
        self.assertIsNotNone(self.r.last_retirement)
        self.assertIsNotNone(self.r.cyclic_rearm_evidence)
        self.assertTrue(self.g.health[1])
        self.g.set(self.now+4.,'IDLE',request=False)
        self.r._poll_cyclic_plc(self.now+4.)
        self.observe(19,4.1)
        self.request(4.2,number=2);self.observe(20,4.3);self.trigger(4.4)
        self.assertEqual(len(self.submitted),2)
        self.assertNotEqual(self.r.arrival['track'],first_track)

    def test_gap_or_unknown_cannot_accumulate_clearance(self):
        self.r.line_profile['cycle_admission']='VERIFIED_CLEARANCE'
        self.observe(1,0);self.request();self.observe(2,.3);self.trigger();self.complete()
        self.g.set(self.now+.5,'READY_NEXT',request=False);self.r._poll_cyclic_plc(self.now+.5)
        for seq in (4,6,8,10,12,14,16):
            self.observe(seq,.5+seq*.1,count=0,area_class='MATCH')
        self.assertIsNone(self.r.last_retirement)
        self.assertEqual(self.r.area_observation['state'],'UNKNOWN')

    def test_final_ambiguous_track_cannot_publish_PASS(self):
        self.observe(1,0);self.request();self.observe(2,.3);self.trigger()
        self.r.coordinator._tracker._state=TrackState.WAIT_AREA_CLEAR
        with self.assertRaisesRegex(ValueError,'TRACK_EVIDENCE_INVALID'):self.complete()
        self.g.result.assert_not_called()


class PolicyAndBinding(unittest.TestCase):
    def test_policy_defaults_and_rejects_other_contracts(self):
        self.assertEqual(start_policy({},'LEGACY_THREE_BOOL'),'FIXED_ZONE')
        for c in ('LEGACY_THREE_BOOL','STANDALONE_V3','MOCK',None):
            with self.assertRaisesRegex(ValueError,'REQUIRES_OPENER'):
                start_policy({'inspection_start_policy':FULL_FRAME},c)
    def test_packet_validation_stale_future_invalid_duplicate_geometry(self):
        p=packet(2,11.)
        self.assertTrue(tracked_frame_evidence(p,10,'e','g',11.1))
        for changed in [dict(monotonic_s=10),dict(monotonic_s=12),dict(integrity={'valid':False}),
                        dict(sequence='2'),dict(frame_id=''),dict(monotonic_s=float('nan'))]:
            self.assertFalse(tracked_frame_evidence(dict(p,**changed),10,'e','g',11.1))
        self.assertFalse(tracked_frame_evidence(p,10,'e','g',14))
    def test_worker_binding_skips_only_zone_and_keeps_freshness_and_association(self):
        binding=dict(camera_epoch='e',worker_generation='g',package_manifest_sha='sha',
            sequence=1,monotonic_s=1,track_id=1,product_box=[.1,.1,.7,1.],
            inspection_zone=ZONE,inspection_start_policy=FULL_FRAME,plc_contract='OPENER_CYCLIC')
        observations=[dict(frame_id='e:2',width=100,height=100,
            freshness=dict(camera_epoch='e',sequence=2,estimated_source_monotonic=2),
            engine_dynamic={'product':{'bounding_box':dict(x1=10,y1=10,x2=70,y2=100)}})]
        result=verify_observations({'decision':'PASS'},observations,binding,'g','sha')
        self.assertEqual(result['decision'],'PASS')
        old=verify_observations({'decision':'PASS'},observations,
            dict(binding,inspection_start_policy='FIXED_ZONE'),'g','sha')
        self.assertIn('PRODUCT_OUTSIDE_INSPECTION_ZONE',old['binding_failures'])
        observations[0]['freshness']['sequence']=1
        result=verify_observations({'decision':'PASS'},observations,binding,'g','sha')
        self.assertIn('FRAME_ORDER_INVALID',result['binding_failures'])
        observations[0]['freshness'].update(sequence=2,camera_epoch='reconnected')
        self.assertIn('CAMERA_EPOCH_CHANGED',
            verify_observations({'decision':'PASS'},observations,binding,'g','sha')['binding_failures'])
        observations[0]['freshness']['camera_epoch']='e'
        observations[0]['engine_dynamic']['product']['bounding_box']=dict(x1=80,y1=10,x2=99,y2=30)
        self.assertIn('INSPECTED_PRODUCT_ASSOCIATION_UNCERTAIN',
            verify_observations({'decision':'PASS'},observations,binding,'g','sha')['binding_failures'])


if __name__ == '__main__':
    unittest.main()
