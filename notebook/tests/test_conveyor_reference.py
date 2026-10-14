"""Fixed empty-noise calibration contracts; synthetic evidence is not a belt trial."""
import hashlib
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


def scene():
    image = np.full((720, 1280, 3), 45, np.uint8)
    image[120:621] = 220
    image[145:596] = 90
    return image


class ConveyorReferenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.config = dict(mode='CONVEYOR_FROZEN_EMPTY_ENVELOPE',
            roi='FULL_WIDTH_CALIBRATED_BELT', shape=[720,1280,3], color='BGR_UINT8',
            belt_bounds=[[0,145,595],[1279,145,595]],
            clear_seconds=1.2, clear_minimum_frames=6, maximum_gap_seconds=.5, maximum_age_seconds=1.,
            calibration_id='synthetic-empty', calibration_scope='FIXED_CAMERA_STATIONARY_BELT',
            empty_confirmed=True, references=[])
        for number in range(9):
            image=scene()
            image[300,number+100]=(95,95,95)
            path=self.root/f'empty_{number}.png'
            cv2.imwrite(str(path),image)
            self.config['references'].append(dict(path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                frame_id=f'empty-{number}',source_pts_ns=1000000000+number*200000000,camera_epoch='one-camera'))

    def tearDown(self):
        self.directory.cleanup()

    def model(self):
        path=self.root/'area.json'
        path.write_text(json.dumps(self.config),encoding='utf-8')
        return load_area_occupancy(path)

    def test_independent_empty_then_product_never_becomes_background(self):
        model=self.model()
        self.assertEqual(model.evaluate(scene())['classification'],'MATCH')
        product=scene();product[240:490,450:800]=190
        for _ in range(3):
            self.assertEqual(model.evaluate(product)['classification'],'OCCUPIED')
        self.assertEqual(model.evaluate(scene())['classification'],'MATCH')

    def test_one_pixel_gold_at_both_full_width_exits(self):
        model=self.model()
        for start in (0,1250):
            image=scene();image[350,start:start+30]=(20,140,190)
            result=model.evaluate(image)
            self.assertEqual(result['classification'],'OCCUPIED',result)
            self.assertEqual(result['regions']['whole']['pixels'],30)

    def test_rail_occlusion_or_camera_shift_cannot_clear(self):
        model=self.model()
        shifted=cv2.warpAffine(scene(),np.float32([[1,0,0],[0,1,40]]),(1280,720))
        covered=scene();covered[120:165,300:600]=20
        for image in (shifted,covered,None,scene().astype(np.float32)):
            self.assertEqual(model.evaluate(image)['classification'],'UNKNOWN')

    def test_corrupt_reference_missing_empty_confirmation_and_hidden_exit_fail_closed(self):
        for change in ('hash','declaration','exit','threshold','duplicate','camera'):
            with self.subTest(change=change):
                original=json.loads(json.dumps(self.config))
                if change=='hash':self.config['references'][0]['sha256']='0'*64
                if change=='declaration':self.config['empty_confirmed']=False
                if change=='exit':self.config['belt_bounds'][0][0]=20
                if change=='threshold':self.config['clear_seconds']=0
                if change=='duplicate':self.config['references'][1]=self.config['references'][0]
                if change=='camera':self.config['references'][1]['camera_epoch']='other'
                self.assertEqual(self.model().evaluate(scene())['classification'],'UNKNOWN')
                self.config=original

    def test_reference_cannot_escape_config_directory(self):
        self.config['references'][0]['path']='../outside.png'
        self.assertEqual(self.model().evaluate(scene())['classification'],'UNKNOWN')

    def test_clear_still_requires_new_contiguous_source_frames(self):
        measurement=self.model().evaluate(scene())
        self.assertEqual(measurement['classification'],'MATCH')
        window=ClearWindow()
        for number in range(8):
            meta=dict(frame_id=f'live-{number}',sequence=number,camera_epoch='live',
                monotonic_s=10+number*.2,generation='worker',integrity={'valid':True})
            result=window.update(measurement,meta,meta['monotonic_s'])
        self.assertEqual(result['state'],'CLEAR')
        self.assertEqual(window.update(measurement,meta,meta['monotonic_s'])['state'],'UNKNOWN')

    def test_launcher_rejects_incomplete_calibration_before_hardware(self):
        import launch_live
        project=Path(__file__).resolve().parents[2]
        folder=self.root/'config';folder.mkdir()
        for path in self.root.glob('empty_*.png'):
            (folder/path.name).write_bytes(path.read_bytes())
        (folder/'plc_reference.json').write_bytes((project/'jetson/config/plc_reference.json').read_bytes())
        self.config['empty_confirmed']=False
        (folder/'area_clearance.json').write_text(json.dumps(self.config),encoding='utf-8')
        with patch.object(launch_live,'ROOT',self.root):
            with self.assertRaises(ValueError):
                launch_live.check_files((project/'jetson/products/ENGINE_Z3005_5/dynamic_parts_005').resolve(),
                    project/'jetson/station.example.json',plc_bench=True)


if __name__=='__main__':
    unittest.main()
