"""Conveyor occupancy contract. Synthetic masks are not physical trial evidence."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'jetson'))
from src.observation.area_occupancy import load_area_occupancy, ClearWindow


def profile():
    return dict(mode='CONVEYOR_DARK_BELT_SELF_OBSERVED',
                version='test-belt', roi='FULL_HEIGHT_CALIBRATED_BELT',
                shape=[720,1280,3], color='BGR_UINT8',
                belt_bounds=[[0,335,758],[120,330,750],[240,327,742],
                             [360,325,732],[480,325,722],[600,327,710],[719,330,699]],
                clear_seconds=1.2, clear_minimum_frames=6,
                maximum_gap_seconds=.5, maximum_age_seconds=1.)


def empty_scene():
    image=np.full((720,1280,3),30,np.uint8)
    bounds=np.array(profile()['belt_bounds'])
    for y in range(720):
        left=int(np.ceil(np.interp(y,bounds[:,0],bounds[:,1])))
        right=int(np.floor(np.interp(y,bounds[:,0],bounds[:,2])))
        image[y,left-24:right+25]=220
        image[y,left:right+1]=70
    # Fixed white bracket outside the belt is not an engine on the belt.
    image[200:500,100:250]=230
    return image


class ConveyorOccupancyTests(unittest.TestCase):
    def make_model(self, config=None):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'area.json'
            path.write_text(json.dumps(config or profile()),encoding='utf-8')
            return load_area_occupancy(path)

    def test_empty_belt_and_fixed_external_fixture(self):
        result=self.make_model().evaluate(empty_scene())
        self.assertEqual(result['classification'],'MATCH',result)
        self.assertTrue(result['reference_valid'])

    def test_product_blocks_empty_without_using_detector(self):
        image=empty_scene()
        image[210:470,430:640]=(180,180,180)
        self.assertEqual(self.make_model().evaluate(image)['classification'],'OCCUPIED')

    def test_one_pixel_wide_retained_gold_at_either_exit_blocks(self):
        for y in (0,690):
            image=empty_scene()
            image[y:y+30,500]=(20,140,190)
            with self.subTest(y=y):
                self.assertEqual(self.make_model().evaluate(image)['classification'],'OCCUPIED')

    def test_rail_occlusion_and_camera_translation_cannot_clear(self):
        images=[]
        shifted=cv2.warpAffine(empty_scene(),np.float32([[1,0,40],[0,1,0]]),(1280,720))
        images.append(shifted)
        covered=empty_scene(); covered[200:400,290:355]=40; images.append(covered)
        images.append(np.full((720,1280,3),50,np.uint8))
        for image in images:
            self.assertEqual(self.make_model().evaluate(image)['classification'],'UNKNOWN')

    def test_invalid_image_fails_closed(self):
        for image in (None,np.zeros((100,100,3),np.uint8),empty_scene().astype(np.float32)):
            self.assertEqual(self.make_model().evaluate(image)['classification'],'UNKNOWN')

    def test_config_cannot_hide_exit_or_override_continuity(self):
        changes=[dict(belt_bounds=[[20,335,758],[719,330,699]]),
                 dict(belt_bounds=[[0,700,300],[719,700,300]]),
                 dict(clear_seconds=0),dict(references=[{'path':'empty.png'}])]
        for change in changes:
            result=self.make_model(dict(profile(),**change)).evaluate(empty_scene())
            self.assertEqual(result['classification'],'UNKNOWN')

    def test_empty_requires_fresh_contiguous_source_frames(self):
        measurement=self.make_model().evaluate(empty_scene())
        self.assertEqual(measurement['classification'],'MATCH')
        window=ClearWindow()
        for number in range(7):
            metadata=dict(frame_id=str(number),sequence=number,camera_epoch='camera',
                          monotonic_s=10+number*.2,generation='worker',integrity={'valid':True})
            result=window.update(measurement,metadata,metadata['monotonic_s'])
        self.assertEqual(result['state'],'CLEAR')
        self.assertEqual(window.update(measurement,metadata,metadata['monotonic_s'])['state'],'UNKNOWN')

    def test_launcher_validates_conveyor_profile_before_hardware_start(self):
        import launch_live
        project=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'config').mkdir()
            (root/'config/area_clearance.json').write_text(json.dumps(profile()),encoding='utf-8')
            (root/'config/plc_reference.json').write_bytes((project/'jetson/config/plc_reference.json').read_bytes())
            with patch.object(launch_live,'ROOT',root):
                try:
                    _,result=launch_live.check_files((project/'jetson/products/ENGINE_Z3005_5/dynamic_parts_005').resolve(),
                        project/'jetson/station.example.json',plc_bench=True)
                except Exception as error:
                    self.fail('Valid conveyor profile rejected: '+repr(error))
                self.assertTrue(result['network_plc_writes_enabled'])
                invalid=profile();invalid['clear_seconds']=0
                (root/'config/area_clearance.json').write_text(json.dumps(invalid),encoding='utf-8')
                with self.assertRaises(ValueError):
                    launch_live.check_files((project/'jetson/products/ENGINE_Z3005_5/dynamic_parts_005').resolve(),
                        project/'jetson/station.example.json',plc_bench=True)


if __name__=='__main__':
    unittest.main()
