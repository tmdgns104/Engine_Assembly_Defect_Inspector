"""Architecture-only tests. Synthetic bytes are never an executable TensorRT engine."""
import ast
import builtins
import copy
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

from src.contracts import CameraFrame, DetectionResult, DetectorError
from src.recipe.package import PackageError, canonical, load_package, sha256
from src.vision import pytorch_detector
from src.vision.detector_factory import create_detector
from test_product_package import write_package, fixture_documents

ROOT = Path(__file__).resolve().parents[3]


def write_manifest(root, manifest):
    (root/'manifest.json').write_text(canonical(manifest), encoding='utf-8')


def trt_fixture(root, artifact_format='trt_plan'):
    documents = fixture_documents()
    documents['preprocessing']['nms_location'] = None
    manifest = write_package(root, documents)
    # Opaque fake artifact, deliberately named .pt: no extension-based interpretation.
    (root/'best.pt').write_bytes(b'synthetic-not-a-real-engine')
    manifest['schema_version'] = 2
    manifest['files']['model'] = {'path':'best.pt','sha256':sha256((root/'best.pt').read_bytes()),
                                'artifact_format':artifact_format}
    manifest['detector'] = {
        'backend':'tensorrt','task':'detect','output':None,'precision':None,
        'source_model_sha256':'1'*64,
        'input':{'shape':[1,3,768,960],'dtype':'float32','layout':'NCHW'},
        'provenance':{'build':{'tool':None,'version':None,'options':{}},
                      'build_environment':{'tensorrt':None,'cuda':None,'l4t':None,
                                 'gpu_compute_capability':None,'plugins':None}}}
    write_manifest(root, manifest)
    return manifest


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)/'package'

    def test_existing_earbud_manifest_and_snapshot_unchanged(self):
        folder = ROOT/'deployment/products/earbud_case_v0/app_v001'
        current = load_package(folder)
        spec = importlib.util.spec_from_file_location('original_package',ROOT/'runs/jetson_p0_003/runtime/src/recipe/package.py')
        old = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'original_package':old}):
            spec.loader.exec_module(old)
        self.assertEqual(current.snapshot(),old.load_package(folder).snapshot())
        self.assertEqual(current.backend,'pytorch')

    def test_legacy_missing_backend_default_without_mutation(self):
        manifest = write_package(self.root)
        del manifest['detector']['backend']
        write_manifest(self.root,manifest)
        original = (self.root/'manifest.json').read_bytes()
        package = load_package(self.root)
        self.assertEqual(package.backend,'pytorch')
        self.assertEqual(package.backend_resolution, {'declared_backend':None,'resolved_backend':'pytorch',
                                                     'resolution_basis':'PYTORCH_LEGACY_DEFAULT'})
        self.assertNotIn('backend',package.manifest['detector'])
        self.assertEqual(package.snapshot()['backend_resolution'],package.backend_resolution)
        self.assertEqual((self.root/'manifest.json').read_bytes(),original)

    def test_factory_explicit_and_legacy_forward_exact_arguments(self):
        for explicit in (True,False):
            with self.subTest(explicit=explicit):
                manifest = write_package(self.root)
                if not explicit:
                    del manifest['detector']['backend']; write_manifest(self.root,manifest)
                package = load_package(self.root)
                with patch.object(pytorch_detector,'PyTorchDetector') as constructor:
                    self.assertIs(create_detector(package),constructor.return_value)
                    constructor.assert_called_once_with(package.model_path,manifest['files']['model']['sha256'],
                        package.names,package.preprocessing['confidence'],package.preprocessing['nms_iou'],
                        package.preprocessing,latency_enabled=False)

    def test_factory_latency_opt_in_only(self):
        write_package(self.root)
        with patch.object(pytorch_detector,'PyTorchDetector') as constructor:
            create_detector(load_package(self.root),latency_enabled=True)
            self.assertIs(constructor.call_args.kwargs['latency_enabled'],True)
        self.assertIs(inspect.signature(create_detector).parameters['latency_enabled'].default,False)
        self.assertIs(inspect.signature(pytorch_detector.PyTorchDetector).parameters['latency_enabled'].default,False)

    def test_unknown_backend_rejected_before_model_read_or_import(self):
        manifest = write_package(self.root)
        package = load_package(self.root)
        package.manifest['detector']['backend'] = 'unknown'
        with patch.object(pytorch_detector,'PyTorchDetector') as constructor, \
             patch.object(Path,'read_bytes',side_effect=AssertionError('file opened')):
            with self.assertRaisesRegex(DetectorError,'UNSUPPORTED_BACKEND'):create_detector(package)
            constructor.assert_not_called()
        manifest['detector']['backend']='unknown';write_manifest(self.root,manifest)
        with self.assertRaisesRegex(PackageError,'UNSUPPORTED_BACKEND'):load_package(self.root)

    def test_synthetic_formats_schema_valid_no_engine_parsing(self):
        for fmt in ('trt_plan','ultralytics_metadata_prefixed_engine'):
            with self.subTest(format=fmt):
                manifest = trt_fixture(self.root,fmt)
                package = load_package(self.root)
                self.assertEqual(package.backend,'tensorrt')
                self.assertEqual(package.snapshot()['manifest'],manifest)

    def test_trt_factory_no_fallback_import_or_model_read(self):
        trt_fixture(self.root)
        package = load_package(self.root)
        imports = []
        original = builtins.__import__
        def guarded(name,*args,**kwargs):
            imports.append(name)
            if name.split('.')[0] in ('torch','tensorrt','ultralytics','onnx'):
                raise AssertionError('Forbidden framework import '+name)
            return original(name,*args,**kwargs)
        with patch.object(pytorch_detector,'PyTorchDetector') as constructor, \
             patch('builtins.__import__',side_effect=guarded), \
             patch.object(Path,'read_bytes',side_effect=AssertionError('model opened')):
            with self.assertRaisesRegex(DetectorError,'^TENSORRT_BACKEND_NOT_IMPLEMENTED$'):
                create_detector(package)
            constructor.assert_not_called()
        self.assertEqual(imports,[])

    def test_unknown_format_rejected_no_autodetect(self):
        manifest = trt_fixture(self.root)
        for value in ('engine','auto','',None,1,[]):
            with self.subTest(value=value):
                manifest['files']['model']['artifact_format']=value
                write_manifest(self.root,manifest)
                with self.assertRaisesRegex(PackageError,'ARTIFACT_FORMAT_UNSUPPORTED'):load_package(self.root)

    def test_artifact_hash_mismatch_rejected(self):
        trt_fixture(self.root)
        (self.root/'best.pt').write_bytes(b'changed')
        with self.assertRaisesRegex(PackageError,'ARTIFACT_HASH_MISMATCH'):load_package(self.root)

    def test_required_contract_fields_rejected_when_missing(self):
        for key in ('backend','input','precision','source_model_sha256','provenance','output','task'):
            with self.subTest(key=key):
                manifest=trt_fixture(self.root);del manifest['detector'][key];write_manifest(self.root,manifest)
                with self.assertRaises(PackageError):load_package(self.root)
        manifest=trt_fixture(self.root);del manifest['files']['model']['artifact_format'];write_manifest(self.root,manifest)
        with self.assertRaises(PackageError):load_package(self.root)

    def test_path_traversal_absolute_and_windows_escape(self):
        for path in ('../outside.engine','C:/outside.engine','/outside.engine','a\\outside.engine'):
            with self.subTest(path=path):
                manifest=trt_fixture(self.root);manifest['files']['model']['path']=path;write_manifest(self.root,manifest)
                with self.assertRaises(PackageError):load_package(self.root)

    def test_resolved_path_escape_even_with_safe_relative_name(self):
        trt_fixture(self.root)
        resolve=Path.resolve
        outside=self.root.parent/'outside.engine'
        def redirect(path,*args,**kwargs):
            return outside if path == self.root/'best.pt' else resolve(path,*args,**kwargs)
        with patch.object(Path,'resolve',redirect):
            with self.assertRaisesRegex(PackageError,'Escaping'):load_package(self.root)

    def test_backend_absence_never_defaults_new_schema_or_invalid_legacy(self):
        manifest=trt_fixture(self.root);del manifest['detector']['backend'];write_manifest(self.root,manifest)
        with self.assertRaises(PackageError):load_package(self.root)
        manifest=write_package(self.root);del manifest['detector']['backend'];manifest['detector']['output']='raw'
        write_manifest(self.root,manifest)
        with self.assertRaises(PackageError):load_package(self.root)

    def test_precision_is_explicit_declaration_not_default_approval(self):
        for value in (None,'fp32','fp16'):
            manifest=trt_fixture(self.root);manifest['detector']['precision']=value;write_manifest(self.root,manifest)
            self.assertEqual(load_package(self.root).manifest['detector']['precision'],value)
        manifest['detector']['precision']='int8';write_manifest(self.root,manifest)
        with self.assertRaises(PackageError):load_package(self.root)

    def test_input_shape_layout_dtype_consistency(self):
        for value in ({'shape':[1,3,640,640],'dtype':'float32','layout':'NCHW'},
                      {'shape':[True,3,768,960],'dtype':'float32','layout':'NCHW'},
                      {'shape':[1,3,768,960],'dtype':'float16','layout':'NCHW'},
                      {'shape':[1,3,768,960],'dtype':'float32','layout':'NHWC'}):
            manifest=trt_fixture(self.root);manifest['detector']['input']=value;write_manifest(self.root,manifest)
            with self.assertRaises(PackageError):load_package(self.root)

    def test_provenance_hash_and_required_shapes(self):
        for value in (None,{},[],{'build':{},'build_environment':{}}):
            manifest=trt_fixture(self.root);manifest['detector']['provenance']=value;write_manifest(self.root,manifest)
            with self.assertRaises(PackageError):load_package(self.root)
        manifest=trt_fixture(self.root);manifest['detector']['source_model_sha256']='not-sha';write_manifest(self.root,manifest)
        with self.assertRaises(PackageError):load_package(self.root)

    def test_output_and_nms_stay_explicitly_unresolved(self):
        manifest=trt_fixture(self.root);manifest['detector']['output']='ultralytics_xyxy';write_manifest(self.root,manifest)
        with self.assertRaises(PackageError):load_package(self.root)

    def test_snapshot_retains_trt_provenance_in_journal_without_migration(self):
        from src.journal.sqlite import Journal
        trt_fixture(self.root)
        snapshot=load_package(self.root).snapshot()
        journal=Journal(self.root.parent/'journal',min_free_bytes=0)
        self.addCleanup(journal.close)
        request={'cell_id':'synthetic','plc_session_id':1,'cycle_id':1,'request_id':1,'attempt':1}
        inspection,_=journal.admit(request,snapshot)
        journal.finish(inspection,{'decision':'REVIEW'},
                       [{'kind':'raw','data':b'synthetic-evidence','width':1,'height':1}])
        self.assertEqual(journal.detail(inspection)['package'],snapshot)
        self.assertEqual(journal.db.execute('PRAGMA user_version').fetchone()[0],1)
        snapshot['manifest']['detector']['source_model_sha256']='mutated'
        self.assertEqual(journal.detail(inspection)['package']['manifest']['detector']['source_model_sha256'],'1'*64)

    def test_worker_source_uses_factory_and_neutral_metadata_only(self):
        from src.vision import inspection_worker
        source=inspect.getsource(inspection_worker.worker_main)
        self.assertIn('create_detector(package)',source)
        self.assertIn('detector.runtime_metadata()',source)
        for forbidden in ('PyTorchDetector','detector.torch','detector.device','detector.input_shape','"pytorch"','"tensorrt"'):
            self.assertNotIn(forbidden,source)

    def test_detection_result_code_unchanged(self):
        current=ROOT/'runs/jetson_p0_004b/candidate_runtime/src/contracts/models.py'
        baseline=ROOT/'runs/jetson_p0_003/runtime/src/contracts/models.py'
        self.assertEqual(current.read_bytes(),baseline.read_bytes())

    def test_pytorch_metadata_detached_json_without_extra_sync(self):
        detector=pytorch_detector.PyTorchDetector.__new__(pytorch_detector.PyTorchDetector)
        detector.device='cuda:0';detector.model_hash='a'*64;detector.input_shape=[1,3,640,640]
        detector.latency_enabled=False;detector.last_reported_speed=None;detector.startup_timestamps_ns={}
        detector.torch=SimpleNamespace(__version__='mock',version=SimpleNamespace(cuda='mock'),
            cuda=SimpleNamespace(get_device_name=Mock(return_value='mock GPU'),synchronize=Mock()))
        metadata=detector.runtime_metadata()
        json.dumps(metadata,allow_nan=False)
        self.assertEqual(metadata['artifact_sha256'],'a'*64)
        self.assertEqual(metadata['source_model_sha256'],'a'*64)
        self.assertFalse(metadata['timing']['latency_enabled'])
        self.assertEqual(metadata['observed_runtime'],{'torch':'mock','cuda':'mock'})
        self.assertNotIn('build_environment',metadata)
        metadata['input_shape'][0]=99
        self.assertEqual(detector.input_shape,[1,3,640,640])
        detector.torch.cuda.synchronize.assert_not_called()

    def test_legacy_package_factory_does_not_require_trt_runtime(self):
        write_package(self.root)
        original=builtins.__import__
        forbidden=[]
        def guarded(name,*args,**kwargs):
            if name.split('.')[0] in ('tensorrt','torch','ultralytics'):
                forbidden.append(name);raise AssertionError(name)
            return original(name,*args,**kwargs)
        with patch.object(pytorch_detector,'PyTorchDetector'),patch('builtins.__import__',side_effect=guarded):
            create_detector(load_package(self.root))
        self.assertEqual(forbidden,[])

    def test_factory_pytorch_mocked_execution_matches_exact_p003(self):
        from datetime import datetime, timezone
        from src.decision.slots import assess
        write_package(self.root)
        package=load_package(self.root)
        spec=importlib.util.spec_from_file_location('p003_detector',ROOT/'runs/jetson_p0_003/runtime/src/vision/pytorch_detector.py')
        baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
        outputs=[]
        for factory,enabled in ((False,False),(True,False),(True,True)):
            torch=ModuleType('torch');ultralytics=ModuleType('ultralytics')
            torch.cuda=SimpleNamespace(is_available=Mock(return_value=True),synchronize=Mock())
            network=Mock()
            network.parameters.return_value=iter([SimpleNamespace(device='cuda:0')])
            model=Mock(task='detect',names=dict(enumerate(package.names)))
            model.model=network;model.to.return_value=model
            tensor=Mock();tensor.detach.return_value.cpu.return_value.tolist.return_value=[[1,2,3,4,.9,0]]
            model.predict.return_value=[SimpleNamespace(boxes=SimpleNamespace(data=tensor),speed={'preprocess':1,'inference':2,'postprocess':3})]
            ultralytics.YOLO=Mock(return_value=model)
            module=pytorch_detector if factory else baseline
            with patch.dict(sys.modules,{'torch':torch,'ultralytics':ultralytics}), \
                 patch.object(module,'time',SimpleNamespace(perf_counter=Mock(side_effect=[1,1.01]),monotonic_ns=Mock(side_effect=[1,2,3,4]))):
                if factory:detector=create_detector(package,latency_enabled=enabled)
                else:detector=baseline.PyTorchDetector(package.model_path,package.manifest['files']['model']['sha256'],
                    package.names,package.preprocessing['confidence'],package.preprocessing['nms_iou'],package.preprocessing)
                frame=CameraFrame(object(),'same-frame',datetime.now(timezone.utc),100,100,'replay')
                result=detector.detect(frame).to_dict()
            torch.cuda.synchronize.assert_called();self.assertEqual(torch.cuda.synchronize.call_count,2)
            self.assertEqual(detector.last_reported_speed,{'preprocess':1,'inference':2,'postprocess':3} if enabled else None)
            ultralytics.YOLO.assert_called_once_with(str(package.model_path))
            model.to.assert_called_once_with('cuda:0')
            observation=dict(result,width=100,height=100,quality={'valid':True})
            outputs.append((result,assess([observation]*3,package.recipe,{},None)))
        self.assertEqual(outputs[0],outputs[1]);self.assertEqual(outputs[1],outputs[2])

    def test_pytorch_constructor_failure_propagates_without_retry(self):
        write_package(self.root)
        with patch.object(pytorch_detector,'PyTorchDetector',side_effect=DetectorError('MODEL_HASH_MISMATCH')) as constructor:
            with self.assertRaisesRegex(DetectorError,'MODEL_HASH_MISMATCH'):create_detector(load_package(self.root))
            self.assertEqual(constructor.call_count,1)

    def test_worker_trt_fault_precedes_camera_constructor(self):
        import queue
        import threading
        from src.vision.inspection_worker import worker_main
        trt_fixture(self.root)
        results=queue.Queue();stopping=threading.Event()
        with patch('src.camera.gstreamer_camera.GStreamerCamera') as camera, \
             patch.object(pytorch_detector,'PyTorchDetector') as detector:
            worker_main(self.root,{},'g',queue.Queue(),results,queue.Queue(),stopping,
                        threading.Event(),SimpleNamespace(value=0))
            camera.assert_not_called();detector.assert_not_called()
        fault=results.get_nowait()
        self.assertEqual(fault['type'],'fault')
        self.assertIn('TENSORRT_BACKEND_NOT_IMPLEMENTED',fault['error'])
        self.assertTrue(stopping.is_set())

    def test_explicit_null_backend_never_defaults(self):
        manifest=write_package(self.root);manifest['detector']['backend']=None;write_manifest(self.root,manifest)
        with self.assertRaisesRegex(PackageError,'UNSUPPORTED_BACKEND'):load_package(self.root)

    def test_provenance_nonfinite_json_rejected_as_package_error(self):
        manifest=trt_fixture(self.root)
        manifest['detector']['provenance']['build']['options']={'workspace':float('nan')}
        (self.root/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
        with self.assertRaisesRegex(PackageError,'BACKEND_CONTRACT_INVALID'):load_package(self.root)

    def test_missing_artifact_sha_rejected_as_package_error(self):
        manifest=trt_fixture(self.root);del manifest['files']['model']['sha256'];write_manifest(self.root,manifest)
        with self.assertRaises(PackageError):load_package(self.root)


if __name__=='__main__':unittest.main()
