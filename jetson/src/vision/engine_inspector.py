"""Worker-owned envelope detector and pose; shares the existing camera frame and lifecycle."""
import hashlib
import json
from pathlib import Path
import time
import cv2
import numpy as np

from src.decision.engine_dynamic import aggregate_three, box_of, inspect_frame, result, SLOTS
from src.decision.calibration import ReferenceError
from src.recipe.package import load_package
from src.vision.detector_factory import create_detector
from src.vision.engine_pose import EnginePoseEstimator


class EngineInspector:
    def __init__(self,package):
        settings=package.recipe['engine_pose']
        path=(package.root/settings['path']).resolve()
        if not path.is_relative_to(package.root.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=settings['sha256']:
            raise ValueError('POSE_REFERENCE_HASH_MISMATCH')
        self.estimator=EnginePoseEstimator(path)
        reference=path.parent/self.estimator.cfg['reference_image']
        if hashlib.sha256(reference.read_bytes()).hexdigest()!=self.estimator.cfg['reference_image_sha256']:
            raise ValueError('POSE_IMAGE_HASH_MISMATCH')
        envelope_root=(package.root/settings['envelope_package']).resolve()
        if not envelope_root.is_relative_to(package.root.parent.parent.resolve()):
            raise ValueError('ENVELOPE_PACKAGE_PATH_INVALID')
        envelope_package=load_package(envelope_root)
        if envelope_package.manifest_hash!=settings['envelope_manifest_sha256']:
            raise ValueError('ENVELOPE_PACKAGE_HASH_MISMATCH')
        if envelope_package.names!=['product_envelope']:
            raise ValueError('ENVELOPE_CLASS_CONTRACT_INVALID')
        self.detector=create_detector(envelope_package,latency_enabled=True)
        self.previous_gray=None
        self.stable_since=None

    def detect(self,frame,observation,*,parts_detector=None):
        started=time.perf_counter()
        envelope=self.detector.detect(frame).to_dict()
        timings={'product_detection_ms':(time.perf_counter()-started)*1000,
            'pose_ms':None,'rectification_ms':None,'part_detection_ms':None,'slot_decision_ms':None}
        pose=None
        if parts_detector is not None:
            from src.contracts import CameraFrame
            from src.decision.engine_dynamic import box_of
            from src.vision.engine_rectification import rectify_image,restore_detections
            products=[d for d in envelope['detections'] if d['confidence']>=self.estimator.cfg['decision_policy']['product_confidence']]
            observation['detections']=[]
            observation['part_inference_input']='NOT_RUN_WITHOUT_RELIABLE_PRODUCT_POSE'
            if len(products)==1:
                stage=time.perf_counter()
                pose=self.estimator.estimate(frame.image,box_of(products[0]))
                timings['pose_ms']=(time.perf_counter()-stage)*1000
                if pose.ok:
                    stage=time.perf_counter()
                    canonical=rectify_image(frame.image,pose.matrix,self.estimator.cfg)
                    timings['rectification_ms']=(time.perf_counter()-stage)*1000
                    canonical_frame=CameraFrame(canonical,frame.frame_id,frame.captured_at,canonical.shape[1],canonical.shape[0],'ENGINE_POSE_RECTIFIED')
                    stage=time.perf_counter()
                    parts=parts_detector.detect(canonical_frame).to_dict()
                    timings['part_detection_ms']=(time.perf_counter()-stage)*1000
                    observation['detections']=restore_detections(parts['detections'],pose.matrix)
                    observation['inference_ms']+=parts['inference_ms']
                    observation['part_inference_input']='ENGINE_POSE_RECTIFIED'
                    observation['part_input_sha256']=hashlib.sha256(canonical.tobytes()).hexdigest()
                    observation['part_input_transform']=pose.matrix.tolist()
        detections=observation['detections']+envelope['detections']
        stage=time.perf_counter()
        value=inspect_frame(frame.image,detections,self.estimator,pose=pose)
        timings['slot_decision_ms']=(time.perf_counter()-stage)*1000
        value['stage_timings_ms']=timings
        value['diagnostic_revision']='ENGINE-DYNAMIC-POSE-LIVE-FIX-001'
        value['detector_stages']=getattr(self.detector,'last_diagnostics',None)
        if not observation['quality']['valid']:
            value['geometric_slot_observations']=value['slot_states']
            value['slot_states']=dict.fromkeys(SLOTS,'NOT_EVALUATED')
        changed,stable=self.motion(frame.image)
        value.update(frame_id=frame.frame_id,source_pts_ns=observation['freshness']['source_pts_ns'],
            quality_valid=observation['quality']['valid'],motion_fraction=changed,stable=stable,
            engine_processing_ms=(time.perf_counter()-started)*1000)
        if observation['freshness'].get('camera_epoch') is not None:
            value['camera_epoch']=observation['freshness']['camera_epoch']
        observation['detections']=detections
        observation['engine_dynamic']=value
        observation['inference_ms']+=envelope['inference_ms']
        return value

    def motion(self,image):
        gray=cv2.resize(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),(320,180))
        now=time.monotonic()
        changed=1.
        if self.previous_gray is not None:
            changed=float(np.mean(cv2.absdiff(gray,self.previous_gray)>25))
        if changed>.008:self.stable_since=None
        elif self.stable_since is None:self.stable_since=now
        self.previous_gray=gray
        stable=self.stable_since is not None and now-self.stable_since>=.6
        return changed,stable

    def observe_product(self,frame,observation):
        """Same envelope/threshold and camera input; parts/pose intentionally not evaluated."""
        started=time.perf_counter()
        envelope=self.detector.detect(frame).to_dict()
        policy=self.estimator.cfg['decision_policy']
        valid=[d for d in envelope['detections'] if d['confidence']>=policy['product_confidence']]
        changed,stable=self.motion(frame.image)
        observation['detections']=envelope['detections']
        observation['inference_ms']=envelope['inference_ms']
        return dict(frame_id=frame.frame_id,camera_epoch=observation['freshness']['camera_epoch'],
            decision='REVIEW',reason_code='TRACKING_ONLY_PARTS_NOT_EVALUATED',
            product=valid[0] if len(valid)==1 else None,products=valid,
            product_selection={'confidence_threshold':policy['product_confidence']},
            detector_stages=getattr(self.detector,'last_diagnostics',None),
            pose={'reliable':False,'reliability_reason':'NOT_EVALUATED_DURING_TRACKING'},
            slot_states=dict.fromkeys(SLOTS,'NOT_EVALUATED'),slot_polygons={},
            quality_valid=observation['quality']['valid'],motion_fraction=changed,stable=stable,
            stage_timings_ms={'product_detection_ms':(time.perf_counter()-started)*1000},
            source_pts_ns=observation['freshness']['source_pts_ns'])

    def close(self):self.detector.close()


def conveyor_frame_gate(observation, capture_zone):
    """Accept only a fresh inspection candidate with a fully visible, posed product.

    Freshness/epoch and the latched Track are checked by the existing selector and
    production binding. This gate does not claim to detect a hand.
    """
    frame=observation['engine_dynamic']
    if observation['quality']['valid'] is not True:
        return 'CONVEYOR_IMAGE_QUALITY_INSUFFICIENT'
    selection=frame.get('product_selection',{})
    if selection.get('valid_count')!=1 or not frame.get('product'):
        return 'CONVEYOR_PRODUCT_UNAVAILABLE'
    x1,y1,x2,y2=box_of(frame['product'])
    width,height=observation['width'],observation['height']
    if not (0<x1<x2<width and 0<y1<y2<height):
        return 'CONVEYOR_PRODUCT_PARTIALLY_VISIBLE'
    cx,cy=(x1+x2)/(2*width),(y1+y2)/(2*height)
    zone=capture_zone['polygon_normalized']
    if not (zone[0][0]<=cx<=zone[2][0] and zone[0][1]<=cy<=zone[2][1]):
        return 'CONVEYOR_OUTSIDE_CAPTURE_ZONE'
    if frame.get('pose',{}).get('reliable') is not True:
        return 'CONVEYOR_POSE_UNRELIABLE'
    if frame.get('reason_code')=='SLOT_OUTSIDE_FRAME':
        return 'CONVEYOR_PRODUCT_PARTIALLY_VISIBLE'
    if frame.get('decision')=='ERROR':
        return 'CONVEYOR_FRAME_ERROR'
    return None


def conveyor_incomplete_result(observations, rejections):
    """A bounded capture window may end with fewer than three valid frames."""
    # Journal requires original image evidence for REVIEW. With no accepted frame,
    # report an explicit system ERROR instead of failing the durable write.
    return result('REVIEW' if observations else 'ERROR','CONVEYOR_INSUFFICIENT_VALID_FRAMES',
                  valid_frame_count=len(observations),
                  frames=[o['engine_dynamic'] for o in observations],
                  conveyor_frame_rejections=rejections)


def assess_dynamic(observations,view,calibration,*,register=False,experiment_policy=None):
    frames=[o['engine_dynamic'] for o in observations]
    if view.get('system_error'):
        return result('ERROR','SYSTEM_ERROR',frames=frames,system_error=str(view['system_error']))
    value=aggregate_three(frames)
    # Invalid frames/system faults and envelope absence retain their distinct precedence.
    if value['decision']=='ERROR' or value['reason_code']=='PRODUCT_ENVELOPE_NOT_FOUND':return value
    if value['reason_code'] in ('ENGINE_POSE_UNCERTAIN','MULTIPLE_PRODUCT_ENVELOPES','IMAGE_QUALITY_INSUFFICIENT','SLOT_OUTSIDE_FRAME'):
        return value
    def review(code,blocked):
        value.update(decision='REVIEW',reason=code,reason_code=code,disposition='REJECT',
            slot_states=dict.fromkeys(SLOTS,'NOT_EVALUATED'),defects=[],
            blocking_frames=[dict(frame_number=i+1,frame_id=f.get('frame_id'),reason_code=code) for i,f in enumerate(frames) if blocked(f)])
        return value
    conveyor=(not register and experiment_policy and
        experiment_policy.get('source_mode')=='PRODUCTION_AUTO' and
        experiment_policy.get('inspection_motion_mode') in ('CONVEYOR_MOTION_DEV','CONVEYOR_MOTION_PLC_BENCH') and
        experiment_policy.get('session_id') and experiment_policy.get('physical_output_enabled') is False)
    if conveyor:
        zone=experiment_policy['capture_zone']
        blocked=[conveyor_frame_gate(o,zone) for o in observations]
        if any(blocked):
            code=next(reason for reason in blocked if reason)
            blocked_ids={f.get('frame_id') for f,reason in zip(frames,blocked) if reason}
            return review(code,lambda f:f.get('frame_id') in blocked_ids)
        centers=[]
        for frame in frames:
            _,y1,_,y2=box_of(frame['product'])
            centers.append((y1+y2)/2)
        value['conveyor_center_delta_y_px']=centers[-1]-centers[0]
        if centers[-1]<=centers[0]:
            return review('CONVEYOR_MOTION_NOT_CONFIRMED',lambda f:True)
        value['frame_motion_policy']='FRAME_MOTION_ACCEPTED_FOR_CONVEYOR'
    elif any(not f.get('stable') for f in frames):
        return review('ENGINE_OR_HAND_MOTION',lambda f:not f.get('stable'))
    experiment=(not register and experiment_policy and experiment_policy.get('source_mode') in ('LAB_AUTO','MOCK_PLC','PRODUCTION_AUTO')
        and experiment_policy.get('session_id') and experiment_policy.get('human_acceptance')=='PENDING'
        and experiment_policy.get('physical_output_enabled') is False)
    if not experiment and (view.get('product_identity')!='human_confirmed' or view.get('alignment_confirmed') is not True or not all(view.get('visible_slots',{}).get(s) is True for s in SLOTS)):
        return review('HUMAN_VISIBILITY_NOT_CONFIRMED',lambda f:True)
    if not register and not (calibration and calibration.get('confirmed')):
        return review('REFERENCE_NOT_CONFIRMED',lambda f:True)
    if experiment and experiment_policy.get('trigger_reason')=='LAB_STABILITY_TIMEOUT':
        return review('LAB_STABILITY_TIMEOUT',lambda f:True)
    return value


def dynamic_reference(observations,package,view):
    value=assess_dynamic(observations,view,None,register=True)
    if value['decision']!='PASS':raise ReferenceError(value['reason_code'],'정상 부품·자세·가시성·정지 상태를 확인한 뒤 다시 촬영하세요.',SLOTS)
    last=observations[-1]
    regions={}
    for name,points in last['engine_dynamic']['slot_polygons'].items():
        points=np.asarray(points)
        lo,hi=points.min(axis=0),points.max(axis=0)
        regions[name]=[max(0,float(lo[0]/last['width'])),max(0,float(lo[1]/last['height'])),
                       min(1,float(hi[0]/last['width'])),min(1,float(hi[1]/last['height']))]
    return {'slots':regions,'reference_box':None,'coordinate_space':'normalized_image',
        'source_dimensions':{'width':last['width'],'height':last['height']},
        'source_frame_ids':[o['frame_id'] for o in observations],'product_id':package.manifest['product_id'],
        'manifest_sha256':package.manifest_hash,'capture_sha256':package.manifest['files']['capture']['sha256'],
        'recipe_sha256':package.manifest['files']['recipe']['sha256'],'confirmed':False,
        'engine_pose_sha256':package.recipe['engine_pose']['sha256'],
        'note':'Human acceptance of the D001 engine coordinate system; captured pose does not replace D001.'}


def draw_engine_overlay(image,observation,final=None,*,show_slots=True):
    from src.decision.engine_dynamic import box_of
    overlay=image.copy()
    value=observation.get('engine_dynamic',{})
    colors={'PASS':(80,230,120),'FAIL':(70,70,255),'REVIEW':(0,180,255),'ERROR':(80,80,255)}
    def label(text,point,size,color):
        cv2.putText(overlay,text,point,cv2.FONT_HERSHEY_SIMPLEX,size,(10,10,10),3,cv2.LINE_AA)
        cv2.putText(overlay,text,point,cv2.FONT_HERSHEY_SIMPLEX,size,color,1,cv2.LINE_AA)
    for d in observation.get('detections',[]):
        x1,y1,x2,y2=map(round,box_of(d))
        color=(255,210,50) if d['class_name']=='product_envelope' else (80,230,120)
        if d['class_name']=='product_envelope' and d!=value.get('product') and d not in value.get('products',[]):
            color=(150,150,150)  # A returned candidate is not an accepted product.
        cv2.rectangle(overlay,(x1,y1),(x2,y2),color,2)
        label(f"{d['class_name']} {d['confidence']:.2f}",(x1,max(18,y1-5)),.5,color)
    states=value.get('slot_states',{})
    labels={'pipe_left':'LEFT PIPE','pipe_right':'RIGHT PIPE','exhaust':'EXHAUST','symbol':'SYMBOL'}
    for slot,points in value.get('slot_polygons',{}).items():
        if not show_slots or not value.get('pose',{}).get('reliable'):continue
        state=states.get(slot,'UNCERTAIN')
        color=(235,130,210)  # Purple dashed reference geometry, distinct from green detections.
        points=np.round(points).astype(np.int32)
        for first,second in zip(points,np.roll(points,-1,axis=0)):
            length=float(np.linalg.norm(second-first))
            for offset in np.arange(0,length,15):
                start=first+(second-first)*offset/max(length,1)
                end=first+(second-first)*min(offset+9,length)/max(length,1)
                cv2.line(overlay,tuple(start.astype(int)),tuple(end.astype(int)),color,2)
        x,y=points.min(axis=0)
    pose=value.get('pose',{})
    if pose.get('reliable') and pose.get('matrix') is not None:
        matrix=np.asarray(pose['matrix'],dtype=float)
        # Envelope centre; axis directions come only from this frame's pose.
        x1,y1,x2,y2=box_of(value['product'])
        centre=np.array([(x1+x2)/2,(y1+y2)/2])
        cv2.circle(overlay,tuple(np.round(centre).astype(int)),5,(255,220,50),-1)
        for delta,color,name in ((np.array([90.,0.]),(70,100,255),'D001 +X'),(np.array([0.,90.]),(255,180,60),'D001 +Y')):
            end=centre+matrix[:,:2]@delta
            cv2.arrowedLine(overlay,tuple(np.round(centre).astype(int)),tuple(np.round(end).astype(int)),color,2,tipLength=.2)
            label(name,tuple(np.round(end).astype(int)),.4,color)
    angle=pose.get('angle_deg')
    status=final or value
    if final is None and not value.get('stable') and status.get('decision')!='ERROR':
        status=dict(status,decision='REVIEW',reason_code='WAIT_FOR_STABLE_FRAME')
    decision=status.get('decision','REVIEW')
    product_confidence=max((float(d['confidence']) for d in observation.get('detections',[]) if d['class_name']=='product_envelope'),default=0.)
    text=[('FINAL ' if final else 'PREVIEW (not a saved decision) ')+decision+' / '+status.get('reason_code','NO_RESULT'),
          (f"angle {angle:.1f} deg" if pose.get('reliable') and angle is not None else 'angle UNRELIABLE')+f" | inliers {pose.get('inliers',0)} | {pose.get('reliability_reason','NO_POSE')}",
          f"post-NMS max candidate {product_confidence:.3f} / threshold {value.get('product_selection',{}).get('confidence_threshold','?')} | "+('STABLE (not hand detection)' if value.get('stable') else 'MOVING / WAIT')]
    if final:
        blockers=','.join(str(b['frame_number']) for b in final.get('blocking_frames',[])) or '-'
        text[2]=f"Shown frame {observation.get('frame_id','?')} | blocking frames {blockers}"
    cv2.rectangle(overlay,(0,0),(overlay.shape[1],80),(15,22,35),-1)
    for i,line in enumerate(text):cv2.putText(overlay,line,(10,22+i*24),cv2.FONT_HERSHEY_SIMPLEX,.55,colors.get(decision,(255,255,255)),1)
    # Slot states and long diagnostics live in the HMI side panel, not on parts.
    return overlay
