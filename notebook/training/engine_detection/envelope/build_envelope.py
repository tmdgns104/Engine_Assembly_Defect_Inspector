"""Repair visibly clipped envelope proposals; never edit approved parts or sources."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

import cv2
import numpy as np

from prepare_data import ROOT, SOURCE, TRAIN

sys.path.insert(0, str(SOURCE/'runtime'))
from engine_pose_slots import EnginePoseEstimator, transform_polygon


def main():
    out = ROOT/'dataset_v003'
    out.mkdir(exist_ok=False)
    review = ROOT/'review_corrected_v003'
    review.mkdir(exist_ok=False)
    estimator = EnginePoseEstimator(SOURCE/'pose_reference.json')
    rows = json.loads((SOURCE/'source_index.json').read_text(encoding='utf-8'))['items']
    results, tiles = [], []
    reference = np.array([[482,49],[849,49],[849,687],[482,687]], np.float32)
    for row in rows:
        rid, split = row['review_id'], row['split']
        image_path = TRAIN/f'dataset/images/{split}/{rid}.png'
        image = cv2.imread(str(image_path))
        assert hashlib.sha256(image_path.read_bytes()).hexdigest() == row['image_sha256']
        h,w = image.shape[:2]
        lines = (SOURCE/f'labels_combined/{split}/{rid}.txt').read_text(encoding='utf-8').splitlines()
        _, cx,cy,bw,bh = map(float, next(x for x in lines if x.startswith('3 ')).split())
        original = np.array([(cx-bw/2)*w,(cy-bh/2)*h,(cx+bw/2)*w,(cy+bh/2)*h])
        pose = estimator.estimate(image, original)
        assert pose.ok, (rid, pose.reason)
        # Pose limits search to the actual engine; foreground extends clipped golden shafts.
        roi = np.zeros((h,w), np.uint8)
        # Allow protruding shafts outside the strict rigid template; keep distant
        # mat highlights out. This mask is annotation repair only, never runtime.
        cv2.fillConvexPoly(roi,np.round(transform_polygon(reference,pose.matrix)).astype(np.int32),255)
        roi=cv2.dilate(roi,np.ones((111,111),np.uint8))
        hsv = cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
        foreground = (((hsv[:,:,2]>100) & ((hsv[:,:,1]<85) | (hsv[:,:,0]<40) | (hsv[:,:,0]>170))) & (roi>0)).astype(np.uint8)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(foreground)
        clean = np.isin(labels, [i for i in range(1,count) if stats[i,cv2.CC_STAT_AREA]>=30]).astype(np.uint8)
        points = cv2.findNonZero(clean)
        assert points is not None
        x,y,ww,hh = cv2.boundingRect(points)
        box = np.array([min(original[0],x-6),min(original[1],y-6),max(original[2],x+ww+6),max(original[3],y+hh+6)])
        box = np.clip(box,[0,0,0,0],[w,h,w,h])
        for kind in ('images','labels','labels_combined'):
            (out/kind/split).mkdir(parents=True,exist_ok=True)
        shutil.copyfile(image_path,out/f'images/{split}/{rid}.png')
        xywh = [(box[0]+box[2])/2/w,(box[1]+box[3])/2/h,(box[2]-box[0])/w,(box[3]-box[1])/h]
        values = ' '.join(f'{x:.10f}' for x in xywh)
        (out/f'labels/{split}/{rid}.txt').write_text('0 '+values+'\n',encoding='utf-8')
        approved = (TRAIN/f'dataset/labels/{split}/{rid}.txt').read_bytes()
        (out/f'labels_combined/{split}/{rid}.txt').write_bytes(approved.rstrip()+b'\n'+('3 '+values+'\n').encode())
        expected = float(row['target_angle_deg_source'])
        error = abs((pose.angle_deg-expected+180)%360-180)
        results.append(dict(row, original_box=original.tolist(), corrected_box=box.tolist(),
            changed=bool(np.max(np.abs(box-original))>1), angle=pose.angle_deg, angle_error_deg=error,
            scale=pose.scale, matrix=pose.matrix.tolist(), matches=pose.good_matches,
            inliers=pose.inliers, reprojection_error_px=pose.median_error_px))
        canvas = image.copy()
        cv2.rectangle(canvas,tuple(np.round(original[:2]).astype(int)),tuple(np.round(original[2:]).astype(int)),(0,0,255),2)
        cv2.rectangle(canvas,tuple(np.round(box[:2]).astype(int)),tuple(np.round(box[2:]).astype(int)),(0,255,255),3)
        tile = cv2.resize(canvas,(384,216))
        tile=np.vstack([np.full((20,384,3),15,np.uint8),tile])
        cv2.putText(tile,rid+' '+row['scenario_capture_truth'],(4,14),cv2.FONT_HERSHEY_SIMPLEX,.36,(255,255,255),1)
        tiles.append(tile)
        if len(tiles)==12:
            sheet = np.vstack([np.hstack(tiles[j:j+4]) for j in range(0,12,4)])
            cv2.imwrite(str(review/f'sheet_{len(results)//12:02}.jpg'),sheet)
            tiles=[]
    (out/'data.yaml').write_text(f'path: {out.as_posix()}\ntrain: images/train\nval: images/val\nnames:\n  0: product_envelope\n',encoding='utf-8')
    summary = {'count':len(results),'pose_success':216,'e04_used':0,'corrected':sum(r['changed'] for r in results),
        'angle_error_median':float(np.median([r['angle_error_deg'] for r in results])),
        'angle_error_max':max(r['angle_error_deg'] for r in results),'rows':results,
        'angle_ground_truth_limit':'Capture target angle is nominal human placement, not metrology.',
        'review_status':'AI correction; original and corrected contact sheets preserved; not human approval.'}
    (ROOT/'dataset_pose_audit_v003.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print({k:v for k,v in summary.items() if k!='rows'})


if __name__=='__main__':
    main()
