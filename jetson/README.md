# Jetson Orin Nano 실행 코드

**다른 Orin Nano에 복사할 때는 [INSTALL_OPERATING_KO.md](INSTALL_OPERATING_KO.md)부터 읽으세요.** `jetson/` 전체에 고정 운영본32c4의 코드·모델7개·SQLite 보관본이 포함됩니다. `python install_operating.py --verify`로 확인합니다. 신규 설치 점검과 새 장치의 실제 GPU·카메라·PLC 수용은 별개입니다. 개발 후보를 설치기에 자동 반영하지 않습니다.

최신 실제 운영 상태는 [프로젝트 README](../README.md)와 [검증 기록](../docs/verification/CONFIG-UI-HISTORY-20261018.json)을 따릅니다. 아래 구조 설명에는 이전 단계의 첫 제품 승인/필수 조립 기록이 남아 있습니다. 현재는 PLC 반복 요청, 미결합 최종판정, 오조립 참고 정책입니다. 과거 Release/미적용 문구는 당시 기록이며 최신 상태가 아닙니다.

## 이전 구조 설명

노트북에서 편집·검증하고 전체 allowlist 묶음을 `/home/jetson/oned_device_bench/current`에 배포합니다. `engine-inspector.service` 하나가 Python Runtime·카메라 Worker·필수 조립 모듈·OpENer를 감독합니다. 현재 확인한 운영 Release는 `engine-integrated-d247e1e9579ab6e7`입니다. Git의 [TASK-019 저장/health 수정](../docs/PYTHON_NOT_READY_FIX_REPORT.md)은 ARM64 격리 검증을 마쳤지만 아직 운영에 적용하지 않았습니다. 저장 작업자는 원본과 최종판정의 durable commit을 담당하고, Runtime은 건강 상태와 같은 요청의 완료를 검증한 뒤에만 발행합니다. [이전 실제 한 제품 시험](../notebook/deployment/JOURNAL_COMPATIBILITY_VERIFICATION.md)은 ERROR를 PLC NG로 전달한 사례이며, 정상 판별과 연속 자동운전은 완료되지 않았습니다. `release.json`은 과거 배포 기준 기록이며 최신 개발 소스의 배포 완료 표식이 아닙니다.

## 위에서 아래로 읽는 순서

| 단계 / 모듈 | 하는 일 | 먼저 읽을 파일 |
|---|---|---|
| 1. 기동·종료 | systemd 기동, 단일 소유권, 설정 확인, 전체 자식 정상 종료 | [`standalone_service.py`](standalone_service.py), [`engine-inspector.service`](service/engine-inspector.service) |
| 2. 객체 조립 | Service·Worker·추적기·Runtime을 만들고 연결 | [`src/runtime/bootstrap.py`](src/runtime/bootstrap.py) |
| 3. 화면과 API | `/line`에서 검사·PLC·오류 표시. 브라우저가 닫혀도 루프 유지 | [`src/runtime/standalone_web.py`](src/runtime/standalone_web.py), [`line_hmi.html`](apps/edge_service/line_hmi.html) |
| 4. 운전 순서 | 최초 승인, PLC 요청과 같은 제품 연결, 검사·완료·이탈 대기 | [`initial_approval.py`](src/runtime/initial_approval.py), [`standalone.py`](src/runtime/standalone.py), [`production.py`](src/runtime/production.py) |
| 5. 제품 추적 | 관측을 같은 제품 ID와 연결, 검사영역 진입 이벤트 생성 | [`vision_coordinator.py`](src/runtime/vision_coordinator.py) → [`bound_clearance_gateway.py`](src/integration/bound_clearance_gateway.py) → [`provider_tracker_bridge.py`](src/integration/provider_tracker_bridge.py) → [`single_active.py`](src/tracking/single_active.py) |
| 6. 검사 연결 | Track·요청·Inspection ID를 결합하여 Service에 검사 의뢰 | [`src/runtime/inspection_bridge.py`](src/runtime/inspection_bridge.py) |
| 7. 검사 관리 | Worker와 큐로 통신, 검사 수명·오류·결과 저장 관리 | [`apps/edge_service/inspection.py`](apps/edge_service/inspection.py) |
| 8. 영상 취득 | Worker 한 개가 카메라 소유, 최신 프레임과 유효성 확인 | [`src/vision/inspection_worker.py`](src/vision/inspection_worker.py), [`src/camera/fresh_frame.py`](src/camera/fresh_frame.py) |
| 9. AI와 판정 | 새3프레임 기존 검사 + 필수 조립 검사 → 통합 최종판정 | [`engine_inspector.py`](src/vision/engine_inspector.py), [`assembly_inspection.py`](src/vision/assembly_inspection.py), [`integrated_decision.py`](src/vision/integrated_decision.py) |
| 10. 구역 점유 | 잔존 물체와 CLEAR 관측. 현재 가로 벨트의 연속 자동 재승인 자격은 미검증 | [`area_occupancy.py`](src/observation/area_occupancy.py), [`horizontal_conveyor.py`](src/observation/horizontal_conveyor.py) |
| 11. 저장 | SQLite Journal·검사 Evidence·이력 | [`src/journal/sqlite.py`](src/journal/sqlite.py) |
| 12. PLC 응답 | Python↔C IPC → OpENer Assembly100 Result→Done, Assembly150 요청 수신 | [`opener_cyclic.py`](src/control/opener_cyclic.py), [`engine_commissioning.c`](opener/source_profile/source/src/ports/POSIX/sample_application/engine_commissioning.c) |

`src/contracts`는 공통 자료형, `src/recipe`는 제품별 모델·검사 규칙, `src/quality`는 영상 품질 조건입니다. 기존 `launch_live.py`·`manage_live.py`, `/auto` 및 Explicit 벤치 코드는 수동/진단 기능으로 보존합니다. 현재 OpENer 운영 중 두 번째 실행자나 Explicit 결과 발행자를 함께 시작하지 않습니다.

```text
engine-inspector.service → standalone_service.py → StandaloneRuntime
PLC 요청 → OpENer → 로컬 IPC → 같은 제품 Track → 새3프레임 검사
                          기존 검사 + 필수 조립 검사 → Journal/Evidence
저장된 최종판정 → 로컬 IPC → OpENer Result → Done → PLC 공정 처리
/line은 상태를 표시하고, 첫 제품 완료 뒤에는 검증된 이탈·다음 승인 대기
```

Request OFF만으로 제품 이탈을 판정하지 않습니다. 카메라 장애·STOP·미완료 검사·불명확한 전송 결과를 빈 화면으로 해제하지 않습니다. `production`은 실행 모드의 이름이며, 실제 PLC 허가를 뜻하지 않습니다.

## 어디를 고치면 되는가

| 바꾸려는 것 | 위치 | 변경 후 우선 확인 |
|---|---|---|
| 현재 화면 문구·배치 | `src/runtime/standalone_web.py`, `apps/edge_service/line_hmi.html` | 표시와 실제 판정·전송 상태 구분 |
| 제품 진입·검사·종료 순서 | `src/runtime/standalone.py`, `production.py`, `initial_approval.py` | 요청/제품 연결과 미완료·정지·승인 차단 |
| 같은 제품 ID 유지 | `src/tracking`, `src/integration` | 관련 이동·가림 재생 |
| 작은 잔여물·빈 화면 판별 | `src/observation/area_occupancy.py` | 작은 손잡이와 실제 빈 화면 반례 둘 다 |
| 현재 PLC 순환 통신 | `src/control/opener_cyclic.py`, `opener/` | 4/8/10B, Result→Done, 한 발행자, 재접속 승인 폐기 |
| 카메라/프레임 유효성 | `src/camera`, `src/vision/inspection_worker.py` | 최신성·장애·동일 frame 연결 |
| 장치 경로·카메라 ID | 배포 위치의 `config/standalone.json`, `config/line_profile.json`, `config/station.json` | 기동 파일 점검 + 해당 장치 |
| 제품 모델·Pose·검사 규칙 | `assets/products`의 승인된 package | 이번 정리에서는 변경하지 않음 |

`config/`는 기본 설정·참조 자산입니다. 장치의 실제 설정과 모델, Journal/승인 원장은 소스와 분리해 보존합니다. 가로 관측과 원본 진단은 포함 여부와 현장 활성화를 구분하며 평상시 대용량 기록은 끕니다. 부팅·서비스 active만으로 검사 READY나 운전 승인을 표시하지 않습니다.

관리/실행 명령과 장치별 설정은 [배포 안내](../notebook/deployment/README.md)에 모았습니다. 과거 H6/H7 주석 사본보다 이 실제 소스를 먼저 읽으세요.

현재 실제 환경의 관측 버전은 [environment.observed.json](environment.observed.json)에 있습니다. 소스 최신 여부, 배포된 release, 실행 환경, 실물 수용 상태는 각각 확인합니다.
