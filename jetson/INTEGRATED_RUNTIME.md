# 통합 프로그램 소스와 운영 범위

> 아래는 2026-10-14 첫 제품 단계의 구조 기록입니다. 현재 `engine-integrated-32c484ac6aeb07f1`은 PLC 반복 요청·미결합 최종판정·오조립 참고 정책이며 [최신 검증](../docs/verification/CONFIG-UI-HISTORY-20261018.json)을 따릅니다. 새 장치는 [통합 설치 안내](INSTALL_OPERATING_KO.md)를 사용하세요. 아래 첫 제품1회/필수 조립 정책을 새 운영 설정으로 재적용하지 않습니다.

최신 개발 원본은 이 `jetson/` 디렉터리다. 이전 TASK 후보는 노트북의 근거·복구 자료이며 개발 원본이 아니다.
운영 경로는 `/home/jetson/oned_device_bench/current`, 감독자는 `engine-inspector.service` 하나다.
현장 설정과 모델은 `config/`, `assets/`, 검사 이력과 승인은 `data/`, 실행 환경은 `envs/`에 보존한다.

## 실제 실행 흐름

1. `standalone_service.py`가 소유권 잠금, 카메라 Worker, 조립 분류기, OpENer 자식을 관리한다.
2. `src/control/opener_cyclic.py`가 OpENer와 로컬 Unix IPC로 통신한다. PLC 결과 발행자는 OpENer 하나다.
3. `src/runtime/initial_approval.py`가 정지·준비·원장 조건과 현재 세션의 명시적 첫 제품 승인을 확인한다.
4. `src/runtime/standalone.py`가 PLC 요청과 현재 제품 Track/새 프레임을 연결한다.
5. 기존 검사와 조립 분류 결과를 Journal에 저장한 다음 실제 최종 결과를 Result → Done 순서로 전달한다.

현재 승인 모드는 **첫 제품 1회**다. 한 번의 사용·STOP·연결 손실 이후 자동 재승인하지 않는다.
PASS는 PLC OK, FAIL/REVIEW/ERROR는 PLC NG로 전달하되 원래 AI 판정과 이유는 기록에 보존한다.
실제 운전 승인, 새 현장 START, 같은 cycle의 유효성, 결과 저장 조건은 별도로 충족해야 한다.

## Journal 호환성

`ACCEPTED`는 항상 차단한다. `COMPLETE`도 저장 실패·완료 시각 누락이면 차단한다.
통합 최종판정이 없는 경우, 명시된 구형 authority와 일치하는 요청/완료 identity를 가진
계약 표식 없는 Legacy 기록만 완료로 인정한다. `plc_contract`, 새 line cycle 또는 Full-Frame
표식이 있는 기록과 알 수 없는 계약은 최종판정 누락 시 계속 차단한다.
날짜, 파일 수정 시각, 35건 ID 목록으로 구분하지 않는다. 과거 DB를 변경하거나 최종판정을 만들어 넣지 않는다.

## 포함과 활성화의 구분

| 기능 | 포함 | 현재 활성/검증 범위 |
|---|---|---|
| TASK-011 AI↔OpENer | 예 | 현장 통신 성공 경로 유지; 실제 AI 제품 시험 별도 |
| TASK-015 Full-Frame Tracking | 예 | 현재 단일 제품 검사 경로 |
| TASK-016 첫 제품 승인 | 예 | 명시적 1회 승인, 연속 자동운전 아님 |
| TASK-013 가로 texture 관측 | 예 | 격리 검증만, 운영 clearance 설정 미전환 |
| TASK-014 원본/tensor 수집 | 예 | 비활성; 서비스 정상 정지와 별도 유지보수 승인 필요 |

`field_raw_maintenance.py`의 기존 기준 계약은 LEGACY_THREE_BOOL다. 현재 OPENER_CYCLIC 운영본에서
바로 실행 가능한 승인으로 간주하지 않는다. 해당 유지보수 경로 재검증 전에는 실행하지 않는다.
이 제한을 없애려고 보호 API를 열거나 두 번째 카메라를 실행하지 않는다.

## 소스·바이너리·배포 연결

`opener/source_profile/`은 실행 바이너리와 같은 TASK-016 C 소스, EDS, upstream 라이선스다.
`opener/OpENer`는 검증한 ARM64 바이너리다. 모델·EDS·Assembly 4/8/10바이트 계약은 유지한다.
`release.json`은 파일 SHA와 Release를 기록한다. 배포 receipt가 GitHub commit과 실제 파일 SHA를 연결한다.
장치별 설정·운영 SQLite·승인 원장·사진은 GitHub에 올리지 않는다.

검증: `python -B -X utf8 notebook/deployment/run_runtime_tests.py notebook.tests.test_initial_history_contract.HistoryContractTests notebook.tests.test_initial_approval notebook.tests.test_initial_runtime`
전체 배포는 승인된 manifest의 파일만 묶고, 노트북에서 원본 current·설정·서비스·SQLite backup API 결과의
해시를 먼저 검증한다. 실패 시 직전 current와 설정을 복구하며 Journal/승인 원장을 과거 상태로 되돌리지 않는다.
