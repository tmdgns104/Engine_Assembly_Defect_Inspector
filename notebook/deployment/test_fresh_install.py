"""Fresh checkout installation boundaries, without opening hardware."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

JETSON = Path(__file__).resolve().parents[2] / 'jetson'
sys.path.insert(0, str(JETSON))


def installer():
    specification = importlib.util.spec_from_file_location('fresh_install', JETSON / 'install.py')
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class FreshInstallTests(unittest.TestCase):
    def test_checkout_contains_real_models_and_complete_assets(self):
        result = installer().verify_source(JETSON)
        self.assertEqual(len(result['models']), 2)
        self.assertTrue(all(item['bytes'] > 1_000_000 for item in result['models']))
        self.assertFalse(result['physical_output_enabled'])

    def test_existing_installation_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'current').mkdir()
            sentinel = root / 'current/user.txt'
            sentinel.write_text('preserve', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                installer().install_layout(root, '/dev/video0', JETSON)
            self.assertEqual(sentinel.read_text(encoding='utf-8'), 'preserve')

    @unittest.skipUnless(os.name == 'posix', 'Linux symlink layout is verified on Linux')
    def test_complete_linux_layout_and_second_install_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'installation'
            module = installer()
            result = module.install_layout(root, '/dev/video0', JETSON)
            self.assertFalse(result['runtime_started'])
            self.assertEqual(result['backend'], 'MOCK')
            self.assertTrue((root / 'current/config').is_symlink())
            release = json.loads((root / 'current/release.json').read_text(encoding='utf-8'))
            import hashlib
            for name, expected in release['files'].items():
                self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), expected, name)
            with self.assertRaises(FileExistsError):
                module.install_layout(root, '/dev/video0', JETSON)

    def test_camera_requires_explicit_device_path(self):
        for path in ('', '/tmp/camera', '/dev/video0 ! fakesink', '/dev/../tmp/camera'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                installer().device_settings(path)

    def test_new_device_uses_mock_without_legacy_overlay(self):
        station, runtime = installer().device_settings('/dev/v4l/by-id/device-video-index0')
        self.assertEqual(station['camera_device'], '/dev/v4l/by-id/device-video-index0')
        self.assertIs(runtime['plc_bench'], False)
        self.assertIs(runtime['mock_auto_request'], True)
        self.assertEqual(runtime['pythonpath'], '../current')
        self.assertNotIn('confirmed', json.dumps(station))


if __name__ == '__main__':
    unittest.main()
