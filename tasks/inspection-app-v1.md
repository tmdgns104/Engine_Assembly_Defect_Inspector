# INSPECTION-APP-V1 — 제품 패키지 기반 공통 검사

Status: IN PROGRESS (2026-09-14). 최신 사용자 지시 `CODEX_INSPECTION_APP_V1_KO.md`가 범위 기준이다.

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
