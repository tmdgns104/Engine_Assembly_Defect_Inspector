import copy
from datetime import datetime, timezone
from pathlib import Path
import queue
import sqlite3
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np

from src.contracts import CameraFrame, CameraError, DetectorError
from src.vision.inspection_worker import worker_main
from src.vision.detector_factory import create_detector
from src.recipe.package import load_package
from src.journal.sqlite import Journal
from apps.edge_service.inspection import InspectionService
from test_trt_schema import executable_fixture
from test_trt_detector import Executor
from test_fresh_frame import trigger, frame as metadata


def run_worker(root, mode='fatal', cleanup_error=False):
    executable_fixture(root)
    clock=SimpleNamespace(now=10.01)
    stopping,cancellation=threading.Event(),threading.Event()
    trace=[]
    executor=Executor()
    if mode!='normal':executor.error=RuntimeError('PRIMARY_EXECUTION_FAILURE')
    def close_executor():
        trace.append('detector_close');executor.closed+=1
        if cleanup_error:raise RuntimeError('DETECTOR_CLEANUP_FAILURE')
    executor.close=close_executor
    class Camera:
        pipeline_text='SYNTHETIC_NO_DEVICE'
        frame_info={}
        def __init__(self,config):
            if mode=='camera_init_failure':raise CameraError('CAMERA_INIT_FAILURE')
            self.sequence=0;trace.append('camera_open')
        def capture(self):
            self.sequence+=1
            if self.sequence>12:raise CameraError('SYNTHETIC_EXHAUSTED')
            clock.now=10+self.sequence*.01
            self.frame_info=metadata(self.sequence,source=clock.now-.002,received=clock.now-.001)
            return CameraFrame(np.zeros((8,8,3),np.uint8),self.frame_info['frame_id'],datetime.now(timezone.utc),8,8,'synthetic')
        def close(self):
            trace.append('camera_close')
            if cleanup_error:raise CameraError('CAMERA_CLEANUP_FAILURE')
    class Results(queue.Queue):
        def put(self,value,*args,**kwargs):
            super().put(value,*args,**kwargs)
            if value['type']=='fault' or (mode=='normal' and value['type']=='result'):stopping.set()
    commands,results,previews=queue.Queue(),Results(),queue.Queue(1)
    for number in (1,2):
        commands.put({'inspection_id':'I'+str(number),'trigger':trigger().to_dict(),
                      'accepted_monotonic':10.,'deadline':12.,'request':{'kind':'inspect','view_assessment':{}},'calibration':None})
    station={'camera_device':'synthetic','frame_spacing_seconds':0,'max_frame_age_seconds':.35,
             'fresh_frame':{'boundary_epsilon_ms':0,'max_trigger_to_frame_ms':2000,'inspection_window_ms':2000},
             'quality':{'min_blur_variance':0,'min_mean_brightness':0,'max_mean_brightness':255}}
    def factory(package):
        if mode=='detector_init_failure':raise DetectorError('DETECTOR_INIT_FAILURE')
        return create_detector(package,executor_factory=lambda _:executor)
    with patch('src.camera.gstreamer_camera.GStreamerCamera',Camera), \
         patch('src.vision.detector_factory.create_detector',side_effect=factory), \
         patch('src.vision.inspection_worker.time',SimpleNamespace(monotonic=lambda:clock.now)):
        worker_main(root,station,'generation',commands,results,previews,stopping,cancellation,SimpleNamespace(value=10.))
    messages=[]
    while not results.empty():messages.append(results.get_nowait())
    return messages,trace,executor,commands.qsize()


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)

    def test_fatal_error_then_fault_no_next_job(self):
        messages,trace,executor,pending=run_worker(self.root/'package')
        self.assertEqual([m['type'] for m in messages],['ready','result','fault'])
        self.assertEqual(messages[1]['result']['decision'],'ERROR')
        self.assertIn('PRIMARY_EXECUTION_FAILURE',messages[2]['error'])
        self.assertEqual(messages[1]['images'],[])
        self.assertEqual((executor.calls,pending),(1,1))
        self.assertEqual(trace,['camera_open','camera_close','detector_close'])

    def test_normal_cleanup_and_full_recipe_evidence(self):
        messages,trace,executor,_=run_worker(self.root/'package','normal')
        self.assertEqual(messages[-1]['result']['decision'],'REVIEW')
        self.assertEqual(len(messages[-1]['images']),4)
        self.assertEqual(executor.calls,3)
        self.assertEqual(trace,['camera_open','camera_close','detector_close'])
        self.assertEqual(executor.closed,1)

    def test_early_detector_init_failure_safe(self):
        messages,trace,executor,_=run_worker(self.root/'package','detector_init_failure')
        self.assertEqual([m['type'] for m in messages],['fault'])
        self.assertEqual(trace,[])

    def test_camera_init_failure_closes_constructed_detector(self):
        messages,trace,executor,_=run_worker(self.root/'package','camera_init_failure')
        self.assertEqual(messages[-1]['type'],'fault')
        self.assertEqual(trace,['detector_close'])

    def test_cleanup_failures_do_not_mask_primary(self):
        messages,trace,executor,_=run_worker(self.root/'package',cleanup_error=True)
        self.assertEqual([m['type'] for m in messages],['ready','result','fault'])
        self.assertIn('PRIMARY_EXECUTION_FAILURE',messages[-1]['error'])
        self.assertEqual(trace,['camera_open','camera_close','detector_close'])

    def test_cleanup_failure_after_normal_result_is_fault(self):
        messages,trace,executor,_=run_worker(self.root/'package','normal',True)
        self.assertEqual([m['type'] for m in messages],['ready','result','fault'])
        self.assertIn('CLEANUP',messages[-1]['error'])
        self.assertEqual(executor.closed,1)

    def service_case(self,mode):
        messages,_,_,_=run_worker(self.root/'package')
        terminal=next(m for m in messages if m['type']=='result')
        fault=next(m for m in messages if m['type']=='fault')
        journal=Journal(self.root/'data',min_free_bytes=0);self.addCleanup(journal.close)
        package=load_package(self.root/'package')
        request={'cell_id':'test-cell','plc_session_id':1,'cycle_id':101,'request_id':1,'attempt':1}
        context=trigger().to_dict()
        identifier,_=journal.admit(request,package.snapshot(),trigger=context)
        service=object.__new__(InspectionService)
        service.station={'station_id':'synthetic','fresh_frame':True}
        service.journal=journal;service.session=1;service.generation='generation'
        service.lock=threading.RLock();service.cancellation=threading.Event()
        service.active={'inspection_id':identifier,'request':request,'trigger':context,'deadline':12.,'accepted_monotonic':10.}
        service.state='INSPECTING';service.error=None;service.preview=None
        service.backend={'backend':'synthetic'};service.previews=queue.Queue();service.results=queue.Queue()
        service.process=SimpleNamespace(is_alive=lambda:True)
        service.heartbeat=SimpleNamespace(value=10.1)
        service.mock=SimpleNamespace(state='IDLE',tick=lambda:None)
        class OneTick:
            count=0
            def wait(self,_):self.count+=1;return self.count>1
        service.closed=OneTick()
        terminal=copy.deepcopy(terminal);terminal['inspection_id']=identifier
        if mode=='cancel':service.cancel(identifier)
        if mode=='deadline':service.active['deadline']=10.05
        if mode=='session':service.session=2
        if mode=='context':terminal['result']['fresh_frame']['trigger']['trigger_id']='wrong'
        service.results.put(terminal);service.results.put(fault);service.results.put(copy.deepcopy(terminal))
        observed=[]
        real_fault=service._fault
        def observe_fault(reason):
            reader=sqlite3.connect(journal.root/'journal.sqlite3')
            try:observed.append((service.active,reader.execute('SELECT state,decision FROM inspections').fetchone()))
            finally:reader.close()
            real_fault(reason)
        with patch.object(service,'_fault',side_effect=observe_fault), \
             patch('apps.edge_service.inspection.time',SimpleNamespace(monotonic=lambda:10.1)):
            service._monitor()
        self.assertEqual(service.state,'RECOVERY')
        self.assertIsNone(service.active)
        expected='COMPLETE' if mode=='valid' else 'CANCELLED'
        self.assertEqual(observed,[(None,(expected,'ERROR'))])
        self.assertEqual(journal.db.execute("SELECT COUNT(*) FROM events WHERE event_type IN ('INSPECTION_COMPLETED','INSPECTION_CANCELLED')").fetchone()[0],1)
        self.assertEqual(journal.db.execute("SELECT COUNT(*) FROM events WHERE event_type='LATE_RESULT_QUARANTINED'").fetchone()[0],1)
        self.assertEqual(journal.db.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_service_error_commit_before_fault_and_one_terminal(self):self.service_case('valid')
    def test_cancel_has_precedence_no_duplicate_terminal(self):self.service_case('cancel')
    def test_deadline_has_precedence_no_duplicate_terminal(self):self.service_case('deadline')
    def test_old_session_has_precedence_no_duplicate_terminal(self):self.service_case('session')
    def test_context_mismatch_has_precedence_no_duplicate_terminal(self):self.service_case('context')
