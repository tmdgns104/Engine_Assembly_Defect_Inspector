"""Freeze TRAIN-only alignment after representative review, then process fixed inputs."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

import cv2
import numpy as np

from preprocess import BodyPreprocessor, PARTS, read_image, write_image, sha
from prepare_alignment import read_rows, sheet


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def alignment_checks(processor):
    ref = processor.estimator.reference
    cases = []
    # Erasing only inspected components must not reverse the body pose.
    erased = ref.copy()
    for x1,y1,x2,y2 in [(440,130,608,305),(722,130,906,305),(601,399,735,498),(631,295,708,366)]:
        erased[y1:y2,x1:x2] = 40
    points = np.array([[670,220],[670,570]], dtype=np.float64)
    for kind, source in [('intact',ref),('all_target_parts_erased',erased)]:
        for degrees in (0,37,90,180,270):
            matrix = cv2.getRotationMatrix2D((670,360),degrees,1)
            current = cv2.warpAffine(source,matrix,(1280,720),borderValue=(40,40,40))
            pose = processor.estimator.estimate(current,[0,0,1280,720])
            error = float(np.linalg.norm(np.c_[points,np.ones(2)] @ (pose.matrix-matrix).T,axis=1).max()) if pose.ok else None
            case = dict(kind=kind,rotation_ccw=degrees,pose_ok=pose.ok,max_landmark_error_px=error)
            assert pose.ok and error < 5, case
            cases.append(case)
    flat = processor.estimator.estimate(np.full_like(ref,40),[0,0,1280,720])
    assert not flat.ok
    return dict(status='PASS',synthetic_cases=cases,flat_image_rejected=True,
                note='Geometry tests are not classification/evaluation data.')


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('output'); args=parser.parse_args()
    output=Path(args.output)
    frozen=output/'alignment/config_frozen.json'
    assert not frozen.exists(), 'Do not overwrite an existing frozen run.'
    processor=BodyPreprocessor(output/'alignment/config_train_draft.json')
    checks=alignment_checks(processor)
    dump(output/'alignment/alignment_checks.json',checks)
    viewed=['T0001','T0040','T0078','T0115','T0152','T0189','T0227','T0301','T0373','T0445','T0517','T0590','T0662',
            'T0020','T0068','T0218','T0355','T0498','T0569','T0641','T0716']
    dump(output/'alignment/visual_review.json',dict(reviewer='codex',reviewed_at=datetime.now(timezone.utc).isoformat(),
         actual_sheets_opened=viewed,probe_count=52,conclusion='Fixed regions preserve connections, missing slots, misassembly and body rotation. No ROI change after viewing.',
         limitations='Representative visual check only; not independent human ground truth.'))
    cfg=processor.cfg.copy();cfg['frozen_at']=datetime.now(timezone.utc).isoformat()
    cfg['fit_source']='TRAIN only; T0001 reference and TRAIN representatives; no VALIDATION images used'
    dump(frozen,cfg)
    config_hash=sha(frozen)
    records=[]; manifests={part:[] for part in PARTS}
    for split,filename in [('TRAIN','export_train_candidates.jsonl'),('VALIDATION','export_validation_candidates.jsonl')]:
        rows=read_rows(output/filename)
        for index,row in enumerate(rows):
            raw=read_image(row['raw_image_path'])
            assert sha(row['raw_image_path'])==row['raw_sha256']
            try:
                result,canonical,crops=processor.process(raw)
            except Exception as exc:
                result=dict(status='FAILED',reason=f'PROCESS_EXCEPTION:{type(exc).__name__}:{exc}',parts={})
                canonical=None;crops={}
            identity={k:row.get(k) for k in ['split','collection_id','session_id','capture_id','display_index','raw_image_path','raw_sha256',
                       'source_group_id','collection_round_id','lineage_root_id','supersedes_capture_id']}
            result.update(identity);result['alignment_config_sha256']=config_hash
            records.append(result)
            for part in PARTS:
                state=row['approved_part_states'][part]
                detail=result['parts'].get(part,dict(status='FAILED',reason=result['reason']))
                record=dict(**identity,part=part,approved_state=state,**detail,
                            label_source='approved_part_states; Codex visual review; not independent human verification',
                            human_reviewed=False,training_accepted=False,selected_for_this_experiment=part in crops,
                            alignment_transform=result.get('pose'),alignment_config_sha256=config_hash,
                            preprocessing_version='fixed-slot-pad224-v1',crop_path=None,crop_sha256=None)
                if part in crops:
                    path=output/'crops'/part/('train' if split=='TRAIN' else 'val')/state/(row['capture_id']+'.png')
                    record['crop_sha256']=write_image(path,crops[part]);record['crop_path']=str(path.resolve())
                manifests[part].append(record)
            if result['status']!='VALID':
                write_image(output/'preprocessing_failures'/(row['display_index']+'.png'),sheet(raw,canonical,crops,row,result))
            if index%50==0 or index==len(rows)-1:
                print(split,index+1,len(rows),result['status'],flush=True)
    for part,rows in manifests.items():
        for split in ('TRAIN','VALIDATION'):
            path=output/f'{part}_{split.lower()}_crop_manifest.jsonl'
            path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows if r['split']==split),encoding='utf-8')
    (output/'preprocessing_records.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),encoding='utf-8')
    report=dict(config_sha256=config_hash,reference_feature_count=len(processor.estimator.ref_kp),alignment_checks=checks,
                by_split={s:dict(inputs=sum(r['split']==s for r in records),statuses=dict(Counter(r['status'] for r in records if r['split']==s)),
                    reasons=dict(Counter(r['reason'] for r in records if r['split']==s and r['reason']))) for s in ('TRAIN','VALIDATION')},
                by_part={p:{s:dict(valid=sum(r['status']=='VALID' for r in rs if r['split']==s),
                          classes=dict(Counter(r['approved_state'] for r in rs if r['split']==s and r['status']=='VALID')),
                          failure_reasons=dict(Counter(r['reason'] for r in rs if r['split']==s and r['status']!='VALID'))) for s in ('TRAIN','VALIDATION')} for p,rs in manifests.items()})
    dump(output/'preprocessing_report.json',report)
    print(json.dumps(report['by_split']),flush=True)


if __name__=='__main__':main()
