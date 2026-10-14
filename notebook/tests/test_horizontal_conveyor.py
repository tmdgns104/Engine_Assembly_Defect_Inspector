"""Independent behavioural fixtures. Synthetic evidence is not field validation."""
import json,sys,tempfile,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'jetson'))
from src.observation.area_occupancy import load_area_occupancy,ClearWindow

def profile():
 return dict(mode='CONVEYOR_HORIZONTAL_TEXTURE_V1',schema_version=1,
  roi='FULL_WIDTH_CALIBRATED_BELT',shape=[720,1280,3],color='BGR_UINT8',
  belt_bounds=[[0,100,620],[1279,100,620]],
  clear_seconds=1.2,clear_minimum_frames=6,maximum_gap_seconds=.5,maximum_age_seconds=1.,
  calibration_id='synthetic-test-only',qualification='ISOLATED_ONLY',
  minimum_line_variance=25,
  feature_low=[25,85,5,0,-60],feature_high=[230,170,60,130,20],
  calibration_evidence={'human_empty_confirmed':True,'sample_count':18,
                        'manifest_sha256':'a'*64,'scope':'SYNTHETIC_TEST_ONLY'})

def scene(shift=0):
 image=np.full((720,1280,3),35,np.uint8)
 image[80:641]=220
 # Dense weave: shifted phase, same local appearance, no object.
 y,x=np.indices((521,1280))
 tile=np.where(((x+shift)//2+y//2)%2==0,90,150).astype(np.uint8)
 image[100:621]=tile[:,:,None]
 return image

def model(config=None):
 with tempfile.TemporaryDirectory() as d:
  p=Path(d)/'area.json';p.write_text(json.dumps(config or profile()),encoding='utf-8')
  return load_area_occupancy(p)

def meta(n,**changes):
 return dict(dict(frame_id=str(n),sequence=n,camera_epoch='camera',generation='worker',
  monotonic_s=10+n*.2,integrity={'valid':True}),**changes)

class HorizontalTests(unittest.TestCase):
 def test_new_horizontal_mode_observes_shifted_texture(self):
  m=model()
  for phase in [0,1,2,3,17]:
   self.assertEqual(m.evaluate(scene(phase))['classification'],'MATCH')
 def test_product_partial_and_exits_never_match(self):
  m=model()
  for start,end in [(0,80),(1200,1280),(500,740)]:
   image=scene();image[280:440,start:end]=(20,140,190)
   self.assertEqual(m.evaluate(image)['classification'],'OCCUPIED')
 def test_thin_remaining_parts_both_exits_and_middle(self):
  for x,y,w,h in [(0,350,30,1),(1250,350,30,1),(600,350,80,1),(3,350,1,30),(1275,350,1,30)]:
   for color in [(20,140,190),(0,0,0),(255,255,255),(180,180,180),(120,120,120)]:
    image=scene();image[y:y+h,x:x+w]=color
    with self.subTest(x=x,w=w,color=color):
     self.assertNotEqual(model().evaluate(image)['classification'],'MATCH')
 def test_hand_and_flat_unknown_obstacles_do_not_clear(self):
  for color in [(100,140,190),(120,120,120)]:
   im=scene();im[200:400,400:600]=color
   self.assertNotEqual(model().evaluate(im)['classification'],'MATCH')
 def test_rail_shift_occlusion_invalid_image(self):
  im=scene();im[80:100,200:400]=20
  for image in [im,np.roll(scene(),30,axis=0),None,scene()[:400],scene().astype(float)]:
   self.assertEqual(model().evaluate(image)['classification'],'UNKNOWN')
 def test_configuration_cannot_hide_exit_or_claim_field_qualification(self):
  changes=[{'belt_bounds':[[1,100,620],[1279,100,620]]},{'clear_seconds':0},
   {'qualification':'FIELD_VERIFIED'},{'schema_version':2},
   {'minimum_line_variance':0},{'minimum_line_variance':float('nan')},
   {'feature_low':[float('nan')]*5},{'calibration_evidence':{}},
   {'feature_high':[255]*5},{'belt_bounds':[[0,100,100],[1279,100,620]]}]
  for change in changes:
   self.assertEqual(model(dict(profile(),**change)).evaluate(scene())['classification'],'UNKNOWN')
 def test_clear_window_and_identity_discontinuities(self):
  m=model().evaluate(scene());self.assertEqual(m['classification'],'MATCH')
  for change in ['duplicate','gap','epoch','generation','config','reference','stale','integrity']:
   window=ClearWindow()
   for n in range(7):v=window.update(m,meta(n),10+n*.2)
   self.assertEqual(v['state'],'CLEAR')
   packet=meta(7);mm=dict(m);now=11.4
   if change=='duplicate':packet=meta(6)
   elif change=='gap':packet=meta(10);now=12
   elif change=='epoch':packet['camera_epoch']='other'
   elif change=='generation':packet['generation']='other'
   elif change=='config':mm['config_version']='other'
   elif change=='reference':mm['reference_version']='other'
   elif change=='stale':now=20
   elif change=='integrity':packet['integrity']={'valid':False}
   self.assertEqual(window.update(mm,packet,now)['state'],'UNKNOWN')
 def test_remaining_product_breaks_clearance_accumulation(self):
  m=model();window=ClearWindow();empty=m.evaluate(scene())
  occupied=scene();occupied[300:420,500:700]=190
  for n in range(7):last=window.update(empty,meta(n),10+n*.2)
  self.assertEqual(last['state'],'CLEAR')
  self.assertNotEqual(window.update(m.evaluate(occupied),meta(7),11.4)['state'],'CLEAR')
  for n in range(8,14):
   last=window.update(empty,meta(n),10+n*.2);self.assertNotEqual(last['state'],'CLEAR')
  self.assertEqual(window.update(empty,meta(14),12.8)['state'],'CLEAR')

 def test_field_launcher_rejects_development_profile_before_camera_or_plc(self):
  import launch_live
  from unittest.mock import patch
  project=Path(__file__).resolve().parents[2]
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'config').mkdir()
   (root/'config/area_clearance.json').write_text(json.dumps(profile()),encoding='utf-8')
   (root/'config/plc_reference.json').write_bytes((project/'jetson/config/plc_reference.json').read_bytes())
   with patch.object(launch_live,'ROOT',root):
    with self.assertRaisesRegex(ValueError,'HORIZONTAL_TEXTURE_ISOLATED_VALIDATION_ONLY'):
     launch_live.check_files(project/'jetson/products/ENGINE_Z3005_5/dynamic_parts_005',
                            project/'jetson/station.example.json',plc_bench=True)

if __name__=='__main__':unittest.main(verbosity=2)
