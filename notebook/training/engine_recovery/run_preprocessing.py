"""Run frozen recovery over all candidates without altering original evidence."""
from collections import Counter
from datetime import datetime,timezone
import json
import time

import cv2
import numpy as np
import torch

from fit_train import OUTPUT
from investigate import BASELINE,diagnostic
from recovery import RecoveryPreprocessor
from preprocess import PARTS,read_image,write_image,sha
from prepare_alignment import read_rows,sheet
from process_dataset import dump,alignment_checks
from src.vision.engine_rectification import rectify_image


def jsonl(path,rows):
    path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')


def safety_checks(processor,train):
    checks=alignment_checks(processor)
    reference=processor.estimator.reference
    # A deliberately wrong transform must not pass the unchanged body anchor.
    wrong=cv2.getRotationMatrix2D((670,360),180,1)
    bad=rectify_image(reference,wrong,processor.cfg)
    score=processor.check_direction(bad)
    assert score<.35,score
    checks['forced_180_degree_rejected']=dict(score=score,threshold=.35)
    # Synthetic hand-like full-body occlusion tests pipeline rejection, not a claim
    # of a general hand detector. Real hand robustness still requires new testing.
    covered=reference.copy()
    cv2.ellipse(covered,(670,340),(240,320),0,0,360,(130,175,210),-1)
    result,_,crops=processor.process(covered)
    assert not crops and result['status']=='FAILED',result
    write_image(OUTPUT/'safety/synthetic_body_occlusion.png',covered)
    checks['synthetic_body_occlusion']=dict(status=result['status'],reason=result['reason'],not_real_hand_validation=True)
    missing=next(r for r in train if r['display_index']=='T0189')
    result,canonical,crops=processor.process(read_image(missing['raw_image_path']))
    assert len(crops)==4 and all(v=='MISSING' for v in missing['approved_part_states'].values())
    checks['actual_missing_T0189_preserved']=True
    write_image(OUTPUT/'safety/T0189_missing.png',sheet(read_image(missing['raw_image_path']),canonical,crops,missing,result))
    # Actual source truncation at the left connection is rejected even though
    # the remaining crop is nonempty. This checks geometry, independent of YOLO.
    shifted=np.array([[1.,0.,-550.],[0.,1.,0.]])
    source=cv2.warpAffine(reference,shifted,(1280,720),borderValue=(40,40,40))
    aligned=rectify_image(source,shifted,processor.cfg)
    result,_,crops=processor.extract(source,aligned,shifted,{})
    assert 'pipe_left' not in crops and result['parts']['pipe_left']['reason']=='ESSENTIAL_REGION_OUT_OF_SOURCE'
    checks['synthetic_true_connection_truncation_rejected']=result['parts']['pipe_left']
    dump(OUTPUT/'safety_checks.json',checks)
    print('SAFETY PASS',flush=True)


def main():
    assert not (OUTPUT/'preprocessing_records.jsonl').exists(),'Keep completed runs immutable'
    processor=RecoveryPreprocessor(OUTPUT/'alignment/config_frozen.json')
    config_hash=sha(processor.path)
    rows=read_rows(BASELINE/'export_train_candidates.jsonl')+read_rows(BASELINE/'export_validation_candidates.jsonl')
    safety_checks(processor,[r for r in rows if r['split']=='TRAIN'])
    old={r['capture_id']:r for r in read_rows(OUTPUT/'baseline_reproduced_records.jsonl')}
    records=[];manifests={p:[] for p in PARTS}
    for index,row in enumerate(rows):
        assert sha(row['raw_image_path'])==row['raw_sha256']
        raw=read_image(row['raw_image_path'])
        torch.cuda.synchronize();started=time.perf_counter()
        result,canonical,crops=processor.process(raw)
        torch.cuda.synchronize();elapsed=(time.perf_counter()-started)*1000
        identity={k:row.get(k) for k in ['split','collection_id','session_id','capture_id','display_index','raw_image_path','raw_sha256',
            'source_group_id','collection_round_id','lineage_root_id','supersedes_capture_id']}
        result.update(identity);result.update(alignment_config_sha256=config_hash,preprocessing_ms=elapsed)
        records.append(result)
        for part in PARTS:
            detail=result['parts'].get(part,dict(status='FAILED',reason=result['reason']))
            record=dict(**identity,part=part,approved_state=row['approved_part_states'][part],**detail,
                alignment_transform=result.get('pose'),alignment_config_sha256=config_hash,
                preprocessing_version=processor.version,crop_path=None,crop_sha256=None,
                human_reviewed=False,training_accepted=False,selected_for_recovery_experiment=part in crops,
                label_source='approved_part_states; Codex reviewed; not independent human ground truth')
            if part in crops:
                path=OUTPUT/'crops'/row['split']/part/(row['capture_id']+'.png')
                record['crop_sha256']=write_image(path,crops[part]);record['crop_path']=str(path)
            manifests[part].append(record)
        if result['pose_route']=='TRAIN_BODY_BANK' or (row['split']=='VALIDATION' and old[row['capture_id']]['status']!='VALID'):
            write_image(OUTPUT/'recovery_reviews'/(row['display_index']+'.png'),sheet(raw,canonical,crops,row,result))
        if index%100==0 or index==len(rows)-1:print(index+1,len(rows),result['status'],result['pose_route'],flush=True)
    jsonl(OUTPUT/'preprocessing_records.jsonl',records)
    for part,items in manifests.items():
        for split in ('TRAIN','VALIDATION'):jsonl(OUTPUT/f'{part}_{split.lower()}_crop_manifest.jsonl',[r for r in items if r['split']==split])
    report=dict(config_sha256=config_hash,by_split={s:dict(inputs=sum(r['split']==s for r in records),
        statuses=dict(Counter(r['status'] for r in records if r['split']==s)),
        reasons=dict(Counter(r['reason'] for r in records if r['split']==s and r['reason'])),
        pose_routes=dict(Counter(r['pose_route'] for r in records if r['split']==s))) for s in ('TRAIN','VALIDATION')},
        by_part={p:{s:dict(valid=sum(r['status']=='VALID' for r in items if r['split']==s),
        classes=dict(Counter(r['approved_state'] for r in items if r['split']==s and r['status']=='VALID')),
        failure_reasons=dict(Counter(r['reason'] for r in items if r['split']==s and r['status']!='VALID'))) for s in ('TRAIN','VALIDATION')} for p,items in manifests.items()})
    dump(OUTPUT/'preprocessing_report.json',report)
    print(json.dumps(report['by_split']),flush=True)


if __name__=='__main__':main()
