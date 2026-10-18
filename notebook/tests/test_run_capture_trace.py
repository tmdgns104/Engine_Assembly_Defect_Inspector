"""Trace/file failures remain diagnostic and cannot replace unsaved raw clips."""
import json
from pathlib import Path
import queue
import sys
import tempfile
import time
from types import SimpleNamespace as NS
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'jetson'))
from apps.edge_service.diagnostic_controller import BufferedTrace, DiagnosticController


class RunTraceTests(unittest.TestCase):
    def test_trace_does_no_acquisition_io_and_preserves_explicit_overflow(self):
        with tempfile.TemporaryDirectory() as root:
            trace=BufferedTrace(root)
            trace.write('{"frame_id":"one"}\n');trace.flush()
            self.assertFalse(list(Path(root).iterdir()))
            with self.assertRaises(OSError):trace.write('x'*(5*1024*1024))
            signal=NS(flush_until=NS(value=time.monotonic()+5))
            trace.permit_flush(signal);trace.thread.join(3)
            self.assertEqual((Path(root)/'runtime.jsonl').read_text(encoding='utf-8'),'{"frame_id":"one"}\n')
            receipt=json.loads((Path(root)/'trace_receipt.json').read_text(encoding='utf-8'))
            self.assertEqual(receipt['state'],'ERROR')
            self.assertEqual(receipt['records'],1)

    def test_legacy_start_cannot_discard_raw_when_trace_overrides_public_state(self):
        with tempfile.TemporaryDirectory() as root:
            service=NS(active=None,state='IDLE',status=lambda:{'camera_ready':True},commands=queue.Queue(1))
            control=DiagnosticController(service);control.root=Path(root)
            trace=BufferedTrace(root);control.trace=trace
            control.value={'state':'ERROR','worker_state':'WAIT_SAFE_FLUSH','mode':'RUN_DIAGNOSTIC'}
            try:
                with self.assertRaises(ValueError):control.start({'clip_id':'overwrite'}, {})
                self.assertTrue(service.commands.empty())
                self.assertFalse(trace.abandoned.is_set())
            finally:
                control.close();trace.close()

    def test_success_waits_for_worker_receipt_and_trace_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            control=DiagnosticController(NS());control.clip_id='one'
            control.trace=BufferedTrace(root)
            control.update({'state':'SAVED','mode':'RUN_DIAGNOSTIC','clip_id':'one'})
            self.assertEqual(control.value['state'],'SAVING')
            self.assertEqual(control.value['worker_state'],'SAVED')
            signals=NS(flush_until=NS(value=time.monotonic()+5))
            control.trace.permit_flush(signals);control.trace.thread.join(3)
            control.update({'state':'SAVED','mode':'RUN_DIAGNOSTIC','clip_id':'one'})
            self.assertEqual(control.value['state'],'SAVED')


if __name__=='__main__':unittest.main()
