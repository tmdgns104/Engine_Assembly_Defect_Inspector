"""노트북에서 실행하는 배포 경계 시험. 카메라·모델 추론은 시작하지 않는다."""
import importlib.util
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def load_packager():
    spec = importlib.util.spec_from_file_location('package_candidate', HERE / 'package_candidate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.packager = load_packager()

    def test_bundle_has_runtime_dependencies_and_no_development_material(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'runtime.tar.gz'
            result = self.packager.build_package(archive)
            with tarfile.open(archive) as bundle:
                names = set(bundle.getnames())
                manifest = json.load(bundle.extractfile('current/release.json'))
            self.assertIn('current/apps/edge_service/auto_hmi.html', names)
            self.assertIn('current/src/vision/diagnostic_capture.py', names)
            self.assertIn('current/src/control/omron_cip.py', names)
            self.assertIn('assets/products/ENGINE_Z3005_5/dynamic_parts_005/self_test.png', names)
            self.assertIn('assets/products/ENGINE_Z3005_5/dynamic_parts_005/pose/reference_bank.npz', names)
            self.assertIn('assets/products/ENGINE_Z3005_5/envelope_v007_fp16/model.plan', names)
            self.assertFalse(any('/tests/' in name or '/verification/' in name or '/runs/' in name for name in names))
            self.assertNotIn('current/scripts/build_tensorrt_plan.py', names)
            self.assertNotIn('data/journal.sqlite3', names)
            self.assertEqual(set(manifest['files']) | set(manifest['links']) | {'current/release.json'}, names)
            self.assertEqual(manifest['release_id'], result['release_id'])
            self.assertEqual(manifest['qualification'], 'DEVELOPMENT_BASELINE_NOT_PRODUCTION_ACCEPTED')

    def test_reject_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                self.packager.checked_file(root, '../outside.py')
            with self.assertRaises(ValueError):
                self.packager.checked_file(root, '/absolute.py')

    def test_missing_allowlisted_file_fails_before_archive_is_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'notebook/deployment').mkdir(parents=True)
            (root / 'notebook/deployment/runtime_allowlist.json').write_text(json.dumps({
                'runtime_files': ['missing.py'], 'product_files': []}), encoding='utf-8')
            output = root / 'out.tar.gz'
            with self.assertRaises(FileNotFoundError):
                self.packager.build_package(output, project_root=root)
            self.assertFalse(output.exists())

    def test_managed_stop_requires_idle_inspection_and_request_off(self):
        path = HERE.parents[1] / 'jetson/manage_live.py'
        spec = importlib.util.spec_from_file_location('managed', path)
        managed = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(managed)
        status = {'operating': False, 'active_cycle': None,
                  'inspection_service': {'active_inspection_id': None, 'diagnostic_capture': {'state': 'IDLE'}},
                  'plc': {'Inspection_Request': False}}
        managed.assert_idle(status)
        status['plc']['Inspection_Request'] = True
        with self.assertRaises(RuntimeError):
            managed.assert_idle(status)
        status['plc']['Inspection_Request'] = False
        status['inspection_service']['diagnostic_capture']['state'] = 'SAVING'
        with self.assertRaises(RuntimeError):
            managed.assert_idle(status)

    def test_deployer_rejects_archive_escape_and_unexpected_links(self):
        spec = importlib.util.spec_from_file_location('deploy', HERE / 'deploy_area.py')
        deploy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(deploy)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.tar'
            for name, link in [('../outside', None), ('current/escape', '/etc'),
                               ('current/config', '../../outside')]:
                with tarfile.open(path, 'w') as archive:
                    member = tarfile.TarInfo(name)
                    if link:
                        member.type = tarfile.SYMTYPE
                        member.linkname = link
                        archive.addfile(member)
                    else:
                        archive.addfile(member, io.BytesIO(b''))
                with self.assertRaises(ValueError):
                    deploy.validate_bundle(path, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_deployer_checks_archive_hash_before_mutation(self):
        spec = importlib.util.spec_from_file_location('deploy', HERE / 'deploy_area.py')
        deploy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(deploy)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.tar'
            path.write_bytes(b'not an approved bundle')
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_SHA256_MISMATCH'):
                deploy.validate_bundle(path, '0' * 64)


if __name__ == '__main__':
    unittest.main(verbosity=2)
