# JETSON-P0-001 — Runtime Gap Analysis

기준: 2026-09-16, app_v007 / Windows HEAD `f6403fc` + 보존된 기존 미커밋 변경. [Baseline](JETSON_RUNTIME_BASELINE.md), [검증 JSON](../verification/JETSON-P0-001.json).

## 분류 기준

- **READY**: 명시한 현재 소프트웨어 기능이 코드로 존재하고 재사용 가능. 실제 연속 운전/PLC/엔진 제품 수용 완료를 뜻하지 않는다.
- **PARTIAL**: 일부 계약/구현은 있지만 요청된 V1 범위에 필요한 연결·보장·측정이 부족하다.
- **MISSING**: 조사한 배포 Runtime/설정/스크립트에 구현 또는 활성 경로가 없다. 계획 문서·패키지 설치·문자열 하나는 구현 근거가 아니다.

Windows 기존 집중 시험61개 PASS와 배포본/Windows 공통49파일 hash 일치를 확인했다. 실제 앱은 중지, torch/NumPy 변환은 FAIL이다. 아래 READY를 현재 장치 RUNNING/READY 또는 생산 수용으로 읽지 않는다. 파일별 함수/line 근거는 감사 시점이며 이후 변경하면 재확인이 필요하다.

## V1 기능 Gap

| 기능 | 분류 | 현재 코드 근거 | 남은 범위 / 다음 연결 |
|---|---|---|---|
| fresh-frame after trigger | PARTIAL | `inspection_worker.py:100-113`: accepted_monotonic+spacing 이후 추정 source time, max age 필터. `gstreamer_camera.py:39-80`: 단조 PTS/latest queue | 현재 기준은 Service 수락 시각이며 PLC 물리 trigger가 아니다. 센서 노출 시각/이동 중 동일 제품 보장 없음. P0-002 |
| frame timestamp / age | PARTIAL | `gstreamer_camera.py:74`: sequence/source_pts_ns/received_monotonic/estimated_source_monotonic/age_seconds/received_at. `contracts/models.py:FrameMetadata` | captured_at은 수신 시각; 노출 시각 검증 false. 추론·저장·PLC 결과 소비 시점의 age 재평가/최대 허용 창 계약 필요. P0-002 |
| latency instrumentation | PARTIAL | `pytorch_detector.py:40`, `inspection_worker.py:129`, `inspection.py:142-149`, `inspection_api.py:118` | CUDA 동기화 포함 detector 전체 호출·worker·result commit 시간 존재. trigger/대기/preprocess/H2D/infer/NMS/encode/save/sync/ACK 단계 및 분포 미완성. P0-003 |
| TensorRT backend | MISSING | `recipe/package.py:102`는 PyTorch detect/ultralytics_xyxy만 허용, `inspection_worker.py:63-74`가 PyTorchDetector 직접 생성 | TRT10.3 설치는 확인. 배포 releases의 .engine/.plan0, 변환·실행0. 새 backend/패키지 계약과 parity는 P0-004 |
| inference backend abstraction | PARTIAL | `contracts/interfaces.py:34` Detector Protocol, `models.py:DetectionResult`; PyTorch 구현 | worker factory/선택 경로가 hardcoded, package validator도 단일 backend. 계약 재사용하고 선택 경계 확장. P0-004 |
| PLC adapter abstraction | PARTIAL | `control/mock_cell.py:6` 주입 port; `edge_service/mock_port.py:6` ServiceMockPort | mock 전용 duck-typed 경계. 명시 PLC I/O 계약·연결 lifecycle·주소/단위·timeout·bit ownership 없음. P0-005/007 |
| Mock PLC | READY | `mock_cell.py:17-72`, `mock_port.py`, `inspection_api.py:68`; `test_mock_cell`5개와 `test_mock_service`1개 이번 PASS | 상승 edge·POSITIONING/SETTLING·durable result·RELEASE/HOLD/FAULT·별도 ACK·복구 구현. 실물 Mock cycle/가상 I/O 수준 PLC 에뮬레이터는 미검증/미구현. P0-005는 기존 구현 확장 |
| Omron PLC adapter | MISSING | src/apps/config/scripts에서 Omron/FINS 활성 구현 없음 | 기종·프로토콜·주소표·데이터 순서·권한 미확정. P0-007은 emulator/무출력 계약부터 |
| PLC heartbeat | MISSING | `inspection_worker.py:66-68`의0.5초 pulse는 Worker→Service 공유 메모리 | PLC 송수신 생존 counter/toggle·peer freshness 없음. Worker heartbeat를 PLC heartbeat로 재명명하지 않음. P0-006 |
| PLC watchdog | MISSING | `inspection.py:173`5초 Worker heartbeat 감시; `mock_cell.py:43`의 HEARTBEAT_OR_SESSION_LOST는 Service 상태 검사 | PLC 측 scan/timeout·출력 안전상태·서로 독립된 watchdog 없음. P0-006/007 |
| request/result ACK | PARTIAL | `inspection.py:218` 동일 request 재조회; `inspection_api.py:60` durable admission HTTP응답; `mock_port.py:38` RESULT_ACK; `mock_cell.py:67` CYCLE_ACK; `journal/sync.py:20` PC ACK | 소프트웨어 admission/result/cycle/PC ACK 구분은 존재. 실제 PLC request-latch/ACK wire protocol·순서/재전송 합의 없음. P0-005/007 |
| session/cycle/request IDs | READY | `journal/sqlite.py:23-47`, `:98`, `inspection.py:208-236` | cell/session/request 고유키, session/counter 영속화, cycle/attempt·1..2^32-1 검사, session mismatch 거부. PLC word mapping/재부팅 handshake는 별도 |
| MQTT | MISSING | `journal/sync.py:16` HTTP loopback 전송; 관련 MQTT import/client/config 경로 없음 | broker/client/topic/QoS/session 규격 없음. 설치/설정 이번0, 지정된 P0-002~007 이후 별도 명세 |
| MQTT outbox | MISSING | `sqlite.py:58,139` outbox는 HTTP event sync용 | 기존 durable outbox 원칙은 재사용 가능. MQTT delivery 상태·broker ACK와 업무 ACK·중복 키 계약은 없음 |
| metrics | PARTIAL | `sqlite.py:240`, `inspection_api.py:115`, `collector.py:90` | 제품/기준 시도 수, 판정/처분, PC pending은 있음. 지연 histogram·GPU/RAM·queue/frame drop·disk 수치/알림 없음 |
| structured logging | PARTIAL | `sqlite.py:139` event envelope/JSON/hash, `inspection.py:147` timing 및 Mock 전이 events | 구조화 감사 이벤트는 존재. 통합 JSON 운영 logger·level·correlation·rotation 정책은 없음; nohup stdout 파일 |
| disk monitor | PARTIAL | `sqlite.py:108` free<100,000,000B/미ACK outbox>=10,000 거부; `inspection.py:186` health capacity | admission/finish/health 시점 gate. 주기적 사용량·inode·쓰기오류 추세/알림은 없음 |
| synced-only retention | MISSING | `frame_assets.sync_state`, `outbox.state`는 존재; `sqlite.py:205` orphan 보존, 원본 자동 삭제 없음 | 보존기간·event와asset ACK 충족·유예/삭제 감사·quota 정책 없음. 지금 삭제 구현/실행 금지 |
| startup self-test | PARTIAL | `package.py:94` hash/계약, `inspection_worker.py:75-88` optional 대표 이미지 추론·첫 카메라 capture, `inspection.py:175`90초 timeout | 현재 package는 self_test 있음. 기대 검출/수치 oracle 비교, 전체 dependency bridge·DB integrity·PC/PLC 검사 자동 gate는 없음. 현 환경은 별도 NumPy 진단 FAIL |
| systemd | MISSING | `scripts/start_inspection_app.sh:1` nohup/pid/log; 대상 system/user unit 목록·unit 파일 내용 검색 일치0 | 자동 시작·Restart/Watchdog·시작 제한 unit 없음. OS systemd 자체 설치와 구분 |
| automatic restart/recovery | PARTIAL | `inspection.py:111,173,288` 오류 감지/명시 activate 복구, `sqlite.py:205` 미완료 취소·고아 보존, `sync.py:46`1~60초 backoff | PC sync retry/시작 시 journal recovery는 있음. Worker fault 후 자동 재기동·service supervisor는 없음. 자동 START를 금지하는 기존 안전 조건 유지 |

READY 2 / PARTIAL 11 / MISSING 8 = 21개. 이 수치는 성능/품질 점수가 아니라 분류 집계다.

## 반드시 구분할 기존 경계

1. **정지 검사와 이동 검사:** 현재 UI는 제품별 사람 가시성/정렬 확인과 고정 승인 좌표를 사용한다. 3프레임 중 같은 slot 결과가 유지되어야 하며 reference가 고정 영역과 IoU 조건을 만족해야 한다. 카메라를 새 프레임으로 읽는 것만으로 Moving Conveyor가 준비되지는 않는다.
2. **발생 시각과 수락 시각:** `accepted_monotonic`은 DB admit 이후다. 실제 trigger가 들어온 시점, GStreamer source PTS, 수신 시점, 추론 완료를 별도 보존해야 한다. 장비 간 UTC를 빼서 latency를 계산하지 않는다.
3. **저장 성공과 결과 처리:** result commit 뒤 공개, ACK 재전송 시 재배출 금지, 취소/세션 변경 뒤 늦은 PASS 거부를 재사용한다. PC JSON ACK로 이미지 보관 완료를 대체하지 않는다.
4. **설치와 실행:** TensorRT 설치/import 성공·CUDA available은 현재 모델이 해당 backend로 실행되었다는 증거가 아니다. 지금 NumPy bridge FAIL과 중지 상태 때문에 현재 Runtime 실행 수용은 미충족이다.

## 지정된 다음 Task 초안

| 순서 | 초안 | 핵심 목적 | 이전 기능 재사용 / 주요 통과 조건 |
|---|---|---|---|
| 1 | [P0-002 Moving Conveyor Fresh Frame](../../tasks/JETSON-P0-002.md) | trigger 이후 유효 프레임 계약·이동 창 경계 | PTS/latest queue/단일 Worker 재사용. pre-trigger/stale/duplicate/다음 제품 혼합 거부; 실제 노출 검증과 추정값 구별 |
| 2 | [P0-003 Latency Instrumentation](../../tasks/JETSON-P0-003.md) | 요청부터 저장·결과 소비까지 단계별 시간 | 기존 durable event 확장. 동일 시계/시작점·cold/warm·분포·오버헤드 분리 |
| 3 | [P0-004 TensorRT Backend](../../tasks/JETSON-P0-004.md) | 공통 Detector와 새 TRT adapter 경계 | 독립 새 패키지·backend factory·pre/postprocess parity. 이번 변환 없음 |
| 4 | [P0-005 Mock PLC](../../tasks/JETSON-P0-005.md) | 현재 MockCell을 명시 PLC 계약/장애 주입으로 확장 | 기존 ACK/ID/idempotency/state machine 유지. held START·timeout·ACK 유실·reconnect 재배출0 |
| 5 | [P0-006 Heartbeat](../../tasks/JETSON-P0-006.md) | peer heartbeat/watchdog와 복구 handshake | Worker 감시와 PLC peer 감시 분리. 지연/중복 heartbeat가 생존 갱신하지 못하게 시험 |
| 6 | [P0-007 OMRON Adapter](../../tasks/JETSON-P0-007.md) | 합의된 프로토콜을 adapter로 연결 | 기종/주소 계약 확정, 먼저 emulator; 실제 제어는 별도 명시 승인/수용 |

모든 초안은 **DRAFT / NOT_STARTED**. P0-002의 대상 실행 전 현재 환경 호환성 문제를 별도 허가 범위에서 해결해야 한다. 이 감사가 패키지 downgrade/재설치/복구 승인은 아니다. MQTT·retention·systemd 등 나머지 Gap의 구현 Task 번호/설계는 이번에 확정하지 않는다.

## 검증과 남은 제한

- 기존 Python Runtime/Mock/Journal/PC/API 격리 시험61개 PASS, 실제 장치28 Python파일 메모리 compile 및 shell syntax PASS, 패키지 무결성 PASS.
- DB·모델·원장·이미지 보존 PASS. 기존 accepted_at 차이1건 및 stale release inventory는 보존하고 해결하지 않음.
- 현재 health/실물 검사·TensorRT·PLC·이동 속도/FPS/센서 노출 시각은 이번 미검증. 현재 dependency bridge는 실제 FAIL.
- “읽기 전용” 진단 중 Ultralytics 설정 자동 갱신과 PC SQLite SHM 변경이 발생했다. [Baseline의 예외](JETSON_RUNTIME_BASELINE.md#보존-검증과-읽기-전용-예외) 및 JSON에 기록했고 원래 내용을 추정 복원하지 않았다.
