# PROXY-DATASET-TRAIN-001 — 실제 Proxy 데이터셋과 Windows 첫 학습

Status: DONE / VERIFIED — 승인·train120/val60 구성·Windows 단일 baseline100epoch 완료

2026-09-13 사용자가 오늘 데이터셋 제작과 학습까지 진행하도록 요청했다. Jetson Orin Nano는 아직 연결하지 않아 현재 실행 범위는 Windows다. HUMAN-CAPTURE-001의 B01 완료 결과와 실제 수집 폴더를 이어받는다.

## 순서와 완료 조건

1. 기존 스탠드 계획과 같은 수집 폴더에서 남은 촬영을 한 장씩 진행한다. 저장과 사람 확정, 재촬영 원본을 구분한다.
2. V0-T05: 기존 앱으로 확정 본수집을 내보내고 실제 부품 위치를 라벨링·검토한다. 화면 안내 ROI나 상태명만으로 위치 정답을 만들지 않는다.
3. V0-T06: 실제 수집 그룹을 유지해 train/validation/test를 분리한다. B03/B04는 실제 독립 회차 선언이 필요하며 시험 예약 자료는 개발에 사용하지 않는다.
4. V0-T07: 기존 프로젝트 GPU 환경에서 고정 baseline을 한 번 학습하고 설정·버전·시간·로그·checkpoint·validation 지표를 보존하고 재로드한다.

제품별 클래스/데이터 설정은 공통 학습·추론 구조와 분리한다. 원본·이벤트·검토 이력과 무관한 CAD 변경은 보존하고 실제 자료는 Git에 올리지 않는다. 학습 완료는 엔진 검사나 Jetson 실행 검증의 완료가 아니다.

## 최종 결과 (2026-09-13)

- 사용자 명시 전체 승인으로 B03 v00360장의 상태만 confirmed로 기록했다. 승인본/검토 근거에 초안 SHA·60개 ID 연결, 사각형 변경0, 보류0. B01/B02 재승인/재변환0.
- 기존 via_to_yolo로 B03 validation_candidate60장/120객체 변환. 공통 구성기로 train120/val60/test0예약 구성. 해시·좌표·클래스·사진/촬영 origin/session/episode/capture 누수 검사 PASS,978개 원본/기존 작업 보호 파일 보존.
- yolov8n.pt →3개 제품 클래스, RTX5070 Laptop cuda:0, imgsz640/epochs100/batch16/seed42, AdamW lr0.001, FP32. 회전5°/이동0.05/크기0.1/HSV0.015,0.2,0.2; flip/mosaic/mixup/cutmix/copy_paste0. 실제 args.yaml과 입력 해시 보존.
- 단일 학습 프로세스 exit0,100epoch 완료. 총313.42초(학습 호출 초기화·최종 검증 포함), epoch loop300.78초. best/last CUDA 재로드 PASS.
- best B03 검증: Precision0.9981466083, Recall1.0, mAP50 0.995, mAP50-95 0.8334960747.60장 예측 저장, conf0.25·IoU0.5 TP120/FP0/FN0. 대표 오탐/미탐은 이 기준에서 없다. 상대적으로 덜 맞는 경계 사례0002 R IoU0.759,0055 L IoU0.774를 확인했다.
- Evidence: docs/verification/PROXY-DATASET-TRAIN-001-BASELINE-20260913.json; training/experiments/earbud_case_v0_20260913_v001/BASELINE_REPORT.md, baseline_result.json, validation_error_analysis.json. 새 집중 테스트8+4개 PASS.
- B04 최종 Test는 미사용 예약. 추가 튜닝·Jetson 배포 미실행. 한 B03 그룹의 검증이며 엔진 데이터 일반화·최종 정상/불량 프로그램·DB 완료는 미확인이다.

## 이전 체크포인트 (2026-09-13, 전체 승인 후 학습 중)

사용자의 "모든사진 OK라는거야 일일이 확인 안받아도되"를 B03 v003 전체60장 부품 종류·사각형 승인으로 기록했다. 새 reviewed/human_review_all60_v001.json에 초안 SHA와60개 ID를 연결했다. 기존 사각형 수정0·보류0·변환60장120객체. B01/B02120장 승인/출력 재사용.
T06 완료: training/outputs/datasets/earbud_case_v0_B01_B03_20260913_v001/의 train120/val60/test0 예약. 원본/후보/라벨/승인 해시와 좌표 검사, 촬영 origin/session/episode/capture 및 사진 해시 누수0. 새 집중 검사8+4개 PASS.
T07 단일100epoch CUDA baseline 실행 중. 설정 training/baseline_config.yaml, 출력 training/experiments/earbud_case_v0_20260913_v001/. run_started.json이 있으므로 중복 실행 금지. 종료 후 baseline_result.json과 best/last 및 B03 예측/오류 집계를 확인한다.

## 이전 체크포인트 (2026-09-13, B03 촬영 완료)

- 기존 GUI에서 B03 재준비 사람 선언을 기록했고 별도 origin_group OG697C8F89699D4572로60장/15묶음 촬영 검토가 완료됐다. 3조명 각20장·4상태 각15장, 검토 대기0. 전체 원본222장/49세션/재촬영 이력28장 보존. 이벤트812개 체인 PASS, B01/B02와 원본 해시·origin_group 중복0. 선언 자체가 물리적 독립성을 자동 증명하지는 않는다.
- 기존 내보내기 EXPORT6F74307E8E314691: 학습120·검증60. 기존 준비 스크립트로 B03_20260913를 별도 생성했다. 최신 project_draft_all60_v003.json은 실제 원본60장을 보며 작성한120개 사각형(L30/R30/case60), 모두 pending이다. 전체 검토 표시를 확인한 뒤 케이스11장의 경계를 보정했고 과거 버전도 보존했다. 형식/기하·출처·978파일 보존 검사 PASS; 사람 라벨 승인0.
- 검토용: training/outputs/labeling/B03_20260913/review_all60_v003/. 원본/작업용 PNG와 검토 표시는 별개이며 검토 표시는 모델 입력이 아니다.
- 다음: B03 라벨 사람 검토 → 승인본/근거 기록 → via_to_yolo.py validation_candidate 변환 → T06 → T07. B04 최종 시험은 미시작 예약 유지. 실제 데이터 첫 학습은 미실행이며 과거 t02_smoke와 구분한다.
- Evidence: docs/verification/PROXY-DATASET-TRAIN-001-B03-CAPTURE-20260913.json, docs/verification/PROXY-DATASET-TRAIN-001-B03-LABEL-DRAFT-20260913.json.

## 이전 근거 (보존)

T05 완료 범위: 기존 VIA 누적 초안120장·240개 영역을 사용자가 부품 종류/경계까지 승인했다. 새 reviewed JSON과 SHA/이미지 ID/응답 근거가 있는 승인 기록을 저장하고, 공통 schema 기반 VIA→YOLO 변환기로120장/240객체 학습 후보를 만들었다. 보류0, 클래스0/1/2=60/60/120, 집중 테스트16개 및 실제 출력 독립 검사 PASS. 사각형·원본·초기/기존 초안·촬영 그룹 보존. 결과는 `training/outputs/yolo/B01_B02_reviewed_20260913_v001/`이며 사용자 검토와 기하 검사는 구분한다. 저장기·수집 GUI·브라우저를 조작하지 않았다.

B01/B02 각60장으로 사람 확정 본수집120장. 기준2장·준비12장 확정 유지, 과거 재촬영28장 포함 원본162장. 34세션 PNG/manifest/해시 검증과 599이벤트 체인 통과. B03/B04 미시작이다.

기존 GUI 내보내기 EXPORTA48C70FCE9B94A62는 학습/라벨링 후보120, 검증0, 시험0, 합성0, 제외42장이다. B03 목적은 validation_candidate이며 이전 두 회차의 같은 origin_group을 그대로 쓰면 보호 규칙으로 정지한다. 날짜 검사는 없지만 실제 촬영 중단·시간/설치 재준비를 확인해야 한다. UI '오늘은 멈추고' 문구만으로 내일까지 기다려야 한다고 안내하지 않는다. 원본과 규칙 변경·우회는 하지 않았다.

현재 프로젝트 .venv: torch2.11.0+cu128, Ultralytics8.4.146. RTX5070 Laptop GPU에서 cuda:0 행렬 연산·동기화 성공, 결과 유한·합3920. 실제 데이터 학습은 미실행이다. 기존 GPU smoke는 환경 참고로만 재사용한다.
