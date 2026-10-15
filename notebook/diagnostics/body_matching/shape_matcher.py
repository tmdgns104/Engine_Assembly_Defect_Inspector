"""Bounded orientation-chamfer search of real fixed-body edges, offline only.

OpenCV Canny is computed BEFORE masking. Thus rectangular annotation boundaries
cannot become template edges. Each physical region has equal weight. This is
not a general-purpose industrial shape engine or GeneralizedHoughGuil clone.
"""
import math
import time

import cv2
import numpy as np

from geometry import body_regions, transform


def edge_maps(im):
    gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    smooth=cv2.GaussianBlur(gray,(3,3),.8)
    edges=cv2.Canny(smooth,50,130)
    gx=cv2.Sobel(smooth,cv2.CV_32F,1,0)
    gy=cv2.Sobel(smooth,cv2.CV_32F,0,1)
    angles=np.mod(np.arctan2(gy,gx),np.pi)
    return edges,angles


class ShapeBodyMatcher:
    def __init__(self,reference,profile):
        self.profile=profile
        labels=body_regions(reference.shape,profile)
        edges,angles=edge_maps(reference)
        self.center=np.array([667.,345.])
        self.points=[];self.angles=[];self.regions=[]
        for region in range(1,len(profile['body_regions'])+1):
            y,x=np.nonzero((labels==region)&(edges!=0))
            # Bounded, spatially uniform sample of genuine unmasked-image edges.
            used=set();chosen=[]
            for i,(xx,yy) in enumerate(zip(x,y)):
                cell=(xx//3,yy//3)
                if cell not in used:
                    used.add(cell);chosen.append(i)
            chosen=np.asarray(chosen,dtype=int)
            self.points.extend(np.c_[x[chosen],y[chosen]])
            self.angles.extend(angles[y[chosen],x[chosen]])
            self.regions.extend([region]*len(chosen))
        self.points=np.asarray(self.points,float)
        self.angles=np.asarray(self.angles,float)
        self.regions=np.asarray(self.regions,int)
        self.count=len(profile['body_regions'])
        self.weights=np.array([1/max(1,np.sum(self.regions==r))/self.count for r in self.regions])

    @staticmethod
    def distances(im):
        edges,angles=edge_maps(im)
        maps=[]
        for b in range(6):
            delta=np.abs((angles-b*np.pi/6+np.pi/2)%np.pi-np.pi/2)
            selected=(edges>0)&(delta<=np.pi/8)
            maps.append(np.minimum(cv2.distanceTransform((~selected).astype(np.uint8),cv2.DIST_L2,3),10))
        return np.stack(maps)

    def matrix(self,parameters):
        x,y,angle,scale=parameters
        a=angle*np.pi/180
        linear=scale*np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]])
        return np.c_[linear,np.array([x,y])-linear@self.center]

    def match(self,current):
        start=time.perf_counter()
        fraction=.25
        small=cv2.resize(current,None,fx=fraction,fy=fraction,interpolation=cv2.INTER_AREA)
        costs=self.distances(small)
        # MatchTemplate computes sum of direction-compatible distance costs at
        # every translation. Rotation/scale are finite, predeclared grids.
        coarse=[]
        for angle in self.profile['shape']['angles_deg']:
            theta=angle*np.pi/180
            rot=np.array([[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]])
            bins=np.rint(((self.angles+theta)%np.pi)*6/np.pi).astype(int)%6
            for scale in self.profile['shape']['scales']:
                p=(self.points-self.center)@rot.T*scale*fraction
                offset=np.floor(p.min(axis=0))-1
                q=np.rint(p-offset).astype(int)
                w,h=q.max(axis=0)+2
                if w>=small.shape[1] or h>=small.shape[0]:continue
                scores=np.zeros((small.shape[0]-h+1,small.shape[1]-w+1),np.float32)
                for b in range(6):
                    kernel=np.zeros((h,w),np.float32)
                    valid=bins==b
                    np.add.at(kernel,(q[valid,1],q[valid,0]),self.weights[valid])
                    if kernel.any():scores+=cv2.matchTemplate(costs[b],kernel,cv2.TM_CCORR)
                # Keep two separated translation minima, including possible
                # symmetry alternatives. Never only keep the visually nice fit.
                for _ in range(2):
                    location=cv2.minMaxLoc(scores)[2]
                    x,y=location;score=float(scores[y,x])
                    coarse.append((score,[(x-offset[0])/fraction,(y-offset[1])/fraction,angle,scale]))
                    cv2.circle(scores,location,12,100,-1)
        # Independent full-resolution distance computation for refinement.
        costs=self.distances(current)
        def sample(parameters):
            p=transform(self.points,self.matrix(parameters)).astype(np.float32)
            bins=np.rint(((self.angles+parameters[2]*np.pi/180)%np.pi)*6/np.pi).astype(int)%6
            result=np.full(len(p),10.,float)
            for b in range(6):
                keep=bins==b
                if keep.any():
                    result[keep]=cv2.remap(costs[b],p[keep,0].reshape(1,-1),p[keep,1].reshape(1,-1),
                        cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=10).ravel()
            return result
        candidates=[]
        for _,parameters in sorted(coarse,key=lambda row:row[0])[:16]:
            x,y,angle,scale=parameters
            values=np.array(parameters,float)
            steps=np.array([4.,4.,2.,.03])
            lower=np.array([x-16,y-16,angle-10,max(.5,scale-.12)])
            upper=np.array([x+16,y+16,angle+10,min(1.5,scale+.12)])
            cost=float(np.sum(sample(values)*self.weights))
            # Bounded four-parameter coordinate descent; no new optimizer
            # dependency and no unbounded search on full-resolution pixels.
            for _ in range(25):
                improved=False
                for axis in range(4):
                    for direction in (-1,1):
                        proposal=values.copy();proposal[axis]+=direction*steps[axis]
                        if np.any(proposal<lower) or np.any(proposal>upper):continue
                        score=float(np.sum(sample(proposal)*self.weights))
                        if score<cost:
                            values,cost=proposal,score;improved=True
                if not improved:steps*=.5
                if steps[0]<.05:break
            distances=sample(values)
            fractions=[float(np.mean(distances[self.regions==r]<=3)) if np.any(self.regions==r) else 0 for r in range(1,self.count+1)]
            row=dict(matrix=self.matrix(values),cost=cost,parameters=values,
                     region_edge_fraction_within_3px=fractions,
                     support=[int(np.sum(distances[self.regions==r]<=3)) for r in range(1,self.count+1)],
                     reason='BODY_GEOMETRY_CANDIDATE' if sum(f>=.65 for f in fractions)>=3 else 'INSUFFICIENT_EDGE_AGREEMENT')
            if not any(np.max(np.linalg.norm(transform(self.points,row['matrix'])-transform(self.points,c['matrix']),axis=1))<8 for c in candidates):
                candidates.append(row)
        candidates.sort(key=lambda r:r['cost'])
        best=candidates[0]
        ambiguous=len(candidates)>1 and candidates[1]['cost'] <= best['cost']*1.05+.05
        if ambiguous:best['reason']='AMBIGUOUS_SHAPE'
        return dict(method='B_ORIENTED_CHAMFER',best=best,alternatives=candidates[1:5],ambiguous=ambiguous,
                    template_edge_samples=len(self.points),elapsed_ms=(time.perf_counter()-start)*1000,
                    validation='CANDIDATE_ONLY_REQUIRES_INDEPENDENT_GEOMETRY_AND_CROP_CHECK')
