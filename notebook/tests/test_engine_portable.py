"""Packaging paths and startup safety, without changing legacy entry behavior."""
from pathlib import Path
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from training.capture_windows import portable


class PortableTests(unittest.TestCase):
    def test_frozen_data_stays_beside_executable_not_extraction_or_cwd(self):
        with tempfile.TemporaryDirectory() as scratch:
            base = Path(scratch).resolve()
            home = base / '팀원 실행 폴더'
            unpack = base / '_MEI12345'
            with patch.object(sys, 'frozen', True, create=True), \
                 patch.object(sys, '_MEIPASS', str(unpack), create=True), \
                 patch.object(sys, 'executable', str(home / 'EngineDatasetWizard.exe')):
                profile, output, logs = portable.locations()
            self.assertEqual(profile, unpack / portable.ENGINE_PROFILE)
            self.assertEqual(output, home / 'data/engine/raw')
            self.assertEqual(logs, home / 'logs')
            self.assertFalse(base.joinpath('팀원 실행 폴더').exists())

    def test_normal_portable_start_reuses_existing_main_and_preserves_output(self):
        with tempfile.TemporaryDirectory() as scratch:
            base = Path(scratch)
            profile, output, logs = base / 'profile.json', base / 'data', base / 'logs'
            output.mkdir()
            original = output / 'existing.txt'
            original.write_text('preserve', encoding='utf-8')
            with patch.object(portable, 'locations', return_value=(profile, output, logs)), \
                 patch('training.capture_windows.__main__.main', return_value=0) as launch:
                self.assertEqual(portable.main([]), 0)
            launch.assert_called_once_with(['--profile', str(profile), '--output-root', str(output)])
            self.assertEqual(original.read_text(encoding='utf-8'), 'preserve')
            self.assertEqual(len(list(logs.glob('startup_*.log'))), 1)

    def test_startup_failure_has_visible_message_and_persistent_log(self):
        with tempfile.TemporaryDirectory() as scratch:
            base = Path(scratch)
            with patch.object(portable, 'locations', return_value=(base/'profile', base/'data', base/'logs')), \
                 patch('training.capture_windows.__main__.main', side_effect=RuntimeError('synthetic startup failure')), \
                 patch.object(portable, 'show_startup_error') as message:
                self.assertEqual(portable.main([]), 1)
            self.assertIn('오류 기록', message.call_args.args[0])
            self.assertIn('synthetic startup failure', next((base/'logs').glob('*.log')).read_text(encoding='utf-8'))

    def test_unknown_arguments_do_not_start_app(self):
        with patch.object(portable, 'show_startup_error') as message, \
             patch('training.capture_windows.__main__.main') as launch:
            self.assertEqual(portable.main(['--unsupported']), 2)
        launch.assert_not_called()
        message.assert_called_once()

    @unittest.skipUnless(os.name == 'nt', 'Windows long-path regression')
    def test_long_collection_paths_save_reopen_and_export_without_os_policy_change(self):
        from test_engine_dataset_v1 import Fixture
        from training.capture_windows.storage_paths import storage_path
        from training.capture_windows.wizard import Collection
        with tempfile.TemporaryDirectory() as scratch:
            branch = storage_path(Path(scratch)/('long capture folder_'*5))
            owned = branch/('nested station_'*5)
            self.assertTrue(owned.is_relative_to(storage_path(scratch)))
            fixture = Fixture(owned)
            try:
                fixture.reach(lambda action: action['kind'] == 'setup_review')
                self.assertEqual(len(fixture.col.attempts), 2)
                folder = fixture.col.folder
                raw = folder/'sessions'/next(iter(fixture.col.attempts.values()))['record']['image_path']
                self.assertGreater(len(str(raw)), 300)
                self.assertTrue(raw.is_file())
                before = raw.read_bytes()
                fixture.col.close()
                # File dialogs can return the ordinary drive spelling of the same folder.
                fixture.col = Collection.open(str(folder).removeprefix('\\\\?\\'))
                self.assertEqual(fixture.col.next_action()['kind'], 'setup_review')
                self.assertTrue((fixture.col.export()/'LABELING_CONTRACT.json').is_file())
                self.assertEqual(raw.read_bytes(), before)
            finally:
                fixture.col.close()
                self.assertTrue(branch.is_relative_to(storage_path(scratch)))
                shutil.rmtree(branch)


if __name__ == '__main__':
    unittest.main()
