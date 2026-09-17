"""Candidate-origin unittest runner; native frameworks and non-test DB writes denied."""
import importlib.abc
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
ORIGINAL = Path('D:/OneDevice_Team_project')
CANDIDATE = OUT/'candidate_runtime'
SCRATCH = OUT/'scratch'
SCRATCH.mkdir(exist_ok=True)
os.environ.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                  PYTHONPATH=str(CANDIDATE), TEMP=str(SCRATCH), TMP=str(SCRATCH))
tempfile.tempdir = str(SCRATCH)
sys.path[:0] = [str(CANDIDATE), str(OUT/'tests'), str(ORIGINAL/'runs/jetson_p0_003'),
               str(ROOT/'tests'), str(ROOT)]


class ForbiddenFramework(importlib.abc.MetaPathFinder):
    attempted = []

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('torch', 'ultralytics', 'tensorrt', 'onnx', 'onnxruntime', 'gi'):
            self.attempted.append(fullname)
            raise AssertionError('Native framework/device import prohibited: '+fullname)


sys.meta_path.insert(0, ForbiddenFramework())
db_connections = []


def audit(event, args):
    if event == 'sqlite3.connect':
        path = args[0]
        if path != ':memory:' and not Path(path).resolve().is_relative_to(SCRATCH):
            raise AssertionError('Non-test SQLite access prohibited: '+str(path))
        db_connections.append(str(path))


sys.addaudithook(audit)
EXISTING = ['test_latency', 'test_fresh_frame', 'test_fresh_frame_service', 'test_fresh_frame_worker',
            'test_contracts', 'test_product_package', 'test_calibration_reference', 'test_inspection_journal',
            'test_inspection_service', 'test_inspection_api', 'test_collector_sync', 'test_mock_cell',
            'test_mock_service', 'test_jetson_bench', 'test_jetson_bench_prepare']


class EvidenceResult(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        self.current = {'id': test.id(), 'result': 'RUNNING'}
        self.rows.append(self.current)

    def addSuccess(self, test):
        super().addSuccess(test)
        self.current['result'] = 'PASS'

    def addError(self, test, err):
        super().addError(test, err)
        self.current.update(result='ERROR', reason=self._exc_info_to_string(err, test))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.current.update(result='FAIL', reason=self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.current.update(result='SKIP', reason=reason)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err:
            self.current.update(result='FAIL', reason=self._exc_info_to_string(err, subtest))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rows = []


if __name__ == '__main__':
    label = sys.argv[1]
    names = EXISTING if label.startswith('existing_114') else (
        ['test_backend_contract'] if label == 'backend_28' else sys.argv[2:])
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    # Only the protected package fixture is read from the original workspace.
    if 'test_backend_contract' in sys.modules:
        sys.modules['test_backend_contract'].ROOT = ORIGINAL
    if 'test_jetson_bench_prepare' in sys.modules:
        sys.modules['test_jetson_bench_prepare'].ROOT = ORIGINAL
    os.chdir(CANDIDATE)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=EvidenceResult).run(suite)
    origins = {n: str(Path(m.__file__).resolve()) for n, m in list(sys.modules.items())
               if getattr(m, '__file__', None) and n.startswith(('src.', 'apps.edge_service.'))}
    inventory = json.loads((OUT/'parent_inventory.json').read_text())['files']
    for name, path in origins.items():
        relative = name.replace('.', '/')
        if relative+'.py' in inventory or relative+'/__init__.py' in inventory or name.startswith('src.vision.tensorrt_'):
            assert Path(path).is_relative_to(CANDIDATE), (name, path)
    record = {'status': 'PASS' if result.wasSuccessful() else 'FAIL', 'tests': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors), 'skips': len(result.skipped),
              'test_results': result.rows, 'origins': origins, 'candidate_source': str(CANDIDATE),
              'python': sys.executable, 'sys_path': sys.path,
              'forbidden_import_attempts': ForbiddenFramework.attempted,
              'temporary_sqlite_connections': len(db_connections), 'existing_db_writes': 0,
              'log': stream.getvalue()}
    path = OUT/('test_'+label+'.json')
    assert not path.exists(), 'Do not overwrite earlier test evidence; use a new label'
    path.write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: record[k] for k in ('status','tests','failures','errors','skips','forbidden_import_attempts')}))
    if not result.wasSuccessful():
        print(stream.getvalue())
    sys.exit(not result.wasSuccessful())
