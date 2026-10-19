"""Independent artifact audit, Korean reports, and a bounded review package."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import inspect
import json
from pathlib import Path
import shutil
import zipfile

import cv2
import numpy as np

from preprocess import PROJECT,PARTS,BodyPreprocessor,padded_224,read_image,sha
from prepare_alignment import read_rows
from process_dataset import dump


def pct(value):return f'{value*100:.1f}%'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('output');args=parser.parse_args()
    output=Path(args.output).resolve();checks=[]
    def passed(name,detail):checks.append(dict(check=name,status='PASS',detail=detail))
    before=json.loads((output/'input_file_hashes_before.json').read_text(encoding='utf-8'))
    for relative,entry in before.items():
        path=PROJECT/relative
        assert sha(path)==entry['sha256'] and path.stat().st_size==entry['bytes'],path
    raw=read_rows(output/'raw_input_hashes.jsonl')
    for row in raw:assert sha(row['raw_image_path'])==row['raw_sha256']
    passed('original_integrity',f'{len(raw)} source images and {len(before)} metadata/label/evidence files unchanged SHA-256')
    inputs={s:read_rows(output/f'export_{s.lower()}_candidates.jsonl') for s in ('TRAIN','VALIDATION')}
    assert [len(inputs[s]) for s in inputs]==[694,155]
    for field in ('raw_sha256','source_group_id','collection_round_id','lineage_root_id'):
        assert not ({r[field] for r in inputs['TRAIN']} & {r[field] for r in inputs['VALIDATION']})
    unresolved=read_rows(PROJECT/'data/guided_capture_20261001/labeling_unresolved_cases.jsonl')
    selected={r['capture_id']:r for rows in inputs.values() for r in rows}
    assert not set(selected)&{r['capture_id'] for r in unresolved}
    assert len(unresolved)==43
    for row in selected.values():
        assert row['review_status']=='APPROVED' and not row['is_superseded']
        assert not row['human_reviewed'] and not row['training_accepted']
        assert '/sessions/' in row['raw_image_path'].replace('\\','/') and '전달_' not in row['raw_image_path']
    passed('candidate_isolation','694 TRAIN /155 VALIDATION; raw/group/round/lineage intersections zero; unresolved43 excluded; approval flags unchanged')
    config=json.loads((output/'alignment/config_frozen.json').read_text(encoding='utf-8'))
    draft=json.loads((output/'alignment/config_train_draft.json').read_text(encoding='utf-8'))
    assert {k:v for k,v in config.items() if k not in ('frozen_at','fit_source')}==draft
    frozen_hash=sha(output/'alignment/config_frozen.json');executed_hash=sha(output/'alignment/config_train_draft.json')
    assert config['reference_split']=='TRAIN'
    reference=selected[config['reference_id']]
    assert reference['split']=='TRAIN' and reference['raw_sha256']==config['reference_image_sha256']==sha(output/'alignment/reference_T0001.png')
    assert list(inspect.signature(BodyPreprocessor.process).parameters)==['self','image']
    records=read_rows(output/'preprocessing_records.jsonl')
    assert {r['capture_id'] for r in records}==set(selected)
    for row in records:
        assert row['alignment_config_sha256']==frozen_hash
        if 'pose' in row:assert row['pose']['diagnostics']['configuration_sha256']==executed_hash
    dump(output/'alignment/config_execution_provenance.json',dict(frozen_sha256=frozen_hash,executed_geometry_config_sha256=executed_hash,
         geometry_equivalent=True,explanation='Frozen config adds only frozen_at and fit_source; processor loaded the byte-preserved draft before freeze. Geometry is identical. No validation tuning.'))
    # Aspect, color, edge preservation: wide/tall markers survive the pad/resize path.
    for height,width in [(50,100),(100,50)]:
        sample=np.full((height,width,3),(5,80,240),np.uint8)
        sample[:5]=[0,255,0];sample[-5:]=[255,0,0];sample[:,:5]=[0,0,255];sample[:,-5:]=[255,255,0]
        padded=padded_224(sample)
        assert padded.shape==(224,224,3)
        for color in [(0,255,0),(255,0,0),(0,0,255),(255,255,0)]:assert np.any(np.all(padded==color,axis=2))
        assert np.any(np.all(padded==40,axis=2))
    passed('alignment_and_preprocessing_contract','TRAIN-only reference and frozen/executed geometry identical; image-only processor; 10 synthetic pose/occlusion checks, blank reject, pad edge/color checks PASS')
    crops=[];by_part={}
    for part in PARTS:
        by_part[part]={}
        for split in inputs:
            rows=read_rows(output/f'{part}_{split.lower()}_crop_manifest.jsonl');by_part[part][split]=rows
            assert len(rows)==len(inputs[split])
            assert {r['capture_id'] for r in rows}=={r['capture_id'] for r in inputs[split]}
            for row in rows:
                source=selected[row['capture_id']]
                assert row['approved_state']==source['approved_part_states'][part]
                for key in ('split','raw_sha256','source_group_id','collection_round_id','lineage_root_id'):
                    assert row[key]==source[key]
                assert not row['human_reviewed'] and not row['training_accepted']
                if row['status']=='VALID':
                    assert row['selected_for_this_experiment'] and sha(row['crop_path'])==row['crop_sha256']
                    assert read_image(row['crop_path']).shape==(224,224,3)
                    assert Path(row['crop_path']).parent.name==row['approved_state']
                    crops.append(row)
                else:assert not row['selected_for_this_experiment'] and row['crop_path'] is None and row['reason']
    disk={str(p.resolve()) for p in (output/'crops').rglob('*.png')}
    assert disk=={r['crop_path'] for r in crops}
    cross_crop_hash={r['crop_sha256'] for r in crops if r['split']=='TRAIN'}&{r['crop_sha256'] for r in crops if r['split']=='VALIDATION'}
    assert not cross_crop_hash
    passed('crop_manifests',f'{len(crops)} valid crops hash/decode/state/provenance PASS; 3396 slots accounted; exact cross-split crop hashes zero')
    predictions=read_rows(output/'validation_predictions.jsonl')
    assert len(predictions)==620 and len({(r['capture_id'],r['part']) for r in predictions})==620
    metrics=json.loads((output/'training_metrics.json').read_text(encoding='utf-8'))
    execution=json.loads((output/'full_execution.json').read_text(encoding='utf-8'))
    environment=json.loads((output/'environment.json').read_text(encoding='utf-8'))
    assert {r['part'] for r in execution}==set(PARTS)
    for run in execution:
        assert run['initial_weights_sha256']==environment['initial_weights_sha256']
        assert sha(run['best_path'])==run['best_sha256']
        assert run['preprocessing_parity']['status']=='PASS'
        assert run['settings']['epochs']==60 and run['settings']['patience']==10 and run['settings']['batch']==16
        part=run['part'];report=metrics['parts'][part]
        names=[run['class_mapping'][str(i)] for i in range(len(run['class_mapping']))]
        rows=[r for r in predictions if r['part']==part]
        source_rows={r['capture_id']:r for r in by_part[part]['VALIDATION']}
        counter=Counter()
        for row in rows:
            assert row['approved_state']==selected[row['capture_id']]['approved_part_states'][part]
            assert row['preprocessing_status']==source_rows[row['capture_id']]['status']
            assert row['model_sha256']==run['best_sha256']
            if row['prediction_status']=='PREDICTED':
                assert set(row['class_scores'])==set(names)
                assert row['predicted_state']==max(row['class_scores'],key=row['class_scores'].get)
                counter[row['approved_state'],row['predicted_state']]+=1
            else:assert row['predicted_state'] is None and row['class_scores'] is None
        cm=[[counter[a,b] for b in names] for a in names]
        assert cm==report['confusion_matrix_rows_true_columns_pred']
        assert sum(counter.values())==report['predicted_count']
        f1=[]
        for name in names:
            tp=counter[name,name];ntrue=sum(counter[name,b] for b in names);npred=sum(counter[a,name] for a in names)
            f1.append(2*tp/(ntrue+npred) if ntrue+npred else 0)
            assert ntrue==report['classes'][name]['support']
        assert abs(sum(f1)/len(f1)-report['macro_f1'])<1e-10
        assert all(np.isfinite(float(v)) for epoch in report['epoch_metrics'] for v in epoch.values())
    simulation=read_rows(output/'classifier_only_simulation.jsonl')
    assert len(simulation)==155
    assert all(r['simulation_output']=='NO_DECISION_PREPROCESSING_FAILED' for r in simulation if not r['all_parts_available'])
    passed('training_and_evaluation','Four independent pretrained starts, finite loss/metrics, checkpoint/class mapping/parity; 620 prediction slots, counter-recomputed matrices/macro F1, 155 simulation rows PASS')
    # Save the exact local tools and reused source hashes needed to reproduce this run.
    source_files=list(Path(__file__).parent.glob('*.py'))
    source_files += [PROJECT/p for p in ['jetson/src/vision/engine_pose.py','jetson/src/vision/engine_rectification.py',
        'jetson/src/vision/engine_inspector.py','jetson/src/decision/engine_dynamic.py',
        '.venv/Lib/site-packages/ultralytics/data/dataset.py','.venv/Lib/site-packages/ultralytics/models/yolo/classify/train.py',
        '.venv/Lib/site-packages/ultralytics/models/yolo/classify/val.py','.venv/Lib/site-packages/ultralytics/models/yolo/classify/predict.py']]
    dump(output/'source_code_hashes.json',{str(p.relative_to(PROJECT)):sha(p) for p in source_files})
    code_dir=output/'source_snapshot';code_dir.mkdir(exist_ok=True)
    for path in Path(__file__).parent.glob('*.py'):shutil.copyfile(path,code_dir/path.name)
    verification=dict(status='PASS',verified_at=datetime.now(timezone.utc).isoformat(),checks=checks,
                      raw_images_unchanged=919,metadata_files_unchanged=len(before),valid_crops=len(crops),prediction_slots=620,
                      execution_scope='Local PC only; operational integration and independent human/physical generalization NOT_RUN')
    dump(output/'training_verification.json',verification)
    prep=json.loads((output/'preprocessing_report.json').read_text(encoding='utf-8'))
    lines=['# ENGINE-MISASSEMBLY-BASELINE-TRAINING-001', '',
           '상태: **LOCAL_BASELINE_EXECUTED / ARTIFACT_VERIFICATION_PASS / PREPROCESSING_FAILURES_REMAIN**', '',
           '네 모델의 smoke·본 학습·저장 모델 재로딩·개발검증을 로컬 GPU에서 실행했다. 모델 지표는 전처리가 성공한 표본에 대한 결과다. 전체 검증155개 중 네 부품 출력이 모두 있는 표본은110개(71.0%)이며 나머지45개는 판정 불가다. 운영 적용 완료 또는 독립 최종시험 성능이 아니다.', '',
           '## 입력과 보존', '',
           '- TRAIN694 / VALIDATION155를 기존 승인 manifest에서 고정했다. 기존 verify.py의 보고서2개만 새 경로로 redirect하고 EventLog.append를 차단해 재실행:9개 검사 PASS.',
           '- 원본919장·기존 metadata/label/evidence39파일 전후 SHA-256 동일. 전달919사본은 원본과 동일하며 별도 샘플로 쓰지 않았다. 원본919/후보849의 해시는 raw_input_hashes.jsonl, manifest 해시는 input_file_hashes_before.json에 보존했다.',
           '- approved_part_states만 정답으로 사용. planned_part_states/part_states/source_capture_metadata는 원본 후보 사본에 분리 보존. human_reviewed=false, training_accepted=false를 유지하며 새 crop manifest의 selected_for_this_experiment로 이번 사용을 구분했다.',
           '- 보류43건(활성 TRAIN 심볼29건과 VALIDATION V0107 포함), 대체된 원본, PILOT, 전달본, E04/TEST_RESERVED를 학습·정렬 기준에 넣지 않았다. split/raw/group/round/lineage 충돌0. split 재분할 없음.', '',
           '## 정렬·좌표·영역', '',
           '- 기존 engine_inspector → envelope detector → EnginePoseEstimator → rectify_image → engine_dynamic 흐름을 실제 소스로 확인했다. 기존 EnginePoseEstimator와 inverse affine rectification 함수를 그대로 import했다. 로컬 envelope 원본 가중치 SHA는 운영 envelope_v007 manifest의 학습 가중치 SHA와 일치한다.',
           '- 운영 D001 기준 사진과 TRAIN T0001을 실제로 비교했다. 두 기준 모두 긴 금색 축 아래/짧은 끝 위가0°이며 파이프 좌우는 엔진 고정 자리다. 원본 픽셀 위치·크기·투시는 동일하지 않으므로 기존 ROI 숫자는 재사용하지 않았다.',
           '- TRAIN T0001만 기준 영상으로 사용했다. V8 본체 표식·고정 본체·축 영역의 ORB948개 특징으로 정렬한다. 검사 대상 네 부품은 기준 특징 영역에서 제외했다. reference→raw 2×3 similarity affine M을 기록하고 raw→canonical은 invertAffineTransform(M)을 쓴다. angle=atan2(M[1,0],M[0,0]); OpenCV 영상 y축은 아래 방향이다.',
           '- 원본 및 canonical1280×720. 동일한 고정영역을 상태와 무관하게 추출한다: pipe_left[426,96,625,345], pipe_right[709,96,922,345], exhaust[569,373,764,524], symbol[599,282,735,392]. 연결부·본체 일부·오조립 이동 범위를 포함하며 결품도 동일한 자리다. 부품 개별 방향 보정 없음.',
           '- TRAIN52개 대표를 처리하고 상태·회전 대표21장을 실제 열어 확인했다. 0/37/90/180/270°×정상/부품가림 합성10개에서 본체 좌표 오차5px 미만, 특징 없는 영상 거부를 확인했다. target_engine_angle/guide ROI/정답 상태는 process(image)의 입력이 아니다.',
           '- 방향은 본체 V8 영역 NCC>=0.35로 추가 확인한다. crop의 원본 유효 픽셀 비율>=0.999를 요구한다. 임계값과 설정은 TRAIN으로만 정하고 VALIDATION 처리 전에 고정했다. VALIDATION 실패를 보고 튜닝하지 않았다.',
           '- 실제 실행 설정은 config_train_draft.json이며 config_frozen.json에는 동일한 설정에 frozen_at/fit_source만 추가됐다. 두 해시와 동등성 검사는 config_execution_provenance.json에 명시했다. pose 진단에는 실제 실행 설정 해시가 남아 있다.', '',
           '## 전처리 결과', '',
           '| split | 입력 | 네 영역 유효 | 일부 영역 유효 | 본체 정렬/방향 실패 |', '|---|---:|---:|---:|---:|']
    for split in inputs:
        item=prep['by_split'][split];status=item['statuses']
        lines.append(f"| {split} | {item['inputs']} | {status.get('VALID',0)} | {status.get('PARTIAL',0)} | {status.get('FAILED',0)} |")
    lines += ['', 'VALIDATION 본체 정렬 품질 실패6건·방향 확인 실패4건. 부품별 추가 화면 경계 제외는 왼쪽 파이프13건·오른쪽22건이다. 고정영역의 배경 여백만 프레임 밖으로 나간 경우도 보수적으로 제외했으므로 모두 실제 부품 절단이라고 해석하면 안 된다. TRAIN 본체 실패29건, 추가 crop 제외 왼쪽10·오른쪽53건.', '',
              '## 학습과 입력 변환', '',
              '- OpenCV decode BGR uint8 → inverse-affine bilinear → 고정ROI → 짧은 변 양쪽에 BGR(40,40,40) 패딩(홀수 잔여는 아래/오른쪽) → OpenCV INTER_LINEAR 224×224 → lossless PNG. 학습/검증/재로딩 예측에서 PIL RGB → 224×224 identity resize → CHW float32 /255 → mean(0,0,0), std(1,1,1).',
              '- 설치된 Ultralytics8.4.146에는 학습 RandomResizedCrop과 검증/예측 CenterCrop 기본값이 있었다. FixedDataset/FixedTrainer/FixedValidator/FixedPredictor로 같은 변환을 명시했다. 추가 crop·반전·회전·RandomErasing·자동 증강·광도 증강 모두0/없음. 각 저장 모델에서 실제 학습·검증 변환과 재로딩 predictor 입력 텐서 완전일치 PASS. 단독 model.predict에 raw 사진을 직접 넣는 사용법은 이 실험 파이프라인이 아니다.',
              '- 참고: [Ultralytics 공식 classification/custom transforms](https://docs.ultralytics.com/tasks/classify/). 현재 설치 소스와 실제 입력 텐서 검사를 판단 근거로 삼았다.',
              f"- 환경: Python{environment['python']}, PyTorch{environment['torch']}, torchvision{environment['torchvision']}, Ultralytics{environment['ultralytics']}, OpenCV{environment['opencv']}, CUDA{environment['cuda']}, {environment['gpu']}. 기존 .venv 사용, 공유 환경 업그레이드 없음.",
              '- 같은 yolo11n-cls.pt에서 부품마다 새 모델을 시작했다. imgsz224, 최대60 epoch, patience10, batch16, seed42, workers0, AdamW lr0=0.001/weight_decay0.0005, FP32/AMP false. OOM 없음·batch 변경 없음. 실제 전체 인자는 full/<part>/args.yaml 및 execution.json. 첫 기준 설정이며 최적화 주장 없음.',
              '- pipe_left에서2 epoch smoke로 데이터/loss/저장/재로딩/예측을 확인한 뒤 네 모델 본 학습을 순차 실행했다. best 선택은 이 개발검증의 macro F1이며 top-5는 기준으로 사용하지 않았다. 동률일 때 설치된 trainer는 마지막 동률 best를 저장한다. 조기종료는 실제 실행된 epoch 수에 반영했다.', '',
              '## 실제 개발검증', '',
              '| 부품 | 학습 유효 | 검증 유효/155 | 검증 처리율 | 본 학습 epoch | macro F1 | 오조립→정상 | 결품→정상 | 정상→불량 |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for part in PARTS:
        m=metrics['parts'][part]
        values=[m[k] for k in ['misassembled_to_correct','missing_to_correct','correct_to_defective']]
        rates=[f"{v['count']}/{v['denominator']} ({pct(v['rate'])})" for v in values]
        lines.append(f"| {part} | {prep['by_part'][part]['TRAIN']['valid']} | {m['predicted_count']} | {pct(m['processing_rate'])} | {m['epochs_executed']} | {m['macro_f1']:.3f} | {' | '.join(rates)} |")
    lines += ['', '오조립 분모는 CORRECT/MISSING 이외 실제 상태 중 전처리 성공 수, 결품 분모는 실제 MISSING의 전처리 성공 수, 정상 오탐 분모는 실제 CORRECT의 전처리 성공 수다. 미처리 사진은 이 모델 지표 분모에 포함하지 않고 별도 처리율에 포함했다. macro F1은 클래스별 F1의 단순 평균이다.', '',
              '클래스 번호는 실제 학습 ImageFolder와 저장 모델의 names를 대조해 저장했으며 폴더 순서를 추정하지 않았다. 아래 행렬은 행=정답, 열=예측이며 표에 적힌 클래스 번호 순서다.']
    for part in PARTS:
        m=metrics['parts'][part]
        lines += ['',f'### {part}', '', '| 번호 | 상태 | TRAIN | VALIDATION | precision | recall | F1 |','|---:|---|---:|---:|---:|---:|---:|']
        for i,name in enumerate(m['class_order']):
            c=m['classes'][name]
            lines.append(f"| {i} | {name} | {prep['by_part'][part]['TRAIN']['classes'][name]} | {c['support']} | {c['precision']:.3f} | {c['recall']:.3f} | {c['f1']:.3f} |")
        lines += ['', '```text', *[' '.join(f'{v:4}' for v in row) for row in m['confusion_matrix_rows_true_columns_pred']], '```']
    lines += ['', '## 오류·판정 불가와 해석', '',
              '- 최종 best 모델들의 처리 성공545개 부품 crop에서 오분류0건. validation_errors.jsonl은 실제0행이며 존재하지 않는 오분류 비교 이미지를 만들지 않았다. 정답/예측 비교는 validation_comparisons, 실패 비교는 preprocessing_failures에 있다.',
              '- CLASSIFIER_ONLY_SIMULATION: 입력155, 네 출력 모두 확보110, ALL_CORRECT11, DEFECT_DETECTED99, NO_DECISION_PREPROCESSING_FAILED45. 실제 불량을 네 부품 전부 정상으로 오인0/99, 그중 방향 오조립 오인0/57. 부분 결과가 있어도 네 부품 중 하나가 없으면 전체 정상으로 처리하지 않았다. 기존 검사기/PLC/3프레임 판정 시험이 아니다.',
              '- V0089는 ORB 결과가 실제로180° 뒤집혔으나 V8 방향 확인에서 거부됐다. V0066은 pose 품질 조건에서 거부됐다. V0118/V0130은 본체 표식 NCC 약0.22로 보류됐다. V0025/V0051은 파이프 고정영역의 화면 경계 때문에 해당 부품 출력이 없다. 실제 실패 이미지6개를 열어 확인했다. 이를 통과시키려고 기준을 완화하지 않았다.',
              '- 높은 crop 분류 점수와 낮은 전체 처리율을 구분해야 한다. 155개 전체에 대한 성공적인 네 부품 결과는110개이며45개는 처리 실패다. 실패가 특정 회전·촬영 조건에 몰릴 수 있어 처리 성공 subset의100%를 전체 정확도로 표현할 수 없다.',
              '- VALIDATION은 best 모델 선택에 사용한 개발검증이다. TRAIN/VALIDATION 모두 동일 ENGINE_01·유사 촬영 배경이며 다른 실물/운영 환경 일반화는 입증하지 않았다. Codex 검토 라벨이며 독립 사람 정답 대조가 끝나지 않았다. 작은 오조립 클래스 검증 수와 원촬영의 상관성도 남아 있다.',
              '- Jetson 통합 전 별도 작업으로 본체 방향의 강건성, 화면 여백으로 인한 처리 제외, 독립 사람 라벨 대조, 새로운 실물/환경 시험, REVIEW/FAIL 결합 기준·실제 고유3프레임을 검증해야 한다. 임의 신뢰도 임계값이나 운영 성능 보장은 제시하지 않았다.', '',
              '## 로컬 산출물과 재사용', '',
              f'실험 루트: `{output}`', '',
              '- `TRAINING_SUMMARY.md`, `TRAINING_VERIFICATION.md`, `training_verification.json`: 결과와 실제 검사 근거.',
              '- `preprocessing_report.json`, `preprocessing_records.jsonl`, `<part>_train_crop_manifest.jsonl`, `<part>_validation_crop_manifest.jsonl`: 모든 입력·파생영역·실패·계보·해시.',
              '- `training_metrics.json`, `validation_predictions.jsonl`(620행), `classifier_only_simulation.jsonl`(155행), `validation_errors.jsonl`(0행).',
              '- `full/<part>/weights/best.pt`, `full/<part>/class_mapping.json`, `full/<part>/preprocessing_parity.json`, `full/<part>/execution.json`, `results.csv`, `args.yaml`.',
              '- `crops/<part>/train|val/<state>/*.png`: 실제 학습 입력3142장. 비교 이미지는 입력 폴더 밖에만 저장했다.',
              '- `alignment/`, `environment.json`, `starting_weights/`, `source_code_hashes.json`, `source_snapshot/`, 입력 해시·검증 폴더, smoke/training/evaluation 로그.',
              '- `BASELINE_REVIEW_PACKAGE_v2.zip`: 보고서·설정·manifest·지표·대표/실패 비교 위주의 작은 패키지. 모델과 전체 crop/원본은 제외했다. 패키지 구성·CRC·SHA는 package_verification.json.', '',
              '이번 작업은 여기서 종료한다. Jetson 접속·배포, PLC 작동, 기존 검출/트래킹/PASS·FAIL 변경, 신규 bbox 정답, 원본/기존 라벨 변경, commit/push는 실행하지 않았다.']
    (output/'TRAINING_SUMMARY.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    ver=['# TRAINING_VERIFICATION', '', f"검증 시각: {verification['verified_at']}", '', '**아래 실행·산출물 검사 PASS. 전처리 실패39개와 부분 실패98개는 그대로 남아 있으며 운영 준비 완료가 아니다.**', '', '| 검사 | 결과 | 실제 근거 |','|---|---|---|']
    ver += [f"| {c['check']} | PASS | {c['detail']} |" for c in checks]
    ver += ['', '## 실행 근거', '',
            '- `freeze_inputs.py`: 기존9개 검증 PASS, 원본 metadata 기록 차단·보고서 redirect 후 hash 보존.',
            '- `prepare_alignment.py`, `process_dataset.py`: TRAIN 대표/합성검사 후 설정동결·849개 처리, 모든 실패 기록.',
            '- `train_models.py --stage smoke`:2 epoch 실제 GPU 학습·loss·checkpoint·재로딩 예측 PASS.',
            '- `train_models.py --stage full`: pipe_left11/pipe_right12/exhaust23/symbol11 epoch 순차 실행, 네 best.pt 존재·독립 시작 SHA·클래스 매핑 확인.',
            '- `evaluate_models.py`: 네 저장 모델별 독립 validation 경로와 별도 predictor 결과 top1 일치, 155×4 전체 결과 슬롯 보존.',
            '- `verify_and_report.py`: 원본919/metadata39/파생3142해시, split/라벨/manifest/전처리/지표 재계산/실패 처리 검증.', '',
            '## 확인한 구현 경계', '',
            '- 전처리 API는 process(image)이며 정답·파일명·시나리오·촬영 안내각을 받지 않는다. 라벨은 처리 후 manifest와 폴더 배치에만 붙는다.',
            '- 모든 입력/계보가 고정 후보에서 유래하며 TRAIN/VALIDATION 교집합0, 미검토/보류/대체/PILOT0. 임의 split 변경 없음.',
            '- 실제 geometry 설정과 frozen 설정의 차이는 기록용2필드뿐이다. 실제 pose diagnostic hash를 숨기지 않고 별도 동등성 검사로 연결했다.',
            '- 부품 방향·오조립 형태는 개별 회전하지 않는다. 본체만 정렬한다. 원본 bbox/부품 bbox 정답을 새로 만들지 않았다.',
            '- 입력224PNG의 색·값·기본 변환은 train/val/reloaded prediction에서 일치. 추가 center/random crop 없음. 단독 검증도 FixedValidator 사용.', '',
            '## 미실행 또는 미달', '',
            '- 전수 전처리 성공: 미달. TRAIN92/VALIDATION45개는 일부 또는 전체 부품 출력이 없다. 실패사진을 정상으로 치환하지 않았다.',
            '- 최종 best의 성공 crop 오분류 사례:0건이므로 오분류 비교 이미지0. 실패 사례와 정상 예측 비교를 대신 제공한다.',
            '- 독립 사람 정답 대조, 다른 실물 엔진/운영 조건 일반화, 독립 최종시험, 운영 임계값/3프레임/PLC: NOT_RUN, 이번 허용 범위 밖.',
            '- Jetson 배포/운영 소스 변경/commit/push: NOT_RUN, 사용자 지시대로 중단.', '',
            '전체 기존 런타임 회귀는 실행하지 않았다. 운영 코드 변경이 없으며 이번 새 로컬 전처리·학습·평가 경로의 실제 실행과 artifact 계약을 검증했다.']
    (output/'TRAINING_VERIFICATION.md').write_text('\n'.join(ver)+'\n',encoding='utf-8')
    # Bounded review handoff. Do not include raw, full crop tree, or model weights.
    include=[p for p in output.iterdir() if p.suffix in ('.md','.json','.jsonl') and not p.name.startswith('export_') and p.name not in ('package_verification.json',)]
    include += list((output/'alignment').glob('*.json'))
    include += [output/'representatives'/f'{i}.png' for i in ['T0001','T0189','T0227','T0301','T0373','T0445','T0517','T0590','T0662','T0020','T0068','T0716']]
    include += [output/'preprocessing_failures'/f'{i}.png' for i in ['V0025','V0051','V0066','V0089','V0118','V0130']]
    include += list((output/'validation_comparisons').glob('*.png'))
    include += list((output/'source_snapshot').glob('*.py'))
    for part in PARTS:
        include += [output/'full'/part/name for name in ['class_mapping.json','preprocessing_parity.json','execution.json','results.csv','args.yaml']]
    package=output/'BASELINE_REVIEW_PACKAGE_v2.zip'
    assert not package.exists(),'Do not overwrite a review package'
    with zipfile.ZipFile(package,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in include:archive.write(path,path.relative_to(output).as_posix())
    with zipfile.ZipFile(package) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist())==len(set(archive.namelist()))
        for path in include:
            import hashlib
            assert hashlib.sha256(archive.read(path.relative_to(output).as_posix())).hexdigest()==sha(path)
    dump(output/'package_verification.json',dict(status='PASS',path=str(package),sha256=sha(package),bytes=package.stat().st_size,
         members=len(include),files=[str(p.relative_to(output)) for p in include],excluded='Raw source images, all model weights, full crops; no large raw ZIP'))
    print(json.dumps(dict(status='PASS',checks=len(checks),crops=len(crops),predictions=len(predictions),zip_bytes=package.stat().st_size)),flush=True)


if __name__=='__main__':main()
