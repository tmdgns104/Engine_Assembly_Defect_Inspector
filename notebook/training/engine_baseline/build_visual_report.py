"""Render existing baseline evidence as an offline, read-only HTML report.

No model inference, training, label editing or input split changes occur here.
Aligned previews replay saved matrices; the displayed model inputs are exact PNGs.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import os

import cv2
import numpy as np

from preprocess import PARTS, read_image, sha
from prepare_alignment import read_rows
from process_dataset import dump
from src.vision.engine_rectification import rectify_image


def preview(path, image):
    resized=cv2.resize(image,(960,540),interpolation=cv2.INTER_AREA)
    ok,encoded=cv2.imencode('.jpg',resized,[cv2.IMWRITE_JPEG_QUALITY,86])
    assert ok
    if path.exists():assert path.read_bytes()==encoded.tobytes(),path
    else:path.write_bytes(encoded.tobytes())
    return path.name


def main():
    parser=argparse.ArgumentParser();parser.add_argument('run');args=parser.parse_args()
    run=Path(args.run).resolve();output=run/'visual_report_v001';assets=output/'assets'
    assets.mkdir(parents=True,exist_ok=True)
    source_names=['training_metrics.json','preprocessing_report.json','preprocessing_records.jsonl',
                  'validation_predictions.jsonl','classifier_only_simulation.jsonl','training_verification.json',
                  'input_verification/verification_results.json','full_execution.json','environment.json',
                  'alignment/config_frozen.json','alignment/alignment_checks.json','alignment/visual_review.json',
                  'export_train_candidates.jsonl','export_validation_candidates.jsonl']
    input_hashes={name:sha(run/name) for name in source_names}
    get=lambda name:json.loads((run/name).read_text(encoding='utf-8'))
    sources=read_rows(run/'export_validation_candidates.jsonl')
    records={r['capture_id']:r for r in read_rows(run/'preprocessing_records.jsonl')}
    predictions={(r['capture_id'],r['part']):r for r in read_rows(run/'validation_predictions.jsonl')}
    simulation={r['capture_id']:r for r in read_rows(run/'classifier_only_simulation.jsonl')}
    cfg=get('alignment/config_frozen.json');cases=[];links=[]
    for source in sources:
        cid=source['capture_id'];record=records[cid];pose=record.get('pose',{})
        assert sha(source['raw_image_path'])==source['raw_sha256']
        image=read_image(source['raw_image_path']);display=source['display_index']
        original='assets/'+preview(assets/f'{display}_original.jpg',image)
        aligned=None
        if pose.get('ok') and pose.get('matrix') is not None:
            aligned='assets/'+preview(assets/f'{display}_aligned.jpg',rectify_image(image,np.array(pose['matrix']),cfg))
        parts={}
        for part in PARTS:
            pred=predictions[cid,part]
            assert pred['approved_state']==source['approved_part_states'][part]
            crop=None
            if pred['crop_path']:
                assert sha(pred['crop_path'])==pred['crop_sha256']
                crop=Path(os.path.relpath(pred['crop_path'],output)).as_posix();links.append(crop)
            parts[part]=dict(truth=pred['approved_state'],prediction=pred['predicted_state'],scores=pred['class_scores'],
                            status=pred['preprocessing_status'],reason=pred['preprocessing_reason'],crop=crop,
                            crop_sha256=pred['crop_sha256'],model_sha256=pred['model_sha256'],
                            coverage=record.get('parts',{}).get(part,{}).get('source_coverage'))
        cases.append(dict(id=display,capture_id=cid,original=original,aligned=aligned,status=record['status'],reason=record['reason'],
                          parts=parts,pose={k:pose.get(k) for k in ['ok','angle_deg','scale','inliers','good_matches','median_error_px','matrix']},
                          anchor=record.get('orientation_anchor_correlation'),simulation=simulation[cid]['simulation_output'],
                          raw_sha256=source['raw_sha256'],raw_path=source['raw_image_path'],raw_url=Path(source['raw_image_path']).as_uri(),
                          group=source['source_group_id'],round=source['collection_round_id'],lineage=source['lineage_root_id']))
        links.append(original)
        if aligned:links.append(aligned)
    data=dict(run_id=run.name,generated_at=datetime.now(timezone.utc).isoformat(),cases=cases,
              metrics=get('training_metrics.json'),preprocessing=get('preprocessing_report.json'),config=cfg,
              verification=get('training_verification.json'),input_verification=get('input_verification/verification_results.json'),
              environment=get('environment.json'),execution=get('full_execution.json'),
              alignment_checks=get('alignment/alignment_checks.json'),visual_review=get('alignment/visual_review.json'),
              source_hashes=input_hashes)
    assert len(cases)==155 and sum(len(c['parts']) for c in cases)==620
    assert Counter(c['status'] for c in cases)=={'VALID':110,'PARTIAL':35,'FAILED':10}
    assert sum(p['prediction'] is not None for c in cases for p in c['parts'].values())==545
    template=Path(__file__).with_name('visual_report_template.html').read_text(encoding='utf-8')
    html=template.replace('@@REPORT_DATA@@',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c'))
    assert '@@REPORT_DATA@@' not in html
    report=output/'REPORT.html';report.write_text(html,encoding='utf-8')
    for link in links:assert (output/link).is_file(),link
    assert input_hashes=={name:sha(run/name) for name in source_names}
    dump(output/'report_generation_verification.json',dict(status='PASS',cases=155,part_slots=620,predicted_parts=545,
         failed_part_slots=75,exact_input_crop_links=545,original_previews=155,aligned_previews=sum(c['aligned'] is not None for c in cases),
         source_artifacts_unchanged=True,source_hashes=input_hashes,report_sha256=sha(report),
         previews='960x540 JPEG display derivatives, not training inputs; stored matrices replayed without estimation',
         browser_verification='PENDING',source_generator_sha256=sha(Path(__file__)),template_sha256=sha(Path(__file__).with_name('visual_report_template.html'))))
    (output/'OPEN_REPORT.cmd').write_text('@echo off\r\nstart "" "%~dp0REPORT.html"\r\n',encoding='ascii')
    print(json.dumps(dict(report=str(report),cases=155,assets=len(list(assets.glob('*.jpg'))),source_artifacts_unchanged=True)),flush=True)


if __name__=='__main__':main()
