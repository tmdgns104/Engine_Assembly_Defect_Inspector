"""Development validation with every source candidate retained, including failures."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from classification import FixedPredictor,FixedValidator
from preprocess import PARTS,read_image,write_image,sha
from prepare_alignment import read_rows
from process_dataset import dump


def ratio(numerator,denominator):
    return dict(count=int(numerator),denominator=int(denominator),rate=float(numerator/denominator) if denominator else None)


def metrics_for(rows,names):
    valid=[r for r in rows if r['prediction_status']=='PREDICTED']
    ids={name:i for i,name in enumerate(names)}
    cm=np.zeros((len(names),len(names)),dtype=np.int64)
    for r in valid:cm[ids[r['approved_state']],ids[r['predicted_state']]]+=1
    classes={}
    for i,name in enumerate(names):
        tp=int(cm[i,i]);actual=int(cm[i].sum());predicted=int(cm[:,i].sum())
        precision=tp/predicted if predicted else 0.
        recall=tp/actual if actual else 0.
        f1=2*tp/(actual+predicted) if actual+predicted else 0.
        classes[name]=dict(support=actual,predicted_count=predicted,precision=precision,recall=recall,f1=f1)
    wrong_orientation=[r for r in valid if r['approved_state'] not in ('CORRECT','MISSING')]
    missing=[r for r in valid if r['approved_state']=='MISSING']
    normal=[r for r in valid if r['approved_state']=='CORRECT']
    return dict(candidate_count=len(rows),predicted_count=len(valid),processing_rate=len(valid)/len(rows),
                failure_reasons=dict(Counter(r['preprocessing_reason'] for r in rows if r['prediction_status']!='PREDICTED')),
                class_order=names,confusion_matrix_rows_true_columns_pred=cm.tolist(),classes=classes,
                accuracy=float(np.trace(cm)/cm.sum()),macro_f1=float(np.mean([v['f1'] for v in classes.values()])),
                misassembled_to_correct=ratio(sum(r['predicted_state']=='CORRECT' for r in wrong_orientation),len(wrong_orientation)),
                missing_to_correct=ratio(sum(r['predicted_state']=='CORRECT' for r in missing),len(missing)),
                correct_to_defective=ratio(sum(r['predicted_state']!='CORRECT' for r in normal),len(normal)))


def comparison(output,source,part_rows):
    canvas=np.full((670,1120,3),35,np.uint8)
    raw=read_image(source['raw_image_path'])
    canvas[35:350,280:840]=cv2.resize(raw,(560,315))
    cv2.putText(canvas,source['display_index']+' / DEVELOPMENT VALIDATION',(20,25),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),1)
    for i,part in enumerate(PARTS):
        row=part_rows[part];x=i*280
        if row['crop_path']:
            canvas[424:648,x+25:x+249]=read_image(row['crop_path'])
        for y,text in [(375,part),(395,'TRUE: '+row['approved_state']),(415,'PRED: '+str(row['predicted_state'] or 'NO OUTPUT'))]:
            color=(100,255,100) if row['approved_state']==row['predicted_state'] else (90,130,255)
            cv2.putText(canvas,text,(x+5,y),cv2.FONT_HERSHEY_SIMPLEX,.43,color,1)
    path=output/'validation_comparisons'/(source['display_index']+'.png')
    write_image(path,canvas)
    return str(path)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('output');args=parser.parse_args()
    output=Path(args.output).resolve();predictions=[];reports={}
    for part in PARTS:
        manifest=read_rows(output/f'{part}_validation_crop_manifest.jsonl')
        best=output/'full'/part/'weights/best.pt'
        model=YOLO(str(best));weight_hash=sha(best)
        names=[model.names[i] for i in range(len(model.names))]
        valid=[r for r in manifest if r['status']=='VALID']
        result_by_id={}
        for start in range(0,len(valid),16):
            batch=valid[start:start+16]
            results=model.predict([read_image(r['crop_path']) for r in batch],predictor=FixedPredictor,
                                  imgsz=224,device=0,quantize=32,verbose=False)
            for row,result in zip(batch,results):
                scores=result.probs.data.cpu().numpy()
                assert len(scores)==len(names) and np.isfinite(scores).all() and abs(float(scores.sum())-1)<1e-5
                result_by_id[row['capture_id']]=(names[int(scores.argmax())],dict(zip(names,map(float,scores))))
        part_predictions=[]
        for row in manifest:
            prediction,scores=result_by_id.get(row['capture_id'],(None,None))
            part_predictions.append(dict(**{k:row.get(k) for k in ['split','capture_id','display_index','raw_image_path','raw_sha256','source_group_id',
                'collection_round_id','lineage_root_id','crop_path','crop_sha256','alignment_config_sha256','preprocessing_version','part','approved_state']},
                predicted_state=prediction,class_scores=scores,preprocessing_status=row['status'],preprocessing_reason=row['reason'],
                prediction_status='PREDICTED' if prediction is not None else 'PREPROCESSING_FAILED',
                model_path=str(best),model_sha256=weight_hash,model_version=output.name+'/'+part,
                evaluation_scope='DEVELOPMENT_VALIDATION',label_source='Codex reviewed; human_reviewed=false'))
        report=metrics_for(part_predictions,names)
        # Independently exercise Ultralytics standalone validation with the same transform.
        standalone=model.val(validator=FixedValidator,data=str(output/'crops'/part),imgsz=224,batch=16,workers=0,
                             device=0,quantize=32,plots=False,project=str(output/'standalone_validation'),name=part)
        assert abs(standalone.top1-report['accuracy'])<1e-6
        report['standalone_validation_top1']=standalone.top1
        epochs=list(csv.DictReader((output/'full'/part/'results.csv').open(encoding='utf-8')))
        report['epochs_executed']=len(epochs)
        report['epoch_metrics']=epochs
        report['best_selection_criterion']='macro F1 on this development VALIDATION; not independent final test'
        report['model_sha256']=weight_hash
        reports[part]=report;predictions+=part_predictions
        print(part,report['predicted_count'],report['macro_f1'],flush=True)
    (output/'validation_predictions.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in predictions),encoding='utf-8')
    sources=read_rows(output/'export_validation_candidates.jsonl')
    grouped={r['capture_id']:{p:next(x for x in predictions if x['capture_id']==r['capture_id'] and x['part']==p) for p in PARTS} for r in sources}
    simulation=[];errors=[]
    for source in sources:
        parts=grouped[source['capture_id']]
        has_defect=any(v!='CORRECT' for v in source['approved_part_states'].values())
        has_misassembly=any(v not in ('CORRECT','MISSING') for v in source['approved_part_states'].values())
        complete=all(r['prediction_status']=='PREDICTED' for r in parts.values())
        all_normal=complete and all(r['predicted_state']=='CORRECT' for r in parts.values())
        dangerous=has_defect and all_normal
        result=dict(capture_id=source['capture_id'],display_index=source['display_index'],all_parts_available=complete,
                    true_any_defect=has_defect,true_any_misassembly=has_misassembly,
                    simulation_output='NO_DECISION_PREPROCESSING_FAILED' if not complete else 'ALL_CORRECT' if all_normal else 'DEFECT_DETECTED',
                    dangerous_all_correct=dangerous,approved_part_states=source['approved_part_states'],
                    predicted_part_states={p:r['predicted_state'] for p,r in parts.items()})
        simulation.append(result)
        wrong=[p for p,r in parts.items() if r['prediction_status']=='PREDICTED' and r['predicted_state']!=r['approved_state']]
        if dangerous or wrong:
            errors.append(dict(**result,wrong_parts=wrong,comparison_path=comparison(output,source,parts)))
    for source in sources[:3]:comparison(output,source,grouped[source['capture_id']])
    sim_summary=dict(scope='CLASSIFIER_ONLY_SIMULATION; not runtime/PLC PASS-FAIL or 3-frame validation',
                     total_candidates=len(simulation),complete=sum(r['all_parts_available'] for r in simulation),
                     output_counts=dict(Counter(r['simulation_output'] for r in simulation)),
                     dangerous_any_defect_all_correct=ratio(sum(r['dangerous_all_correct'] for r in simulation),
                         sum(r['true_any_defect'] and r['all_parts_available'] for r in simulation)),
                     dangerous_misassembly_all_correct=ratio(sum(r['dangerous_all_correct'] and r['true_any_misassembly'] for r in simulation),
                         sum(r['true_any_misassembly'] and r['all_parts_available'] for r in simulation)))
    dump(output/'training_metrics.json',dict(parts=reports,classifier_only_simulation=sim_summary,
         definitions=dict(misassembled_to_correct='True state excluding CORRECT and MISSING; denominator = successfully processed such states',
                          missing_to_correct='True MISSING predicted CORRECT / successfully processed true MISSING',
                          correct_to_defective='True CORRECT predicted any other class / successfully processed true CORRECT',
                          confusion='Rows true, columns prediction in saved class_order; no failed input counted normal')))
    for name,rows in [('classifier_only_simulation.jsonl',simulation),('validation_errors.jsonl',errors)]:
        (output/name).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    print(json.dumps(sim_summary),flush=True)


if __name__=='__main__':main()
