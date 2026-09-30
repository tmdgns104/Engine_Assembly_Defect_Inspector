"""Focused moving-mode policy checks; no camera, model or PLC is started."""
import sys
import tempfile
import time
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'jetson'))

from apps.edge_service.inspection import InspectionService
from src.decision.engine_dynamic import SLOTS
from src.journal.sqlite import Journal
from src.vision.engine_inspector import assess_dynamic, conveyor_frame_gate, conveyor_incomplete_result
from src.runtime.production import ProductionRuntime
from src.tracking.contracts import TrackState
from src.vision.production_binding import motion_cycle_matches
from notebook.deployment.deploy_area import validate_runtime_settings
from runtime_fixtures import trigger_worker, write_package


ZONE = {'polygon_normalized': [[.2, .25], [.8, .25], [.8, .65], [.2, .65]]}
FULL_VIEW = {'polygon_normalized': [[0, 0], [1, 0], [1, 1], [0, 1]]}
POLICY = {'source_mode': 'PRODUCTION_AUTO', 'inspection_motion_mode': 'CONVEYOR_MOTION_DEV',
          'session_id': 'synthetic-session', 'physical_output_enabled': False,
          'human_acceptance': 'PENDING', 'capture_zone': ZONE}


def observation(number, *, y2=500, pose=True, quality=True):
    product = {'class_name': 'product_envelope', 'confidence': .9,
               'bounding_box': {'x1': 500, 'y1': 170 + number * 20,
                                'x2': 800, 'y2': y2 + number * 20}}
    frame = {'frame_id': f'epoch-{number}', 'source_pts_ns': number * 200_000_000,
             'camera_epoch': 'epoch', 'decision': 'PASS',
             'reason_code': 'ALL_REQUIRED_PARTS_PRESENT', 'product': product,
             'product_selection': {'valid_count': 1}, 'pose': {'reliable': pose},
             'quality_valid': quality, 'assignment_reliable': True, 'stable': False,
             'slot_states': dict.fromkeys(SLOTS, 'PRESENT')}
    return {'frame_id': frame['frame_id'], 'width': 1280, 'height': 720,
            'quality': {'valid': quality}, 'engine_dynamic': frame}


class ConveyorMotionTests(unittest.TestCase):
    def test_changed_cycle_or_track_cannot_keep_motion_binding(self):
        binding={'cycle_id':'cycle-1','track_id':1}
        self.assertTrue(motion_cycle_matches(binding,SimpleNamespace(cycle_id='cycle-1'),1))
        self.assertFalse(motion_cycle_matches(binding,SimpleNamespace(cycle_id='cycle-1'),2))
        self.assertFalse(motion_cycle_matches(binding,SimpleNamespace(cycle_id='cycle-2'),1))

    def test_motion_mode_requires_mock_and_an_explicit_valid_capture_zone(self):
        before={'port':18771,'plc_bench':False,'mock_auto_request':True}
        after=dict(before,inspection_motion_mode='CONVEYOR_MOTION_DEV',
                   conveyor_capture_zone_normalized=ZONE['polygon_normalized'])
        validate_runtime_settings(before,after)
        validate_runtime_settings(before,dict(after,
            conveyor_capture_zone_normalized=FULL_VIEW['polygon_normalized']))
        with self.assertRaises(ValueError):
            validate_runtime_settings(before,dict(after,plc_bench=True,mock_auto_request=False))
        with self.assertRaises(ValueError):
            validate_runtime_settings(before,dict(after,conveyor_capture_zone_normalized=[]))

    def test_plc_motion_mode_requires_real_plc_and_explicit_zone(self):
        before={'port':18771,'plc_bench':False,'mock_auto_request':True,
                'inspection_motion_mode':'CONVEYOR_MOTION_DEV',
                'conveyor_capture_zone_normalized':FULL_VIEW['polygon_normalized']}
        after=dict(before,plc_bench=True,mock_auto_request=False,
                   inspection_motion_mode='CONVEYOR_MOTION_PLC_BENCH')
        validate_runtime_settings(before,after)
        with self.assertRaises(ValueError):
            validate_runtime_settings(before,dict(after,mock_auto_request=True))

    def test_trigger_skips_stability_only_in_explicit_motion_mode(self):
        packet={'stable': False, 'processed_monotonic': 100., 'sequence': 10,
                'monotonic_s': 99.9, 'provider': {'observations': [
                    {'bbox': {'x1': .4, 'y1': .2, 'x2': .6, 'y2': .6}}]}}
        for mode,should_submit in [('STATIONARY',False),('CONVEYOR_MOTION_DEV',True),
                                   ('CONVEYOR_MOTION_PLC_BENCH',True)]:
            bridge=SimpleNamespace(inspection_id='inspection-1',submit_production=Mock())
            runtime=SimpleNamespace(operating=True,error=None,
                handshake=SimpleNamespace(state='REQUEST_LATCHED',accepted_at=100.,token='request-1',
                                          bind=Mock()),
                service=SimpleNamespace(active=False,generation='worker',
                                        package=SimpleNamespace(manifest_hash='package')),
                area_config_version=None,coordinator=SimpleNamespace(
                    _tracker=SimpleNamespace(_track_id=1),active_cycle=SimpleNamespace(cycle_id='cycle')),
                eligible=True,latest_packet=packet,inspection_motion_mode=mode,
                request_track_id=1,request_cycle_id='cycle',
                observation_stale_seconds=2.,request_wait_seconds=8.,inspected_tracks=set(),session_id='session',
                epoch='epoch',zone=ZONE,bridge=None,gateway=SimpleNamespace(backend='MOCK'),_event=Mock())
            with patch('src.runtime.production.InspectionBridge',return_value=bridge):
                ProductionRuntime._trigger(runtime,100.1)
            self.assertEqual(bridge.submit_production.called,should_submit)

    def test_plc_request_cannot_bind_the_next_track(self):
        packet={'stable':False,'processed_monotonic':100.,'sequence':10,'monotonic_s':99.9,
                'provider':{'observations':[{'bbox':{'x1':.4,'y1':.2,'x2':.6,'y2':.6}}]}}
        bridge=SimpleNamespace(inspection_id='inspection-1',submit_production=Mock())
        runtime=SimpleNamespace(operating=True,error=None,
            handshake=SimpleNamespace(state='REQUEST_LATCHED',accepted_at=100.,token='request-1',bind=Mock()),
            service=SimpleNamespace(active=False,generation='worker',package=SimpleNamespace(manifest_hash='package')),
            area_config_version=None,coordinator=SimpleNamespace(
                _tracker=SimpleNamespace(_track_id=2),active_cycle=SimpleNamespace(cycle_id='cycle-2')),
            eligible=True,latest_packet=packet,inspection_motion_mode='CONVEYOR_MOTION_PLC_BENCH',
            request_track_id=1,request_cycle_id='cycle-1',
            observation_stale_seconds=2.,request_wait_seconds=8.,inspected_tracks=set(),session_id='session',
            epoch='epoch',zone=FULL_VIEW,bridge=None,gateway=SimpleNamespace(backend='OMRON_CIP_BENCH'),_event=Mock())
        with patch('src.runtime.production.InspectionBridge',return_value=bridge):
            ProductionRuntime._trigger(runtime,100.1)
        bridge.submit_production.assert_not_called()

    def test_plc_request_snapshot_requires_a_current_eligible_track(self):
        events=[]
        tracker=SimpleNamespace(_track_id=7)
        runtime=SimpleNamespace(coordinator=SimpleNamespace(_tracker=tracker,
                active_cycle=SimpleNamespace(cycle_id='cycle-7')),
            latest_packet={'frame_id':'frame-7','processed_monotonic':100.},
            observation_stale_seconds=2.,eligible=True,
            handshake=SimpleNamespace(token='request-7'),_event=events.append,
            request_track_id=None,request_cycle_id=None)
        ProductionRuntime._snapshot_plc_request_track(runtime,100.1)
        self.assertEqual((runtime.request_track_id,runtime.request_cycle_id),(7,'cycle-7'))
        self.assertEqual(events[-1]['frame_id'],'frame-7')
        tracker._track_id=8
        ProductionRuntime._snapshot_plc_request_track(runtime,103.)
        self.assertIsNone(runtime.request_track_id)
        self.assertIsNone(runtime.request_cycle_id)

    def test_plc_request_without_a_track_finishes_as_timeout_diagnostic(self):
        bridge=SimpleNamespace(inspection_id='inspection-1',submit_production=Mock())
        runtime=SimpleNamespace(operating=True,error=None,
            handshake=SimpleNamespace(state='REQUEST_LATCHED',accepted_at=100.,token='request-1',bind=Mock()),
            service=SimpleNamespace(active=False,generation='worker',package=SimpleNamespace(manifest_hash='package')),
            area_config_version='area-v1',coordinator=SimpleNamespace(
                _tracker=SimpleNamespace(_track_id=2,_state=TrackState.WAIT_AREA_CLEAR),
                active_cycle=SimpleNamespace(cycle_id='cycle-2')),
            eligible=False,latest_packet={'processed_monotonic':100.,'sequence':10,'monotonic_s':99.9},
            inspection_motion_mode='CONVEYOR_MOTION_PLC_BENCH',request_track_id=None,request_cycle_id=None,
            observation_stale_seconds=2.,request_wait_seconds=8.,inspected_tracks=set(),session_id='session',
            epoch='epoch',zone=FULL_VIEW,bridge=None,gateway=SimpleNamespace(backend='OMRON_CIP_BENCH'),_event=Mock())
        with patch('src.runtime.production.InspectionBridge',return_value=bridge):
            ProductionRuntime._trigger(runtime,100.1)
            bridge.submit_production.assert_not_called()
            ProductionRuntime._trigger(runtime,108.1)
        self.assertEqual(bridge.submit_production.call_args.args[0]['track_id'],None)
        self.assertEqual(bridge.submit_production.call_args.args[0]['trigger_reason'],
                         'REQUEST_TRACK_TIMEOUT_DIAGNOSTIC')

    def test_stationary_policy_still_rejects_motion(self):
        rows = [observation(n) for n in (1, 2, 3)]
        self.assertEqual(assess_dynamic(rows, {}, {'confirmed': True})['reason_code'],
                         'ENGINE_OR_HAND_MOTION')

    def test_explicit_motion_policy_can_pass_three_distinct_visible_frames(self):
        rows = [observation(n) for n in (1, 2, 3)]
        value = assess_dynamic(rows, {}, {'confirmed': True}, experiment_policy=POLICY)
        self.assertEqual(value['decision'], 'PASS')
        self.assertEqual(value['frame_motion_policy'], 'FRAME_MOTION_ACCEPTED_FOR_CONVEYOR')

    def test_plc_motion_policy_uses_same_three_frame_gates(self):
        rows=[observation(n) for n in (1,2,3)]
        policy=dict(POLICY,inspection_motion_mode='CONVEYOR_MOTION_PLC_BENCH',capture_zone=FULL_VIEW)
        self.assertEqual(assess_dynamic(rows,{}, {'confirmed':True},experiment_policy=policy)['decision'],'PASS')
        rows[1]['engine_dynamic']['pose']['reliable']=False
        self.assertNotEqual(assess_dynamic(rows,{}, {'confirmed':True},experiment_policy=policy)['decision'],'PASS')

    def test_partial_product_is_not_a_motion_pass(self):
        rows = [observation(n, y2=720) for n in (1, 2, 3)]
        value = assess_dynamic(rows, {}, {'confirmed': True}, experiment_policy=POLICY)
        self.assertEqual(value['reason_code'], 'CONVEYOR_PRODUCT_PARTIALLY_VISIBLE')
        self.assertEqual(value['decision'], 'REVIEW')

    def test_full_view_accepts_early_complete_product_but_rejects_cropped_frame(self):
        rows = [observation(n) for n in (1, 2, 3)]
        for row in rows:
            row['engine_dynamic']['product']['bounding_box'].update(x1=40, x2=340)
        full_view_policy = dict(POLICY, capture_zone=FULL_VIEW)
        self.assertEqual(assess_dynamic(rows, {}, {'confirmed': True},
                                        experiment_policy=full_view_policy)['decision'], 'PASS')
        self.assertEqual(assess_dynamic(rows, {}, {'confirmed': True},
                                        experiment_policy=POLICY)['reason_code'],
                         'CONVEYOR_OUTSIDE_CAPTURE_ZONE')
        rows[1]['engine_dynamic']['product']['bounding_box']['x1'] = 0
        self.assertEqual(assess_dynamic(rows, {}, {'confirmed': True},
                                        experiment_policy=full_view_policy)['reason_code'],
                         'CONVEYOR_PRODUCT_PARTIALLY_VISIBLE')

    def test_duplicate_frame_and_unreliable_pose_are_rejected(self):
        rows = [observation(n) for n in (1, 2, 3)]
        rows[2]['engine_dynamic']['frame_id'] = rows[1]['engine_dynamic']['frame_id']
        self.assertEqual(assess_dynamic(rows, {}, {'confirmed': True}, experiment_policy=POLICY)['decision'],
                         'ERROR')
        self.assertEqual(conveyor_frame_gate(observation(1, pose=False), ZONE),
                         'CONVEYOR_POSE_UNRELIABLE')
        self.assertEqual(conveyor_frame_gate(observation(1, quality=False), ZONE),
                         'CONVEYOR_IMAGE_QUALITY_INSUFFICIENT')

    def test_two_valid_frames_end_in_review(self):
        value=conveyor_incomplete_result([observation(1),observation(2)],[])
        self.assertEqual(value['decision'],'REVIEW')
        self.assertEqual(value['valid_frame_count'],2)

    def test_zero_valid_frames_cannot_claim_evidence_backed_review(self):
        value=conveyor_incomplete_result([],[])
        self.assertEqual(value['decision'],'ERROR')
        self.assertEqual(value['valid_frame_count'],0)
        self.assertEqual(value['reason_code'],'CONVEYOR_INSUFFICIENT_VALID_FRAMES')
        with tempfile.TemporaryDirectory() as folder:
            journal=Journal(Path(folder),min_free_bytes=0)
            try:
                request={'cell_id':'test','plc_session_id':1,'request_id':1,'cycle_id':1,'attempt':1}
                inspection_id,_=journal.admit(request,{'manifest':{'product_id':'engine','release_id':'test'}})
                stored=journal.finish(inspection_id,value,[])
                self.assertEqual(stored['decision'],'ERROR')
                self.assertTrue(stored['storage_success'])
            finally:
                journal.close()

    def test_motion_capture_window_expiry_can_publish_a_bounded_review(self):
        """The capture window is strict, but its REVIEW must reach durable storage."""
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            write_package(root/'package')
            station={'station_id':'test','cell_id':'test','inspection_timeout_seconds':1,
                     'startup_timeout_seconds':5,'max_frame_age_seconds':.35,'frame_spacing_seconds':.15,
                     'fresh_frame':{'boundary_epsilon_ms':0,'max_trigger_to_frame_ms':50,
                                    'inspection_window_ms':50}}
            service=InspectionService(root/'package',station,root/'data',trigger_worker)
            try:
                deadline=time.monotonic()+5
                while not service.status()['camera_ready'] and time.monotonic()<deadline:
                    time.sleep(.01)
                self.assertTrue(service.status()['camera_ready'])
                service.production_enabled=True
                service.production_owner=SimpleNamespace(
                    session_id='runtime',inspection_motion_mode='CONVEYOR_MOTION_DEV',zone=ZONE,
                    coordinator=SimpleNamespace(active_cycle=SimpleNamespace(cycle_id='cycle-1'),
                                                _tracker=SimpleNamespace(_track_id=1)))
                request={'cell_id':'test','plc_session_id':service.session,'request_id':1,'cycle_id':1,
                         'attempt':1,'kind':'calibrate','package_sha256':service.package.manifest_hash,
                         'source_mode':'PRODUCTION_AUTO','control_mode':'production',
                         'runtime_binding':{'runtime_session_id':'runtime','cycle_id':'cycle-1','track_id':1,
                                            'inspection_motion_mode':'CONVEYOR_MOTION_DEV',
                                            'request_accepted_monotonic':time.monotonic()},
                         'view_assessment':{'product_identity':'human_confirmed','alignment_confirmed':True,
                                            'visible_slots':{'first':True,'second':True}}}
                admitted,_=service.submit(request,_production=True)
                admitted_deadlines=dict(service.active)
                while service.active is not None and time.monotonic()<deadline:
                    time.sleep(.01)
                result=service.journal.detail(admitted['inspection_id'])
                self.assertEqual(result['state'],'COMPLETE')
                self.assertEqual(result['decision'],'REVIEW')
                self.assertLess(admitted_deadlines['capture_deadline'],admitted_deadlines['deadline'])
            finally:
                service.close()


if __name__ == '__main__':
    unittest.main()
