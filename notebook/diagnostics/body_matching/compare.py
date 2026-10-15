"""Run one predeclared candidate on saved originals. No live-device access."""
import argparse
import time
from pathlib import Path

import cv2
import numpy as np

from geometry import image, read_json, write_json, sha, transform


def main():
    ap=argparse.ArgumentParser();ap.add_argument('work',type=Path);ap.add_argument('--method',choices=['B','C'],required=True)
    ap.add_argument('--names',nargs='*');ap.add_argument('--mode',default='full');ap.add_argument('--synthetic',action='store_true')
    args=ap.parse_args();work=args.work
    profile=read_json(work/'PROFILE.json');manifest=read_json(work/'MANIFEST.json')
    assert sha(work/'PROFILE.json')==manifest['profile_sha256']
    cv2.setNumThreads(1)
    reference=image(profile['reference']);assert sha(profile['reference'])==profile['reference_sha256']
    if args.method=='B':
        from shape_matcher import ShapeBodyMatcher
        matcher=ShapeBodyMatcher(reference,profile)
    else:
        from loftr_matcher import LearnedBodyMatcher
        checkpoint=Path(profile['loftr'].get('checkpoint_path',work/'loftr_indoor_ds_new.ckpt'))
        assert sha(checkpoint)==profile['loftr']['weights']['sha256']
        matcher=LearnedBodyMatcher(reference,profile,checkpoint)
    jobs=[]
    if args.synthetic:
        for name,angle,scale,dx,dy in [('self',0,1,0,0),('translate',0,1,-70,30),('rot25',25,1,0,0),
                                    ('rot90',90,1,0,0),('rot_minus90',-90,.85,0,0),('rot160',160,.85,0,0)]:
            matrix=cv2.getRotationMatrix2D((667,345),angle,scale);matrix[:,2]+=[dx,dy]
            raw=reference.copy() if name=='self' else cv2.warpAffine(reference,matrix,(1280,720),borderValue=(40,40,40))
            jobs.append((dict(name=name,group='synthetic',known=matrix),raw))
        jobs.extend([(dict(name='mirror',group='negative'),cv2.flip(reference,1)),
                     (dict(name='blank',group='negative'),np.full_like(reference,40))])
    else:
        for r in manifest['records']:
            if args.names and r['name'] not in args.names:continue
            assert sha(r['path'])==r['raw_sha256']
            jobs.append((r,image(r['path'])))
    corners=np.concatenate([np.array([[x1,y1],[x2,y1],[x2,y2],[x1,y2]]) for x1,y1,x2,y2 in profile['crop_regions'].values()])
    manual=read_json(work/'MANUAL_CHECKS.json')
    output=work/(args.method+'_'+args.mode);output.mkdir(exist_ok=True)
    for row,raw in jobs:
        result=matcher.match(raw) if args.method=='B' else matcher.match(raw,args.mode)
        result.update(name=row['name'],frame_id=row.get('frame_id'),group=row['group'],profile_sha256=sha(work/'PROFILE.json'),
                      raw_sha256=row.get('raw_sha256'),classifier_used_for_alignment=False)
        best=result['best'];matrix=best.get('matrix')
        if matrix is not None:
            if 'known' in row:
                result['known_transform']=row['known']
                result['synthetic_crop_corner_errors_px']=np.linalg.norm(transform(corners,matrix)-transform(corners,row['known']),axis=1)
            if row['group'] in manual['groups']:
                result['independent_landmark_errors_px']=np.linalg.norm(transform(manual['reference'],matrix)-np.array(manual['groups'][row['group']]),axis=1)
            overlay=raw.copy()
            for name,(x1,y1,x2,y2) in profile['crop_regions'].items():
                pts=transform([[x1,y1],[x2,y1],[x2,y2],[x1,y2]],matrix).round().astype(np.int32)
                cv2.polylines(overlay,[pts],True,(0,255,255),2)
                cv2.putText(overlay,name,tuple(pts[0]),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,0,255),2)
            cv2.imwrite(str(output/(row['name']+'_overlay.png')),overlay)
        write_json(output/(row['name']+'.json'),result)
        errors=result.get('synthetic_crop_corner_errors_px',result.get('independent_landmark_errors_px'))
        print(row['name'],best['reason'],best['support'],round(result['elapsed_ms']),
              'error_max',None if errors is None else round(float(max(errors)),2),flush=True)
    write_json(output/'RUN.json',dict(method=args.method,mode=args.mode,jobs=[r[0]['name'] for r in jobs],
        load_ms=getattr(matcher,'load_ms',None),code_sha256={p.name:sha(p) for p in Path(__file__).parent.glob('*.py')},
        profile_sha256=sha(work/'PROFILE.json'),classification='NOT_RUN',production_changed=False))


if __name__=='__main__':main()
