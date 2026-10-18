"""Maintenance recording cannot start the line or change an inspection."""
import copy
import threading
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

from apps.edge_service.inspection_api import create_app
from src.runtime.standalone_web import configure_line_web
from src.runtime.stopped_capture import StoppedCapture, PREFIX
from notebook.tests.supervised_asgi_fixture import LocalAsgiClient


class StoppedCaptureTests(unittest.TestCase):
    def setUp(self):
        self.snapshot=dict(connected=True,fresh=True,bool_valid=True,phase='SYNC_LOW',raw100='00000000',
            boot=1,connection=2,request_id=3,
            controls=dict(Inspection_Request=False,Mc_Run=False,EStop_OK=True,Stop_PB=True))
        self.camera=dict(state='IDLE',camera_ready=True,worker_alive=True,ready=True,storage_pending=False)
        self.capture=NS(value={'state':'IDLE'},start=Mock(side_effect=self.start_capture),stop=Mock(side_effect=self.stop_capture),record=Mock())
        self.service=NS(lock=threading.RLock(),diagnostic_capture=self.capture,active=None,generation='camera1',
            session='service1',health=lambda:dict(self.camera))
        self.runtime=NS(lock=threading.RLock(),service=self.service,line_profile={},closing=False,error=None,
            session_id='runtime1',epoch='epoch1',final_pending=None,audit_pending=None,
            handshake=NS(token=None),gateway=NS(contract_version='OPENER_CYCLIC',read_snapshot=self.current),
            assembly=NS(status=lambda:dict(ready=True,pending=0,outstanding=0,active_identifier=None)))
        self.subject=StoppedCapture(self.runtime)

    def current(self,now):
        return dict(copy.deepcopy(self.snapshot),generated=time.monotonic(),received=time.monotonic())

    def start_capture(self,body,context):
        self.capture.value=dict(state='STARTING',clip_id=body['clip_id'])
        return self.capture.value

    def stop_capture(self):
        self.capture.value=dict(self.capture.value,state='SAVING')
        return self.capture.value

    def test_stopped_capture_is_bounded_and_not_an_inspection(self):
        self.subject.start({'clip_id':'raw_negative'})
        body,context=self.capture.start.call_args.args
        self.assertEqual(body['duration_seconds'],5)
        self.assertLessEqual(body['max_bytes'],128*1024*1024)
        self.assertTrue(context['maintenance_diagnostic_only'])
        self.assertIsNone(self.runtime.handshake.token)
        with self.assertRaises(ValueError): self.subject.start({'clip_id':'duplicate'})

    def test_running_request_estop_invalid_output_or_stale_control_rejected(self):
        for group,key,value in [('controls','Mc_Run',True),('controls','Inspection_Request',True),
                ('controls','EStop_OK',False),('controls','Stop_PB',False),
                (None,'connected',False),(None,'raw100','01000000'),(None,'phase','REQUEST_RECEIVED')]:
            old=copy.deepcopy(self.snapshot)
            (self.snapshot[group] if group else self.snapshot)[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): self.subject.start({'clip_id':'x'})
            self.snapshot=old
        self.runtime.gateway.read_snapshot=lambda now:None
        with self.assertRaises(ValueError):self.subject.start({'clip_id':'x'})
        self.capture.start.assert_not_called()

    def test_busy_camera_storage_or_owned_request_rejected(self):
        for key,value in [('state','RECOVERY'),('camera_ready',False),('worker_alive',False),('storage_pending',True)]:
            old=dict(self.camera);self.camera[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.subject.start({'clip_id':'x'})
            self.camera=old
        self.runtime.handshake.token='request'
        with self.assertRaises(ValueError):self.subject.start({'clip_id':'x'})

    def test_limits_and_unknown_inputs_are_rejected(self):
        for key,value in [('duration_seconds',6),('duration_seconds',float('nan')),('max_frames',101),
                ('max_bytes',129*1024*1024),('expected_result','PASS')]:
            with self.subTest(key=key),self.assertRaises(ValueError):self.subject.start({'clip_id':'x',key:value})

    def test_start_signal_during_recording_stops_only_diagnostics_once(self):
        self.subject.start({'clip_id':'x'})
        self.snapshot['controls']['Mc_Run']=True
        self.subject.poll(time.monotonic());self.subject.poll(time.monotonic())
        self.capture.stop.assert_called_once()
        self.assertIsNotNone(self.subject.status()['interruption'])
        self.assertIsNone(self.runtime.error)
        self.assertIsNone(self.runtime.handshake.token)
        self.capture.record.assert_called_once()

    def test_camera_epoch_change_invalidates_recording(self):
        self.subject.start({'clip_id':'x'});self.runtime.epoch='new'
        self.subject.poll(time.monotonic())
        self.capture.stop.assert_called_once()

    def test_diagnostic_faults_cannot_raise_into_plc_loop(self):
        self.subject.start({'clip_id':'x'})
        self.runtime.gateway.read_snapshot=Mock(side_effect=RuntimeError('snapshot unavailable'))
        self.capture.record.side_effect=OSError('trace full')
        self.capture.stop.side_effect=RuntimeError('queue full')
        self.subject.poll(time.monotonic())
        status=self.subject.status()
        self.assertIn('snapshot unavailable',status['interruption'])
        self.assertIn('trace full',status['trace_error'])
        self.assertIn('queue full',status['stop_error'])
        self.assertIsNone(self.runtime.error)

    def test_web_requires_loopback_same_origin_and_real_session_token(self):
        app=create_app(self.service,{},own_service=False)
        configure_line_web(app,self.runtime,{})
        headers={'Host':'127.0.0.1:18771','Origin':'http://127.0.0.1:18771','Content-Type':'application/json'}
        with LocalAsgiClient(app) as client:
            token=__import__('json').loads(client.get('/api/v1/session').text)['token']
            path=PREFIX+'/start'
            self.assertEqual(client.post(path,json={'clip_id':'x'},headers=headers).status_code,403)
            headers['x-inspection-token']=token
            self.assertEqual(client.post(path,json={'clip_id':'x'},headers=dict(headers,Origin='http://other')).status_code,403)
            self.assertEqual(client.post('/api/v1/diagnostics/capture/start',json={'clip_id':'x'},headers=headers).status_code,403)
            self.assertEqual(client.post('/api/v1/runtime/auto/start',json={},headers=headers).status_code,403)
            self.assertEqual(client.post(path,json={'clip_id':'x'},headers=headers).status_code,200)
        self.capture.start.assert_called_once()

if __name__=='__main__':unittest.main()
