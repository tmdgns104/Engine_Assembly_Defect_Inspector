"""Freeze baseline evidence, reproduce preprocessing and render failure diagnostics."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

PROJECT=Path(__file__).resolve().parents[3]
BASELINE=PROJECT/'runs/engine_misassembly_baseline_training_001/v001_20261002T191929Z'
sys.path.insert(0,str(PROJECT/'notebook/training/engine_baseline'))
from preprocess import BodyPreprocessor,PARTS,read_image,write_image,sha
from prepare_alignment import read_rows
from process_dataset import dump
from src.vision.engine_rectification import rectify_image


def diagnostic(row,record,config,output):
    raw=read_image(row['raw_image_path']);pose=record.get('pose',{});matrix=pose.get('matrix')
    canvas=np.full((720,1440,3),30,np.uint8)
    cv2.putText(canvas,row['display_index']+' '+record['status']+' '+str(record['reason']),(10,25),cv2.FONT_HERSHEY_SIMPLEX,.57,(255,255,255),1)
    canvas[48:453,0:720]=cv2.resize(raw,(720,405))
    if matrix is not None:
        matrix=np.array(matrix)
        canonical=rectify_image(raw,matrix,config)
        support=cv2.warpAffine(np.ones(raw.shape[:2],np.uint8),cv2.invertAffineTransform(matrix),(1280,720),flags=cv2.INTER_NEAREST)
        annotated=canonical.copy();annotated[support==0]=(140,35,140)
        for part,box in config['crop_regions_xyxy'].items():
            x1,y1,x2,y2=box;cv2.rectangle(annotated,(x1,y1),(x2,y2),(0,220,255),2)
            cv2.putText(annotated,part,(x1,y1-6),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,255,255),1)
        canvas[48:453,720:1440]=cv2.resize(annotated,(720,405))
        for i,part in enumerate(PARTS):
            x1,y1,x2,y2=config['crop_regions_xyxy'][part]
            region=annotated[y1:y2,x1:x2]
            from preprocess import padded_224
            canvas[486:710,i*360+55:i*360+279]=padded_224(region)
            detail=record.get('parts',{}).get(part,{})
            label=part+' '+row['approved_part_states'][part]+' cov='+str(round(detail.get('source_coverage',0),5))
            cv2.putText(canvas,label,(i*360+5,476),cv2.FONT_HERSHEY_SIMPLEX,.39,(255,255,255),1)
    write_image(output/'diagnostics'/(row['display_index']+'.png'),canvas)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output');args=parser.parse_args()
    output=Path(args.output).resolve() if args.output else PROJECT/'runs/engine_preprocessing_recovery_001'/('v001_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    output.mkdir(parents=True,exist_ok=False)
    # Capture immutable experiment artifacts; active local viewer logs are not experiment evidence.
    baseline_files=[p for p in BASELINE.rglob('*') if p.is_file() and p.suffix not in ('.log','.cache')]
    protected={str(p):dict(sha256=sha(p),bytes=p.stat().st_size) for p in baseline_files}
    labelroot=PROJECT/'data/guided_capture_20261001'
    for name in ['labeling_review_manifest.jsonl','export_train_candidates.jsonl','export_validation_candidates.jsonl','labeling_unresolved_cases.jsonl']:
        p=labelroot/name;protected[str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size)
    for p in (PROJECT/'notebook/training/engine_baseline').glob('*'):
        if p.is_file():protected[str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size)
    dump(output/'protected_hashes_before.json',protected)
    rows=read_rows(BASELINE/'export_train_candidates.jsonl')+read_rows(BASELINE/'export_validation_candidates.jsonl')
    baseline={r['capture_id']:r for r in read_rows(BASELINE/'preprocessing_records.jsonl')}
    fixed={s:[r['capture_id'] for r in rows if r['split']==s] for s in ('TRAIN','VALIDATION')}
    fixed.update(validation_success_110=[cid for cid in fixed['VALIDATION'] if baseline[cid]['status']=='VALID'],
                 validation_failure_45=[cid for cid in fixed['VALIDATION'] if baseline[cid]['status']!='VALID'])
    dump(output/'fixed_populations.json',fixed)
    dump(output/'run.json',dict(task='ENGINE-PREPROCESSING-RECOVERY-001',baseline=str(BASELINE),output=str(output),
         created_at=datetime.now(timezone.utc).isoformat(),classification_models_frozen=True,retraining=False))
    print('OUTPUT',output,flush=True)
    processor=BodyPreprocessor(BASELINE/'alignment/config_frozen.json')
    crop_records={(r['capture_id'],p):r for p in PARTS for s in ('train','validation') for r in read_rows(BASELINE/f'{p}_{s}_crop_manifest.jsonl')}
    reproduction=[];diffs=[]
    for i,row in enumerate(rows):
        assert sha(row['raw_image_path'])==row['raw_sha256']
        actual,canonical,crops=processor.process(read_image(row['raw_image_path']))
        original=baseline[row['capture_id']]
        mismatches=[]
        if (actual['status'],actual['reason'])!=(original['status'],original['reason']):mismatches.append('STATUS_OR_REASON')
        for part in PARTS:
            old=crop_records[row['capture_id'],part]
            if (part in crops)!=(old['status']=='VALID'):mismatches.append(part+'_AVAILABILITY')
            elif part in crops:
                ok,encoded=cv2.imencode('.png',crops[part]);assert ok
                if hashlib.sha256(encoded.tobytes()).hexdigest()!=old['crop_sha256']:mismatches.append(part+'_PIXELS')
        if mismatches:diffs.append(dict(id=row['display_index'],differences=mismatches))
        actual.update(capture_id=row['capture_id'],display_index=row['display_index'],split=row['split'])
        reproduction.append(actual)
        if row['split']=='VALIDATION' and original['status']!='VALID':diagnostic(row,original,processor.cfg,output)
        if i%100==0:print(i+1,len(rows),'differences',len(diffs),flush=True)
    (output/'baseline_reproduced_records.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in reproduction),encoding='utf-8')
    summary=dict(status='PASS' if not diffs else 'MISMATCH',rows=len(rows),differences=diffs,
                 by_split={s:dict(Counter(r['status'] for r in reproduction if r['split']==s)) for s in fixed if s in ('TRAIN','VALIDATION')})
    dump(output/'baseline_reproduction_verification.json',summary)
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
