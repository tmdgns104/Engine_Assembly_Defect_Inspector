# 촬영 → 라벨링 → 데이터셋 → 학습 코드 안내

노트북에서 데이터를 만들고 학습한 코드를 여기에 보관합니다. **이번 게시에서는 촬영·라벨 승인·학습을 다시 실행하지 않았습니다.** Jetson 운영 프로그램/가중치는 [설치 안내](../../jetson/INSTALL_OPERATING_KO.md)에 있습니다.

## 코드와 자료의 구분

| 단계 | 코드 | 입력 → 출력 |
|---|---|---|
| 촬영 | [capture_windows](capture_windows), [start_capture.cmd](../start_capture.cmd), [start_misassembly.cmd](../start_misassembly.cmd) | 실제 USB 카메라 → PNG, 촬영 순서/조명/각도/결품 상태/그룹 원장 |
| 촬영 검토·인계 | [engine_exports.py](capture_windows/engine_exports.py) | 검토한 수집 → 원본 해시와 provenance를 연결한 라벨링 인계 |
| 사각형 라벨 작업 공간 | [prepare_via_project.py](scripts/prepare_via_project.py) | 인계 자료 → 원본 사본·VIA JSON·제품 label_schema. 자동 정답 승인 없음 |
| 승인 라벨 변환 | [via_to_yolo.py](scripts/via_to_yolo.py) | 실제 검토 기록 + reviewed JSON → YOLO txt·PNG·candidate_manifest |
| 학습/검증 분리 | [build_grouped_dataset.py](scripts/build_grouped_dataset.py) | train/validation 후보 → 중복·촬영 그룹 검사, dataset.yaml·분리 목록 |
| 일반 검출 학습 | [train_baseline.py](scripts/train_baseline.py), [evaluate_baseline.py](scripts/evaluate_baseline.py) | 명시한 YAML + CUDA → best/last.pt·실행 설정·검증 결과 |
| 현재 엔진 부품 검출 학습 원본 | [train_engine_parts.py](engine_detection/parts/train_engine_parts.py) | CFA8507의 검토 사각형·원본 ZIP → 3클래스 YOLO11n |
| 엔진 전체 검출 학습 원본 | [envelope](engine_detection/envelope) | 엔진 전체 bbox 구성/수정 → YOLO11n 1클래스 학습·ONNX 내보내기 |
| 부품별 참고 분류 학습 | [engine_baseline](engine_baseline) | 부품 상태 라벨 → 몸체 정렬·4자리 crop → 부품별 분류 모델 4개 |
| 참고 분류의 전처리 보완·평가 | [engine_recovery](engine_recovery) | TRAIN 기준 특징/유효 영역 → 동결 전처리, 기존 분류기 재평가·보고서 |

`engine_detection`, `engine_baseline`, `engine_recovery`는 실제 실험 소스입니다. 당시 입력 파일·승인·모델 해시·경로가 고정된 부분이 있어 **다운로드 후 전부 순차 실행하는 자동 재학습 프로그램이 아닙니다.** 특히 `engine_baseline/process_dataset.py`의 검토 목록과 `freeze_inputs.py`의 자료 수량은 과거 고정 실험 기록입니다. 새 자료의 검토 사실이나 사용자 승인으로 재사용하지 않습니다.

## 1. 수집과 라벨 기준

기존 수집은 같은 폴더에서 재개하고 원본·재촬영 이력·촬영 그룹을 보존합니다. 준비 버튼은 촬영 준비 확인이며 사진/라벨 검토 승인이 아닙니다. [엔진 제품 schema](datasets/engine/engine_model_top_v0/label_schema.json)와 [촬영 계획](datasets/engine/engine_model_top_v0/collection-plan.json)을 사용합니다.

VIA에서는 실제 보이는 부품에 사각형을 그립니다. 결품 상태는 촬영 provenance에 남고, 빈 자리에 가짜 부품 box를 만들지 않습니다. 검토 이미지의 박스/문구가 그려진 PNG는 모델 입력으로 사용하지 않습니다. `via_to_yolo.py`의 사람 검토 기록은 대상 JSON/schema/provenance SHA와 실제 승인 이미지 ID에 연결됩니다. 코드 실행만으로 승인받았다고 기록하지 않습니다.

간편 수집의 추가 데이터 연결은 [misassembly_dataset.py](capture_windows/misassembly_dataset.py), 부품 상태·가시성·회차·검토 이력·내보내기는 [misassembly_readiness.py](capture_windows/misassembly_readiness.py)에 있습니다. 이 모듈은 기존 수집 앱의 단계별 기능이며 독립 라벨링 실행기가 아닙니다. 현재 공개 UI에 연결된 범위와 모듈 구현 범위를 구분합니다.

## 2. 재사용 가능한 VIA·YOLO 명령

Windows 프로젝트 루트에서 현재 `.venv`를 명시합니다. 패키지 경로만 현재 폴더 구조에 맞춥니다.

```powershell
$env:PYTHONPATH = (Resolve-Path .\notebook).Path + ';' + (Resolve-Path .\jetson).Path
.\.venv\Scripts\python.exe -B -X utf8 -m training.scripts.prepare_via_project --help
.\.venv\Scripts\python.exe -B -X utf8 -m training.scripts.via_to_yolo --help
.\.venv\Scripts\python.exe -B -X utf8 -m training.scripts.build_grouped_dataset --help
```

실제 입력을 준비한 뒤 사용합니다(꺾쇠 항목은 자신의 경로로 교체).

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m training.scripts.via_to_yolo --project <reviewed.json> --schema <label_schema.json> --provenance <provenance.json> --review-record <human_review.json> --original-root <collection> --output <새_변환폴더> --purpose train_candidate
.\.venv\Scripts\python.exe -B -X utf8 -m training.scripts.build_grouped_dataset --train <train_candidate_manifest.json> --val <validation_candidate_manifest.json> --output <새_dataset폴더>
.\.venv\Scripts\python.exe -B -X utf8 -m training.scripts.train_baseline --config <학습설정.yaml>
.\.venv\Scripts\python.exe -B -X utf8 -m training.scripts.evaluate_baseline --experiment <학습결과폴더>
```

검증 후보 변환에는 `--purpose validation_candidate`를 씁니다. 학습 YAML은 `model`, `data`, `project`, `name`, `device`와 실제 학습 인자를 지정합니다. `data`는 위 단계가 만든 dataset.yaml입니다. 이미 시작한 학습 폴더를 재사용하지 않습니다. 이 도구가 만든 dataset_integrity/split_manifest가 필요하므로 임의 YAML만 넣어 실행하지 않습니다.

분리는 이미지 SHA·origin_group/session/episode/capture ID를 검사합니다. 파일명이나 그룹 이름만 바꿔 독립성을 만들지 않습니다. E04/B04처럼 예약된 Test는 학습·보정·개발 검증에 사용하지 않습니다. 자세한 입력/출력 계약은 [scripts/README.md](scripts/README.md)에 있습니다.

## 3. 운영 모델을 어떤 자료와 코드로 만들었는가

| 모델 계통 | 출처/설정 | 현재 사용 |
|---|---|---|
| 엔진 부품 검출 | CFA8507 E01/E02 train144, E03 val72. `train_engine_parts.py`: YOLO11n, 기본100epochs/imgsz640/batch8/seed42, AMP OFF, flip/rotation/mosaic OFF. 원본 best.pt SHA `42db183006ad2a4f61dc9c22e7a61a5b506cdacb5099004fc7c3b73b74bf5259` | `dynamic_parts_005/model.plan`; gray_pipe(두 자리), exhaust_top, symbol_module |
| 엔진 전체 검출 | 같은 개발 분할144/72, 별도 전체 bbox. `envelope/train_envelope.py`: YOLO11n,100epochs/640/batch8/seed42, 회전180·translate0.2·scale0.25·mosaic0.5. best.pt SHA `cf117defe782e1ae8b355e0ed13c014fc6f1538aa2dcdbe0fb6cfa54200f7755` | `envelope_v007_fp16/model.plan`; product_envelope |
| 부품별 참고 분류 | 고정 원본 후보 train694/val155 → 전처리 통과 crop만 사용. `engine_baseline/train_models.py`: YOLO11n-cls,224px/60epochs/patience10/batch16/seed42/AdamW, 강한 무작위 증강 없음 | 왼쪽/오른쪽 파이프·배기·문양 각각의 `.pt`. 최종 PASS/FAIL에는 오조립 점수를 반영하지 않음 |

실제 epoch 수·채택 가중치는 해당 run의 `args.yaml`, `execution.json`, 결과 파일과 해시로 확인합니다. 설정 최대 epoch를 실제 완료 epoch라고 쓰지 않습니다. 참고 분류 후보 원본 수694/155는 모든 crop의 학습 수를 뜻하지 않습니다. 당시 라벨 출처는 `Codex visual review; human_reviewed=false`로 기록돼 있으며 사람 전수 검증으로 바꾸지 않습니다.

TensorRT 최종 모델 출처/shape/전처리/해시는 [부품 manifest](../../jetson/products/ENGINE_Z3005_5/dynamic_parts_005/manifest.json)와 [엔진 전체 manifest](../../jetson/products/ENGINE_Z3005_5/envelope_v007_fp16/manifest.json), 참고 모델은 [동결 manifest](../../assets/misassembly_runtime/FROZEN_MANIFEST.json)에 있습니다. 부품 학습과 전체 검출 학습은 별개이며, 과거 4클래스 통합 후보를 운영 모델 학습 결과로 혼동하지 않습니다.

## 4. 과거 고정 실험을 읽는 순서

1. `engine_detection/parts/train_engine_parts.py`: source_index·검토 bbox 검증 → 원본 지정 항목만 추출 → YOLO → CUDA학습 → val·모델 해시.
2. `engine_detection/envelope/`: `prepare_data` → `build_envelope`/`finalize_envelope` → `train_envelope` → `export_envelope`. 과거 후보/원본 폴더와 검토 결과가 필요합니다. bbox 자동 수정 제안과 실제 시각 검토는 구분됩니다.
3. `engine_baseline/`: `freeze_inputs` → `prepare_alignment` → 대표 이미지 검토 → `process_dataset` → `train_models` → `evaluate_models` → `verify_and_report`. `classification.py`가 train/val/predict의 동일 전처리를 정의합니다.
4. `engine_recovery/`: `investigate` → `fit_train` → `run_preprocessing` → `replay_frozen`/`evaluate` → `verify_artifacts`. 여기서 fit은 TRAIN 특징 기준 보완이며 분류 모델 재학습이 아닙니다.

원본 학습 코드의 과거 경로는 출처를 숨기지 않기 위해 보존했습니다. [SOURCE_PROVENANCE.json](engine_detection/SOURCE_PROVENANCE.json)에 이관 전 위치·SHA를 기록했습니다. `source_index.json`, `bbox_candidates.json`, 원본 ZIP, `data/guided_capture_20261001`, 과거 `runs/...`의 JSON/원본/선행 모델이 없으면 고정 실험은 재현되지 않습니다. 새 데이터 작업은 기존 자료를 덮어쓰지 않고 별도 입력·검토·새 출력 경로로 준비합니다.

## 5. GitHub에 있는 것과 없는 것

- 포함: 촬영/검토/변환/분리/학습/평가 소스, 제품 schema·계획, 현재 사용 모델·기준 자산, 승인된 검사 SQLite 보관본.
- 제외: 전체 촬영 PNG/영상·라벨 원본 모음·보호된 최종 시험·모든 학습 run·개인 환경·SSH 키. 소스 공개와 전체 학습 데이터 공개는 다릅니다.
- 이번 검증: 구문/의존성·합성 입력의 라벨/분리·설치 보존 검증. 신규 학습/GPU 성능/새 라벨 정확도 검증은 실행하지 않았습니다.
