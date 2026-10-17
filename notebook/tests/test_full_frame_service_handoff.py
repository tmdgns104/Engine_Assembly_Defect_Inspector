"""Actual Service admission/worker queue; no Worker or camera is launched."""
import queue,threading,time,unittest
from types import SimpleNamespace as NS
from apps.edge_service.inspection import InspectionService
from notebook.tests.test_full_frame_request import RuntimeFixture as _Fixture
from src.runtime.inspection_start import FULL_FRAME


class ServiceHandoff(unittest.TestCase):
    def test_new_policy_and_track_survive_real_service_submission(self):
        f=_Fixture();f.setUp()
        self.addCleanup(f.doCleanups)
        s=f.service
        s.production_enabled=True;s.production_owner=f.r;s.switching=False
        s.mock=NS(state='IDLE',job=None)
        s.station=dict(cell_id='fixture',inspection_timeout_seconds=8,
            max_frame_age_seconds=.35,frame_spacing_seconds=.15,
            fresh_frame=dict(boundary_epsilon_ms=0,max_trigger_to_frame_ms=3000,inspection_window_ms=3000))
        s.preview={'freshness':{'camera_epoch':'e'}}
        s.preview_received=time.monotonic()
        s.process=NS(is_alive=lambda:True)
        s.commands=queue.Queue(maxsize=1);s.cancellation=threading.Event()
        s.submit=InspectionService.submit.__get__(s)
        f.observe(1,0);f.request();f.observe(2,.3);f.trigger()
        self.assertEqual(s.state,'BUSY')
        job=s.commands.get_nowait()
        binding=job['production_binding']
        self.assertEqual(binding['inspection_start_policy'],FULL_FRAME)
        self.assertEqual(binding['track_id'],f.r.arrival['track'])
        self.assertEqual(binding['trigger_frame_id'],'e:2')
        self.assertEqual(binding['inspection_id'],f.r.bridge.inspection_id)
        self.assertEqual(job['trigger']['capture_epoch'],'e')
        self.assertEqual(job['experiment_policy']['inspection_motion_mode'],'STATIONARY')
        self.assertEqual(f.j.detail(binding['inspection_id'])['state'],'ACCEPTED')
        self.assertEqual(f.g.result.call_count,0)
