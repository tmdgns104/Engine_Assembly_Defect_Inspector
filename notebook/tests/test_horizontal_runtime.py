"""Exercise actual runtime observation gate, without starting workers or devices."""
import sys,unittest,time,copy
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'jetson'))
from src.runtime.production import ProductionRuntime
from src.observation.area_occupancy import ClearWindow
from src.observation.contracts import ProviderStatus
from test_horizontal_conveyor import model,scene,meta

class RuntimeObservationTests(unittest.TestCase):
 def make_runtime(self):
  r=ProductionRuntime.__new__(ProductionRuntime)
  m=model().evaluate(scene())
  r.area_config_version=m['config_version']
  r.area_reference_required=True
  r.area_approval=dict(config_version=m['config_version'],camera_epoch='camera',generation='worker')
  r.area_window=ClearWindow()
  return r,m
 def feed(self,r,m,n,status=ProviderStatus.NO_FOREGROUND,change=None):
  packet=meta(n);measurement=dict(m,**packet)
  if change:measurement.update(change)
  packet['area_occupancy']=measurement
  with patch('src.runtime.production.time.monotonic',return_value=packet['monotonic_s']):
   r._observe_area(packet,NS(status=status))
  return r.area_observation
 def test_current_frame_identity_required_even_with_matching_surface(self):
  for change in [dict(frame_id='other'),dict(sequence=100),dict(camera_epoch='other'),
                 dict(generation='other'),dict(config_version='other'),dict(monotonic_s=0)]:
   r,m=self.make_runtime()
   for n in range(7):v=self.feed(r,m,n)
   self.assertEqual(v['state'],'CLEAR')
   self.assertEqual(self.feed(r,m,7,change=change)['state'],'UNKNOWN')
 def test_detector_absence_alone_cannot_clear_unknown_surface(self):
  r,m=self.make_runtime()
  m.update(classification='UNKNOWN',reference_valid=False)
  for n in range(10):v=self.feed(r,m,n)
  self.assertNotEqual(v['state'],'CLEAR')
 def test_product_observation_contradicts_an_empty_surface(self):
  r,m=self.make_runtime()
  for n in range(10):v=self.feed(r,m,n,ProviderStatus.PRODUCT_OBSERVED)
  self.assertEqual(v['state'],'UNKNOWN')
 def test_changed_worker_requires_new_approval_not_previous_clear(self):
  r,m=self.make_runtime()
  r.area_approval['generation']='previous-worker'
  for n in range(10):v=self.feed(r,m,n)
  self.assertEqual(v['state'],'UNKNOWN')
 def test_in_flight_request_blocks_clearing_existing_track(self):
  r,_=self.make_runtime()
  r.coordinator=NS(active_cycle=NS(cycle_id='cycle-A'),_tracker=NS(_track_id='track-A'))
  r.operating=True;r.service=NS(error=None,state='IDLE',active=None)
  r.handshake=NS(state='INSPECTING',token='request-A')
  r.area_observation=dict(state='CLEAR')
  result=r._area_clearance(meta(10),NS(status=ProviderStatus.NO_FOREGROUND))
  self.assertIsNone(result)
  self.assertEqual(r.coordinator._tracker._track_id,'track-A')

if __name__=='__main__':unittest.main(verbosity=2)
