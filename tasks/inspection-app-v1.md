# INSPECTION-APP-V1 — 제품 패키지 기반 공통 검사

Status: IN PROGRESS (2026-09-14). 최신 사용자 지시 `CODEX_INSPECTION_APP_V1_KO.md`가 범위 기준이다.

USB 재연결 복구 완료 (2026-09-14 14:13 KST): 기존 CAMERA_FRAME_TIMEOUT/종료 Worker를 동일 manifest 재활성화로 복구, 새 Worker/실제 USB 미리보기 PASS. 전후13이력 보존. 기준 미승인은 복구 전후 유지하며 신규 검사·사람 승인0. Evidence: runs/inspection_app_v1/camera_reconnect_20260914_1412/verification.json. 사용자가 수행한 분리 이후의 복구 검증이며 전체 USB 실패 수용을 완료로 바꾸지 않는다.

재기동 요청 완료 (2026-09-14 13:43 KST): 기존 app_v007/PC 수집/SSH 터널 실행, Jetson cuda:0 자체 추론·USB1280×720 미리보기·health READY·PC sync 정상 확인. 신규 검사0, 현재 제품 배치·초점은 사람 조정 필요. 수동 실행 안내 보완, 실제 브라우저 렌더는 도구 미연결로 UNVERIFIED. 이 재기동 완료는 아래 실물 수용 완료를 뜻하지 않는다. Evidence: runs/inspection_app_v1/startup_20260914/verification.json 및 docs/STATUS.md의 Latest Startup.

최신 실물 결과: 사용자 후보 명시 승인 후 별도 calibration DB 저장 확인. 신규 정상 제품 검사5031fbaf16a94877b5b6aa46f9e90c03 PASS, L/R PRESENT. 새 원본3+overlay1과 Jetson/PC 결과·ID·해시·이벤트/이미지 ACK 대조 완료. 기준 진단 a7908d3c586f422c9648cbfc97feffac REVIEW 원문 유지. 정상1건 실행 검증 완료, 브라우저 이력 표시 사람 확인과 누락3상태는 대기. 상세 docs/STATUS.md의 Latest Physical Normal Inspection 및 해당 verification.json.

실물 재개: 사용자 배치/가시성 확인 후 기준 진단 a7908d3c586f422c9648cbfc97feffac의 새 후보 생성 성공. REVIEW는 사람 자리 승인 대기이며 제품 판정이 아니다. 원본3+overlay1의 저장/PC4자산 해시 확인. 다음 필수 행동은 이 사진의 보라색 L/R 위치를 사람이 확인하는 것. 아직 승인0, 정상 제품 검사 대기.

## Current bounded task — app_v006 calibration fix (2026-09-14)

결과: 최종 app_v007 DEPLOYED / HUMAN_ACCEPTANCE_PENDING. app_v006은 중간 검증 릴리스로 보존했다. 재등록 시 이전 승인 사용을 재시작 후까지 차단하는 경계를 app_v007에 추가했다. Windows 최종227개, Jetson 최종 변경 관련14개 PASS. 원본/관측 재현에서 후보 생성 PASS이나 실제 사람 승인0, 제품 검사0이다. 현재 원장의 기준 진단9건/36이미지와 기존5건/20이미지는 보존했다. 상세 증거 docs/verification/INSPECTION-CALIBRATION-FIX-20260914.json. 실제 네 상태 수용 전까지 전체 Task는 IN PROGRESS.

사용자 승인 범위: app_v005의 기준 등록 실패를 현재 검출 좌표 기반 후보 생성으로 수정하고 별도 app_v006으로 배포한다. 기준 등록만 클래스/수량/품질/연속 관측을 검증하여 새 좌표를 제안한다. 같은 클래스 다중 자리의 모호한 대응은 사람 지정 필요로 거부한다. 일반 검사는 승인된 좌표를 고정 사용하며 원본/정규화/화면 좌표를 분리한다.
별도 calibration 원장에 제품/패키지/촬영/설비/기준 사진 연결을 보존하고 화면과 판정에 동일 좌표를 사용한다. 사람 승인 전 차단, 누락 기준 거부, 중복 배정 거부, 기존 모델/Recipe/hash/임계값/기록 보존을 집중 검증한다. 실제 정상 검사/원본/DB 수용은 사용자 배치 및 기준 승인 후에만 실행한다. 재학습·튜닝·전체 재분석·실 PLC/엔진 제외. 기존 진단5건/20이미지는 생산 성공으로 변경하지 않는다.
검증 수준 STANDARD: 원기록 재현 → 순수 후보/판정 회귀 → Service 승인/저장/바인딩 → 기존 관련 테스트 → Jetson 소스/패키지 대조·동일 기록 재현 → 새 릴리스 기동·기록 보존. 실물 승인 대기와 코드 검증을 구별한다.

목표: 제품 패키지 → Jetson 카메라/GPU → 범용 슬롯 판정 → 원본/SQLite → 이력 → PC 수집 → Mock ACK/종료/복구.
기존 BENCH 릴리스/모델/기록을 보존한다. B04·재학습·ROI·ONNX/TRT 전환·실 PLC·CAD·전역 개선 제외.

구간 A: 검증된 불변 제품 패키지, 같은 클래스 여러 슬롯/수량의 유일 배정, 기존 GPU/카메라 Adapter 재사용, 별도 Worker 프로세스와 Service 단일 DB writer, 저장 후 게시, 이력 화면. 각 기능별 정상/실패 시험 뒤 실제 대상 릴리스에 연결한다.
구간 B: PC DB/outbox/asset 분리 ACK 및 Mock 요청/결과/종료. 실제 카메라 경로에서 사람 가시성을 상수로 만들지 않는다.
구간 C: 유휴 교체/실패 복원/안정 data_root/실행·정지·복구 안내 및 실측. 미시험 실물은 NOT_RUN.

현재 근거: d572848의 BENCH 구현 재사용. 기존 Jetson 프로세스 6678은 READY이고 확인된 calibration 존재. 마지막 재기준 촬영은 검출 불확실 ERROR. 실제 네 상태 수용 시험 완료로 해석하지 않는다. FastAPI/uvicorn은 대상 기본 Python에 없으며 기존 CUDA 패키지는 그대로 유지한다.

검증: 패키지 schema/hash/경로/클래스/입력/빈 규칙 거부 → 다중 슬롯 유일 배정/수량/coverage → SQLite FK/고유성/파일·commit 실패/멱등/재시작 → Worker 지연·종료 중 HTTP/취소/늦은결과 → 대상 카메라·DB·화면 → PC/Mock. 현재 시험 수와 증거는 진행하면서 갱신한다.

## 실행 체크포인트 — 2026-09-14

- A 구현/자동 시험 및 실제 USB→CUDA→기준 진단 PNG/SQLite→조회 연결. 패키지 신규 사람 calibration과 생산 실물 수용은 대기. 과거 BENCH 기준 확인을 새 패키지 승인으로 바꾸지 않았다.
- B Windows PC Service 실제 실행, Jetson 역방향 SSH 전송, PC 실제 중단 중 진단3건 보관/복구/중복 방지/20자산 hash 확인. Mock 상태 머신/Control Agent와 Edge API·journal 연결, 별도 RESULT_ACK/CYCLE_ACK/PC ACK 집중 시험. 실물 Mock 사이클은 사람 준비 대기.
- C 동일 실제 Baseline 패키지 재활성화, 유휴/ACK 중 교체 거부·실패 복원 fixture, 안정 data_root/세션/이력 유지, ASGI 종료/자식 프로세스 확인·실제 재시작 검증. 다른 실제 모델/엔진/PLC 검증 아님.
- 실측: PC 중단 중 실제 USB 기준 진단 n=3, 각 관측3프레임. 클라이언트 한 장비 단조 시계 request→조회 P50 약1347ms/P95(linear) 약1486ms. 평균3프레임 inference 약243ms. 작은 대상 부재 진단으로 정상 제품 P95 수용을 주장하지 않는다. 신규 별도 durable timing event 및 Worker 메모리는 runtime JSON에 보존.
- Windows 전체218개(46.980초) PASS; 최종 변경 집중14개, Mock/Service5개 PASS; Jetson 최종27개(7.103초) PASS. HTML JavaScript syntax PASS; 브라우저 렌더링은 사용자 대기.
- 실제 릴리스 app_v005, package app_v001/기존 Baseline. 전체45파일 해시 일치, SQLite integrity ok/FK 위반0, Edge/PC 기준 진단5행·자산20개, outbox/asset pending0.
- 실패 증거: 강제 종료된 multiprocessing.Event 잠금의 복구 정지 → 단일 writer raw flag와 서버 소유 bounded queue; Service SIGTERM 뒤 Worker 잔류 → ASGI lifespan 종료 확인; Jetson /proc children 미지원 → ps --ppid. 이전 릴리스·원본·실패 로그 보존.

다음 한 단계: 사용자 브라우저 http://127.0.0.1:8768 실제 표시 확인 후, 정상 제품 준비와 기준 자리 확인을 한 행동씩 안내한다. 준비/구현 지시를 실물 PASS로 해석하지 않는다. 사람 대기를 제외한 현재 구현/PC/Mock 파일 시험은 완료했다.

Evidence: docs/verification/INSPECTION-APP-V1-20260914.json, runs/inspection_app_v1/final_verification.json, jetson_final_runtime.json, pc_offline_live_captures.json, record_*.json, windows_full_tests_v3.log. 실행/종료/패키지 교체: apps/edge_service/INSPECTION_APP.md.
