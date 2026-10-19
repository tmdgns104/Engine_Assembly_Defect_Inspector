"""Fit a small fixed-body descriptor bank from TRAIN, then freeze configuration."""
from datetime import datetime,timezone
import json
import shutil

import cv2
import numpy as np

from investigate import BASELINE,PROJECT
from recovery import RecoveryPreprocessor
from preprocess import BodyPreprocessor,PARTS,read_image,write_image,sha
from prepare_alignment import read_rows
from process_dataset import dump
from src.vision.engine_rectification import rectify_image
from src.vision.engine_pose import transform_polygon

OUTPUT=PROJECT/'runs/engine_preprocessing_recovery_001/v001_20261003T033452Z'


def main():
    assert not (OUTPUT/'alignment/config_frozen.json').exists(),'Preserve frozen alignment configuration'
    alignment=OUTPUT/'alignment';alignment.mkdir(exist_ok=True)
    cfg=json.loads((BASELINE/'alignment/config_frozen.json').read_text(encoding='utf-8'))
    shutil.copyfile(BASELINE/'alignment/reference_T0001.png',alignment/'reference_T0001.png')
    # The corners removed below contain background across TRAIN state examples.
    # Keep the entire old input rectangle; these polygons only control visibility.
    cfg['essential_polygons']={
        'pipe_left':[[486,96],[624,96],[624,344],[426,344],[426,171]],
        'pipe_right':[[709,96],[862,96],[921,171],[921,344],[709,344]],
        'exhaust':[[569,373],[763,373],[763,523],[569,523]],
        'symbol':[[599,282],[734,282],[734,391],[599,391]]}
    cfg['schema_version']='essential-support-train-bank-v1'
    cfg['visibility_policy']='Every essential pixel needs complete bilinear source support; optional corners retain original constant40 padding'
    cfg['fit_source']='TRAIN only; candidate labels select representative review coverage, never passed into preprocessing'
    base=BodyPreprocessor(BASELINE/'alignment/config_frozen.json')
    records={r['capture_id']:r for r in read_rows(OUTPUT/'baseline_reproduced_records.jsonl')}
    train=read_rows(BASELINE/'export_train_candidates.jsonl')
    # Choose up to two views per measured 30-degree bin, spanning acquisition.
    # Angle comes from the image-derived transform, never the guide angle.
    bins={}
    for row in train:
        record=records[row['capture_id']]
        if record['status']=='VALID' and all(v=='CORRECT' for v in row['approved_part_states'].values()):
            bins.setdefault(round(record['pose']['angle_deg']/30),[]).append(row)
    references=[]
    for group in bins.values():
        references.extend(group[i] for i in sorted({0,len(group)-1}))
    points=[];descriptors=[];provenance=[]
    for row in references:
        record=records[row['capture_id']];matrix=np.array(record['pose']['matrix'])
        raw=read_image(row['raw_image_path']);assert sha(row['raw_image_path'])==row['raw_sha256']
        mask=cv2.warpAffine(base.reference_mask,matrix,(raw.shape[1],raw.shape[0]),flags=cv2.INTER_NEAREST)
        kp,des=base.estimator.orb.detectAndCompute(base.estimator._gray(raw),mask)
        distance=cv2.distanceTransform(mask,cv2.DIST_L2,5)
        keep=[i for i,k in enumerate(kp) if distance[round(k.pt[1]),round(k.pt[0])]>=k.size*.5+3]
        canonical_points=transform_polygon([kp[i].pt for i in keep],cv2.invertAffineTransform(matrix))
        points.extend(canonical_points);descriptors.extend(des[keep])
        provenance.append(dict(capture_id=row['capture_id'],display_index=row['display_index'],split='TRAIN',
            raw_sha256=row['raw_sha256'],matrix=matrix.tolist(),descriptor_count=len(keep)))
    bank=alignment/'train_body_bank.npz'
    np.savez_compressed(bank,points=np.array(points,np.float32),descriptors=np.array(descriptors,np.uint8))
    cfg['reference_bank']=dict(path=bank.name,sha256=sha(bank),references=provenance)
    cfg['frozen_at']=datetime.now(timezone.utc).isoformat()
    dump(alignment/'config_frozen.json',cfg)
    dump(alignment/'fit_provenance.json',dict(train_only=True,references=provenance,descriptor_count=len(points),
        numeric_pose_thresholds_unchanged=True,direction_threshold_unchanged=True,crop_rectangles_unchanged=True))
    # Draw essential outline on a diverse TRAIN-only review set; never model input.
    groups={}
    for row in train:
        if records[row['capture_id']]['status']!='FAILED':
            groups.setdefault(tuple(row['approved_part_states'][p] for p in PARTS),[]).append(row)
    selected=[]
    for group in groups.values():
        seen=set()
        for row in group:
            angle_bin=round(records[row['capture_id']]['pose']['angle_deg']/60)
            if angle_bin not in seen:selected.append(row);seen.add(angle_bin)
    for start in range(0,len(selected),6):
        sheet=np.full((930,1280,3),30,np.uint8)
        for j,row in enumerate(selected[start:start+6]):
            raw=read_image(row['raw_image_path']);record=records[row['capture_id']]
            canonical=rectify_image(raw,np.array(record['pose']['matrix']),cfg)
            for part,polygon in cfg['essential_polygons'].items():
                cv2.polylines(canonical,[np.array(polygon)],True,(0,255,0),2)
            tile=cv2.resize(canonical[80:440,400:940],(540,360))
            x=(j%2)*640;y=(j//2)*310
            tile=cv2.resize(tile,(420,280));sheet[y+25:y+305,x+110:x+530]=tile
            title=row['display_index']+' '+' / '.join(row['approved_part_states'][p] for p in PARTS)
            cv2.putText(sheet,title,(x+5,y+17),cv2.FONT_HERSHEY_SIMPLEX,.32,(255,255,255),1)
        write_image(OUTPUT/'train_geometry_review'/f'page_{start//6+1:02d}.png',sheet)
    dump(OUTPUT/'train_geometry_review/manifest.json',selected)
    print('TRAIN BANK',len(references),len(points),'GEOMETRY REVIEW',len(selected),'PAGES',(len(selected)+5)//6)


if __name__=='__main__':main()
