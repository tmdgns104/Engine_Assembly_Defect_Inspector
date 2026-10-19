"""Preserve photo-review observations and inspect actual ORB correspondences."""
from datetime import datetime,timezone
import json
import cv2
import numpy as np
from fit_train import OUTPUT
from investigate import BASELINE
from recovery import RecoveryPreprocessor
from preprocess import read_image,write_image,sha
from prepare_alignment import read_rows
from process_dataset import dump
from run_preprocessing import jsonl
from src.vision.engine_pose import _expanded_mask


def main():
    before={r['capture_id']:r for r in read_rows(OUTPUT/'baseline_reproduced_records.jsonl')}
    after={r['capture_id']:r for r in read_rows(OUTPUT/'preprocessing_records.jsonl')}
    source={r['capture_id']:r for r in read_rows(BASELINE/'export_validation_candidates.jsonl')}
    processor=RecoveryPreprocessor(OUTPUT/'alignment/config_frozen.json')
    reviews=[];matches=[]
    for cid,row in source.items():
        old,new=before[cid],after[cid]
        if old['status']=='VALID':continue
        category='OPTIONAL_BACKGROUND_ONLY' if old['status']=='PARTIAL' else 'WRONG_180_DEGREE_POSE' if row['display_index']=='V0089' else 'INSUFFICIENT_BODY_MATCHES' if 'POSE_QUALITY' in old['reason'] else 'DIRECTION_ANCHOR_MISREGISTRATION'
        note={'OPTIONAL_BACKGROUND_ONLY':'원본과 정렬/유효픽셀 마스크를 직접 확인. 파이프·연결부·상태 판독 범위가 보이고 외측 위 모서리 배경만 원본 밖.',
            'WRONG_180_DEGREE_POSE':'기존 긴 금색 축이 위로 향함. 방향 게이트의 거부가 올바름. 변경 후 긴 축 아래·짧은 축 위를 직접 확인.',
            'INSUFFICIENT_BODY_MATCHES':'대략적인 방향은 맞지만 기존 대응점 inlier 수가 10 미만. 매칭 분포와 오차 기록을 별도 보존.',
            'DIRECTION_ANCHOR_MISREGISTRATION':'긴 축 아래 방향은 대략 맞으나 본체 좌표가 어긋나 V8 고정 앵커의 직접 일치도가 부족함.'}[category]
        reviews.append(dict(capture_id=cid,display_index=row['display_index'],reviewer='codex',human_reviewed=False,
            reviewed_at=datetime.now(timezone.utc).isoformat(),category=category,observation=note,
            actual_part_or_connection_truncation_observed=False if category=='OPTIONAL_BACKGROUND_ONLY' else None,
            source_sha256=row['raw_sha256'],before_status=old['status'],after_status=new['status'],
            result='RECOVERED' if new['status']=='VALID' else 'SAFETY_HOLD_RETAINED',
            evidence_before=str(OUTPUT/'diagnostics'/(row['display_index']+'.png')),
            evidence_after=str(OUTPUT/'recovery_reviews'/(row['display_index']+'.png'))))
        if old['status']!='FAILED':continue
        raw=read_image(row['raw_image_path']);box=old['products'][0]['bounding_box']
        kp,des=processor.estimator.orb.detectAndCompute(processor.estimator._gray(raw),_expanded_mask(raw.shape,[box[k] for k in ('x1','y1','x2','y2')],.18))
        pairs=processor.estimator.matcher.knnMatch(processor.estimator.ref_des,des,k=2)
        good=[p[0] for p in pairs if len(p)==2 and p[0].distance<.75*p[1].distance]
        src=np.float32([processor.estimator.ref_kp[m.queryIdx].pt for m in good]).reshape(-1,1,2)
        dst=np.float32([kp[m.trainIdx].pt for m in good]).reshape(-1,1,2)
        matrix,mask=cv2.estimateAffinePartial2D(src,dst,method=cv2.RANSAC,ransacReprojThreshold=3.,maxIters=7000,confidence=.995,refineIters=20)
        inliers=mask.ravel().astype(bool)
        assert int(inliers.sum())==old['pose']['inliers']
        region_counts=[]
        for x1,y1,x2,y2 in processor.cfg['fixed_body_feature_regions_xyxy']:
            region_counts.append(int(sum(x1<=x<x2 and y1<=y<y2 for x,y in src[inliers].reshape(-1,2))))
        details=dict(display_index=row['display_index'],capture_id=cid,baseline_pose=old['pose'],
            inlier_counts_by_fixed_body_region=region_counts,reference_points=src.reshape(-1,2).tolist(),
            raw_points=dst.reshape(-1,2).tolist(),inlier_mask=inliers.tolist(),
            after_pose=new['pose'],bank_attempt=new.get('bank_attempt'),bank_direction_score=new.get('bank_direction_score'))
        matches.append(details)
        rendered=cv2.drawMatches(processor.estimator.reference,processor.estimator.ref_kp,raw,kp,good,None,
            matchesMask=list(map(int,inliers)),flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
        write_image(OUTPUT/'correspondences'/(row['display_index']+'.png'),rendered)
    jsonl(OUTPUT/'failure_review_45.jsonl',reviews)
    dump(OUTPUT/'pose_correspondence_analysis_10.json',matches)
    dump(OUTPUT/'alignment/visual_review.json',dict(reviewer='codex',human_reviewed=False,
        train_pages_actually_viewed=list(range(1,17)),train_representatives=91,
        conclusion='Across reviewed TRAIN poses/states, removed top outer triangles are background. Full crop rectangle unchanged. Existing outward-pipe outer margins are narrow; no broader-state coverage claimed.',
        validation_failures_actually_viewed=[r['display_index'] for r in reviews],
        recovered_pose_images_actually_viewed=['V0086','V0089','V0127','V0151','V0166','V0176'],
        config_sha256=sha(OUTPUT/'alignment/config_frozen.json')))
    # Contact sheets for every newly aligned TRAIN image, separate from model input.
    train_new=[r for r in after.values() if r['split']=='TRAIN' and r['pose_route']=='TRAIN_BODY_BANK']
    for start in range(0,len(train_new),3):
        canvas=np.full((1440,840,3),30,np.uint8)
        for j,row in enumerate(train_new[start:start+3]):
            canvas[j*480:(j+1)*480]=cv2.resize(read_image(OUTPUT/'recovery_reviews'/(row['display_index']+'.png')),(840,480))
        write_image(OUTPUT/'train_recovered_review'/f'page_{start//3+1:02d}.png',canvas)
    print('FAILURE REVIEWS',len(reviews),'POSE ANALYSES',len(matches),'TRAIN POSE REVIEWS',len(train_new))


if __name__=='__main__':main()
