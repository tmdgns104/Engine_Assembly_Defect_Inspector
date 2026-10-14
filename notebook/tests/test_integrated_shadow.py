"""Saved current-request images feed shadow only; no camera/model/PLC test."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import sys
import tempfile
import unittest
import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'jetson'))
from src.vision.misassembly_shadow import ShadowObserver


class FakeModels:
    def __init__(self):
        self.contexts = []
        self.resets = 0
        self.processor = SimpleNamespace(guard=SimpleNamespace(reset=self.reset))

    def reset(self):
        self.resets += 1

    def process(self, image, context):
        self.contexts.append(context)
        return ({'shadow_state': 'FAIL_CANDIDATE', 'parts': {'exhaust': {
            'predicted_state': 'SIDEWAYS', 'class_scores': {'CORRECT': .1, 'SIDEWAYS': .9}}}}, image, {'exhaust': image})


class ShadowTests(unittest.TestCase):
    def test_same_durable_raws_shadow_never_modifies_production_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = FakeModels()
            history = SimpleNamespace(add=lambda r: {'state': 'REVIEW'})
            observer = ShadowObserver(root, root/'shadow', loader=lambda: (model, SimpleNamespace, lambda: history), start=False)
            assets, observations = [], []
            for i in range(3):
                image = np.full((8, 8, 3), i+20, np.uint8)
                encoded = cv2.imencode('.png', image)[1].tobytes()
                (root/f'{i}.png').write_bytes(encoded)
                assets.append(dict(kind='raw', relative_path=f'{i}.png', sha256=hashlib.sha256(encoded).hexdigest(), frame_id=f'f{i}'))
                observations.append(dict(input_pixel_sha256=hashlib.sha256(image.tobytes()).hexdigest(), quality={'valid': True},
                    freshness={'frame_id': f'f{i}', 'camera_epoch': 'camera', 'source_pts_ns': i+1, 'integrity': {'valid': True}}))
            row = dict(inspection_id='a'*32, decision='PASS',
                       request={'runtime_binding': {'track_id': 7}}, result={'observations': observations, 'assets': assets})
            result = observer.process_one(row)
            self.assertEqual(row['decision'], 'PASS')
            self.assertEqual(result['source'], 'MISASSEMBLY_SHADOW')
            self.assertEqual(result['production_decision'], 'PASS')
            self.assertEqual(len(model.contexts), 3)
            self.assertEqual(model.resets, 1)
            self.assertTrue(all(c.track_id == 7 for c in model.contexts))
            self.assertTrue(all(f['shadow_state'] == 'FAIL_CANDIDATE' for f in result['frames']))
            self.assertFalse(result['plc_output'])
            with self.assertRaises(FileExistsError):
                observer.process_one(row)

    def test_invalid_evidence_cannot_be_classified_or_escape_data_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            observer = ShadowObserver(root, root/'shadow', loader=lambda: (_ for _ in ()).throw(AssertionError('NO_MODEL')), start=False)
            for name in ('../outside.png', '/absolute.png'):
                row = dict(inspection_id=hashlib.md5(name.encode()).hexdigest(), decision='ERROR',
                           result={'observations': [], 'assets': [dict(kind='raw', relative_path=name, frame_id='f')]}, request={})
                with self.assertRaises(ValueError):
                    observer.process_one(row)


if __name__ == '__main__':
    unittest.main()
