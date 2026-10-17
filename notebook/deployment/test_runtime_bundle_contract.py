"""Checkout/package regressions. No camera, inference, network or field writes."""
import hashlib
import json
from pathlib import Path
import struct
import sys
from unittest.mock import patch
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'jetson'))
from build_bundle import collect_release


class RuntimeBundleContractTests(unittest.TestCase):
    def test_completed_evidence_import_is_allowlisted(self):
        spec=json.loads((ROOT/'jetson/runtime_allowlist.json').read_text(encoding='utf-8'))
        relative='src/runtime/completed_evidence.py'
        self.assertIn(relative,spec['runtime_files'])
        compile((ROOT/'jetson'/relative).read_text(encoding='utf-8'),relative,'exec')

    def fixture(self, root):
        (root/'jetson').mkdir()
        (root/'jetson/runtime_allowlist.json').write_text(json.dumps(dict(
            runtime_files=[], product_files=[], source_baseline_manifest_sha256='fixture')), encoding='utf-8')
        for name in ('station', 'runtime'):
            (root/f'jetson/{name}.example.json').write_text('{}', encoding='utf-8')

    def test_offline_dependency_hash_and_path_are_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root)
            assets = root/'offline'; assets.mkdir()
            content = b'isolated packaging fixture, not an image or model'
            (assets/'dependency.bin').write_bytes(content)
            manifest = dict(files=[dict(relative_path='dependency.bin', sha256=hashlib.sha256(content).hexdigest())])
            lock = root/'jetson/assembly_assets.lock.json'
            lock.write_text(json.dumps(manifest), encoding='utf-8')
            _, release, _ = collect_release(root, assembly_assets=assets, require_assembly=True)
            self.assertEqual(release['bundle_scope'], 'INTEGRATED_AI_OFFLINE')
            (assets/'dependency.bin').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'FROZEN_SHADOW_DEPENDENCY_CHANGED'):
                collect_release(root, assembly_assets=assets, require_assembly=True)
            manifest['files'][0]['relative_path'] = '../dependency.bin'
            lock.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'INVALID_ALLOWLIST_PATH'):
                collect_release(root, assembly_assets=assets)

    def test_local_image_backed_profile_cannot_lose_its_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.fixture(root)
            config=root/'jetson/config'; config.mkdir()
            (config/'reference.bin').write_bytes(b'fixture')
            (config/'area_clearance.json').write_text(json.dumps(dict(references=[dict(
                path='reference.bin', sha256=hashlib.sha256(b'fixture').hexdigest())])), encoding='utf-8')
            path=root/'jetson/runtime_allowlist.json'; spec=json.loads(path.read_text())
            spec['runtime_files']=['config/area_clearance.json']; path.write_text(json.dumps(spec))
            with self.assertRaisesRegex(ValueError, 'AREA_REFERENCE_NOT_ALLOWLISTED'):
                collect_release(root)

    def test_core_bundle_is_explicitly_not_full_assembly_runtime(self):
        files, release, _ = collect_release(ROOT)
        self.assertEqual(release['bundle_scope'], 'CORE_MOCK_ONLY')
        self.assertFalse(release['assembly_assets_included'])
        self.assertFalse(release['field_automatic_operation_verified'])
        self.assertFalse(any('/conveyor_references/' in name for name in files))
        for name in ('src/runtime/aborted_recovery.py', 'src/runtime/health_diagnostics.py',
                     'src/runtime/completed_evidence.py',
                     'src/runtime/product_passage.py', 'src/vision/assembly_evidence.py',
                     'src/vision/assembly_inspection.py', 'apps/edge_service/result_storage.py',
                     'apps/edge_service/line_hmi.html', 'apps/edge_service/inspection_details.js',
                     'src/control/opener_cyclic.py', 'opener/OpENer'):
            self.assertIn('current/' + name, files)
        self.assertNotIn('current/src/runtime/automatic_admission.py', files)

    def test_required_assembly_never_silently_omitted(self):
        with self.assertRaisesRegex(ValueError, 'REQUIRED_ASSEMBLY_ASSETS_MISSING'):
            collect_release(ROOT, require_assembly=True)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                collect_release(ROOT, assembly_assets=Path(directory), require_assembly=True)

    def test_four_classifiers_and_alignment_are_locked_not_field_photos(self):
        manifest = json.loads((ROOT/'jetson/assembly_assets.lock.json').read_text(encoding='utf-8'))
        names = [item['relative_path'] for item in manifest['files']]
        self.assertEqual(len(names), len(set(names)))
        for component in ('exhaust', 'pipe_left', 'pipe_right', 'symbol'):
            self.assertEqual(sum(name.endswith('/'+component+'/weights/best.pt') for name in names), 1)
            self.assertEqual(sum(name.endswith('/'+component+'/class_mapping.json') for name in names), 1)
        self.assertTrue(any(name.endswith('/train_body_bank.npz') for name in names))
        self.assertTrue(any(name.endswith('/reference_T0001.png') for name in names))
        self.assertFalse(any('conveyor_references' in name for name in names))
        self.assertNotIn('frozen_source_root', manifest)

    def test_binary_is_arm64_and_matches_verified_profile(self):
        binary = (ROOT/'jetson/opener/OpENer').read_bytes()
        self.assertEqual(binary[:4], b'\x7fELF')
        self.assertEqual(struct.unpack_from('<H', binary, 18)[0], 183)
        profile = json.loads((ROOT/'jetson/opener/source_profile/PROFILE.json').read_text(encoding='utf-8'))
        self.assertIn(hashlib.sha256(binary).hexdigest(), json.dumps(profile))


if __name__ == '__main__':
    unittest.main()
