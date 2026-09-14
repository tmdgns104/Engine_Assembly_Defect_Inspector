"""Synthetic reference/inspection tests; no physical approval or model execution."""

import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.decision.calibration import ReferenceError, reference_proposal, station_fingerprint
from src.decision.slots import assess, pixel_box
from src.vision.inspection_worker import encode_evidence
from src.journal.sqlite import ConflictError
from test_product_package import detection
import test_inspection_service


def package_fixture():
    root = Path(__file__).resolve().parents[1]
    recipe = json.loads((root/'config/products/earbud_case_v0/recipe.json').read_text(encoding='utf-8'))
    return SimpleNamespace(recipe=recipe, manifest_hash='fixture-package', manifest={
        'product_id':'fixture', 'files':{'capture':{'sha256':'fixture-capture'}, 'recipe':{'sha256':'fixture-recipe'}}})


def observations():
    objects = [detection([100, 100, 400, 400], 'case'),
               detection([130, 230, 210, 330], 'earbud_left'),
               detection([270, 230, 350, 330], 'earbud_right')]
    return [{'frame_id':str(i), 'width':1280, 'height':720, 'quality':{'valid':True},
             'freshness':{'source_pts_ns':i}, 'detections':copy.deepcopy(objects)} for i in range(3)]


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.package = package_fixture()
        self.observations = observations()

    def test_shifted_reference_uses_original_pixels_and_preserves_recipe(self):
        original = copy.deepcopy(self.package.recipe)
        candidate = reference_proposal(self.observations, self.package)
        for actual, expected in zip(pixel_box(candidate['slots']['L'],1280,720),[130,230,210,330]):
            self.assertAlmostEqual(actual,expected,places=10)
        self.assertFalse(candidate['confirmed'])
        self.assertEqual(original,self.package.recipe)
        self.assertNotEqual(candidate['slots']['L'],original['slots'][0]['region'])

    def test_missing_left_right_or_both_cannot_register(self):
        for absent in ({'earbud_left'},{'earbud_right'},{'earbud_left','earbud_right'}):
            frames = copy.deepcopy(self.observations)
            for frame in frames:
                frame['detections'] = [d for d in frame['detections'] if d['class_name'] not in absent]
            with self.subTest(absent=absent), self.assertRaises(ReferenceError) as caught:
                reference_proposal(frames,self.package)
            self.assertEqual(caught.exception.code,'REFERENCE_COUNT')
            self.assertTrue(caught.exception.slots)

    def test_every_frame_must_have_counts_confidence_and_quality(self):
        for failure in ('missing','extra','confidence','quality','duplicate','out_of_order','motion','case_motion','coordinates','nan','size'):
            frames = copy.deepcopy(self.observations)
            if failure=='missing': frames[0]['detections'].pop()
            if failure=='extra': frames[0]['detections'].append(copy.deepcopy(frames[0]['detections'][1]))
            if failure=='confidence': frames[0]['detections'][1]['confidence']=.79
            if failure=='quality': frames[0]['quality']['valid']=False
            if failure=='duplicate': frames[0]['frame_id']=frames[1]['frame_id']
            if failure=='out_of_order': frames[0]['freshness']['source_pts_ns']=100
            if failure=='motion': frames[0]['detections'][1]=detection([430,230,510,330],'earbud_left')
            if failure=='case_motion': frames[0]['detections'][0]=detection([500,100,800,400],'case')
            if failure=='coordinates': frames[0]['detections'][1]['bounding_box']['x1']=-1
            if failure=='nan': frames[0]['detections'][1]['confidence']=float('nan')
            if failure=='size': frames[0]['width']=640
            with self.subTest(failure=failure),self.assertRaises(ReferenceError):
                reference_proposal(frames,self.package)

    def test_ambiguous_shared_class_is_not_assigned_twice(self):
        self.package.recipe['slots'][1]['allowed_classes']=['earbud_left']
        with self.assertRaises(ReferenceError) as caught:
            reference_proposal(self.observations,self.package)
        self.assertEqual(caught.exception.code,'REFERENCE_SLOT_MAPPING')
        self.assertEqual(caught.exception.slots,['L','R'])

    def test_confirmed_reference_is_fixed_during_inspections(self):
        candidate = reference_proposal(self.observations,self.package)
        view = {'alignment_confirmed':True,'product_identity':'human_confirmed','visible_slots':{'L':True,'R':True}}
        self.assertEqual(assess(self.observations,self.package.recipe,view,candidate)['decision'],'REVIEW')
        approved = dict(candidate,confirmed=True)
        self.assertEqual(assess(self.observations,self.package.recipe,view,approved)['decision'],'PASS')
        for absent,slot in [('earbud_left','L'),('earbud_right','R')]:
            frames = copy.deepcopy(self.observations)
            for frame in frames: frame['detections']=[d for d in frame['detections'] if d['class_name']!=absent]
            result=assess(frames,self.package.recipe,view,approved)
            self.assertEqual(result['decision'],'FAIL')
            self.assertEqual(result['defects'][0]['slot'],slot)
        moved=copy.deepcopy(self.observations)
        for frame in moved: frame['detections'][1]=detection([430,230,510,330],'earbud_left')
        self.assertEqual(assess(moved,self.package.recipe,view,approved)['decision'],'REVIEW')
        self.assertEqual(approved['slots'],candidate['slots'])

    def test_overlay_uses_same_normalized_candidate_and_raw_pixels_unchanged(self):
        import cv2
        import numpy as np
        from datetime import datetime, timezone
        candidate = reference_proposal(self.observations,self.package)
        original=np.zeros((720,1280,3),dtype=np.uint8)
        frame=SimpleNamespace(image=original,width=1280,height=720,captured_at=datetime.now(timezone.utc))
        images=encode_evidence([frame]*3,self.observations,self.package.recipe,candidate)
        raw=cv2.imdecode(np.frombuffer(images[0]['data'],dtype=np.uint8),cv2.IMREAD_COLOR)
        overlay=cv2.imdecode(np.frombuffer(images[-1]['data'],dtype=np.uint8),cv2.IMREAD_COLOR)
        self.assertTrue(np.array_equal(raw,original))
        self.assertGreater(int(overlay[280,130,0]),100)
        self.assertGreater(int(overlay[280,130,2]),100)
        self.assertLess(int(overlay[280,130,1]),130)
        self.assertFalse(original.any())


class ReferenceApprovalTests(unittest.TestCase):
    setUp=test_inspection_service.ServiceTests.setUp
    tearDown=test_inspection_service.ServiceTests.tearDown
    wait_for=test_inspection_service.ServiceTests.wait_for
    request=test_inspection_service.ServiceTests.request

    def stored_candidate(self):
        request=self.request()
        identifier,_=self.service.journal.admit(request,self.service.package.snapshot())
        package=self.service.package
        candidate={'coordinate_space':'normalized_image','confirmed':False,'source_inspection_id':identifier,
            'manifest_sha256':package.manifest_hash,'product_id':package.manifest['product_id'],
            'capture_sha256':package.manifest['files']['capture']['sha256'],
            'recipe_sha256':package.manifest['files']['recipe']['sha256'],
            'station_id':self.service.station['station_id'],'cell_id':self.service.station['cell_id'],
            'station_sha256':station_fingerprint(self.service.station),'slots':{'first':[0,0,.4,1],'second':[.6,0,1,1]}}
        self.service.journal.finish(identifier,{'decision':'REVIEW','reason':'synthetic fixture','calibration_candidate':candidate},
            [{'kind':'raw','data':b'synthetic fixture bytes','width':1,'height':1}])
        return identifier,candidate

    def test_approval_gate_persistence_and_station_binding(self):
        identifier,candidate=self.stored_candidate()
        request=dict(self.request(2),kind='inspect')
        with self.assertRaises(ConflictError): self.service.submit(request)
        with self.assertRaises(ConflictError): self.service.confirm_calibration(identifier,False)
        confirmed=self.service.confirm_calibration(identifier,True)
        self.assertTrue(confirmed['confirmed'])
        self.assertEqual(self.service._load_calibration(),confirmed)
        self.assertFalse(self.service.journal.detail(identifier)['result']['calibration_candidate']['confirmed'])
        self.service.station['camera_device']='different-fixture-camera'
        self.assertIsNone(self.service._load_calibration())
        with self.assertRaises(ConflictError): self.service.confirm_calibration(identifier,True)
        self.assertEqual(self.service.journal.db.execute('SELECT count(*) FROM calibrations').fetchone()[0],1)

    def test_human_visibility_and_old_session_candidate_rejected(self):
        request=self.request()
        request['view_assessment']={}
        with self.assertRaises(ConflictError): self.service.submit(request)
        identifier,_=self.stored_candidate()
        self.service.session+=1
        with self.assertRaises(ConflictError): self.service.confirm_calibration(identifier,True)

    def test_new_reference_attempt_blocks_old_approval_including_after_reload(self):
        identifier,_=self.stored_candidate()
        self.service.confirm_calibration(identifier,True)
        self.assertIsNotNone(self.service._load_calibration())
        job,_=self.service.submit(self.request(2))
        self.wait_for(lambda:self.service.journal.detail(job['inspection_id'])['state']=='COMPLETE')
        self.assertIsNone(self.service.calibration)
        self.assertIsNone(self.service._load_calibration())
        self.assertFalse(self.service.status()['ready'])
        with self.assertRaises(ConflictError): self.service.submit(dict(self.request(3),kind='inspect'))
        with self.assertRaises(ConflictError): self.service.confirm_calibration(identifier,True)
        self.assertEqual(self.service.journal.db.execute('SELECT count(*) FROM calibrations').fetchone()[0],1)


if __name__=='__main__': unittest.main()
