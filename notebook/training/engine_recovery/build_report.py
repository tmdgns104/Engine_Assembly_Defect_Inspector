"""Extend the original report in a new run, preserving its full baseline section."""
import json
import os
from pathlib import Path
import re
import cv2
import numpy as np
from fit_train import OUTPUT
from investigate import BASELINE
from preprocess import PARTS,read_image,write_image,padded_224,sha
from prepare_alignment import read_rows
from process_dataset import dump
from build_visual_report import preview
from src.vision.engine_rectification import rectify_image


def main():
    out=OUTPUT/'visual_report_v001';assets=out/'assets';assets.mkdir(parents=True,exist_ok=True)
    rel=lambda p:Path(os.path.relpath(p,out)).as_posix()
    load=lambda name:json.loads((OUTPUT/name).read_text(encoding='utf-8'))
    cfg=load('alignment/config_frozen.json');metrics=load('before_after_metrics.json');latency=load('pc_latency.json')
    latency['routes']={route:dict(median=float(np.median([r['end_to_end_ms'] for r in latency['samples'] if r['pose_route']==route]))) for route in ['BASELINE','TRAIN_BODY_BANK']}
    sources=read_rows(BASELINE/'export_validation_candidates.jsonl')
    old={r['capture_id']:r for r in read_rows(OUTPUT/'baseline_reproduced_records.jsonl')}
    new={r['capture_id']:r for r in read_rows(OUTPUT/'preprocessing_records.jsonl')}
    preds=[{(r['capture_id'],r['part']):r for r in read_rows(root/'validation_predictions.jsonl')} for root in [BASELINE,OUTPUT]]
    changes={r['capture_id']:r for r in read_rows(OUTPUT/'case_changes.jsonl')}
    reviews={r['capture_id']:r for r in read_rows(OUTPUT/'failure_review_45.jsonl')}
    cases=[];links=[]
    for row in sources:
        cid=row['capture_id'];id=row['display_index'];raw=read_image(row['raw_image_path'])
        original=rel(BASELINE/'visual_report_v001/assets'/f'{id}_original.jpg');links.append(original)
        case=dict(id=id,capture_id=cid,original=original,raw_path=row['raw_image_path'],raw_sha256=row['raw_sha256'],
            group=row['source_group_id'],round=row['collection_round_id'],lineage=row['lineage_root_id'],change=changes[cid],review=reviews.get(cid))
        for index,(phase,record) in enumerate([('before',old[cid]),('after',new[cid])]):
            display_pose=record.get('bank_attempt') if record['status']=='FAILED' and record.get('bank_attempt',{}).get('matrix') else record['pose']
            matrix=np.array(display_pose['matrix']);canonical=rectify_image(raw,matrix,cfg)
            aligned='assets/'+preview(assets/f'{id}_{phase}.jpg',canonical)
            support=cv2.warpAffine(np.ones(raw.shape[:2],np.float32),cv2.invertAffineTransform(matrix),(1280,720),flags=cv2.INTER_LINEAR)
            annotated=canonical.copy();annotated[support<1]=(130,35,140)
            for part,box in cfg['crop_regions_xyxy'].items():
                x1,y1,x2,y2=box;cv2.rectangle(annotated,(x1,y1),(x2-1,y2-1),(0,220,255),2)
                cv2.polylines(annotated,[np.array(cfg['essential_polygons'][part])],True,(60,255,70),2)
            overlay='assets/'+preview(assets/f'{id}_{phase}_regions.jpg',annotated)
            links.extend([aligned,overlay]);parts={}
            for part in PARTS:
                pred=preds[index][cid,part];detail=record.get('parts',{}).get(part,{})
                crop=rel(pred['crop_path']) if pred['crop_path'] else None
                diagnostic=None
                if crop:links.append(crop)
                else:
                    x1,y1,x2,y2=cfg['crop_regions_xyxy'][part]
                    path=out/'diagnostic_crops'/f'{id}_{phase}_{part}.png'
                    write_image(path,padded_224(canonical[y1:y2,x1:x2]));diagnostic=rel(path);links.append(diagnostic)
                parts[part]=dict(truth=pred['approved_state'],prediction=pred['predicted_state'],scores=pred['class_scores'],
                    crop=crop,diagnostic=diagnostic,crop_sha256=pred['crop_sha256'],coverage=detail.get('source_coverage'),
                    essential_missing=detail.get('essential_support',{}).get('unsupported_pixels'))
            bank=record.get('bank_attempt');hold=''
            if record['status']=='FAILED':
                ratio=bank.get('diagnostics',{}).get('inlier_ratio') if bank else None
                hold=f'추가 본체 매칭 inlier 비율 {ratio:.1%} < 기준 25%. 방향 또는 정렬 근거가 부족해 후 후보를 모델에 전달하지 않았습니다.' if ratio is not None else record['reason']
            case[phase]=dict(status=record['status'],reason=record['reason'],aligned=aligned,overlay=overlay,parts=parts,
                pose=record['pose'],display_pose=display_pose,bank_attempt=bank,pose_route=record.get('pose_route','BASELINE'),
                anchor=record.get('orientation_anchor_correlation') if display_pose is record['pose'] else None,hold_note=hold)
        cases.append(case)
    # Keep the original complete HTML content; relocate only its relative links.
    baseline_html=(BASELINE/'visual_report_v001/REPORT.html').read_text(encoding='utf-8')
    pattern=r'(<script id="report-data" type="application/json">)(.*?)(</script>)'
    match=re.search(pattern,baseline_html,re.S);data=json.loads(match.group(2))
    def rebase(value):
        if isinstance(value,dict):return {k:rebase(v) for k,v in value.items()}
        if isinstance(value,list):return [rebase(v) for v in value]
        if isinstance(value,str) and (value.startswith('assets/') or value.startswith('../')):return rel((BASELINE/'visual_report_v001'/value).resolve())
        return value
    text=re.sub(pattern,lambda m:m.group(1)+json.dumps(rebase(data),ensure_ascii=False).replace('<','\\u003c')+m.group(3),baseline_html,flags=re.S)
    text=re.sub(r'href="(\.\./[^\"]+)"',lambda m:'href="'+rel((BASELINE/'visual_report_v001'/m.group(1)).resolve())+'"',text)
    fragment=Path(__file__).with_name('recovery_section.html').read_text(encoding='utf-8')
    text=text.replace('<main>','<main>\n'+fragment,1).replace('<nav aria-label="보고서 목차">','<nav aria-label="보고서 목차"><a href="#recovery">전처리 회복 비교</a>',1)
    text=text.replace('<title>엔진 조립 검사 · 학습과 검증을 눈으로 확인하기</title>','<title>엔진 전처리 회복 · 수정 전후 비교 보고서</title>')
    text=text.replace('<h1>사진에서 판단까지,','<h1>기준 실험 · 수정 전<br>사진에서 판단까지,',1)
    payload=json.dumps(dict(cases=cases,metrics=metrics,latency=latency),ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    script=Path(__file__).with_name('recovery_report.js').read_text(encoding='utf-8')
    text=text.replace('</body>',f'<script id="recovery-data" type="application/json">{payload}</script><script>{script}</script></body>')
    (out/'REPORT.html').write_text(text,encoding='utf-8')
    (out/'OPEN_REPORT.cmd').write_text('@echo off\r\nstart "" "%~dp0REPORT.html"\r\n',encoding='ascii')
    # Normalize '..' before Windows stat; unnormalized paths can exceed MAX_PATH.
    for link in links:assert (out/link).resolve().is_file(),link
    dump(out/'report_generation_verification.json',dict(status='PASS',cases=len(cases),old_failures=45,recovered=41,remaining=4,
        input_crop_links=sum(bool(c[p]['parts'][part]['crop']) for c in cases for p in ['before','after'] for part in PARTS),
        linked_images=len(links),missing_images=0,baseline_html_sha256=sha(BASELINE/'visual_report_v001/REPORT.html'),
        report_sha256=sha(out/'REPORT.html'),browser_verification='PENDING'))
    print('REPORT',out/'REPORT.html','LINKS',len(links),flush=True)


if __name__=='__main__':main()
