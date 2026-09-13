# Codex 실행 지시서 — 단일 튜닝 후 Jetson 공통 검사 시스템

작성: 2026-09-13 / 실행 지시서 v1
작업 공간: `D:\OneDevice_Team_project`
권장 Codex 설정: 사용자가 선택한 `gpt-5.3-codex-spark / high / Fast OFF` 유지. 확인하지 못한 설정을 적용했다고 보고하지 않는다.
목표: 이어폰으로 실제 촬영→검사→원기록→Mock 제어→PC 이력을 연결하고, 엔진 수령 후 데이터·모델·Recipe·촬영 프로파일을 교체하여 공통 소프트웨어를 재사용한다.

## 0. 이번에 승인된 범위와 읽는 순서

- 모델 튜닝은 **신규 학습 최대 1회**다. 그 뒤 추가 모델 탐색 없이 배포·검사 소프트웨어에 집중한다.
- 이 문서의 순서는 이번 구현 제안이다. 아래 노션 계약 요약은 PLAN-r3 요구사항이며, 소프트웨어 구현 완료 증거가 아니다. Codex에 Notion 연결이 없으면 이 요약으로 진행하고, 실제 계약 충돌이 생길 때만 필요한 부분을 요청한다. 이번 지시는 노션 본문·제출 계획서 양식 변경을 포함하지 않는다.
- 처음에는 0~3절과 현재 저장소 지침·STATUS·관련 파일만 읽어 튜닝을 시작한다. 다음 단계에서 4절, 5~8절, 9~10절을 필요한 순서로 읽는다. 같은 문서 전체를 매번 다시 읽지 않는다.
- 작은 구현·시험 단위로 순차 진행한다. 기존 범위에서 다음 단위로 넘어갈 때마다 사용자 승인을 요구하지 않는다. 한꺼번에 모든 파일을 작성한 뒤 시험을 몰아서 하지 않는다.
- 단계가 바뀔 때만 `지금부터 [튜닝/모델 변환/Windows 검사 구현/Jetson 배포/통합시험]합니다. 실행 위치: ...`를 한 줄로 알린다.
- 사용자가 해야 하는 것은 카메라 연결·물체 배치·실제 결과 확인 등 물리 작업이다. 필요한 행동 하나씩 안내한다. 파일 확인·구현·변환·검증·기존 결과 재사용은 직접 진행한다.
- 추가 유료 API, CAD 수정, 새로운 데이터 수집/라벨링 UI, 전역 Skill/Hook 개선, 대규모 문서 재작성, 자동 Reject, 다품종 동시 운전, RAG, ROS 2/Gazebo, OEE, 실제 모터 구동은 이번 범위에서 제외한다.
- 시스템/도구의 권한·중단 지침은 준수한다. 비밀정보를 채팅·로그에 남기거나 보안 제한을 우회하지 않는다.

### 구현 경로

| 순서 | 실행 위치 | 실제 완료물 |
|---|---|---|
| S1 | Windows GPU | 고정 ROI 단일 튜닝 → 기준 모델과 비교 → 하나 선택 |
| S2 | Windows, Jetson은 가능하면 읽기 전용 관측 | 선택 모델·전처리 묶음, ONNX, 결과 비교 |
| S3 | Windows | Worker/Service 최소 계약, 실제 모델 Replay → 판정 → 파일/DB → 작은 조회 화면 |
| S4 | Jetson | 대상 환경의 TensorRT 엔진, 실제 USB 촬영 → 판정 → 로컬 저장·화면 |
| S5 | Jetson + Windows | Mock 요청/ACK/복구, PC 기록·이미지 수집, 운영 화면 |
| S6 | 각각의 실제 실행 장비 | 장애·재기동 시험, 성능 기록, 실행 안내, 엔진 교체 안내 |

S3는 최소 동작 경로부터 완성하고 S4 실기기 연결을 앞당긴다. PC 통계나 모든 확장 기능이 끝날 때까지 실제 Jetson 촬영을 미루지 않는다. Jetson 접속이 막히면 S4만 대기로 남기고 Windows에서 가능한 S5/S6를 진행한다. 이 S번호는 작업 순서 표기이며 기존 V0-Txx/ARCH-Txx를 재번호화하지 않는다.

## 1. 완료된 작업과 오류 요약 정정

이하는 사용자가 제공한 실행 로그의 상태다. 디스크에 후속 결과가 있으면 더 최신인 실제 결과를 확인하여 재사용한다.

- 기준 실험: `training/experiments/earbud_case_v0_20260913_v001/`
- 모델: `baseline/weights/best.pt`, 원본 COCO 사전학습 YOLOv8n에서 학습했다. COCO8 smoke 체크포인트가 아니다.
- B01/B02 train 120장·240객체, B03 val 60장·120객체. 라벨 승인과 YOLO 변환 완료. B04는 최종 시험 예약으로 미사용.
- 실제 기준 설정: imgsz 640, epochs 100, batch 16, seed 42, AdamW lr0.001, FP32, workers0. 회전5도/이동0.05/크기0.1/HSV0.015·0.2·0.2, flip/mosaic/mixup/cutmix/copy_paste0. 세부값은 실제 args.yaml을 따른다.
- 기존 검증: P0.9981466/R1.0/mAP50 0.995/mAP50-95 0.8334961. conf0.25, 클래스 일치·정답 매칭 IoU0.5에서 TP120/FP0/FN0.
- 평가·오류 분석 완료. 모델 학습/추론 재실행0, 라벨 수정0, B04 접근0, Jetson 실행0.
- OPPOSITE confidence 평균0.9433, BASE0.9661, DIM0.9668. **DIM의 일관된 저하는 없다.** 평균 IoU는 BASE가 가장 낮다. 이어폰 평균 IoU 약0.878, 케이스 약0.958.
- 마지막 자동 Conversation recap의 `DIM 쪽 일관적 성능 저하가 확인됩니다`는 본문/집계와 상충한다. 본문과 실제 JSON을 기준으로 짧게 정정하고 분석을 다시 시작하지 않는다.
- 분석 추천: 고정 ROI 1순위, 전체 프레임 imgsz768 2순위. 이번에는 **ROI 한 번만 실행**하며, 이전 768 제안과 병렬 실행하지 않는다.

우선 읽을 파일:
`docs/STATUS.md`, 현재 T08 작업 파일, 기존 실험의 `ERROR_ANALYSIS.md`, `error_analysis_supplement.json`, `baseline/args.yaml`, `baseline_result.json`, 기존 학습/평가 스크립트.
데이터 설정: `training/outputs/datasets/earbud_case_v0_B01_B03_20260913_v001/dataset.yaml` 및 같은 폴더 split_manifest.
Git 상태·진행 중 학습 프로세스·기존 튜닝 결과를 한 번 확인한다. 완료된 촬영/라벨 승인/기준 학습/분석은 반복하지 않는다.

## 2. S1 — 고정 ROI 단일 튜닝

### 유일한 변경 변수

- 원본 1280×720 기준 고정 ROI: xyxy `[287, 168, 863, 628]`, 크기576×460.
- 배열 crop은 `image[168:628, 287:863]`이며 오른쪽·아래쪽은 제외 경계다.
- 분석 당시 train 라벨 전체 외곽+48px 여유로 정한 영역이다. B03는 포함 여부만 검사했다. 매 이미지 정답을 보고 crop하지 않는다.
- imgsz640, 같은 원본 COCO pretrained, train120/val60, epochs100/batch16/seed42/AdamW/FP32와 기존 증강 수치를 유지한다. 학습된 baseline best.pt에서 이어 학습하지 않는다.
- 실제 증강의 공간 효과가 crop으로 달라질 수 있음을 기록한다. 입력 크기768, CLAHE, Gamma, sharpen, denoise, 다른 모델/seed/epoch 실험을 추가하지 않는다.

### 데이터 변환과 보존

- 원본/승인 라벨/기존 출력은 보존한다. 파생 crop 데이터와 설정은 새 버전의 경로에 둔다.
- 이미지와 모든 박스를 함께 변환한다. 원본 좌표에서 x는287, y는168을 빼고, 실제 crop 크기로 YOLO 좌표를 정규화한다. 원본과 파생 자료의 연결·촬영 그룹·승인 근거를 유지한다.
- train/val의 이미지 수·객체 수가 각각120/240 및60/120인지 검사한다. ROI 밖 객체가 있으면 버리거나 잘라 숫자를 맞추지 않는다. 원인과 후보 부적합을 기록한다.
- 원본 해상도가 다르면 이 좌표를 임의로 적용하지 않는다. 학습 전 좌표 순변환/역변환과 경계 검사를 수행한다.
- 새 실험에 시작 기록·설정·초기 가중치 해시를 먼저 저장하고 학습을 한 번 시작한다. OOM/실패 때 batch를 바꿔 두 번째 학습을 자동 실행하지 않는다. 실패 기록은 보존하고 기존 baseline 배포로 진행할 수 있는지 판단한다.

### 비교와 선택

- 같은 B03 전체60장/120객체, 동일 conf/NMS/매칭 기준으로 비교한다. ROI 결과는 원본 좌표로 복원해 정답과 비교한다. cropped 좌표를 원본 좌표와 직접 비교하거나 놓친 객체를 통계에서 빼지 않는다.
- 기존 결과는 재사용한다. 비용 비교에 필요한 제한된 추론은 허용하지만 재학습은 추가하지 않는다.
- P/R/mAP50/mAP50-95, L/R IoU 평균·p10, 최저 사례, FP/FN과 조명별 악화를 확인한다. 서로 다른 confidence 운영점이나 AP와 고정 임계값 집계를 섞지 않는다.
- 지연은 같은 장치·정밀도·batch1에서 워밍업을 제외하고 crop/전처리 포함 p50/p95, 실제 tensor shape, 메모리를 기록한다. 모델 추론만의 시간도 구분한다. 개발 PC 결과를 Jetson 성능으로 보고하지 않는다.
- **이번 작업의 배포 후보 선택 규칙 제안(실행 전 고정):** 기존 FP/FN0을 유지하고, mAP50-95가 절대값0.01 이상 개선되며 L/R IoU 하위10%가 악화하지 않을 때 ROI 후보를 우선한다. 이는 노션의 공식 인수 품질 기준이 아니라 이번 단일 실험의 선택 기준이다. 조건별 의미 있는 악화·잘림·비용 문제 또는 애매한 개선이면 baseline 유지.
- Jetson 비용 적합성은 대상에서 따로 확인한다. ROI 후보가 대상에서 부적합하면 추가 학습 없이 보존 baseline으로 되돌릴 수 있다.
- 결과와 선택 근거는 짧은 MODEL_SELECTION 기록 하나에 남긴다. 둘 중 선택한 가중치+전처리는 개발 배포 후보로 고정한다. B04 미평가를 숨기거나 최종 인수 완료라고 하지 않는다.

## 3. 운영 규율·현재 저장소 유지

- 기존 저장소/remote/브랜치를 확인하고 그대로 사용한다. 노션의 `미등록` 문구만 보고 신규 저장소를 만들지 않는다. 기존 V0-Txx와 노션 ARCH-Txx는 별개이며 요구사항 매핑만 남긴다.
- 현재 T08은 분석 완료/튜닝 미실행이다. 이번 1회 실행과 선택 결과만 추가한다. 기존 T09 등의 미수행 최종 평가를 번호가 비슷하다고 완료로 바꾸지 않는다.
- 이전 학습·도구 구현이 미커밋 상태일 수 있다. 삭제/reset/무관한 변경 통합을 하지 않는다. 담당 변경을 식별해 기존 저장소 승인 정책에 맞게 체크포인트 commit/push하고 실제 결과만 기록한다. 원본 이미지·큰 모델·비밀정보를 Git에 넣지 않는다.
- 비용·보안·원본 손실·장비 환경 파괴 위험·실물 구동·계약의 의미 변경·원인 불명 반복 실패만 사용자에게 보고하고 중단한다. 이미 허용된 기능을 구현하기 위한 호환 가능한 계약 확장·관련 시험은 계속 진행한다.
- 실패 재현을 위해 사용자의 실제 DB나 디스크를 고의로 망가뜨리지 않는다. 시험용 경로·프로파일에서 장애를 주입한다.

## 4. S2 — 모델·전처리 패키지와 ONNX

- 가능하면 Jetson을 먼저 읽기 전용으로 관측한다: 정확한 보드/RAM, OS, JetPack/L4T, Python, CUDA, TensorRT, OpenCV, 디스크 여유. 기존 SSH 설정을 사용하고 인증 실패를 반복하지 않는다. 접속 불가이면 Windows 작업은 계속한다.
- 기존 배포 경로가 있으면 재사용한다. 버전별 패키지에는 weights/ONNX, class map, 전처리, Recipe, capture profile, manifest와 SHA/데이터·코드 버전/검증 결과를 묶는다. `current` 참조는 유휴 상태에서만 전환하고 rollback 후보를 보존한다.
- crop 활성 여부·원본 크기·ROI·채널순서·픽셀 dtype/정규화·resize 보간·letterbox 비율/패딩·입력 tensor shape·후처리·NMS·좌표계를 명시한다. 학습 전용 증강은 추론에 적용하지 않는다.
- ROI 모델에는 같은 crop이 필요하다. baseline을 선택했으면 모델 입력 crop은 OFF다. 운영 중 스위치만 바꿔 성능 검증 없이 다른 입력 분포를 사용하지 않는다.
- ONNX는 batch1 고정 shape를 우선 검토하고 대상 TensorRT 호환 opset을 사용한다. 입력 shape는 명시적으로 고정하고 PyTorch 비교에도 동일하게 적용한다. imgsz640이 항상 실제 추론640×640이었다고 가정하지 않는다.
- 검증된 ONNX exporter/후처리를 재사용한다. YOLO26 문서 예제를 YOLOv8 출력 형식으로 간주하지 않는다. 실제 export의 입출력 tensor와 클래스 수를 확인한다.
- 결과 일치 비교는 B03에서 같은 전처리·입력 tensor·후처리로 수행한다. raw 출력 비교가 가능하면 함께 확인하며 NMS 전후와 임계값 경계 차이는 분리한다. 허용 오차를 결과를 본 뒤 느슨하게 바꾸지 않는다.
- 좌표 역변환은 letterbox 역변환→crop offset 순서로 원본까지 복원한다. 라이브러리가 이미 crop 이미지 좌표로 복원했으면 letterbox를 두 번 풀지 않는다. 관련 테스트를 만든다.
- 패키지 추가는 버전/충돌을 확인해 최소한만 한다. 학습 venv를 망가뜨리지 않으며 필요한 경우 작은 별도 export/runtime 환경을 사용한다. 이미지 업로드나 유료 서비스 없이 로컬 변환한다.
- **Windows에서 만든 TensorRT 엔진을 Jetson에 배포하지 않는다.** ONNX와 manifest를 전달해 실제 Jetson에서 엔진을 만들고 검증한다. 고정된 하나의 정밀도를 우선하고 FP16 채택 시 같은 B03에서 수치/검출 변화를 확인한다. INT8·추가 보정 데이터 실험은 하지 않는다.

## 5. S3~S5 — 노션 PLAN-r3의 실행 구조

이 절은 노션 02/04의 필수 계약을 실행용으로 추린 것이다. 새 경쟁 설계를 만들지 않고, 기존 코드와 대조하여 부족한 부분만 구현한다.

### 세 프로그램

1. **Vision Worker / Jetson:** 카메라와 모델의 단일 소유자. 새 프레임·품질/정렬·탐지·Recipe 판정을 담당한다. 매 요청마다 프로세스나 모델을 다시 로딩하지 않는다. DB 최종 commit과 PLC 결과 게시를 하지 않는다.
2. **Edge Service / Jetson:** 요청 수명·Control Agent·health/API·Journal 단일 writer·Outbox. Worker와 제한된 IPC로 연결한다. Worker가 오래 걸리거나 죽어도 통신 감시가 지속돼야 한다.
3. **MES/HMI Service / Windows:** 이벤트/이미지 수집, 자신의 로컬 SQLite, 조회·통계·브라우저 화면. 실제 PLC 출력·Reset 직접 쓰기 없음.

Windows 시험에서는 앞의 두 프로그램도 실행할 수 있게 만든다. 기존 T03 Camera/Detector 계약·저장기·API를 재사용한다. Fake/Replay는 시험용으로 두고 실제 ONNX→TensorRT 경로를 우선한다. 사용하지 않을 운영용 PyTorch backend까지 새로 늘리지 않는다. Windows/x86 COM Bridge를 Jetson으로 옮기지 않는다. Kafka/Kubernetes나 모듈별 별도 HTTP 서버는 추가하지 않는다.

### 모드와 출처

- DEV_MOCK: Fake/Replay 계약·장애 시험. 실제 검사 실적이 아니다.
- BENCH_EDGE: 실제 Jetson·카메라·모델 + 수동 요청. 격리된 cell/세션/cycle/request, source_mode=live, control_mode=none.
- MOCK_CELL_EDGE: 실제 Jetson·카메라·모델 + Mock PLC. Vision Event는 live, 가상 제어 Event는 mock, control_mode=mock. 한 장을 새 제품 여러 개의 실촬영으로 재사용하지 않는다.
- source_mode는 mock/replay/live, control_mode와 deployment_profile은 별도 필드다. 실제 카메라에 Fake Detector를 연결해 만든 판정은 mock이다. live 실패를 Replay로 몰래 대체하지 않는다.
- DIRECT_EDGE는 나중에 선정 PLC adapter와 현장 시험을 추가한다. 이번에는 인터페이스·프로파일 경계만 보존하고 실 PLC 지원 완료라고 하지 않는다.

### 사용자 화면

큰 최근 이미지/선택적 미리보기, 검출 부품·박스, 현재 결과·이유, 실제 촬영/가상 제어 배지, READY/BUSY/FAULT/복구 원인, 모델/Recipe 버전, 오늘 수량·과거 검사·상세 이미지·동기화 상태를 제공한다. 아직 구현하지 않은 분석 메뉴는 만들지 않는다.
수동 검사 버튼은 BENCH, 가상 START/센서/회수 조작은 격리된 Mock 패널에만 둔다. 일반 HMI가 PLC 코일/모터/Reset을 직접 쓰지 않는다. 기존 FastAPI·HTML/CSS/JS 구조를 우선하고 새 프런트엔드 대형 프레임워크를 설치하지 않는다.
실행 파일·검증된 주소·로그 경로를 제공하여 사용자가 명령어를 외우지 않게 한다. 아직 없는 app.py나 확인하지 않은 포트를 실행 안내로 쓰지 않는다.

## 6. 요청·판정·데이터 계약

### 현재 제품/요청에만 결과 적용

- request_key=(cell_id, plc_session_id, request_id), cycle_key=(cell_id, plc_session_id, cycle_id).
- cell_id는 고정된 비어 있지 않은 문자열. plc_session_id/cycle_id/request_id는1~4294967295의 JSON 정수/DB INTEGER다. inspection_id/event_id는 불변 고유 문자열이다.
- 동일 request_key+동일 의미 payload는 기존 작업/결과 반환. 다른 cycle/Recipe 등 내용이 다르면 충돌 거부. request_id 하나만 전역 UNIQUE로 두지 않는다. 의미 있는 전체 요청 내용의 fingerprint를 검증한다.
- PLC/Agent/Worker 재시작·ID 랩·DB 복원 시 과거 제어 세션을 재사용하지 않는다. 세션 유일성과 이전 Worker 작업 종료가 불확실하면 READY=0/RECOVERY. Mock·Bench·실PLC namespace를 분리한다.
- 한 번에 검사 하나. 다른 요청은 BUSY로 거부. 취소 수락과 실제 작업 종료/격리는 다르다. 취소·만료·이전 세션 결과는 유효 게시/통과시키지 않고 별도 늦은 결과로 기록한다.
- Request: schema_version, 요청 추적 ID, run_id, source/control/deployment, product_type, unit_id(null 허용), recipe_id/version/hash, coverage_id, required_views, attempt_no.
- Result: 요청 추적, inspection_id, decision, coverage_complete, unassessed_slots, defects[defect_code/slot_id/rule_id/view_id/evidence], reason_codes/error_code, model_version, capture_profile_id, frame_asset_ids, timings, evidence_status.
- Event: event_id, producer_id/session/seq, 요청 추적(nullable 진단 조건 구분), event_type, occurred_at, 불변 payload와hash, 출처/run. received_at은 수신측 기록이다. 재전송에 ID·발생시각·본문을 다시 만들지 않는다.
- 기존 T03 계약과 새 확장 사이 변환을 한 곳에 두고, 기존 기록을 대량 재명명하지 않는다. JSON schema·예제·서비스 동작·DB 제약이 일치하는지 시험한다.

### 판정은 순수 함수, 근거 부족은 정상으로 대체하지 않기

- 입력: 관측 Detection + ViewAssessment + 선택 Recipe. 카메라·DB 없이 순수 판정 함수를 시험할 수 있어야 한다.
- 슬롯 상태: PRESENT / ABSENT_CONFIRMED / UNOBSERVABLE / UNCERTAIN.
- 우선순위: 시스템 수행 실패 ERROR → 확인된 불량 FAIL(미확인 목록도 보존) → 필요한 관찰 부족 REVIEW → 전체 활성 규격 충족 PASS.
- 단순 미검출과 실제 부재를 동일시하지 않는다. 글로벌 blur 점수 통과만으로 모든 슬롯의 가시성을 증명하지 않는다. 실제 빈자리/가림/반사를 구별할 수 있도록 검증된 슬롯별 부재·관찰 규칙이 있을 때만 ABSENT_CONFIRMED를 허용한다. 충분한 방법이 아직 없으면 REVIEW와 미검증 항목을 남긴다.
- 현재 이어폰에서 정상·L누락·R누락·양쪽누락과 판단 불가를 실제로 확인한다. 부족한 부재 확인은 소규모 비학습 규칙을 검토할 수 있으나 두 번째 모델 학습은 하지 않는다. 개발 B03는 규칙 검증에 사용 가능하되 해당 정답/시나리오를 추론 입력으로 읽지 않는다.
- 제품 미투입은 수락 전 거부, 수락 후 확인되면 ERROR/NO_PRODUCT. 단순히 케이스 미검출만으로 실제 빈 투입을 확정하지 않는다.
- Recipe는 제품·버전/hash·coverage·required_views·슬롯·허용 부품/수량/위치·촬영 프로파일·품질/판정 규칙을 가진다. 검사 중 교체 금지. 제품 식별 불확실성은 REVIEW, 검증된 제품 불일치는 D11/보류. 요청 필드 일치가 실제 물체 식별 성공은 아니다.
- 없는 부품의 가상 검출 박스를 만들지 않는다. 누락 표시는 Recipe의 기대 슬롯 영역임을 구분한다. 검출 confidence를 제품 불량 확률이라고 표시하지 않는다.
- 슬롯·기준 객체를 `case`나 L/R 고정 조건문으로 구현하지 않는다. 부품명·규칙은 제품 설정에서 읽는다. 아직 미검증인 색/방향/오부품 규칙은 비활성으로 두고 지원 완료라고 하지 않는다.

### 저장과 PC 수집

- 원장은 Jetson Edge Journal. 테이블은 cycles, inspections, defects, frame_assets, events, dispositions, outbox. PC는 별도 로컬 DB로 수집·조회한다. 기존 스키마가 다르면 백업·migration/호환 경로를 만들고 운영 DB를 초기화하지 않는다.
- 이미지 파일의 임시 기록→OS에 맞는 영속화·최종 이름 전환→hash→결과와outbox DB transaction commit→유효 결과 게시. 파일과DB 전체를 하나의 원자 transaction이라고 가정하지 않는다. 재기동 시 미완료·고아파일을 점검한다.
- 원본 전체 프레임을 보존하고 crop/박스 표시본은 별도 자산이다. 각 asset에 ID·촬영시각·크기·SHA·local_relpath·sync_state를 기록한다. 영상이 없는 실패는 null+사유이며 가짜 사진을 채우지 않는다.
- DB UNIQUE/FK·중복 충돌은 실제 동작으로 검증한다. 같은 이벤트/본문 재전송은1회 집계, 같은 ID/다른 본문은 격리한다. REPLACE로 원결과를 덮어쓰지 않는다.
- 저장 실패/공간 부족은 READY=0·PASS 게시 금지. 오류 자체를 저장하지 못한 경우도 성공으로 보고하지 않고 가능한 진단/후속 DATA_GAP으로 구분한다.
- Outbox 재전송과 이미지 복제를 분리한다. PC DB commit ACK가 이미지 수신 완료는 아니다. 미도착 이미지는 SYNC_PENDING. 큐/공간 상한 초과 시 신규 검사 차단. 초기 원본 자동 삭제 OFF.
- decision과 disposition은 별개다. PASS/FAIL/REVIEW/ERROR를 수동 처분으로 바꾸지 않는다. disposition은 PENDING/RELEASED/QUARANTINED/REMOVED/ABORTED.
- 재검사는 같은 cycle+새 request/attempt. 검사 시도 수와 제품 처리 수를 구분하고 자동 재검사 OFF. UTC 저장·한국시각 화면 표시, 지연은 동일 장치의 단조 시계로 측정한다.

## 7. Mock 제어·API·장애 시험

### Mock PLC의 최소 운전

RECOVERY→IDLE→새 START→POSITIONING→SETTLING→WAIT_RESULT→RELEASE/HOLD/FAULT→COMPLETE→IDLE.
제품 한 개, START 한 번당cycle 하나, START 유지로 자동 반복하지 않는다. S2/S3는 가상 센서라고 표시한다. PASS는 유효한 현재 결과일 때만 RELEASE, FAIL/REVIEW는HOLD·수동 회수, ERROR/timeout은FAULT. 복구/Reset만으로 다음 사이클을 시작하지 않는다.
Control Agent만 검사 통신을 쓴다. Worker·HMI는 실제 PLC 출력에 접근하지 않는다.
RESULT_ACK=결과1회소비, CYCLE_TERMINAL/CYCLE_ACK=처분종료 이력 영속화, PC ingest ACK=PC DB 저장 확인. 서로 대체하지 않는다. 종료 ACK·빈 구역·별도 START 전 다음 제품을 진행하지 않는다.
Heartbeat 신선도·요청 만료·ACK 시간 초과를 가상 시계로 시험한다. 노션 mailbox를 구현할 때 VALID/GEN을 통한 갱신 중 읽기 차단과 필드 소유권을 유지한다. 실 주소·word order·원자성은 아직 확인되지 않은 실PLC 계약으로 남긴다.

### API는 노션 이름을 유지

- 검사: POST /api/v1/inspection-jobs, GET /api/v1/inspection-jobs/{request_key}, POST /api/v1/inspection-jobs/{request_key}/cancel. 신규202, BUSY/내용충돌409, 동일요청은 기존 작업 반환.
- Edge 조회: GET /api/v1/health, /api/v1/events?after={cursor}, /api/v1/assets/{asset_id}.
- PC 수집: POST /internal/v1/events, PUT /internal/v1/assets/{asset_id}.
- HMI: GET /api/v1/cell/status, /api/v1/inspections(목록/필터/상세), /api/v1/metrics, WS /ws/hmi. 초기 polling을 사용하면 임시 방식임을 기록하고 해당 계약의 완료 여부를 구분한다.
- 처분: POST /api/v1/dispositions는 권한 있는 기록 전용. 원판정/실모터/Reset 변경 없음.
- request_key의 URL 표현은 복합키와 일대일로 변환하고 DB/API/Mock에 같은 자료형을 적용한다. 단일 request_id URL로 축약하지 않는다.
- localhost를 기본으로 하고 필요한 LAN 연결만 허용한다. 수집·쓰기 인증, 허용 호스트, 자산경로 이탈 차단, 비밀정보 제외를 적용한다. 임의 파일 경로 대신 asset_id를 받는다. 실제 PLC 인터넷 노출 금지.

### 자동 시험의 필수 범위

기존 AT-01~24를 요구 시나리오로 연결한다. F-01~09는 그 세부 조건이며33개 독립 시험으로 합산하지 않는다.

1. 정상/확인된 누락/가림/카메라실패의 네 결과 및 근거·저장.
2. 같은 요청 반복의 단일 작업, 같은 세션/ID+다른본문 충돌, 다른 세션의 동일 request 번호 공존.
3. BUSY 중 새 요청, 오래된 프레임, 취소/만료/이전세션의 늦은 PASS 차단.
4. RESULT_ACK/종료ACK 손실·재전송 시 중복배출/중복집계0, 갱신 중 mailbox 읽기 거부.
5. Worker 중단·양방향 heartbeat 상실·저장 전후/ACK 전후 재기동에서 미완료 요청 복구 및 오통과0.
6. 파일쓰기/DB commit/공간한도 실패의 PASS차단, PC중단/복구 재전송 및 충돌 격리.
7. BUSY 중 모델/Recipe 변경 거부, 제품불일치/식별불가 처리, HMI 실제 제어 경로 없음.
8. 최소형 START 유지·빈 투입·가상센서 미도달/고착·STOP에서 무단 다음 사이클0.

Mock 소프트웨어 시험→저장사진 Replay+실제 모델→Jetson 실제카메라 시험의 범위를 분리한다. 없는 실PLC·벨트·E-stop 실물 시험은 NOT RUN/해당이유로 남기고 안전검증 PASS라고 하지 않는다.
관련 테스트는 구현 단위마다 실행하고, 통합 마무리 때 영향받는 전체 회귀를 한 번 실행한다. 테스트가 없다는 이유로 검증을 생략하거나, 코드가 그대로인데 사진마다 전체 테스트를 반복하지 않는다.

## 8. S4/S6 — Jetson에서 실제 실행·기동·성능

- 기존 SSH host와 사용자 인증 경로를 확인한다. 과거192.168.50.2나 /dev/video0을 영구값으로 쓰지 않는다. 카메라 장치·지원 포맷·실제 해상도·영상 수신을 관측한다. 연결/물체 배치는 사용자에게 한 단계씩 요청한다.
- 새 버전 폴더에 패키지를 전달하고 SHA를 확인한다. 사용 중 서비스를 무단 중단하거나 원본 환경을 지우지 않는다. 확인한 JetPack/TensorRT/Python에 맞춰 최소 의존성만 준비한다. Windows venv·COM bridge 복사, 보드 재설치, 임의 최신판 업그레이드 금지.
- 실제 Jetson에서 TensorRT 엔진 생성·재로드·B03 parity·측정을 수행한다. 엔진에는 ONNX/설정hash·보드/라이브러리 버전을 연결한다. 변환 실패를 Fake나 다른 모델의 성공으로 대체하지 않는다.
- BENCH_EDGE에서 실제 USB 새프레임→선택 전처리→탐지→판정→원본/DB 저장을 확인한다. 미리보기 영상에 탐지 상자가 보이는 것만으로 한 사이클 완료라고 하지 않는다.
- 실제 해상도/시야가 ROI 기준과 맞지 않으면 조용히 crop/rescale하지 않는다. 촬영 프로파일 불일치로 신규검사를 막고 기준 재확인. ROI 밖/가려진 검사 자리를 확인했다고 하지 않는다.
- 모델·카메라는 재사용하고 한 요청의 버전·새프레임·deadline을 유지한다. 제품 교체 중에는 이전 프레임으로 다음 요청을 처리하지 않는다.
- 자동 기동은 확인한 대상 환경에 맞는 systemd 등으로 구성한다. 서비스가 다시 켜지는 것과 검사 READY·실제 이송 재개는 다르다. BOOT/INIT/ERROR/RECOVERY/BUSY/RESULT_PENDING에서는 새 요청 수락을 제한한다.
- 재부팅·장시간·카메라 단절 시험에 사람이나 장비 조작이 필요하면 대기로 남긴다. 실행하지 않은 장시간 안정성을 파일 존재로 PASS 처리하지 않는다.
- 모델 inference_ms, 요청~로컬저장 inspection_total_ms, 요청~결과게시 request_to_result_ms, 전체cycle시간을 따로 측정한다. p50/p95·표본수·워밍업·실제shape·메모리·실패/timeout을 함께 보고한다. 서로 다른 PC/Jetson의 비동기 시각을 빼지 않는다.
- 노션의 request_to_result P95≤2,000ms는 개발 목표이며 현재 실측치나 안전timeout이 아니다. 성능미달을 숨기거나 느린 실패를 제외해 달성했다고 하지 않는다.

## 9. 엔진 교체·최종 인수 경계

- 엔진용으로 교체할 것: 실제 엔진 데이터/라벨, 학습한 가중치·ONNX·대상에서 다시 만든engine, 부품맵, Recipe/슬롯/coverage, 촬영·전처리 프로파일, 해당 검증 근거.
- 재사용할 것: Camera/Detector 인터페이스, Worker/Service, 요청·ACK·복구, Journal·PC수집·DB, API/HMI, Mock/실PLC 경계, 공통 시험 도구.
- `ENGINE_Z3005_5 / Z3005_5_VISUAL`을 첫 목표, Z3005-3을 별도 제품으로 다룬다. 실제 부품 수·슬롯좌표·공차를 발명하지 않는다. 엔진 설정 틀은 비활성/UNVERIFIED로 둔다.
- 모델 파일 교체만으로 새 제품이 검증되거나 새 불량종류가 지원된다고 하지 않는다. 특히 보이지 않는 면·가림·방향/색 검사는 실제 가시성과 규칙을 확인한다.
- 공통 코드 변경 없이 다른 클래스/슬롯 수의 가상 설정을 읽는 테스트는 가능하지만 엔진실물 성공으로 집계하지 않는다. 실PLC는 선정 adapter 외에도래더/I/O/정착/센서/복구/기계안전 재시험이 필요하다.
- B04는 모델·전처리·Recipe·판정기준을 고정한 뒤 별도 최종시험에 남긴다. 이번 개발 중 읽거나 tuning에 쓰지 않는다. 최종시험 미수행은 최종인수 미완료로 표시하되 소프트웨어 개발·Jetson bench를 막지 않는다.
- 결과명은 `이어폰 기반 공통 시스템 검증`이며 엔진 대상 Gate A/B/D 또는 실PLC Gate C/D-REAL을 대리 완료하지 않는다. mock/replay/live와 검사품질/제어무결성/실기기 성능을 각각 보고한다.

## 10. 인계·문서·토큰 사용

- 100줄 분석 로그보다 현재 단계·변경파일·관련 시험·결과경로·다음 행동을 짧게 보고한다. 학습은 기록을 파일에 남기고 경계/오류 위주로 확인하며 지나친 polling을 피한다.
- 과거 대화/Obsidian 전체검색을 매번 반복하지 않는다. 기존 지식 저장 절차는 필요한 완료 지점에서만 수행하고 저장 실패로 핵심 구현을 되돌리지 않는다.
- 단계마다 계획서를 새로 생성하지 않는다. 기존 STATUS에 현재 작업/완료근거/다음작업/장비대기만 추가하고 상세 근거는 한 경로로 연결한다. 이 문서를 새 AGENTS 전역규칙으로 설치하지 않는다.
- source와 실제 테스트·설정·짧은 인계 문서를 선택해 기존 승인 정책에 맞게 Git에 반영한다. 실제 commit/push 여부와 미커밋 보존 작업을 구분한다.
- 최종 전달: Windows 실행 방법, Jetson 실행/상태/로그/정지 방법, 운영화면 주소, 선택모델·전처리 버전, DB/이미지 위치, 모델 비교·parity·통합시험·실측 결과, 미검증 항목, 엔진 교체 절차.
- Spark가 특정 문제를 해결하지 못하면 재현조건·오류·최소 관련파일로 상위모델 검토 요청을 준비한다. 모델을 자동으로 바꿨다고 주장하지 않으며 무한 재시도하지 않는다.
- 도구/컨텍스트 한계로 중단해야 하면 마지막 검증 체크포인트와 이어갈 명령을 남긴다. 계획만 작성하고 끝내지 않으며, 가능한 실행을 실제로 수행한다.

### 근거와 구분

1. 사용자 첨부 `붙여넣은 텍스트 (1)(20260913-130804).txt`: 분석 결과·추천 ROI·기존 입력/원본 보존·DIM 요약 상충. 상세 근거는 저장소 ERROR_ANALYSIS.md 및 JSON.
2. 사용자 첨부 `붙여넣은 텍스트 (1)(20260913-124159).txt`: 기준 학습·실제 설정·검증 결과와 산출물.
3. Notion `02 시스템 설계 · 소프트웨어·데이터 계약`, PLAN-r3, 페이지 ID `3d30d6990ab8818c9e73c3a05239cb4d`, 조회2026-09-13: 세프로그램·식별자·Recipe·저장/API·런타임.
4. Notion `04 PLC 운전·실패 처리·통합시험`, PLAN-r3, 페이지 ID `3d30d6990ab881d0bd3aef6f7f82d1c6`, 조회2026-09-13: 최소형·상태·ACK·실패·AT/F·목표/인수구분.
5. 기존 대화에서 확인한 Notion01 작업체계와 사용자 최신 범위: 한 번만 튜닝 후 공통 소프트웨어 우선. S순서와 ROI 선택의0.01 기준은 본 지시서의 구현 제안이며 기존 측정 사실이 아니다.
6. 구현 API/호환성은 설치본과 해당 버전 공식 문서를 대조한다. 참고: https://docs.ultralytics.com/modes/export/ , https://docs.nvidia.com/deeplearning/tensorrt/latest/getting-started/support-matrix.html . 문서 예제가 현재 모델/Jetson에 그대로 맞는다고 가정하지 않는다.

지금은 1절의 현재 실행 여부를 확인하고, 2절의 고정 ROI 한 번부터 실제로 진행한다. 선택·변환·검사 핵심·Jetson·통합까지 위 순서로 이어간다.
