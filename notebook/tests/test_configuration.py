"""값 보존·소비 연결·후보 거부. 장치/카메라/모델 실행은 하지 않는다."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'jetson'))
from src import config
from src.configuration import validate_settings, station_settings, profile_settings, snapshot
from src.vision.engine_inspector import EngineInspector


class ConfigurationTests(unittest.TestCase):
    def candidate(self, **changes):
        data={k:v for k,v in vars(config).items() if k.isupper()}
        return SimpleNamespace(**dict(data,**changes))

    def test_invalid_settings_are_rejected_not_defaulted(self):
        for changes in ({'ENGINE_PRODUCT_CONFIDENCE':float('nan')},{'ENGINE_PART_CONFIDENCE':True},
            {'POSE_MIN_SCALE':2.0},{'HISTORY_EXPORT_LIMIT':1000000},
            {'FRAME_SPACING_SECONDS':2},{'PLC_HEALTH_LEASE_SECONDS':1},
            {'REQUIRED_OBSERVATIONS':4},{'MOTION_STABLE_SECONDS':.2},
            {'FRAME_SPACING_SECONDS':True},{'STARTUP_TIMEOUT_SECONDS':'90'},
            {'POSE_CLAHE_GRID':(0,8)},{'RUN_CAPTURE_SCRATCH_BYTES':1.5},
            {'TRACK_ZONE_HYSTERESIS':-1},{'IPC_GRANT_LEASE_SECONDS':1}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                validate_settings(self.candidate(**changes))

    def test_startup_snapshot_is_detached(self):
        captured=snapshot()
        with patch.object(config,'ENGINE_PRODUCT_CONFIDENCE',.55):
            self.assertNotEqual(captured['sha256'],snapshot()['sha256'])
        self.assertEqual(captured,snapshot())

    def test_station_consumes_config_without_changing_identity_or_original(self):
        station={'cell_id':'fixture','camera_device':'fixture','fresh_frame':{'acceptance_scope':'existing'},'quality':{}}
        original=copy.deepcopy(station)
        with patch.object(config,'MIN_BLUR_VARIANCE',31):
            actual=station_settings(station)
        self.assertEqual(actual['quality']['min_blur_variance'],31)
        self.assertEqual(actual['fresh_frame']['inspection_window_ms'],3000)
        self.assertEqual(actual['camera_device'],'fixture')
        self.assertEqual(station,original)

    def test_motion_reads_changed_parameter(self):
        import numpy as np
        inspector=EngineInspector.__new__(EngineInspector);inspector.reset_motion()
        with patch.object(config,'MOTION_PIXEL_DIFFERENCE',29):
            inspector.motion(np.zeros((180,320,3),dtype=np.uint8))
        self.assertEqual(inspector.motion_evidence['difference_threshold'],29)

    def test_profile_keeps_control_policy(self):
        profile={'cycle_admission':'PLC_AUTOMATIC_REPEAT','pusher_enabled':False}
        self.assertEqual(profile_settings(profile)['cycle_admission'],profile['cycle_admission'])
        self.assertFalse(profile_settings(profile)['pusher_enabled'])

    def test_package_mismatch_rejected_before_model_start(self):
        from src.configuration import validate_package_settings
        from src.recipe.package import load_package
        root=Path(__file__).resolve().parents[2]
        package=load_package(root/'jetson'/config.ENGINE_PARTS_PACKAGE)
        validate_package_settings(package)
        with patch.object(config,'ENGINE_PRODUCT_CONFIDENCE',.55),self.assertRaisesRegex(ValueError,'CONFIG_PACKAGE_MISMATCH'):
            validate_package_settings(package)

    def test_recorded_configuration_is_detached_from_later_changes(self):
        from src.configuration import recorded_package
        from src.journal.sqlite import Journal
        settings=snapshot()
        package=SimpleNamespace(snapshot=lambda:{'manifest':{'product_id':'fixture'}})
        with tempfile.TemporaryDirectory() as temp:
            journal=Journal(temp,min_free_bytes=1)
            try:
                request=dict(cell_id='fixture',plc_session_id=1,request_id=1,cycle_id=1,attempt=1,kind='inspect')
                identifier,_=journal.admit(request,recorded_package(package,settings))
                settings['values']['ENGINE_PRODUCT_CONFIDENCE']=.9
                stored=json.loads(journal.db.execute('SELECT package_json FROM inspections WHERE inspection_id=?',(identifier,)).fetchone()[0])
                self.assertEqual(stored['configuration']['values']['ENGINE_PRODUCT_CONFIDENCE'],.5)
                self.assertEqual(stored['configuration']['sha256'],snapshot()['sha256'])
            finally:journal.db.close()

    def test_restarted_worker_cannot_silently_mix_new_config(self):
        from src.configuration import validate_worker_settings
        original=snapshot()
        validate_worker_settings(original,{'configuration_sha256':original['sha256']})
        with patch.object(config,'ENGINE_PART_CONFIDENCE',.55):
            changed=snapshot()
        for backend in ({},{'configuration_sha256':changed['sha256']}):
            with self.assertRaisesRegex(ValueError,'WORKER_CONFIGURATION_MISMATCH'):
                validate_worker_settings(original,backend)

    def test_frozen_products_default_generation_preserves_all_bytes(self):
        from notebook.deployment.configure_products import generate, ROOT
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'products';receipt=generate(target)
            for item,relative in zip(receipt['products'],(config.ENGINE_ENVELOPE_PACKAGE,config.ENGINE_PARTS_PACKAGE)):
                source=ROOT/'jetson'/relative
                self.assertEqual(item['manifest_sha256'],item['source_manifest_sha256'])
                for path in source.rglob('*'):
                    if path.is_file():self.assertEqual(path.read_bytes(),(target/source.name/path.relative_to(source)).read_bytes())
            with self.assertRaises(FileExistsError):generate(target)

    def test_package_config_change_regenerates_hashes_and_preserves_source(self):
        from notebook.deployment.configure_products import generate, ROOT
        from src.recipe.package import load_package
        source=ROOT/'jetson'/config.ENGINE_PARTS_PACKAGE/config.ENGINE_POSE_REFERENCE
        before=source.read_bytes()
        with tempfile.TemporaryDirectory() as temp,patch.object(config,'ENGINE_PRODUCT_CONFIDENCE',.55):
            receipt=generate(Path(temp)/'products')
            item=receipt['products'][1]
            self.assertNotEqual(item['manifest_sha256'],item['source_manifest_sha256'])
            loaded=load_package(Path(temp)/'products'/item['path'])
            pose=json.loads((loaded.root/config.ENGINE_POSE_REFERENCE).read_text(encoding='utf-8'))
            self.assertEqual(pose['decision_policy']['product_confidence'],.55)
        self.assertEqual(source.read_bytes(),before)


if __name__=='__main__':unittest.main()
