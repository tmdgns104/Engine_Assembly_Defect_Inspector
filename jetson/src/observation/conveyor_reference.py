"""Frozen empty-belt noise comparison for a calibrated horizontal camera view.

Calibration is explicit, hashed and immutable. Current frames never update it.
This observes surface occupancy, not product identity, safety or motor feedback.
"""
import hashlib
import json
from pathlib import Path
from time import perf_counter

MODE = 'CONVEYOR_FROZEN_EMPTY_ENVELOPE'
PIXEL_DIFFERENCE = 30  # Existing native reference-comparison tolerance.
WHOLE_COMPONENT = 80  # Existing conveyor occupied-component threshold.
EXIT_COMPONENT = 30   # Existing thin retained-object threshold, both exits.


def validate_reference_config(config):
    if (config.get('mode') != MODE or config.get('roi') != 'FULL_WIDTH_CALIBRATED_BELT'
            or config.get('shape') != [720,1280,3] or config.get('color') != 'BGR_UINT8'
            or config.get('empty_confirmed') is not True
            or config.get('calibration_scope') != 'FIXED_CAMERA_STATIONARY_BELT'
            or not config.get('calibration_id')):
        raise ValueError('UNSUPPORTED_CONVEYOR_REFERENCE_CONFIG')
    for key, value in dict(clear_seconds=1.2, clear_minimum_frames=6,
                           maximum_gap_seconds=.5, maximum_age_seconds=1.).items():
        if config.get(key) != value:
            raise ValueError('UNSUPPORTED_AREA_CONTINUITY_POLICY:'+key)
    bounds=config.get('belt_bounds')
    if not isinstance(bounds,list) or not 2 <= len(bounds) <= 16:
        raise ValueError('CONVEYOR_BOUNDS_REQUIRED')
    previous=-1
    for row in bounds:
        if (not isinstance(row,list) or len(row)!=3 or any(type(v) is not int for v in row)):
            raise ValueError('CONVEYOR_INTEGER_NATIVE_BOUNDS_REQUIRED')
        x,top,bottom=row
        if not (previous<x<=1279 and 24<=top<bottom<696 and 256<=bottom-top<=672):
            raise ValueError('CONVEYOR_BOUNDS_INVALID')
        previous=x
    if bounds[0][0]!=0 or bounds[-1][0]!=1279:
        raise ValueError('CONVEYOR_BOTH_EXITS_MUST_REMAIN_OBSERVED')
    references=config.get('references')
    if not isinstance(references,list) or not 9 <= len(references) <= 32:
        raise ValueError('CONVEYOR_EMPTY_REFERENCE_SEQUENCE_REQUIRED')
    ids=[item['frame_id'] for item in references]
    times=[item['source_pts_ns'] for item in references]
    epochs={item['camera_epoch'] for item in references}
    if (len(set(ids))!=len(ids) or len(epochs)!=1 or not next(iter(epochs))
            or any(type(t) is not int for t in times)
            or any(b<=a for a,b in zip(times,times[1:]))
            or times[-1]-times[0]<1_200_000_000):
        raise ValueError('CONVEYOR_CALIBRATION_FRESHNESS_INVALID')


class ConveyorReferenceOccupancy:
    @classmethod
    def from_config(cls, path, raw=None):
        import cv2
        import numpy as np
        path=Path(path)
        raw=path.read_bytes() if raw is None else raw
        config=json.loads(raw)
        validate_reference_config(config)
        model=cls()
        model.config=config
        model.config_version=hashlib.sha256(raw).hexdigest()
        bounds=np.asarray(config['belt_bounds'])
        model.columns=np.arange(1280)
        model.top=np.ceil(np.interp(model.columns,bounds[:,0],bounds[:,1])).astype(int)
        model.bottom=np.floor(np.interp(model.columns,bounds[:,0],bounds[:,2])).astype(int)
        model.belt=((np.arange(720)[:,None]>=model.top)&(np.arange(720)[:,None]<=model.bottom))
        model.low=model.high=None
        root=path.parent.resolve()
        for item in config['references']:
            source=(root/item['path']).resolve()
            if not source.is_relative_to(root):
                raise ValueError('CONVEYOR_REFERENCE_OUTSIDE_CONFIG')
            data=source.read_bytes()
            if hashlib.sha256(data).hexdigest()!=item['sha256']:
                raise ValueError('CONVEYOR_REFERENCE_HASH_MISMATCH')
            image=cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_COLOR)
            if image is None or list(image.shape)!=config['shape']:
                raise ValueError('CONVEYOR_REFERENCE_FORMAT_INVALID')
            if min(model.rail_support(image))<.8:
                raise ValueError('CONVEYOR_REFERENCE_RAIL_GEOMETRY_INVALID')
            value=image.astype(np.int16)
            model.low=value if model.low is None else np.minimum(model.low,value)
            model.high=value.copy() if model.high is None else np.maximum(model.high,value)
        return model

    def rail_support(self,image):
        import cv2
        import numpy as np
        gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        offsets=np.arange(6,14)
        upper=gray[self.top[:,None]-offsets,self.columns[:,None]]
        lower=gray[self.bottom[:,None]+offsets,self.columns[:,None]]
        support=(np.mean(upper>155,axis=1)>=.75)&(np.mean(lower>155,axis=1)>=.75)
        return [float(np.mean(support[x:x+60])) for x in range(0,1280,60)]

    def evaluate(self,image):
        import cv2
        import numpy as np
        started=perf_counter()
        result=dict(config_version=self.config_version,reference_version=self.config['calibration_id'],
                    reference_valid=False,classification='UNKNOWN',regions={})
        def finish(reason,classification='UNKNOWN',valid=False):
            return dict(result,reason=reason,classification=classification,reference_valid=valid,
                        comparison_ms=(perf_counter()-started)*1000)
        if image is None or image.dtype!=np.uint8 or list(image.shape)!=self.config['shape']:
            return finish('IMAGE_GEOMETRY_OR_FORMAT_INVALID')
        support=self.rail_support(image)
        result['regions']['surface_geometry']=dict(belt_bounds=self.config['belt_bounds'],
            full_width=True,rail_support_by_60_columns=support)
        if min(support)<.8:
            return finish('CONVEYOR_RAIL_GEOMETRY_OR_OCCLUSION')
        value=image.astype(np.int16)
        delta=np.maximum(np.maximum(self.low-value,value-self.high),0).max(2)
        foreground=((delta>PIXEL_DIFFERENCE)&self.belt).astype(np.uint8)
        def largest(mask,x_offset=0):
            count,_,stats,_=cv2.connectedComponentsWithStats(mask,8)
            if count<=1:
                return dict(pixels=0,box=None)
            index=int(stats[1:,4].argmax())+1
            box=stats[index,:4].tolist();box[0]+=x_offset
            return dict(pixels=int(stats[index,4]),box=box)
        whole=largest(foreground)
        left=largest(foreground[:,:64])
        right=largest(foreground[:,-64:],1216)
        result['regions'].update(whole=whole,left_exit=left,right_exit=right,
            foreground_pixels=int(foreground.sum()),pixel_difference=PIXEL_DIFFERENCE,
            calibration_scope=self.config['calibration_scope'])
        # No erosion, spatial shrinkage, detector fallback or current-image learning.
        if whole['pixels']>=WHOLE_COMPONENT or max(left['pixels'],right['pixels'])>=EXIT_COMPONENT:
            return finish('CONVEYOR_EMPTY_REFERENCE_DIFFERENCE','OCCUPIED',True)
        return finish('CONVEYOR_FROZEN_EMPTY_ENVELOPE_MATCH','MATCH',True)
