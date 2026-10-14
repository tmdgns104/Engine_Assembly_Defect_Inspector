"""Reference-free occupancy for one explicitly calibrated dark conveyor belt.

The fixed full-height belt is never fitted around a detected product. Current
rail evidence validates camera placement; missing evidence fails closed. This is
not a general object detector or a clearance claim about the surrounding table.
"""
import hashlib
import json
from pathlib import Path
from time import perf_counter


MODE = 'CONVEYOR_DARK_BELT_SELF_OBSERVED'


def validate_conveyor_config(config):
    if (config.get('mode') != MODE or config.get('roi') != 'FULL_HEIGHT_CALIBRATED_BELT'
            or config.get('shape') != [720,1280,3] or config.get('color') != 'BGR_UINT8'
            or config.get('references')):
        raise ValueError('UNSUPPORTED_CONVEYOR_AREA_CONFIG')
    for key, expected in dict(clear_seconds=1.2,clear_minimum_frames=6,
                              maximum_gap_seconds=.5,maximum_age_seconds=1.).items():
        if config.get(key) != expected:
            raise ValueError('UNSUPPORTED_AREA_CONTINUITY_POLICY:'+key)
    bounds=config.get('belt_bounds')
    if not isinstance(bounds,list) or not 2 <= len(bounds) <= 16:
        raise ValueError('CONVEYOR_BOUNDS_REQUIRED')
    previous_y=-1
    for row in bounds:
        if (not isinstance(row,list) or len(row)!=3
                or any(type(v) is not int for v in row)):
            raise ValueError('CONVEYOR_INTEGER_NATIVE_BOUNDS_REQUIRED')
        y,left,right=row
        if not (previous_y < y <= 719 and 24 <= left < right < 1256 and 256 <= right-left <= 768):
            raise ValueError('CONVEYOR_BOUNDS_INVALID')
        previous_y=y
    if bounds[0][0]!=0 or bounds[-1][0]!=719:
        raise ValueError('CONVEYOR_BOTH_EXITS_MUST_REMAIN_OBSERVED')


class ConveyorSurfaceOccupancy:
    def __init__(self,config,config_version):
        self.config=config
        self.config_version=config_version

    @classmethod
    def from_config(cls,path,raw=None):
        raw=Path(path).read_bytes() if raw is None else raw
        config=json.loads(raw)
        validate_conveyor_config(config)
        return cls(config,hashlib.sha256(raw).hexdigest())

    def evaluate(self,image):
        import cv2
        import numpy as np
        started=perf_counter()
        result=dict(config_version=self.config_version,reference_version='CONVEYOR_BELT_GEOMETRY_V1',
                    reference_valid=False,classification='UNKNOWN',regions={})

        def finish(reason,classification='UNKNOWN',valid=False):
            return dict(result,reason=reason,classification=classification,reference_valid=valid,
                        comparison_ms=(perf_counter()-started)*1000)

        if image is None or image.dtype!=np.uint8 or list(image.shape)!=self.config['shape']:
            return finish('IMAGE_GEOMETRY_OR_FORMAT_INVALID')
        gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        bounds=np.asarray(self.config['belt_bounds'])
        rows=np.arange(720)
        left=np.ceil(np.interp(rows,bounds[:,0],bounds[:,1])).astype(int)
        right=np.floor(np.interp(rows,bounds[:,0],bounds[:,2])).astype(int)
        columns=np.arange(1280)[None,:]
        belt=(columns>=left[:,None]) & (columns<=right[:,None])

        # These narrow strips lie on the silver rails, outside the belt. They
        # validate placement; they never become a learned empty-image reference.
        offsets=np.arange(6,14)
        left_rail=gray[rows[:,None],left[:,None]-offsets]
        right_rail=gray[rows[:,None],right[:,None]+offsets]
        support=(np.mean(left_rail>155,axis=1)>=.75) & (np.mean(right_rail>155,axis=1)>=.75)
        blocks=[float(np.mean(support[y:y+60])) for y in range(0,720,60)]
        dark_fraction=float(np.mean(gray[belt]<125))
        result['regions']['surface_geometry']=dict(belt_bounds=self.config['belt_bounds'],
            rail_support_by_60_rows=blocks,dark_fraction=dark_fraction,full_height=True)
        if min(blocks)<.8:
            return finish('CONVEYOR_RAIL_GEOMETRY_OR_OCCLUSION')

        hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
        foreground=(((gray>135) | ((hsv[:,:,1]>100)&(hsv[:,:,2]>90))) & belt).astype(np.uint8)

        def largest(mask,y_offset=0):
            count,_,stats,_=cv2.connectedComponentsWithStats(mask,8)
            if count<=1:
                return dict(pixels=0,box=None)
            index=int(stats[1:,4].argmax())+1
            box=stats[index,:4].tolist()
            box[1]+=y_offset
            return dict(pixels=int(stats[index,4]),box=box)

        whole=largest(foreground)
        top=largest(foreground[:64])
        bottom=largest(foreground[-64:],656)
        result['regions'].update(whole=whole,top_exit=top,bottom_exit=bottom,
                                 foreground_pixels=int(foreground.sum()))
        # Preserve the prior whole-component and thin-exit thresholds. Observe
        # both exits; no erosion, edge-strip removal, voting or detector fallback.
        if whole['pixels']>=80 or max(top['pixels'],bottom['pixels'])>=30:
            return finish('CONVEYOR_OBJECT_PRESENT','OCCUPIED',True)
        if dark_fraction<.55:
            return finish('CONVEYOR_DARK_BELT_NOT_RECOGNIZED')
        return finish('CONVEYOR_NO_OBJECT','MATCH',True)
