"""Assembly native/GIL stalls must not strand the control interpreter."""
import ctypes
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest


def holding_gil_loader():
    # PyDLL deliberately retains the interpreter lock for a native call.
    if os.name == 'nt':
        ctypes.PyDLL('kernel32').Sleep(550)
    else:
        ctypes.PyDLL(None).usleep(550_000)
    return (None, None, None)


def broken_loader():
    raise RuntimeError('MODEL_LOAD_FAILED_FIXTURE')


class AssemblyProcessTests(unittest.TestCase):
    def make(self, loader=holding_gil_loader):
        from src.vision.assembly_process import ProcessAssemblyInspector
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        owner=ProcessAssemblyInspector(root,root/'assembly',loader=loader)
        self.addCleanup(owner.close)
        return owner

    def wait(self, predicate, seconds=12):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            value=predicate()
            if value:return value
            time.sleep(.01)
        self.fail('bounded worker wait expired')

    def test_native_gil_hold_does_not_block_parent_and_no_camera_owner(self):
        owner=self.make(); gaps=[];last=time.monotonic()
        while not owner.ready:
            self.assertIsNone(owner.status()['error'])
            time.sleep(.01);now=time.monotonic();gaps.append(now-last);last=now
            self.assertLess(len(gaps),1200)
        self.assertLess(max(gaps),.2)
        self.assertNotEqual(owner.status()['worker_pid'],os.getpid())
        self.assertEqual(owner.status()['execution_owner'],'ASSEMBLY_PROCESS_NO_CAMERA')
        self.assertEqual(owner.status()['mode'], 'REFERENCE_ANALYSIS_WITH_DURABLE_EVIDENCE')

    def test_load_failure_and_process_exit_are_not_ready(self):
        failed=self.make(broken_loader)
        self.wait(lambda:failed.status()['error'])
        self.assertFalse(failed.ready)
        owner=self.make();self.wait(lambda:owner.ready)
        owner.process.terminate();owner.process.join(3)
        self.assertFalse(owner.ready)
        self.assertIn('EXITED',owner.status()['error'])

    @unittest.skipUnless(os.name == 'posix', 'existing assembly fsync contract is Linux-only')
    def test_exact_identifier_is_durable_before_result_and_duplicate_is_rejected(self):
        owner=self.make();self.wait(lambda:owner.ready)
        identifier='a'*32
        row=dict(inspection_id=identifier,decision='REVIEW',request={},result={'assets':[],'observations':[]})
        owner.submit(row)
        with self.assertRaisesRegex(ValueError,'DUPLICATE|BUSY'):owner.submit(row)
        self.wait(lambda:owner.status()['outstanding']==0 or owner.status()['error'])
        self.assertIsNone(owner.status()['error'])
        result=owner.result(identifier)
        self.assertEqual(result['inspection_id'],identifier)
        self.assertIn(result['state'],('ERROR','NOT_RUN'))
        self.assertIsNone(owner.result('b'*32))
        self.assertEqual(owner.status()['outstanding'],0)
        owner.close()
        self.assertFalse(owner.ready)
        self.assertFalse(owner.process.is_alive())

    def test_forged_existing_file_is_not_an_acknowledged_result(self):
        owner=self.make();self.wait(lambda:owner.ready)
        target=owner.evidence_path('b'*32);target.parent.mkdir()
        target.write_text('{"inspection_id":"'+'b'*32+'","state":"COMPLETE"}')
        self.assertIsNone(owner.result('b'*32))


if __name__=='__main__':unittest.main()
