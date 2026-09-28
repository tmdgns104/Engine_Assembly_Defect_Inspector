"""Normalize only a verified engine pose; return all detections to raw camera coordinates."""
import cv2
import numpy as np
from src.decision.engine_dynamic import box_of
from src.vision.engine_pose import transform_polygon

def rectify_image(image,matrix,config):
    width,height=config['frame_width'],config['frame_height']
    canonical=cv2.warpAffine(image,cv2.invertAffineTransform(np.asarray(matrix)),(width,height),borderValue=(40,40,40))
    x1,y1,x2,y2=config['canonical_product_box_xyxy']
    dx,dy=(x2-x1)*.18,(y2-y1)*.18
    mask=np.zeros((height,width),np.uint8)
    cv2.rectangle(mask,(max(0,int(x1-dx)),max(0,int(y1-dy))),
                  (min(width,int(x2+dx)),min(height,int(y2+dy))),255,-1)
    canonical[mask==0]=40
    return canonical

def restore_detections(detections,matrix):
    restored=[]
    for detection in detections:
        x1,y1,x2,y2=box_of(detection)
        polygon=transform_polygon([[x1,y1],[x2,y1],[x2,y2],[x1,y2]],matrix)
        lo,hi=polygon.min(axis=0),polygon.max(axis=0)
        restored.append(dict(detection,bounding_box=dict(x1=float(lo[0]),y1=float(lo[1]),x2=float(hi[0]),y2=float(hi[1])),
                             canonical_box=[x1,y1,x2,y2],detection_polygon=polygon.tolist()))
    return restored
