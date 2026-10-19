"""Evaluate all 155 development cases with the four unchanged baseline models."""
from collections import Counter
import json
import time

import numpy as np
import torch
from ultralytics import YOLO

from fit_train import OUTPUT
from investigate import BASELINE
from recovery import RecoveryPreprocessor
from preprocess import PARTS,read_image,sha
from classification import FixedPredictor
from prepare_alignment import read_rows
from process_dataset import dump
from evaluate_models import metrics_for,ratio
from run_preprocessing import jsonl


def predict(model,images):
    return model.predict(images,predictor=FixedPredictor,imgsz=224,device=0,quantize=32,verbose=False)


def main():
    assert not (OUTPUT/'validation_predictions.jsonl').exists(),'Preserve completed evaluation'
    models={};predictions=[];part_metrics={}
    fixed=json.loads((OUTPUT/'fixed_populations.json').read_text(encoding='utf-8'))
    old_predictions={(r['capture_id'],r['part']):r for r in read_rows(BASELINE/'validation_predictions.jsonl')}
    before={r['capture_id']:r for r in read_rows(OUTPUT/'baseline_reproduced_records.jsonl')}
    after={r['capture_id']:r for r in read_rows(OUTPUT/'preprocessing_records.jsonl')}
    for part in PARTS:
        weight=BASELINE/'full'/part/'weights/best.pt'
        model=YOLO(str(weight));models[part]=model
        names=[model.names[i] for i in range(len(model.names))]
        dump(OUTPUT/f'{part}_class_mapping.json',{str(i):name for i,name in enumerate(names)})
        manifest=read_rows(OUTPUT/f'{part}_validation_crop_manifest.jsonl')
        valid=[r for r in manifest if r['status']=='VALID'];results_by_id={}
        for start in range(0,len(valid),16):
            batch=valid[start:start+16]
            for row,result in zip(batch,predict(model,[read_image(r['crop_path']) for r in batch])):
                scores=result.probs.data.cpu().numpy()
                assert np.isfinite(scores).all() and abs(float(scores.sum())-1)<1e-5
                results_by_id[row['capture_id']]=(names[int(scores.argmax())],dict(zip(names,map(float,scores))))
        part_rows=[]
        for row in manifest:
            label,scores=results_by_id.get(row['capture_id'],(None,None))
            part_rows.append(dict(**row,predicted_state=label,class_scores=scores,
                preprocessing_status=row['status'],preprocessing_reason=row['reason'],
                prediction_status='PREDICTED' if label is not None else 'PREPROCESSING_FAILED',
                model_path=str(weight),model_sha256=sha(weight),model_version=BASELINE.name+'/'+part,
                evaluation_scope='DEVELOPMENT_REGRESSION_VALIDATION',retrained=False))
        part_metrics[part]=metrics_for(part_rows,names)
        part_metrics[part]['subsets']={}
        for key,ids in [('original_success_110',fixed['validation_success_110']),('original_failure_45',fixed['validation_failure_45'])]:
            part_metrics[part]['subsets'][key]=metrics_for([r for r in part_rows if r['capture_id'] in ids],names)
        predictions.extend(part_rows)
        print(part,part_metrics[part]['predicted_count'],part_metrics[part]['accuracy'],flush=True)
    jsonl(OUTPUT/'validation_predictions.jsonl',predictions)
    by_id={cid:{r['part']:r for r in predictions if r['capture_id']==cid} for cid in fixed['VALIDATION']}
    sources=read_rows(BASELINE/'export_validation_candidates.jsonl')
    simulation=[];changes=[]
    for source in sources:
        cid=source['capture_id'];parts=by_id[cid]
        complete=all(r['prediction_status']=='PREDICTED' for r in parts.values())
        truth=source['approved_part_states'];any_defect=any(v!='CORRECT' for v in truth.values())
        all_normal=complete and all(r['predicted_state']=='CORRECT' for r in parts.values())
        simulation.append(dict(capture_id=cid,display_index=source['display_index'],all_parts_available=complete,
            true_any_defect=any_defect,true_any_misassembly=any(v not in ('CORRECT','MISSING') for v in truth.values()),
            simulation_output='NO_DECISION_PREPROCESSING_FAILED' if not complete else 'ALL_CORRECT' if all_normal else 'DEFECT_DETECTED',
            dangerous_all_correct=any_defect and all_normal,approved_part_states=truth,
            predicted_part_states={p:r['predicted_state'] for p,r in parts.items()}))
        changes.append(dict(capture_id=cid,display_index=source['display_index'],
            subset='original_success_110' if cid in fixed['validation_success_110'] else 'original_failure_45',
            before_status=before[cid]['status'],after_status=after[cid]['status'],after_reason=after[cid]['reason'],
            recovered=before[cid]['status']!='VALID' and after[cid]['status']=='VALID',
            pose_route=after[cid]['pose_route'],approved_part_states=truth,
            parts={p:dict(before_prediction=old_predictions[cid,p]['predicted_state'],after_prediction=parts[p]['predicted_state'],
                before_crop_sha256=old_predictions[cid,p]['crop_sha256'],after_crop_sha256=parts[p]['crop_sha256'],
                same_input=old_predictions[cid,p]['crop_sha256']==parts[p]['crop_sha256'],
                wrong=parts[p]['predicted_state'] is not None and parts[p]['predicted_state']!=truth[p]) for p in PARTS}))
    jsonl(OUTPUT/'classifier_only_simulation.jsonl',simulation)
    jsonl(OUTPUT/'case_changes.jsonl',changes)
    jsonl(OUTPUT/'validation_errors.jsonl',[r for r in changes if any(p['wrong'] for p in r['parts'].values())])
    sim=dict(scope='CLASSIFIER_ONLY_SIMULATION; not PLC/runtime/3-frame test',total_candidates=155,
        complete=sum(r['all_parts_available'] for r in simulation),output_counts=dict(Counter(r['simulation_output'] for r in simulation)),
        dangerous_any_defect_all_correct=ratio(sum(r['dangerous_all_correct'] for r in simulation),sum(r['true_any_defect'] and r['all_parts_available'] for r in simulation)),
        dangerous_misassembly_all_correct=ratio(sum(r['dangerous_all_correct'] and r['true_any_misassembly'] for r in simulation),sum(r['true_any_misassembly'] and r['all_parts_available'] for r in simulation)))
    report=dict(parts=part_metrics,classifier_only_simulation=sim,
        preprocessing={s:dict(before=dict(Counter(r['status'] for r in before.values() if r['split']==s)),
            after=dict(Counter(r['status'] for r in after.values() if r['split']==s))) for s in ('TRAIN','VALIDATION')},
        recovered_ids=[r['display_index'] for r in changes if r['recovered']],
        remaining_unresolved_ids=[r['display_index'] for r in changes if r['after_status']!='VALID'],
        original_success_changed_ids=[r['display_index'] for r in changes if r['subset']=='original_success_110' and
            (r['after_status']!='VALID' or any(not p['same_input'] or p['before_prediction']!=p['after_prediction'] for p in r['parts'].values()))],
        definitions=json.loads((BASELINE/'training_metrics.json').read_text(encoding='utf-8'))['definitions'],
        baseline_metrics=json.loads((BASELINE/'training_metrics.json').read_text(encoding='utf-8')),
        label_source='Codex review, human_reviewed=false; same ENGINE_01; development regression, not independent final test')
    dump(OUTPUT/'before_after_metrics.json',report)
    print(json.dumps(sim),flush=True)


if __name__=='__main__':main()
