"""Fresh physical controls gate diagnostics; diagnostics never gate PLC outputs."""
import importlib.util
import json
from pathlib import Path
import sys
import threading
import time
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'jetson'))
from notebook.tests import test_stopped_diagnostic_capture as stopped_fixture
from notebook.tests.supervised_asgi_fixture import LocalAsgiClient
from apps.edge_service.inspection_api import create_app
from src.runtime.standalone_web import configure_line_web

PREFIX = '/api/v1/maintenance/run-capture'


class RunControlTests(unittest.TestCase):
    current = stopped_fixture.StoppedCaptureTests.current
    start_capture = stopped_fixture.StoppedCaptureTests.start_capture
    stop_capture = stopped_fixture.StoppedCaptureTests.stop_capture

    def setUp(self):
        stopped_fixture.StoppedCaptureTests.setUp(self)
        self.signals = NS(started_at=NS(value=0.), stop_code=NS(value=0), flush_until=NS(value=0.))
        self.signals.reset = lambda: None
        self.service.run_capture_signals = self.signals
        self.service.diagnostic_capture.arm_run = Mock(side_effect=self.arm_run)
        self.runtime.cycle_issue = None
        if importlib.util.find_spec('src.runtime.run_capture'):
            from src.runtime.run_capture import RunCaptureControl
            self.control = RunCaptureControl(self.runtime)

    def arm_run(self, body, context, signals):
        self.capture.value = dict(state='ARMED',clip_id=body['clip_id'],mode='RUN_DIAGNOSTIC')
        return self.capture.value

    def test_new_route_requires_token_same_origin_and_does_not_open_old_routes(self):
        app=create_app(self.service,{},own_service=False)
        configure_line_web(app,self.runtime,{})
        headers={'Host':'127.0.0.1:18771','Origin':'http://127.0.0.1:18771','Content-Type':'application/json'}
        with LocalAsgiClient(app) as client:
            token=json.loads(client.get('/api/v1/session').text)['token']
            self.assertEqual(client.post(PREFIX+'/arm',json={'clip_id':'one'},headers=headers).status_code,403)
            headers['x-inspection-token']=token
            self.assertEqual(client.post(PREFIX+'/arm',json={'clip_id':'one'},headers=dict(headers,Origin='http://other')).status_code,403)
            self.assertEqual(client.post('/api/v1/runtime/auto/start',json={},headers=headers).status_code,403)
            self.assertEqual(client.post('/api/v1/diagnostics/capture/start',json={'clip_id':'one'},headers=headers).status_code,403)
            self.assertEqual(client.post(PREFIX+'/arm',json={'clip_id':'one'},headers=headers).status_code,200)

    def test_start_requires_stopped_idle_arm_then_new_run_and_worker_ack(self):
        self.snapshot['controls']['Mc_Run']=True
        with self.assertRaises(ValueError): self.control.arm({'clip_id':'one'})
        self.snapshot['controls']['Mc_Run']=False
        self.control.arm({'clip_id':'one'})
        self.assertEqual(self.signals.started_at.value,0)
        # Actual OPENER_CYCLIC run snapshot: Stop_PB stays True when released.
        # Mc_Run distinguishes the running line from the stopped arm condition.
        self.snapshot['controls'].update(Mc_Run=True,Stop_PB=True)
        self.control.poll(time.monotonic())
        self.assertGreater(self.signals.started_at.value,0)
        self.assertIsNone(self.runtime.handshake.token)
        self.assertEqual(self.signals.flush_until.value,0)
        with self.assertRaises(ValueError): self.control.arm({'clip_id':'two'})

    def test_early_start_without_worker_ack_interrupts_only_capture(self):
        self.control.arm({'clip_id':'one'}); self.capture.value['state']='STARTING'
        self.snapshot['controls'].update(Mc_Run=True,Stop_PB=True)
        self.control.poll(time.monotonic())
        self.assertEqual(self.signals.started_at.value,0)
        self.assertGreater(self.signals.stop_code.value,0)
        self.assertIsNone(self.runtime.error)

    def test_recording_accepts_real_run_controls_and_request_then_stops_on_mc_run_low(self):
        self.control.arm({'clip_id':'one'})
        self.snapshot['controls'].update(Mc_Run=True,Stop_PB=True)
        self.control.poll(time.monotonic())
        self.assertGreater(self.signals.started_at.value,0)
        self.capture.value['state']='RECORDING'
        self.snapshot['controls']['Inspection_Request']=True
        self.control.poll(time.monotonic())
        self.assertEqual(self.signals.stop_code.value,0)
        self.assertIsNone(self.control.status()['interruption'])
        self.assertEqual(self.signals.flush_until.value,0)
        self.snapshot['controls'].update(Mc_Run=False,Inspection_Request=False)
        self.control.poll(time.monotonic())
        self.assertGreater(self.signals.stop_code.value,0)
        self.assertEqual(self.control.status()['state'],'WAIT_SAFE_FLUSH')
        self.assertIsNone(self.runtime.error)

    def test_open_stop_or_estop_chain_does_not_start_diagnostics(self):
        for failed_control in ('Stop_PB','EStop_OK'):
            with self.subTest(failed_control=failed_control):
                self.setUp()
                self.control.arm({'clip_id':'one'})
                self.snapshot['controls']['Mc_Run']=True
                self.snapshot['controls'][failed_control]=False
                self.control.poll(time.monotonic())
                self.assertEqual(self.signals.started_at.value,0)
                self.assertGreater(self.signals.stop_code.value,0)
                self.assertIsNotNone(self.control.status()['interruption'])
                self.assertEqual(self.signals.flush_until.value,0)
                self.assertIsNone(self.runtime.error)

    def test_recording_stops_on_owner_or_connection_change_without_plc_mutation(self):
        self.control.arm({'clip_id':'one'})
        self.runtime.epoch='other'
        self.control.poll(time.monotonic())
        self.assertGreater(self.signals.stop_code.value,0)
        self.assertIn('OWNER',self.control.status()['interruption'])
        self.assertIsNone(self.runtime.error)

    def test_new_product_tracking_session_keeps_same_device_recording(self):
        self.control.arm({'clip_id':'one'})
        self.snapshot['controls']['Mc_Run']=True
        self.control.poll(time.monotonic())
        self.capture.value['state']='RECORDING'
        # StandaloneRuntime._start_automatic_observation_window deliberately
        # renews this tracking ID for each accepted PLC cycle, not the Worker.
        self.runtime.session_id='next-product-observation-window'
        self.snapshot['controls']['Inspection_Request']=True
        self.control.poll(time.monotonic())
        self.assertEqual(self.signals.stop_code.value,0)
        self.assertIsNone(self.control.status()['interruption'])
        self.assertEqual(self.signals.flush_until.value,0)
        self.assertIsNone(self.runtime.error)

    def test_later_tracking_cycle_does_not_relabel_completed_window_as_owner_failure(self):
        self.control.arm({'clip_id':'one'})
        self.snapshot['controls']['Mc_Run']=True
        self.control.poll(time.monotonic())
        self.capture.value['state']='WAIT_SAFE_FLUSH'
        self.control.poll(time.monotonic())
        self.runtime.session_id='cycle-after-recording-deadline'
        self.snapshot['controls']['Inspection_Request']=True
        self.control.poll(time.monotonic())
        self.assertIsNone(self.control.status()['interruption'])
        self.assertGreater(self.signals.stop_code.value,0)
        self.assertEqual(self.signals.flush_until.value,0)

    def test_actual_service_camera_plc_owner_changes_still_interrupt(self):
        for changed in ('session','generation','epoch','boot','connection','signals'):
            with self.subTest(changed=changed):
                self.setUp()
                self.control.arm({'clip_id':'one'})
                self.snapshot['controls']['Mc_Run']=True
                self.control.poll(time.monotonic())
                self.capture.value['state']='RECORDING'
                if changed in ('session','generation'):
                    setattr(self.service,changed,'replacement')
                elif changed=='epoch':self.runtime.epoch='replacement'
                elif changed=='signals':self.service.run_capture_signals=object()
                else:self.snapshot[changed]='replacement'
                self.control.poll(time.monotonic())
                self.assertGreater(self.signals.stop_code.value,0)
                self.assertEqual(self.control.status()['interruption'],'RUN_CAPTURE_OWNER_CHANGED')
                self.assertEqual(self.signals.flush_until.value,0)
                self.assertIsNone(self.runtime.error)

    def test_flush_lease_requires_stop_low_zero_outputs_and_no_pending_storage(self):
        self.control.arm({'clip_id':'one'}); self.control.stop()
        self.capture.value['state']='WAIT_SAFE_FLUSH'
        self.camera['storage_pending']=True
        self.control.poll(time.monotonic())
        self.assertEqual(self.signals.flush_until.value,0)
        self.camera['storage_pending']=False
        self.control.poll(time.monotonic())
        self.assertGreater(self.signals.flush_until.value,time.monotonic())
        self.snapshot['controls']['Mc_Run']=True
        self.control.poll(time.monotonic())
        self.assertEqual(self.signals.flush_until.value,0)

    def test_faulted_inspection_can_save_diagnostic_after_safe_stop(self):
        self.control.arm({'clip_id':'one'}); self.control.stop()
        self.capture.value['state']='WAIT_SAFE_FLUSH'
        self.runtime.error='EXISTING_INSPECTION_ERROR'
        self.control.poll(time.monotonic())
        self.assertGreater(self.signals.flush_until.value,time.monotonic())
        self.assertEqual(self.runtime.error,'EXISTING_INSPECTION_ERROR')

    def test_stale_or_failed_snapshot_drops_flush_permission_without_raising(self):
        self.control.arm({'clip_id':'one'}); self.control.stop()
        self.capture.value['state']='WAIT_SAFE_FLUSH'
        self.control.poll(time.monotonic())
        self.runtime.gateway.read_snapshot=Mock(side_effect=OSError('IPC read failed'))
        self.control.poll(time.monotonic())
        self.assertEqual(self.signals.flush_until.value,0)
        self.assertIsNone(self.runtime.error)

    def test_unknown_truth_and_oversized_request_are_rejected(self):
        for update in ({'expected':'PASS'},{'duration_seconds':21},{'max_frames':241},{'max_bytes':769*1024**2}):
            with self.subTest(update=update),self.assertRaises(ValueError):
                self.control.arm(dict(clip_id='one',**update))

    def test_stop_only_capture_cannot_replace_armed_or_unsaved_run(self):
        self.control.arm({'clip_id':'one'})
        for state in ('ARMED','WAIT_SAFE_FLUSH'):
            self.capture.value['state']=state
            with self.subTest(state=state),self.assertRaises(ValueError):
                self.subject.start({'clip_id':'replacement'})

    def test_trace_failure_cannot_be_reported_as_saved_run(self):
        self.control.arm({'clip_id':'one'});self.control.stop()
        self.capture.value.update(state='ERROR',worker_state='SAVED')
        self.capture.trace_error='RUNTIME_TRACE_WRITE: RUN_TRACE_LIMIT'
        self.control.poll(time.monotonic())
        self.assertEqual(self.control.status()['state'],'ERROR')

    def test_repeated_stop_preserves_completed_receipt_status(self):
        self.control.arm({'clip_id':'one'});self.control.stop()
        self.capture.value.update(state='SAVED',worker_state='SAVED')
        self.control.poll(time.monotonic())
        self.assertEqual(self.control.status()['state'],'SAVED')
        self.assertEqual(self.control.stop()['state'],'SAVED')


if __name__=='__main__':unittest.main()
