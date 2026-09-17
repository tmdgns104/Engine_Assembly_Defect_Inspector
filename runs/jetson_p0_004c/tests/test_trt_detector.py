import ast
import builtins
from datetime import datetime, timezone
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

from src.contracts import CameraFrame, DetectorError
from src.recipe.package import load_package
from src.vision.detector_factory import create_detector
from test_trt_schema import executable_fixture, trt_fixture, write_manifest
from test_trt_postprocess import raw


class Executor:
    def __init__(self):
        self.output=raw([([320,320,160,160],0,.9)])
        self.calls=0
        self.closed=0
        self.inputs=[]
        self.error=None
    def execute(self,array):
        self.calls+=1;self.inputs.append(array.copy())
        if self.error:raise self.error
        return self.output
    def runtime_metadata(self):return {'device':'CPU_TEST_ONLY','context_usable':True}
    def close(self):self.closed+=1


class DetectorTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)/'package'
        executable_fixture(self.root)
        self.package=load_package(self.root)
        self.executor=Executor()
        self.frame=CameraFrame(np.full((8,8,3),[1,2,3],np.uint8),'input-id',datetime.now(timezone.utc),8,8,'synthetic')

    def detector(self,**kwargs):
        return create_detector(self.package,executor_factory=lambda package:self.executor,**kwargs)

    def test_default_is_native_not_implemented_without_forbidden_import(self):
        original=builtins.__import__;attempts=[]
        def guarded(name,*args,**kwargs):
            if name.split('.')[0] in ('torch','ultralytics','tensorrt'):
                attempts.append(name);raise AssertionError(name)
            return original(name,*args,**kwargs)
        with patch('builtins.__import__',side_effect=guarded):
            with self.assertRaisesRegex(DetectorError,'^TENSORRT_NATIVE_RUNTIME_NOT_IMPLEMENTED$'):
                create_detector(self.package)
        self.assertEqual(attempts,[])

    def test_real_preprocess_decode_result_and_identity(self):
        detector=self.detector()
        result=detector.detect(self.frame)
        self.assertEqual(result.frame_id,'input-id')
        self.assertEqual(result.model_version,'1'*64)
        self.assertEqual(result.detections[0].bounding_box.to_dict(),dict(x1=3.,y1=3.,x2=5.,y2=5.))
        self.assertEqual(result.detections[0].class_name,self.package.names[0])
        np.testing.assert_allclose(self.executor.inputs[0][0,:,0,0],[3/255,2/255,1/255])
        self.assertEqual(set(result.to_dict()),{'frame_id','detections','model_version','inference_ms'})
        self.assertGreaterEqual(result.inference_ms,0)

    def test_metadata_identities_detached_json_and_timing_default_off(self):
        detector=self.detector()
        detector.detect(self.frame)
        metadata=detector.runtime_metadata()
        self.assertEqual(metadata['backend'],'tensorrt')
        self.assertEqual(metadata['artifact_sha256'],self.package.manifest['files']['model']['sha256'])
        self.assertEqual(metadata['source_model_sha256'],'1'*64)
        self.assertEqual(metadata['source_onnx_sha256'],'2'*64)
        self.assertFalse(metadata['timing']['latency_enabled'])
        self.assertIsNone(metadata['timing']['detector_host_total_ms'])
        self.assertIsNone(metadata['timing']['h2d_ms'])
        json.dumps(metadata,allow_nan=False)
        metadata['input_contract']['shape'][0]=99
        self.assertEqual(detector.runtime_metadata()['input_contract']['shape'][0],1)

    def test_timing_opt_in_host_only(self):
        detector=self.detector(latency_enabled=True)
        detector.detect(self.frame)
        self.assertGreaterEqual(detector.runtime_metadata()['timing']['detector_host_total_ms'],0)

    def test_empty_valid(self):
        self.executor.output=raw([])
        self.assertEqual(self.detector().detect(self.frame).detections,())

    def test_bad_input_recoverable_no_execute_then_good_input(self):
        detector=self.detector()
        frame=CameraFrame(self.frame.image,'bad',self.frame.captured_at,9,8,'synthetic')
        with self.assertRaisesRegex(DetectorError,'INPUT_CONTRACT_MISMATCH'):detector.detect(frame)
        self.assertEqual(self.executor.calls,0)
        self.assertEqual(detector.detect(self.frame).frame_id,'input-id')

    def test_unknown_execution_error_invalidates_and_never_returns_empty(self):
        from src.contracts.interfaces import FatalDetectorError
        detector=self.detector();self.executor.error=RuntimeError('synthetic failure')
        with self.assertRaises(FatalDetectorError):detector.detect(self.frame)
        self.executor.error=None
        with self.assertRaises(FatalDetectorError):detector.detect(self.frame)
        self.assertEqual(self.executor.calls,1)

    def test_invalid_output_fatal_even_if_executor_claims_usable(self):
        from src.contracts.interfaces import FatalDetectorError
        detector=self.detector();self.executor.output={'invalid':np.zeros((1,8,8400),np.float32)}
        with self.assertRaisesRegex(FatalDetectorError,'OUTPUT_CONTRACT_MISMATCH'):detector.detect(self.frame)
        self.assertEqual(detector.runtime_metadata()['runtime_state'],'INVALIDATED')

    def test_close_idempotent_and_no_execution_after_close(self):
        detector=self.detector();detector.close();detector.close()
        self.assertEqual(self.executor.closed,1)
        with self.assertRaises(DetectorError):detector.detect(self.frame)
        self.assertEqual(self.executor.calls,0)

    def test_wrapped_format_rejected_before_executor(self):
        manifest=executable_fixture(self.root)
        manifest['files']['model']['artifact_format']='ultralytics_metadata_prefixed_engine'
        write_manifest(self.root,manifest)
        with self.assertRaisesRegex(DetectorError,'ARTIFACT_FORMAT_UNSUPPORTED'):
            create_detector(load_package(self.root),executor_factory=lambda _:self.fail('executor created'))

    def test_pt_close_only_addition_preserves_original_method_ast(self):
        from src.vision.pytorch_detector import PyTorchDetector
        instance=object.__new__(PyTorchDetector)
        instance.close();instance.close()
        parent=Path(__file__).resolve().parents[2]/'jetson_p0_004b/candidate_runtime/src/vision/pytorch_detector.py'
        old=ast.parse(parent.read_text(encoding='utf-8'))
        current=ast.parse(inspect.getsource(__import__('src.vision.pytorch_detector',fromlist=['x'])))
        def methods(tree):
            return {node.name:ast.dump(node,include_attributes=False) for node in ast.walk(tree)
                    if isinstance(node,ast.FunctionDef) and node.name in ('__init__','_observe_input','detect','runtime_metadata')}
        self.assertEqual(methods(old),methods(current))
