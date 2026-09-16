# JETSON-P0-001 — Jetson Runtime Baseline Audit

Status: **AUDIT_COMPLETE_WITH_FINDINGS / RUNTIME_ACCEPTANCE_NOT_MET** (2026-09-16).
검증 수준 STANDARD. 구현·배포 Task가 아니라 읽기/진단/문서화 Task다.

## 목적과 계약

엔진 Dataset/모델 작업과 독립적으로 현재 app_v007의 파일·환경·기능·제약을 고정한다. 원본 app_v007, earbud package, 기존 정상 검사 결과, DB·이미지·모델을 보존한다. 기존 미커밋 변경을 유지한다. 실제 PLC 제어, MQTT 설치/설정, TensorRT 변환, 재설치, 새 촬영, git reset/clean, commit/push는 금지한다. 이후 P0-002~007은 초안만 만든다.

근거 문서: docs/STATUS.md, PROJECT.md, REQUIREMENTS.md, ARCHITECTURE.md, DECISIONS.md, tasks/inspection-app-v1.md, apps/edge_service/INSPECTION_APP.md. 과거 실행 기록과 이번 실제 관측을 구별했다. 이전 Knowledge의 adapter 경계와 단계별 검증 원칙은 REUSE, 현재 환경·파일 hash로 재검증했다.

## 산출물

- [JETSON_RUNTIME_BASELINE.md](../docs/jetson/JETSON_RUNTIME_BASELINE.md): 실제 환경, 카메라 모드, 패키지/모델/DB hash, 구조/재사용 표11행, 예외.
- [JETSON_RUNTIME_GAP_ANALYSIS.md](../docs/jetson/JETSON_RUNTIME_GAP_ANALYSIS.md): 21개 Gap, READY2/PARTIAL11/MISSING8, 근거와 후속 범위.
- [JETSON-P0-001.json](../docs/verification/JETSON-P0-001.json): 기계 판독 관측·보존·검증·수용 상태.
- 이 Task 및 JETSON-P0-002~007.md 초안6개. docs/STATUS.md는 결과 블록만 추가하고 기존 본문 보존.
- 로컬 상세 Evidence: `runs/jetson_p0_001/`. 진단 스크립트는 Task 기록용이며 제품 Runtime 코드에 연결하지 않는다.

## 실행 및 검증 결과

| 수용 항목 | 결과 | Evidence / 제한 |
|---|---|---|
| 현재 환경·camera supported mode·서비스 확인 | PASS | 기존 SSH 읽기 진단, before/supplement/after.json. 실제 스트림 시작0 |
| 구조11기능·Gap21기능의 코드 근거 | PASS | Windows/배포 공통49파일 byte hash 동일, 문서 표/심볼/line |
| app_v007/earbud/model/images 보존 | PASS | 원격 release50/패키지7/이미지72, PC이미지72 전후 동일 |
| DB 본체/WAL·정상 결과 및 원장 행 보존 | PASS | 양측 integrity ok/FK0, 18건 요청/결과 hash 일치; 기존 accepted_at 차이1건 그대로 |
| 사용자 미커밋 변경 보존 | PASS | 기존 tracked14파일 초기 hash 동일; 이후 STATUS 기존 본문 byte 보존 확인. 기존 untracked 제거0 |
| 격리 Runtime 시험 | PASS | 기존61 tests, 7.415초. 새 테스트/구현0. Windows fake camera/model·임시 DB |
| 대상 코드·패키지 정적 검증 | PASS | Python28파일 메모리 compile, bash -n 시작/종료, load_package hash/계약 |
| 현재 app_v007 동일 실행 가능 | **UNVERIFIED / 수용 미충족** | 앱/PC 중지. venv torch.from_numpy 합성 진단 **FAIL**. 기동은 session/DB·camera를 바꾸므로 이번 미실행 |
| 진단 전체의 읽기 전용 유지 | **FAIL — 예외 공개** | Ultralytics import의 사용자 settings.json 자동 갱신; PC mode=ro SQLite의 -shm 변경. DB/WAL/이미지/모델 원본은 동일 |
| git diff --check | PASS | 마지막 검사 및 새 문서 whitespace 확인은 verification JSON에 기록 |
| commit/push/실 PLC/MQTT 변경/TRT 변환 | 수행0 | 실행 범위는 로컬 문서/진단/격리 시험 |

실제 실행 명령은 상세 Evidence에 보존했다. 주요 확인은 `v4l2-ctl --list-formats-ext`, `gst-inspect-1.0`, Python version/import 및 distribution metadata, `PRAGMA integrity_check`/`foreign_key_check`, SHA256 비교, 기존 unittest9모듈, `git diff --check`다. 서비스 start/stop/activate·POST검사 API는 호출하지 않았다.

첫 원격 진단은 local helper의 문자열 분할 오류로 원격 Python parse가 실패했다. 실패 JSON을 별도 보존하고 helper만 수정한 뒤 성공했다. 최초 shell 조회의 quoting 오류도 확인했으며 수집은 인자 배열+stdin으로 대체했다. 최종 PASS는 성공한 관측에만 부여한다.

## 주요 발견과 미해결

- L4T36.4.7/Python3.10.12/torch2.8.0/CUDA12.6/TRT10.3.0. 실제 OpenCV5.0.0·NumPy2.2.6은 과거 환경 기록과 차이가 있다. `RuntimeError: Numpy is not available`를 재현했으며 원인 변경의 시점/주체는 미확인이다.
- app_v007은 중지, PC collector/역방향 tunnel도 중지. 현재 READY라고 하지 않는다. startup 원래 경로와 파일은 보존했다.
- 저장본 Edge/PC 각18행·72자산·event34 ID 일치, 기존 outbox/asset ACKED. 현 연결 시험은 별도다.
- release_files.json은 app_v005와 오래된4해시를 포함한다. 이번 실제 해시가 Baseline이며 원본 목록을 덮어쓰지 않았다.
- Worker heartbeat/Mock ACK를 PLC heartbeat/실장비 제어와 구분한다. TensorRT는 설치 상태만 확인했다.
- 두 읽기 전용 부수 효과의 이전·이후 hash 또는 측정 한계를 기록했다. 추정 복원·삭제·환경 수리는 수행하지 않았다.

## 다음 Task

[P0-002 Moving Conveyor Fresh Frame](JETSON-P0-002.md) → [P0-003 Latency](JETSON-P0-003.md) → [P0-004 TensorRT](JETSON-P0-004.md) → [P0-005 Mock PLC](JETSON-P0-005.md) → [P0-006 Heartbeat](JETSON-P0-006.md) → [P0-007 OMRON](JETSON-P0-007.md).

모두 DRAFT / NOT_STARTED. P0-002의 목표장치 실행은 현재 dependency 호환성 문제를 별도 승인된 범위에서 해결하고 재검증한 뒤 진행한다. 이번 감사의 문서 완료와 실행 수용 완료를 구별하며 전체 Task를 무조건 PASS로 닫지 않는다.
