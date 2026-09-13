Current Phase:
V0 Proxy Inspection System — 진행 중, 전체 완료 아님

Latest Checkpoint (2026-09-14, INSPECTION-APP-V1):
현재 Task는 tasks/inspection-app-v1.md. CODEX_INSPECTION_APP_V1_KO.md의 공통 앱 범위로 DB/PC/Mock 제어를 구현했으며, 아래 과거 BENCH의 DB 제외/8767 실행 표기는 당시 기록이다. 현재 Jetson 릴리스 app_v005, 검사 화면 http://127.0.0.1:8768, Windows PC 조회 http://127.0.0.1:8769. 기존 bench_v001은 소스·모델·기록을 보존하고 종료했다.
제품 패키지 hash/schema/클래스/전처리/Recipe/촬영 검증, 같은 클래스 다중 슬롯·수량의 유일 배정, 별도 GPU/카메라 Worker 프로세스, Service 단일 SQLite writer와 PNG→commit→게시, 이력/asset 조회, 패키지 활성화/실패 복원, PC outbox·별도 DB·독립 이미지 ACK, Mock 요청/결과/종료 ACK·복구를 연결했다. Engine 모델/실물 슬롯은 미준비 비활성이다.
실제 Jetson cuda:0/Orin/입력[1,3,640,640], 기존 best.pt SHA256 49f533e4e4e5846d1582564d8efbb38a647ad10348a976db9085d94df16250c1 유지. 격리 app_v1 환경은 기존 사용자 torch2.8.0과 시스템 OpenCV4.8.0을 그대로 사용하며 FastAPI/uvicorn만 별도 설치했다. 실제 USB 기준 진단5건은 대상 부재로 전부 REVIEW, PNG15장+overlay5장·SQLite5행·PC20자산 해시 일치. 생산 검사0건이다. 사람 가시성을 자동 승인하지 않았다.
PC 실제 중단 중3건을 Edge에 보관하고 재연결 후 중복 없이 수집, outbox/이미지 대기0. 동일 Baseline 패키지 실제 재활성화·세션 변경·기존 이력 유지 확인. Service 종료 뒤 자식 Worker가 남던 실패를 보존하고 ASGI lifespan 정리로 수정, 부모/자식 종료와 재시작 확인. 실제 Windows 전체218개 PASS, 마지막 변경 관련14개 및5개 PASS, 최종 Jetson27개 PASS, 릴리스45파일 해시 일치·SQLite integrity ok/FK 위반0. 가상 시간/가짜 Worker 시험은 실물 시험과 구분한다.
남은 수용: 브라우저 실제 표시, 현재 패키지 기준 자리 사람 확인, 정상/L누락/R누락/양쪽누락의 사진·판정·DB·화면, 물리 USB 단절, 사람 준비 후 실제 카메라 Mock 사이클. 모두 대기이며 전체 완료로 표시하지 않는다. B04/재학습/ONNX·TensorRT/실 엔진/실 PLC·모터는 미실행. 실행 안내 apps/edge_service/INSPECTION_APP.md, 증거 docs/verification/INSPECTION-APP-V1-20260914.json 및 runs/inspection_app_v1/.

GitHub publication verification (2026-09-14):
사용자 요청에 따라 촬영 도구 보완/라벨 변환/그룹 분리/Baseline·오류 분석/Jetson BENCH 코드와 검증 기록을 기존 master에 동기화한다. 전체 자동 테스트185개 PASS(50.302초), 새 checkout 임시 폴더 준비 보완 후 관련11개 PASS. 원본 사진·가중치·ONNX/engine·임시 분석·무관한 미커밋 CAD 작업은 게시하지 않는다. ROI 폴더의 복사된 Baseline 보고서와 미검증 환경 설정 주장이 있는 과거 MODEL_SELECTION 문서는 로컬에 보존하며 배포 선택 근거로 게시하지 않는다. 현재 BENCH Baseline 선택은 최신 사용자 지시를 따른다. 실제 실물4상태 검증은 아래와 같이 대기 상태다.

Latest Runtime Checkpoint (2026-09-13 → 09-14, JETSON-BENCH-001):
전용키 자동 SSH 접속 성공. 실제 Jetson Orin Nano/aarch64/L4T36.4.7/Python3.10.12/torch2.8.0 CUDA12.6/Ultralytics8.4.118/OpenCV4.8.0 확인 및 CUDA 연산 성공. 기존 환경을 재설치하지 않고 PyTorch CUDA 단일 경로를 선택했다. TensorRT10.3 설치 존재는 확인했지만 사용하지 않았고 ONNX parity는 NOT_RUN_PT_PATH.
원래 Baseline best.pt를 전송해 SHA256 일치. B03 BASE CENTER 네 상태 원본4장을 Jetson cuda:0에서 실제 추론, 모두 기대 부품 목록 일치(총8객체). 실제 입력은 FP32[1,3,640,640]/rect=False/전체 프레임. 첫 호출5888ms, 다음 세 호출52~59ms는 smoke 관측이며 정식 성능 벤치마크가 아니다.
기존 Camera/Detector 계약 기반 PyTorch/GStreamer adapter와 apps/edge_service/bench.py+bench.html, config/earbud_bench.json 구현. Jetson Python3.10의 StrEnum 호환만 최소 보완. 단일 Worker 소유·요청 후 source PTS·3연속 관측·제품별 자리/가시성 확인·요청별 원본PNG/JSON·중복거부·저장오류/단절 표시. DB/PLC는 후속으로 유지.
실제 USB MJPG1280x720 수신/증가 PTS12프레임/HTTP READY와 이미지 수신 확인. 첫 USB 연결 대기0.5초 실패를 보존하고 초기 프레임만3초 대기로 수정한 뒤 실제 수신 성공. 브라우저 조작 도구 미연결로 사용자의 화면 확인 대기.
Windows/Jetson 계약19개씩, BENCH 집중11개씩 PASS. 모델/배포파일8개 해시 일치. Evidence: docs/verification/JETSON-BENCH-001-20260913.json 및 runs/jetson_bench_001/.
현재 Jetson 서비스 실행 중, 노트북 http://127.0.0.1:8767 (SSH tunnel, 대상은127.0.0.1에만 bind). 정상 기준 자리 사람 확인·실제 네 상태 판정/저장·물리 단절·실제 중복 HTTP 검사는 아직 대기이며 전체 완료가 아니다. 다음 행동은 사용자가 브라우저에서 현재 영상 확인. 실행/종료/위치는 apps/edge_service/JETSON_BENCH.md.

Latest Request / Checkpoint (2026-09-13, JETSON-BENCH-001):
현재 Task는 tasks/jetson-bench-001.md. 최신 사용자 요청이 CODEX_EDGE_VISION_NEXT_KO의 전체 시스템 순서보다 우선한다. 기존 Baseline으로 Jetson 저장 사진 GPU smoke → 실제 USB → 노트북 브라우저 정상/누락 검사 화면까지만 진행한다. 재학습/추가 ROI·768/B04/MES·DB복제·PLC는 이번 범위 밖이며 최종 DB·PLC 요구는 후속으로 유지한다.
원래 baseline_result와 best.pt SHA256 일치. best.onnx 구조/클래스 확인: FP32[1,3,640,640] → [1,7,8400], NMS 노드0. ONNX parity와 Jetson 실행은 미실행.
provenance의 B03 BASE CENTER 네 상태 원본을 각1장 준비하고 해시 대조했다. runs/jetson_bench_001/staging_v001/에 manifest/별도 평가정답/원본 사본4장 보존. 준비 코드 집중 테스트3개 PASS. 실제 GPU·카메라·웹 화면 PASS가 아니다.
현재 실행 중인 SSH 프로세스에서 접속 경로를 확인했으나 BatchMode 인증1회 거절(publickey,password). SSH config 없음. 사용자에게 scripts/connect_jetson_bench.py를 터미널에서 실행해 전용키 인증을 설정하도록 안내했다. 호스트키 검증/네트워크 설정을 변경하지 않았으며 키 생성·대상 설정·환경 probe는 아직 미실행. 접속 인증 뒤 단일 backend를 결정한다.

아래 Current Task/튜닝 미실행 표기는 이전 분석 시점 기록이다. 최신 요청은 위 JETSON-BENCH-001이며 Baseline/ROI 학습을 반복하지 않는다.

Completed:
V0-T01, PLAN-REVISION-001, PLAN-AUDIT-001, V0-T02, V0-T03, V0-T04
V0-T05: DONE / VERIFIED (B01/B02 120장 위치 라벨 사람 승인·YOLO 학습 후보 변환 범위)
V0-T06, V0-T07, PROXY-DATASET-TRAIN-001: DONE / VERIFIED (B03 승인60장·train120/val60·Windows 첫 baseline 완료)
HUMAN-CAPTURE-001-PREP: DONE / VERIFIED (촬영 준비 범위)
WINDOWS-CAPTURE-001: DONE / VERIFIED (소프트웨어 + 최초 실제 USB 촬영 흐름)
WINDOWS-CAPTURE-002: DONE / VERIFIED (제품별 안내 촬영 소프트웨어)
DATASET-WIZARD-001: DONE / VERIFIED (전체 계획 수집 길잡이 소프트웨어)

Current Task:
V0-T08 — 평가·오류 분석 및 실험안 완료 / VERIFIED. 실제 튜닝 실행은 사용자 요청에 따라 미실행.

Latest Checkpoint (2026-09-13, V0-T08 분석 완료):
기존 B03 예측60장/120객체를 조건·배치·상태·클래스별로 분석했다. OPPOSITE 평균confidence0.9433이 BASE0.9661/DIM0.9668보다 낮지만 평균IoU는 BASE0.9134가 가장 낮다. L/R IoU약0.878,case0.958. 최저IoU0002 R0.75872,최저confidence0046 R0.88213. FP0/FN0,IoU<0.75도0이며<0.85는13개다. 최저 두목록의18사진/19객체를 실제 원본·GT/pred·기존예측으로 보조 검토했다. 작은 이어폰 경계 차이와 반사/케이스 경계 불확실성은 원인 후보이며 라벨 수정은 하지 않았다.
ERROR_ANALYSIS.md/error_analysis_detailed.json/error_analysis_supplement.json/error_review_v001/을 기존 실험 폴더에 추가했다. 독립IoU120,분포/합계/순위/원본보존 및 새 집중테스트4개 PASS. Evidence: docs/verification/V0-T08-ERROR-ANALYSIS-20260913.json.
추천은 baseline 유지 대조 + 고정ROI만 변경(1순위) + imgsz768만 변경(2순위). 실제 학습/추론 재실행0,B04 접근0,Jetson0. T08의 과거 실제 튜닝 실행 계획은 후속 대기이며 이번 분석 완료와 구분한다.

Earlier Checkpoint (2026-09-13, Windows 첫 baseline 완료):
PROXY-DATASET-TRAIN-001 DONE / VERIFIED. B03 v003 전체60장 사용자 승인→새 승인본/사람 검토 기록→validation_candidate 변환60장120객체 완료, 보류0. B01/B02 기존 train120장과 B03 val60장, B04 test0 예약으로 T06 구성·누수 검사 PASS. 원본/기존 승인본/수집 기록을 포함한978개 보호 파일 해시 유지.
T07 단일100epoch 실제 학습 exit0 완료: yolov8n.pt, RTX5070 Laptop cuda:0, imgsz640/batch16/seed42/AdamW/FP32. 학습 호출 총313.42초(초기화·마지막 검증 포함), epoch loop300.78초. best/last 재로드 CUDA PASS. best B03 Precision0.9981466 / Recall1.0 / mAP50 0.995 / mAP50-95 0.8334961. B03 예측60장 저장, conf0.25·IoU0.5 class-aware matching TP120/FP0/FN0. IoU가 낮은0002 R(0.759),0055 L(0.774) 예측 이미지 보조 확인; 미검출 사례로 부르지 않는다.
결과: training/experiments/earbud_case_v0_20260913_v001/BASELINE_REPORT.md 및 docs/verification/PROXY-DATASET-TRAIN-001-BASELINE-20260913.json. 데이터: training/outputs/datasets/earbud_case_v0_B01_B03_20260913_v001/dataset.yaml. 새 집중 검사12개 PASS. B04 최종 시험·추가 튜닝·Jetson 배포는 이번에 미실행이며 다음 별도 단계로 남긴다. 전체 엔진 정상/불량 검사·DB 저장 완료를 뜻하지 않는다.

Earlier Checkpoint (2026-09-13, B03 전체 라벨 승인 후 학습 중):
사용자가 "모든사진 OK라는거야 일일이 확인 안받아도되"라고 B03 v00360장 전체의 라벨을 명시 승인했다. 새 project_reviewed_all60_v001.json/human_review_all60_v001.json 저장, 사각형 변경0·120객체·보류0. 기존 초안과 부분 검토 로그는 보존했다. via_to_yolo.py validation_candidate60장 변환 PASS.
T06 DONE: training/outputs/datasets/earbud_case_v0_B01_B03_20260913_v001/에 train120/val60/test0 예약·dataset.yaml/분리 목록/누수 검사 저장. 이미지 SHA 및 origin/session/episode/capture 중복0. 새 데이터 검사8개·오류 집계 검사4개 PASS.
T07 현재 실행 중: training/baseline_config.yaml, yolov8n.pt, CUDA RTX5070 Laptop, imgsz640/100epochs/batch16/seed42/AdamW/FP32. 출력 training/experiments/earbud_case_v0_20260913_v001/baseline, 로그 training/outputs/earbud_baseline_20260913_v001.log. 이미 시작한 동일 baseline을 중복 실행하지 않는다. 완료 여부는 baseline_result.json 또는 baseline_failure.json으로 확인한다. B04 예약 유지·Jetson 미실행.

Earlier Checkpoint (2026-09-13, B03 촬영 완료 후):
B01/B02 승인·YOLO 변환120장 유지. B03 실제60장 저장 및15묶음 사람 촬영 검토 완료, 촬영 검토 대기0. BASE/DIM/OPPOSITE 각20장, 네 상태 각15장이다. 전체 원본222장·49세션이며 과거 재촬영28장도 보존했다. B03는 사용자 촬영 중단·케이스/조명 재준비 확인 후 기존 GUI로 시작했고 origin_group OG697C8F89699D4572 / validation_candidate다. B01/B02의 OG1023298FB0FC4631과 그룹·실제 이미지 해시 중복0. 물리적 독립성은 사람 선언이며 자동 입증이 아니다.
기존 GUI 내보내기 EXPORT6F74307E8E314691와 prepare_via_project.py를 재사용해 별도 B03_20260913 작업 공간을 만들었다. 실제 B03 원본60장을 확대 확인하고120개(L30/R30/case60) pending 사각형을 작성했다. 최신 초안은 training/outputs/labeling/B03_20260913/project_draft_all60_v003.json, 검토 이미지는 같은 폴더의 review_all60_v003/이다. 사람 위치 라벨 승인0, B03 YOLO 변환0. B01/B02 승인본·출력과 원본을 포함한978개 보호 파일 해시 유지. 이전 B03 초안v001/v002도 보존한다.
B04 미시작·최종 시험 예약 유지. 앱의 현재 멈춤은 B04의 용도 전환 보호이며 B03 미완료가 아니다. dataset.yaml/분리 목록/실제 데이터 첫 학습은 아직 미실행이다. 과거 t02_smoke의 모델 파일은 이번 실데이터 학습 결과가 아니다.
근거: docs/verification/PROXY-DATASET-TRAIN-001-B03-CAPTURE-20260913.json 및 docs/verification/PROXY-DATASET-TRAIN-001-B03-LABEL-DRAFT-20260913.json.
현재 다음 작업: B03 최신 초안60장의 실제 부품 종류·사각형 범위만 사람 검토 → 승인 범위 YOLO 변환 → T06 그룹 분리 → Windows 첫 학습. B01/B02 재승인이나 B04 촬영은 요구하지 않는다.

Current Authorization (2026-09-13):
사용자가 오늘 데이터셋 제작과 첫 학습까지 진행하도록 범위를 확장했다. Jetson Orin Nano는 아직 연결하지 않았으며 지금 단계는 Windows에서 수행한다. 이전 촬영 전용 범위의 라벨링·학습 금지는 이번 명시 요청으로 대체되지만 원본 보존·사진별 준비·사람 검토·독립 그룹·시험 예약 정책은 유지한다.
프로젝트 .venv에서 torch2.11.0+cu128 / Ultralytics8.4.146, RTX5070 Laptop GPU의 실제 cuda:0 행렬 연산(유한 결과·합3920)을 앞서 확인했다. 현재 실제 위치 라벨120장은 승인·변환됐으나 baseline 학습은 아직 미실행이다. 이번 파일 작업에서는 GPU를 재실행하거나 환경을 재설치하지 않았다.

Earlier State (B03 완료 이전 기록, 최신 진행은 위 Latest Checkpoint 우선):
사용자 요청으로 브라우저 재연결 시도를 중단하고 허용된 로컬 PNG·VIA JSON 파일 작업을 유지한다. 브라우저의 미저장 내용은 읽지 않았다. 이어가기 위치는 tasks/v0-t05-labeling-validation.md의 Finalization Result와 tasks/v0-t06-grouped-split.md를 따른다.
V0-T05 DONE / VERIFIED — 사용자가 project_draft_all120_v001.json 전체120장의 부품 종류·사각형 범위를 학습용으로 명시 승인했다. 새 project_reviewed_all120_v001.json에120장 confirmed·240개(earbud_left60,earbud_right60,case120)를 기록했고 보류0장이다. human_review_all120_v001.json에 원래 초안/승인본 SHA256·전체 실제 이미지 ID·사용자 응답·기록 시각을 연결했다. 0001·0002·0057·0081을 포함한 경계 불확실성 메모는 사용자 현행 기준 승인으로 해결했으며 기존 메모와 pending 초안 자체는 보존했다. 사각형/클래스 변경0.
제품 schema를 읽는 공통 training/scripts/via_to_yolo.py로 training/outputs/yolo/B01_B02_reviewed_20260913_v001/에 실제 원본 사본120장·YOLO120파일/240객체·출처 목록을 저장했다. 집중 테스트16개 PASS(0.463초). 별도 실제 출력 검사 PASS: 원본/작업용/출력 해시, 클래스·객체 수·양의 유한 좌표·범위·그룹 연결, 픽셀 역변환 최대 오차4.8000061e-08 <= 허용1e-06, 보호368파일 보존. 기존 검토 이미지와 체크포인트는 학습 입력에서 제외했다. 근거는 docs/verification/V0-T05-YOLO.json 및 출력 폴더 independent_audit.json이다.
B02 DONE / VERIFIED — 현재 B01/B02 본수집120장 사람 확정(각60장), 검토 대기0. 원본162장(기준2·준비12·본수집120·과거 재촬영28), 34세션 검증과 599이벤트 체인 확인. B03/B04는 아직 시작하지 않았다.
B01/B02는 같은 origin_group OG1023298FB0FC4631 / train_candidate다. B03을 독립 회차 선언 없이 시작하면 기존 용도 충돌 보호 규칙으로 일시 정지된다. 코드의 '오늘은 멈추고' 문구는 날짜 제한 검사를 뜻하지 않는다. 실제 촬영 중단 후 시간/설치 재준비 사실을 확인해야 하며 선언만으로 물리적 독립성이 검증되는 것은 아니다.
기존 GUI의 라벨링용 자료 정리로 exports/EXPORTA48C70FCE9B94A62/ 생성 완료. 학습·라벨링 후보120장, 검증0·시험0·합성0, 제외42장(기준/준비14+과거 거절28). 그120장의 위치 라벨 승인·YOLO 변환이 완료됐다. B03는 현재 스탠드 계획상60장이나 실제 시작/촬영/라벨0이며 B04는 최종 시험 예약이다. dataset.yaml·그룹 분리 완료·학습 실행은 아직 없다. 기존 수집 기록과 창을 조작하지 않았고 물리적 재준비도 완료로 기록하지 않았다. 다음은 사용자의 실제 B03 설치 재준비 확인이다.

Earlier B01 Checkpoint (historical):
B01 DONE / VERIFIED — 2026-09-13 첫 본수집60장 저장·사람 확정 완료. 전체 계획은 진행 중이며 B02 준비 화면에서 대기한다.
실제 원본102장: 기준2장·준비12장 모두 확정, B01 원본88장 중 현재 유효60장 확정·과거 재촬영 원본28장 보존. 검토 대기0장, B02 촬영0장. 전체 본수집 목표240장 중60장 확정.
조명 정정 이후 사용자가 실제 GUI에서40장을 추가 촬영·묶음 검토했다. 현재 확정 B01은 BASE/DIM/OPPOSITE 각20장, NORMAL/MISSING_LEFT/MISSING_RIGHT/MISSING_BOTH 각15장이다. 같은 B01 origin_group을 유지하고 독립성은 선언하지 않았다.
19개 실제 세션의 PNG/manifest 재로드·크기·해시와 이벤트386개 검증 통과. 모든102장 source_kind=camera,1280×720. 현재 B02 회차 준비 두 체크는 미선택이고 round_started는 B01 하나뿐이다.
마지막 MISSING_BOTH의 SIMILAR_IMAGE는 과거 main_B01_BASE_LEFT/MISSING_BOTH와의 유사도 경고다. 픽셀 해시는 다르며 저장 실패가 아니다.
기존 GUI에서 경고 확인 후 사진을 묶음 검토까지 보존했으며, 이 동작으로 사람 검토 완료를 기록하지 않았다.
사용자가 혼자 진행한 뒤 조명 위치·밝기·거리를 전혀 바꾸지 않았다고 확인했다. 함께 진행할 때는 조명을 바꿨다는 후속 확인에 따라 기준/준비와 BASE 본수집20장은 유지했다.
DIM20장과 OPPOSITE8장을 실제 비교 GUI에서 조명 조건 불일치 사유로 재촬영 처리했다. 기존 batch_accepted14개는 모두 보존되고, 해당28장에 기존 attempt_rejected 이벤트만 추가됐다. 실제 물체 재배치 선언은 모두 false다.
촬영을 막은 확정 묶음 재검토 진입점 누락을 수집 현황→기존 비교 화면 연결로 보완했다. 사용자가 지적한 조명 안내 문제는 조건 전환/재개 시 별도 조명 준비 확인 창으로 보완했다. 조명 확인은 촬영하지 않고 실행 중 UI 상태로만 유지한다.
원본/manifest/계획 사본/이벤트 스키마/품질 임계값/사람 묶음 승인 정책은 변경하지 않았다. 내부 함수 우회로 실제 자료를 정정하지 않았다.
수정 관련21개 테스트, 전체132개 테스트(40.057초), 최종 현황창 라벨 위치 정리 후 관련1개 테스트 통과. 실제 앱 정상 종료 후 기존 실행 파일로 단일 창 재실행, 같은 수집 폴더 복원·검증·재촬영 처리 완료.
수집 폴더: data/proxy/raw/collections/C2709B20787804587/ — 새 계획을 만들지 않고 이 폴더로 이어한다.
스탠드 있음 계획 v1(BASE/DIM/OPPOSITE), 첫 본수집 B01 목표 60장. 화면 왼쪽=실물 L은 사용자 확인 완료.
재시작 후 Windows HCAM01L 존재 확인, DSHOW 후보2를 직접 연결해 실제 작업대 영상1280×720/MJPG 수신을 확인했다. 요청도1280×720이며 FPS·높이·조도는 미확인이다. 이후 사용자가 실제 설치 및 조명 준비 확인을 거쳐 같은 setup으로 B01을 완료했다.
HCAM01L은 Windows 장치 목록에서 확인했으며 앱의 device_name은 null이다. 후보 번호를 영구 장치 식별자로 취급하지 않는다.
실제 영상 읽기 실패로 촬영을 일시 정지했다. 3개 세션의 PNG 8장 재로드·크기·해시와 이벤트 32개를 검증한 뒤 같은 설정으로 재연결했다.
사용자가 실제 설치 유지 여부를 확인했고 앱은 같은 미촬영 단계로 재개했다. 이 복구 중 추가 촬영 0장, 끊김의 정확한 원인은 미확인이다.
미리보기의 미연결 안내문 잔류는 별도 표시 오류로 남아 있다. 실제 PNG에는 안내문/기준 테두리가 없으며 원본 픽셀 해시 대조도 통과했다.
최소 수정은 wizard_app.py/wizard_views.py와 관련 회귀 테스트·사용 안내에 한정했다. CAD·환경·Jetson·학습·라벨링은 변경하지 않았다. 준비 시험 확인은 데이터 충분성의 보장이 아니다.

Software Verification (DATASET-WIZARD-001, historical):
DONE / VERIFIED — 계획/setup/조명/배치/상태 자동 순서, 준비 후 한 장 저장·검증,
품질 보조, 묶음 사람 확인·재촬영·정확한 재개·그룹 용도 예약·라벨링 인계 목록 구현.
130/130 자동 테스트 (기존111 + 추가19), 실제 Tk 창의 합성 입력/비교/확대 확인.
이 소프트웨어 검증 당시 새 계획의 실제 USB 촬영은 사용자 실행 대기였고 본수집 확정 0이었다. 현재 실제 진행은 위 State를 따른다.
기존 WINDOWS-CAPTURE-001의 실제 네 장 및 WINDOWS-CAPTURE-002의 원래 Evidence는 보존한다.

Product Selection:
완료: earbud_case_v0 — 열린 케이스 안의 실제 L/R 이어폰

Capture Tool / Configuration:
JSON profile 선택, v1 호환 + v2 설정 사본/해시, 네 시나리오 지원 완료.
Windows 촬영 창: 제품/상태 선택, DSHOW/MSMF 후보 선택, 실시간 미리보기,
원본 PNG 한 장 저장, 묶음/배치 관리, 기존 기록 검증·수량 복원.
Windows 전체 92/92 테스트 성공 (기존 56개 보존 + 추가 36개).
후속 안내 기능: capture-guide.json, 조건별 새 묶음, 모든 상태의 단계 안내, 준비/원본 검토 게이트.
새 전체 테스트 111/111 (원래 92개 + 안내 기능 19개). 검토 기록은 버전 있는 별도 JSONL이며 기존 manifest는 유지한다.
실제 Tk 창의 합성 입력 검증 이후, HCAM01L / DSHOW 후보2 / 1280×720 / MJPG 영상 수신과 PNG 저장을 확인했다.
장치 보고 FPS는 미확인(null)이다. 후보 번호는 현재 열거 결과이며 영구 장치 identity가 아니다.
실행: scripts/start_capture_windows.cmd (기존 프로젝트 .venv, 추가 설치 없음).
현재 기본 화면: 「시작 / 이어하기」 수집 길잡이. 수동/한 조건 도우미는 고급 설정 또는 --manual로 유지.
기준 사진2장 → 준비 시험12장 → 본수집 초기240장(4회차×3조명×5배치×4상태).
스탠드가 없으면 준비 시험4장/본수집80장으로 조정하며 제외 이유를 보존한다. 충분한 학습량의 보장이 아니다.
수집 계획/이벤트는 별도 v1 파일이며 기존 manifest v1/v2와 GuidedRound의 사진별 검토 정책은 유지한다.

Confirmed Formal Captures:
4장 (2026-09-13): NORMAL 1 / MISSING_LEFT 1 / MISSING_RIGHT 1 / MISSING_BOTH 1.
Session: S20260912T171113_B362774D. 같은 묶음, 실제 배치별 E0001~E0004.
사용자가 실물 배치와 준비를 확인했고, 사용자 요청에 따라 Codex가 GUI에서 상태 선택·저장을 수행했다.
기존 verifier의 reload/크기/기록/해시 검증 성공. 사진은 로컬 Git 제외 경로에만 있다.
이 네 장은 최초 구도·저장 흐름 확인용이다. 새 수집 길잡이의 준비/본수집 수량에 소급 편입하지 않는다.
과거 81장 계획 및 90장 제안을 현재 확정 수량이나 실적으로 사용하지 않는다.

Human Placement / Photo Review:
4개 상태의 사용자 배치 완료 / Codex가 실제 원본 4장을 열어 확인.
열린 케이스와 각 이어폰 상태는 보이나 노이즈·부드러운 윤곽이 관찰되어 구도/저장 확인용으로 유지한다.
최종 촬영 품질과 확대 수집 조건의 사용자 승인은 아직 없다.

V0-T05 / Labeling:
IN PROGRESS — 본수집120장 전체에240개 pending 초안 저장. 기존 review_first4_v001/을 보존하며 누적 검토 자료는 training/outputs/labeling/B01_B02_20260913/review_all120_v001/에 있다. 검토 이미지는 학습 입력이 아니다. 사람 라벨 검토0, B03 미시작.

Historical Next Task (B03 완료 이전; 현재 다음 작업은 Latest Checkpoint 참조):
V0-T05 — 사용자가 현재 VIA 작업을 보존한 뒤 project_draft_all120_v001.json을 Project → Load로 불러와 라벨을 확인·수정한다. 우선0001·0002의 기존 경계와0057 L·0081 R의 어두운 줄기를 확인한다. 전체 사진의 의미 정확성 확인은 별도로 필요하며 실제 확인한 사진만 사람 검토 완료로 기록한다. 이후 B01/B02 라벨 검토→B03 실제 독립 촬영/라벨링→그룹 분리→Windows 첫 학습 목표를 유지한다. 이번 작업에서 브라우저 조작·새 촬영·학습은 실행하지 않았다.
기준 사진 2장과 준비 사진 12장은 모두 사람 확인 완료이며 중복 촬영하지 않는다.
B01 필수60장에 대한 저장과 사람 확정이 완료됐으며 기존 불일치28장은 이력으로 보존한다. B02를 시작할 때 조명 준비 확인→물체 배치→한 장 준비 확인을 분리한다. 촬영은 매번 사람 준비를 확인한다.
B03/B04의 실제 독립 회차 확인을 유지한다. 같은 날이라도 실제 촬영 중단·시간 간격·설치 재준비 사실을 확인해야 하며 같은 연속 촬영을 이름만 바꿔 독립 자료로 취급하지 않는다.
수집 후 기존 T05→T06→T07의 라벨 검증·그룹 분리·baseline 순서를 이어간다. 시험 예약 자료는 학습·튜닝에 쓰지 않으며 기존 프레임 안내 영역을 부품 위치 정답으로 변환하지 않는다.

Evidence / Boundaries:
- 수집 길잡이: tasks/dataset-wizard-001.md; docs/verification/DATASET-WIZARD-001.json; training/capture_windows/DATASET_WIZARD_KR.md.
- 130/130 PASS. 기존 실제 원본/기록을 포함한 보호 파일149개 해시 일치, 패키지42개 버전 유지. 이번 새 실제 촬영0장.
- 안내 촬영 계약: tasks/windows-capture-002.md; 검증: docs/verification/WINDOWS-CAPTURE-002.txt.
- 기존 실제 PNG 4장과 manifest/session-info 총6개 파일 SHA256 일치. 이 사진은 안내 완료 건수로 소급 집계하지 않는다.
- 현재 촬영 화면 계약: tasks/windows-capture-001.md; 사용 안내: training/capture_windows/README_KR.md.
- 현재 검증: docs/verification/WINDOWS-CAPTURE-001.txt. 92/92 PASS, 보호 tracked 파일 150개 해시 일치, 설치 패키지 42개 버전 유지.
- 후속 실기기 검증: docs/verification/WINDOWS-CAPTURE-001-HARDWARE.json. 실제4장과 state/episode/크기/SHA256 연결, 재연결/GUI 수량 복원 확인. 단순 장치 목록 인식과 실제 프레임 수신·저장을 구분한다.
- 선행 준비 계약: tasks/human-capture-001-prep.md.
- 준비 검증: docs/verification/HUMAN-CAPTURE-001-PREP.txt; 보호 파일 229개 해시 일치, 기존 v1 sample 3장 검증 성공.
- 검사 명세·촬영 순서: training/datasets/proxy/earbud_case_v0/README.md.
- 기존 V0-T02 GPU smoke, T03 공통 계약, T04 수집 도구·사용자 실행 하드웨어 검증은 완료 상태와 원래 Evidence를 유지한다.
- T04 CAMERA_SMOKE 3장은 USER-EXECUTED / VERIFIED인 과거 관측이며 정식 데이터에서 제외한다. 현재 카메라 모델·노드·지원 포맷은 미확인이다. 당시 노드/FPS를 현재 값으로 가정하지 않는다.
- 이번 Windows 후속 작업은 사용자 승인 후 지정 USB 카메라를 연결하고, 실제 배치 준비 확인마다 한 장씩 저장했다. 자동 burst 촬영, Jetson 접속, CAD 수정, 환경 설치, 라벨링/분할/학습/튜닝/평가/변환/PLC 제어 없음.
- 합성 sample 검증은 실제 촬영·검사 성공·모델 성능 검증으로 집계하지 않는다.
- Detector/Decision/DB/HMI 구현은 기존 후속 Task 범위다. 준비 완료는 V0 완료가 아니다.
