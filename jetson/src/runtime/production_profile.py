"""Station maintenance geometry, independent of frozen model/pose thresholds."""
import hashlib
import json
import math
from src.tracking.contracts import InspectionWindow,SingleActiveTrackerConfig


def calibration_sha(calibration):
    return hashlib.sha256(json.dumps(calibration,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def validate_zone(value):
    points=value['polygon_normalized']
    if (not isinstance(points,list) or len(points)!=4 or
        any(not isinstance(p,list) or len(p)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in p) for p in points)):
        raise ValueError('NORMALIZED_RECTANGLE_REQUIRED')
    x1,y1=points[0]; x2,y2=points[2]
    if points!=[[x1,y1],[x2,y1],[x2,y2],[x1,y2]] or x2-x1<.1 or y2-y1<.1:
        raise ValueError('NORMALIZED_RECTANGLE_REQUIRED')
    if value.get('entry_policy')!='product_center': raise ValueError('UNSUPPORTED_ZONE_ENTRY_POLICY')
    return InspectionWindow(x1,y1,x2,y2)


def tracker_config(zone, *, wait_area_clear=False):
    return SingleActiveTrackerConfig(validate_zone(zone),'x',1,.22,.22,12,1,
        max_center_speed_norm_s=.2,max_unobserved_seconds=3,
        free_motion=True,zone_hysteresis=.025,zone_entry_frames=3,wait_area_clear=wait_area_clear)


def proposed_zone():
    return dict(version='production_zone_v001',polygon_normalized=[[.2,.2],[.8,.2],[.8,.8],[.2,.8]],
        entry_policy='product_center',confirmed=False,calibration_sha=None)
