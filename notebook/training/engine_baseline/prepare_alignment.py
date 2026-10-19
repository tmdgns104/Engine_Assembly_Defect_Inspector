"""Create TRAIN-only registration configuration and representative review sheets."""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil

import cv2
import numpy as np

from preprocess import PROJECT, PARTS, BodyPreprocessor, read_image, sha, write_image


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def sheet(raw,canonical,crops,row,evidence):
    canvas=np.full((640,1120,3),35,np.uint8)
    for image,x,title in [(raw,0,'ORIGINAL'),(canonical,560,'BODY ALIGNED')]:
        if image is not None:
            canvas[38:353,x:x+560]=cv2.resize(image,(560,315))
        cv2.putText(canvas,title,(x+10,25),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),1)
    for i,part in enumerate(PARTS):
        x=i*280
        if part in crops:
            canvas[395:619,x+20:x+244]=crops[part]
        label=part+' / '+row['approved_part_states'][part]
        cv2.putText(canvas,label,(x+5,380),cv2.FONT_HERSHEY_SIMPLEX,.42,(180,240,255),1)
    cv2.putText(canvas,row['display_index']+' '+str(evidence.get('reason') or 'VALID'),(10,636),cv2.FONT_HERSHEY_SIMPLEX,.43,(255,255,255),1)
    return canvas


def main():
    parser=argparse.ArgumentParser();parser.add_argument('output');args=parser.parse_args()
    output=Path(args.output); config_dir=output/'alignment';config_dir.mkdir(exist_ok=True)
    rows=read_rows(output/'export_train_candidates.jsonl')
    reference=next(r for r in rows if r['display_index']=='T0001')
    assert all(s=='CORRECT' for s in reference['approved_part_states'].values())
    path=config_dir/'reference_T0001.png'
    if not path.exists():shutil.copyfile(reference['raw_image_path'],path)
    config=dict(schema_version='body-fixed-train-v1',reference_id=reference['capture_id'],reference_image=path.name,
                reference_image_sha256=sha(path),reference_split='TRAIN',frame_width=1280,frame_height=720,
                canonical_orientation='Long gold shaft down, short up; engine-fixed left/right; same direction as runtime D001',
                canonical_product_box_xyxy=[475,50,860,690],
                registration=dict(orb_nfeatures=5000,orb_nlevels=8,orb_fast_threshold=7,ratio_test=.75,
                                  min_good_matches=12,min_inliers=10,min_inlier_ratio=.25,
                                  max_median_reprojection_error_px=3.0,min_scale=.65,max_scale=1.45),
                decision_policy=dict(product_confidence=.5),
                fixed_body_feature_regions_xyxy=[[620,197,709,280],[490,344,580,431],[743,344,835,432],[642,530,698,678],[646,64,697,151]],
                orientation_anchor_xyxy=[625,202,704,274],min_orientation_anchor_correlation=.35,
                crop_regions_xyxy=dict(pipe_left=[426,96,625,345],pipe_right=[709,96,922,345],exhaust=[569,373,764,524],symbol=[599,282,735,392]),
                preprocessing=dict(size=224,padding_bgr=[40,40,40],resize='symmetric_square_pad_then_bilinear',part_orientation_correction=False),
                envelope_detector=dict(path='runs/engine_dynamic_pose_002/training/envelope_v004/weights/best.pt',
                                       sha256='cf117defe782e1ae8b355e0ed13c014fc6f1538aa2dcdbe0fb6cfa54200f7755',
                                       preprocessing=json.loads((PROJECT/'jetson/products/ENGINE_Z3005_5/envelope_v007_fp16/preprocessing.json').read_text(encoding='utf-8'))))
    cfg_path=config_dir/'config_train_draft.json'
    cfg_path.write_text(json.dumps(config,indent=2),encoding='utf-8')
    processor=BodyPreprocessor(cfg_path)
    print('REFERENCE_FEATURES',len(processor.estimator.ref_kp),flush=True)
    # Labels choose review examples only; the processing function receives image pixels alone.
    groups={}
    for row in rows:
        key=tuple(row['approved_part_states'][part] for part in PARTS)
        groups.setdefault(key,[]).append(row)
    representatives=[]
    for group in groups.values():
        for index in sorted({0,len(group)//4,len(group)//2,3*len(group)//4}):
            representatives.append(group[index])
    results=[]
    for i,row in enumerate(representatives):
        raw=read_image(row['raw_image_path'])
        result,canonical,crops=processor.process(raw)
        result.update(display_index=row['display_index'],capture_id=row['capture_id'],approved_part_states=row['approved_part_states'])
        write_image(output/'representatives'/f"{row['display_index']}.png",sheet(raw,canonical,crops,row,result))
        results.append(result)
        print(i+1,row['display_index'],result['status'],result['reason'],result.get('orientation_anchor_correlation'),flush=True)
    (output/'alignment/train_probe_results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(dict(total=len(results),statuses=dict(Counter(r['status'] for r in results)),reasons=dict(Counter(r['reason'] for r in results)))) ,flush=True)


if __name__=='__main__':main()
