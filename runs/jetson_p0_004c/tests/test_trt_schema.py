import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.contracts import DetectorError
from src.recipe.package import load_package, PackageError, canonical, sha256
from src.vision.detector_factory import create_detector
from test_backend_contract import trt_fixture, write_manifest


def output_contract(nc=4):
    return {'layout':'BCN','box_format':'xywh','coordinate_space':'letterbox_pixels',
            'class_score_semantics':'sigmoid_probabilities','objectness_semantics':'absent',
            'number_of_classes':nc,'tensor_shape_contract':{
                'name':'output0','dtype':'float32','shape':[1,4+nc,8400],
                'batch_axis':0,'feature_axis':1,'candidate_axis':2}}


def executable_fixture(root):
    manifest = trt_fixture(root)
    preprocessing = json.loads((root/'preprocessing.json').read_text())
    preprocessing.update(size=[640,640],nms_location='adapter')
    raw = canonical(preprocessing).encode()
    (root/'preprocessing.json').write_bytes(raw)
    manifest['files']['preprocessing']['sha256'] = sha256(raw)
    detector = manifest['detector']
    detector.update(output=output_contract(),precision='fp16')
    detector['input']['shape'] = [1,3,640,640]
    detector['provenance']['source_onnx'] = {
        'sha256':'2'*64,'export':{'tool':'synthetic-ultralytics','version':'fixture','options':{}},
        'export_environment':{'python':'synthetic','torch':'synthetic','ultralytics':'synthetic',
                              'onnx':'synthetic','host_architecture':'synthetic'}}
    write_manifest(root,manifest)
    return manifest


class SchemaTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)/'package'

    def test_null_valid_but_factory_rejects_before_adapter_import(self):
        trt_fixture(self.root)
        package = load_package(self.root)
        with patch('builtins.__import__',side_effect=AssertionError('adapter import')):
            with self.assertRaisesRegex(DetectorError,'^TENSORRT_CONTRACT_NON_EXECUTABLE$'):
                create_detector(package)

    def test_executable_schema_and_snapshot_provenance(self):
        manifest = executable_fixture(self.root)
        package = load_package(self.root)
        snapshot = package.snapshot()
        self.assertEqual(snapshot['manifest_sha256'],sha256((self.root/'manifest.json').read_bytes()))
        self.assertEqual(snapshot['manifest']['detector']['source_model_sha256'],'1'*64)
        self.assertEqual(snapshot['manifest']['detector']['provenance']['source_onnx']['sha256'],'2'*64)
        self.assertEqual(snapshot['manifest']['files']['model']['sha256'],manifest['files']['model']['sha256'])
        snapshot['manifest']['detector']['output']['layout']='BAD'
        self.assertEqual(package.manifest['detector']['output']['layout'],'BCN')

    def test_missing_and_unknown_output_fields_fail_closed(self):
        for key in output_contract():
            with self.subTest(missing=key):
                manifest = executable_fixture(self.root)
                del manifest['detector']['output'][key]
                write_manifest(self.root,manifest)
                with self.assertRaisesRegex(PackageError,'TENSORRT_CONTRACT_NON_EXECUTABLE'):
                    load_package(self.root)
        for key,value in [('layout','BNC'),('box_format','xyxy'),('number_of_classes',3),
                          ('objectness_semantics','multiply'),('unexpected',True)]:
            with self.subTest(invalid=key):
                manifest = executable_fixture(self.root)
                manifest['detector']['output'][key]=value
                write_manifest(self.root,manifest)
                with self.assertRaisesRegex(PackageError,'TENSORRT_CONTRACT_NON_EXECUTABLE'):
                    load_package(self.root)

    def test_tensor_shape_dtype_axes_and_size_fail_closed(self):
        for key,value in [('shape',[1,8,10]),('shape',[1,7,8400]),('dtype','int8'),
                          ('name',''),('feature_axis',2),('candidate_axis',1),('batch_axis',True)]:
            with self.subTest(key=key,value=value):
                manifest = executable_fixture(self.root)
                manifest['detector']['output']['tensor_shape_contract'][key]=value
                write_manifest(self.root,manifest)
                with self.assertRaisesRegex(PackageError,'TENSORRT_CONTRACT_NON_EXECUTABLE'):
                    load_package(self.root)

    def test_onnx_provenance_required_and_finite(self):
        for mutation in ('missing','hash','export','environment','nonfinite'):
            with self.subTest(mutation=mutation):
                manifest = executable_fixture(self.root)
                source=manifest['detector']['provenance']['source_onnx']
                if mutation=='missing':del manifest['detector']['provenance']['source_onnx']
                if mutation=='hash':source['sha256']='invalid'
                if mutation=='export':source['export']['version']=None
                if mutation=='environment':del source['export_environment']['torch']
                if mutation=='nonfinite':source['export']['options']['bad']=float('nan')
                (self.root/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
                with self.assertRaises(PackageError):load_package(self.root)

    def test_mixed_null_and_adapter_contract_rejected(self):
        manifest=executable_fixture(self.root)
        manifest['detector']['output']=None
        write_manifest(self.root,manifest)
        with self.assertRaises(PackageError):load_package(self.root)
