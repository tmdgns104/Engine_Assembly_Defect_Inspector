"""Within one saved inspection only. Relative tracking cannot certify its anchor.

No optical flow is run on a previous product. Every target is rectified from its
own pixels. Classification results are never inputs to tracking.
"""
import time
import cv2
import numpy as np
from geometry import transform


def relative_body(anchor,target,labels):
    start=time.perf_counter();cv2.setNumThreads(1)
    a=cv2.cvtColor(anchor,cv2.COLOR_BGR2GRAY);b=cv2.cvtColor(target,cv2.COLOR_BGR2GRAY)
    src=[];dst=[];regions=[];fb_errors=[]
    for region in range(1,int(labels.max())+1):
        # No pyramid. The complete 9x9 window and derivative neighbourhood
        # remain within the selected physical surface in both images.
        mask=(labels==region).astype(np.uint8)*255
        yy,xx=np.nonzero(mask)
        if not len(xx):continue
        x1,x2,y1,y2=int(xx.min()),int(xx.max())+1,int(yy.min()),int(yy.max())+1
        origin=np.array([x1,y1])
        local_a=np.ascontiguousarray(a[y1:y2,x1:x2]);local_b=np.ascontiguousarray(b[y1:y2,x1:x2])
        local_inner=cv2.erode(np.ascontiguousarray(mask[y1:y2,x1:x2]),np.ones((13,13),np.uint8),
                             borderType=cv2.BORDER_CONSTANT,borderValue=0)
        points=cv2.goodFeaturesToTrack(local_a,80,.01,4,mask=local_inner,blockSize=3)
        if points is None:continue
        options=dict(winSize=(9,9),maxLevel=0,criteria=(cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,30,.005))
        q,s1,_=cv2.calcOpticalFlowPyrLK(local_a,local_b,points,None,**options)
        back,s2,_=cv2.calcOpticalFlowPyrLK(local_b,local_a,q,None,**options)
        if back is None:continue
        error=np.linalg.norm(back-points,axis=2).ravel()
        xy=np.rint(q.reshape(-1,2)).astype(int)
        keep=(s1.ravel()>0)&(s2.ravel()>0)&(error<=1.)&np.isfinite(error)
        inside=(xy[:,0]>=0)&(xy[:,0]<local_a.shape[1])&(xy[:,1]>=0)&(xy[:,1]<local_a.shape[0])
        keep &= inside
        indices=np.flatnonzero(keep)
        keep[indices] &= local_inner[xy[indices,1],xy[indices,0]]>0
        src.extend(points.reshape(-1,2)[keep]+origin);dst.extend(q.reshape(-1,2)[keep]+origin);regions.extend([region]*sum(keep));fb_errors.extend(error[keep])
    src=np.asarray(src,float).reshape(-1,2);dst=np.asarray(dst,float).reshape(-1,2);regions=np.asarray(regions)
    result=dict(points_anchor=src,points_target=dst,regions=regions,fb_errors_px=fb_errors,
                reason='INSUFFICIENT_RELATIVE_BODY_SUPPORT',matrix=None)
    if len(src)>=6:
        # Fit only one subset; validate other points without using them in fit.
        fit=np.arange(len(src))%2==0;held=~fit
        matrix,inliers=cv2.estimateAffinePartial2D(src[fit],dst[fit],method=cv2.RANSAC,ransacReprojThreshold=1.)
        if matrix is not None:
            err=np.linalg.norm(transform(src,matrix)-dst,axis=1)
            support=[int(np.sum((regions==r)&(err<=1))) for r in range(1,int(labels.max())+1)]
            result.update(matrix=matrix,support=support,held_errors_px=err[held],max_fb_px=float(max(fb_errors)),
                reason='RELATIVE_ONLY_ANCHOR_QUALIFICATION_REQUIRED' if sum(n>=3 for n in support)>=2 and max(err[held])<=1 else 'RELATIVE_GEOMETRY_REJECTED')
    result['elapsed_ms']=(time.perf_counter()-start)*1000
    return result
