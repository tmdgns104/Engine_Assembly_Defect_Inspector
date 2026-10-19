"""새 장치 설치 경계. 실물 카메라/PLC/GPU를 사용하지 않는다."""
import importlib.util
import ast
from contextlib import closing
import io
import json
import os
from pathlib import Path, PurePosixPath
import sqlite3
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('portable_install', PROJECT/'jetson/install_operating.py')
install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install)
ARTIFACTS = PROJECT/'.p'
ARTIFACTS.mkdir(exist_ok=True)


class PortableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metadata = install.verify_bundle()

    def test_all_operating_files_and_seven_models_preserved(self):
        self.assertEqual(len(self.metadata['source_file_hashes']), 200)
        self.assertEqual(self.metadata['model_count'], 7)
        self.assertEqual(self.metadata['source_release'], 'engine-integrated-32c484ac6aeb07f1')
        self.assertFalse(any(name.startswith('data/') for name in self.metadata['files']))

    def test_history_sqlite_is_valid_and_not_active_data(self):
        with tempfile.TemporaryDirectory(dir=ARTIFACTS) as tmp:
            path = Path(tmp)/'history.sqlite3'
            with tarfile.open(install.ARCHIVE) as archive:
                path.write_bytes(archive.extractfile('history/journal.sqlite3').read())
            with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                self.assertEqual(db.execute('SELECT count(*) FROM inspections').fetchone()[0], 368)

    def test_unsafe_members_rejected(self):
        for name in ('../bad', '/tmp/bad', 'current/../../bad', 'current\\bad',
                     'current//bad', 'data/journal.sqlite3', 'C:/bad'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                install.validate_member_name(name)

    def test_archive_corruption_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory(dir=ARTIFACTS) as tmp:
            path = Path(tmp)/'bad.tar.gz'
            path.write_bytes(b'not an archive')
            install.write_json(path.with_suffix('.json'), {'sha256':'0'*64})
            with self.assertRaisesRegex(ValueError, 'BUNDLE_SHA256'):
                install.verify_bundle(path)

    def test_link_and_duplicate_archive_members_rejected(self):
        for duplicate in (False, True):
            with tempfile.TemporaryDirectory(dir=ARTIFACTS) as tmp:
                path = Path(tmp)/'bad.tar.gz'
                with tarfile.open(path, 'w:gz') as archive:
                    info = tarfile.TarInfo('current/test')
                    info.type = tarfile.REGTYPE if duplicate else tarfile.SYMTYPE
                    info.linkname = '/etc/passwd' if not duplicate else ''
                    archive.addfile(info, io.BytesIO(b''))
                    if duplicate:
                        archive.addfile(info, io.BytesIO(b''))
                install.write_json(path.with_suffix('.json'), {'sha256':install.digest(path)})
                with self.assertRaises(ValueError):
                    install.verify_bundle(path)

    def test_existing_runtime_data_never_overwritten(self):
        with tempfile.TemporaryDirectory(dir=ARTIFACTS) as tmp:
            base = Path(tmp)
            (base/'data').mkdir()
            sentinel = base/'data/user-original'
            sentinel.write_text('keep')
            with self.assertRaises(FileExistsError):
                install.check_new_base(base)
            self.assertEqual(sentinel.read_text(), 'keep')

    def test_device_settings_do_not_copy_approval(self):
        with tempfile.TemporaryDirectory(dir=ARTIFACTS) as tmp:
            stage = Path(tmp)
            (stage/'templates').mkdir(); (stage/'config').mkdir()
            with tarfile.open(install.ARCHIVE) as archive:
                for name in ('station', 'line_profile', 'standalone'):
                    (stage/f'templates/{name}.json').write_bytes(archive.extractfile(f'templates/{name}.json').read())
            install.device_config(stage, PurePosixPath('/home/alex/oned_device_bench'), '/dev/video2', 'cell-02')
            cfg = install.read_json(stage/'config/standalone.json')
            self.assertFalse(cfg['cyclic_transport_activation_approved'])
            self.assertFalse(cfg['cyclic_publication_enabled'])
            self.assertEqual(cfg['pythonpath'], '../current')
            self.assertEqual(cfg['listen_host'], '127.0.0.1')
            self.assertIn('/home/alex/', cfg['opener_ipc_path'])
            profile = install.read_json(stage/'config/line_profile.json')
            self.assertFalse(profile['observed_capture_zone']['confirmed'])
            self.assertEqual(profile['camera']['camera_device'], '/dev/video2')
            self.assertEqual(profile['inspection_start_policy'], 'PLC_REQUEST_TRACKED_FULL_FRAME')

    def test_invalid_device_names_cannot_inject_systemd(self):
        for user in ('root\nExecStart=/bin/sh', 'alex%', 'name space'):
            with self.assertRaises(ValueError):
                install.validate_device('/dev/video0', 'cell-02', PurePosixPath('/home/alex/app'), user)
        for camera in ('/dev/../tmp/bad', '/dev/video0 ! fakesink', '/tmp/video'):
            with self.assertRaises(ValueError):
                install.validate_device(camera, 'cell-02', PurePosixPath('/home/alex/app'), 'alex')
        unit = install.service_text('/home/alex/app', 'alex')
        self.assertIn('User=alex\n', unit)
        self.assertNotIn('/home/jetson/', unit)

    def test_explicit_setup_confirmation_required(self):
        with self.assertRaisesRegex(ValueError, 'CONFIRMATION'):
            install.enable_plc(Path('/missing'), stopped=True, camera_checked=False, contract_checked=True)

    @unittest.skipUnless(os.name == 'posix', 'Linux file layout and symlink test')
    def test_linux_prepare_and_first_setup_without_start(self):
        with tempfile.TemporaryDirectory(dir=ARTIFACTS) as tmp:
            base = Path(tmp)/'app'
            result = install.prepare(base, '/dev/video2', 'cell-02', 'alex')
            self.assertFalse(result['runtime_started'])
            self.assertEqual(list((base/'data').iterdir()), [])
            original = install.verify_installed(base)
            with patch.object(install, 'require_local_line_ready'), patch.object(
                    install, 'load_local_reference', return_value=(
                        {'source_inspection_id':'fixture-only'}, {'confirmed':True,'fixture_only':True})):
                configured = install.enable_plc(base, stopped=True, camera_checked=True, contract_checked=True)
            updated = install.verify_installed(base)
            self.assertNotEqual(original['release_id'], updated['release_id'])
            self.assertEqual(configured['new_device_execution'], 'NOT_VERIFIED')
            self.assertTrue(install.read_json(base/'config/standalone.json')['cyclic_publication_enabled'])
            self.assertEqual(list((base/'data').iterdir()), [])
            with self.assertRaises(FileExistsError):
                install.prepare(base, '/dev/video2', 'cell-02', 'alex')
            with self.assertRaisesRegex(ValueError, 'ALREADY_CONFIGURED'):
                install.enable_plc(base, stopped=True, camera_checked=True, contract_checked=True)
            (base/'current/standalone_service.py').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'INSTALLED_HASH'):
                install.verify_installed(base)


class ReferenceTests(unittest.TestCase):
    """실제 Journal 스키마와 기준 등록의 REVIEW 결과 계약을 사용한다."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ARTIFACTS)
        self.root = Path(self.temp.name).resolve()
        self.database = self.root/'journal.sqlite3'
        tree = ast.parse((PROJECT/'jetson/src/journal/sqlite.py').read_text(encoding='utf-8'))
        schema = next(ast.literal_eval(node.value) for node in tree.body
                      if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SCHEMA' for t in node.targets))
        self.expected = {'manifest_sha256':'package', 'station_id':'new-station'}
        self.candidate = dict(self.expected, confirmed=False, source_inspection_id='reference-1',
                              source_frame_ids=['camera-new-1','camera-new-2','camera-new-3'])
        self.reference = dict(self.candidate, confirmed=True)
        ref_sha = install.hashlib.sha256(json.dumps(self.reference, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.zone = dict(confirmed=True, calibration_sha=ref_sha,
                        polygon_normalized=[[0,0],[1,0],[1,1],[0,1]], entry_policy='product_center')
        with closing(sqlite3.connect(self.database)) as db, db:
            db.executescript(schema)
            db.execute('INSERT INTO inspections VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
                'reference-1','cell',1,1,1,1,'fingerprint',json.dumps({'kind':'calibrate'}),'{}',
                'COMPLETE','REVIEW',json.dumps(dict(decision='REVIEW',storage_success=True,
                calibration_candidate=self.candidate)),'time-1','time-2'))
            db.execute('INSERT INTO calibrations VALUES (?,?,?,?,?)',
                       ('calibration-1','package','new-station',json.dumps(self.reference),'time-3'))
            db.execute('INSERT INTO service_state VALUES (?,?)',('production_zone',json.dumps(self.zone)))
            for i in range(3):
                path = self.root/f'raw-{i}.png'
                path.write_bytes(b'fixture image content '+bytes([i]))
                db.execute('INSERT INTO frame_assets VALUES (?,?,?,?,?,?,?,?,?,?,?)', (
                    str(i),'reference-1','raw',path.name,install.digest(path),1,1,path.stat().st_size,
                    'time-2','top','PENDING'))

    def tearDown(self):
        self.temp.cleanup()

    def mutate(self, sql, parameters=()):
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute(sql, parameters)

    def test_current_reference_and_zone_read_without_db_changes(self):
        before = install.digest(self.database)
        reference = install.read_confirmed_reference(self.root, self.expected)
        self.assertEqual(reference, self.reference)
        self.assertEqual(install.read_confirmed_zone(self.root, reference), self.zone)
        self.assertEqual(install.digest(self.database), before)

    def test_missing_human_confirmation_or_changed_station_rejected(self):
        with self.assertRaisesRegex(ValueError, 'CONFIRMED_CURRENT'):
            install.read_confirmed_reference(self.root, dict(self.expected, station_id='old-station'))
        self.mutate('UPDATE calibrations SET payload_json=?', (json.dumps(self.candidate),))
        with self.assertRaisesRegex(ValueError, 'CONFIRMED_CURRENT'):
            install.read_confirmed_reference(self.root, self.expected)

    def test_existing_product_inspection_not_first_setup(self):
        self.mutate('UPDATE inspections SET request_json=?', (json.dumps({'kind':'inspect'}),))
        with self.assertRaisesRegex(ValueError, 'ONLY_FINISHED_NEW'):
            install.read_confirmed_reference(self.root, self.expected)

    def test_corrupted_original_rejected(self):
        (self.root/'raw-1.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_HASH'):
            install.read_confirmed_reference(self.root, self.expected)

    def test_unconfirmed_or_old_reference_zone_rejected(self):
        for zone in (dict(self.zone, confirmed=False), dict(self.zone, calibration_sha='previous')):
            self.mutate('UPDATE service_state SET value=?', (json.dumps(zone),))
            with self.assertRaisesRegex(ValueError, 'CONFIRMED_ZONE'):
                install.read_confirmed_zone(self.root, self.reference)


if __name__ == '__main__':
    unittest.main()
