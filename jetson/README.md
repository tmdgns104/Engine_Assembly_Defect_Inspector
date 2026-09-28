# Jetson Orin Nano 실행 코드

이 폴더가 Jetson 기능을 수정하는 원본입니다. 노트북에서 편집·검증하고 필요한 파일만 Jetson의 `/home/jetson/oned_device_bench/current`에 배포합니다. 현재 하드웨어의 `current` 전환은 아직 완료되지 않았습니다. 설치 상태와 알려진 실패는 [루트 안내](../README.md)를 확인하세요.

## 위에서 아래로 읽는 순서

| 단계 / 모듈 | 하는 일 | 먼저 읽을 파일 |
|---|---|---|
| 1. 기동·종료 | 경로·파일·MOCK 설정 확인, 기존 서버 시작/정상 종료 | [`manage_live.py`](manage_live.py), [`launch_live.py`](launch_live.py) |
| 2. 객체 조립 | Service·Worker·추적기·Runtime을 만들고 연결 | [`src/runtime/bootstrap.py`](src/runtime/bootstrap.py) |
| 3. 화면과 API | `/auto` 화면, 시작/정지·검사·상태 요청을 Runtime으로 전달 | [`apps/edge_service/integration_api.py`](apps/edge_service/integration_api.py), [`auto_hmi.html`](apps/edge_service/auto_hmi.html) |
| 4. 운전 순서 | 제품 진입, 같은 Track 유지, 검사 가능 여부, 요청·종료 조건 | [`src/runtime/production.py`](src/runtime/production.py) |
| 5. 제품 추적 | 관측을 같은 제품 ID와 연결, 검사영역 진입 이벤트 생성 | [`vision_coordinator.py`](src/runtime/vision_coordinator.py) → [`bound_clearance_gateway.py`](src/integration/bound_clearance_gateway.py) → [`provider_tracker_bridge.py`](src/integration/provider_tracker_bridge.py) → [`single_active.py`](src/tracking/single_active.py) |
| 6. 검사 연결 | Track·요청·Inspection ID를 결합하여 Service에 검사 의뢰 | [`src/runtime/inspection_bridge.py`](src/runtime/inspection_bridge.py) |
| 7. 검사 관리 | Worker와 큐로 통신, 검사 수명·오류·결과 저장 관리 | [`apps/edge_service/inspection.py`](apps/edge_service/inspection.py) |
| 8. 영상 취득 | Worker 한 개가 카메라 소유, 최신 프레임과 유효성 확인 | [`src/vision/inspection_worker.py`](src/vision/inspection_worker.py), [`src/camera/fresh_frame.py`](src/camera/fresh_frame.py) |
| 9. AI와 판정 | 제품 envelope → Pose → 부품 검출 → Slot/3프레임 판정 | [`engine_inspector.py`](src/vision/engine_inspector.py), [`engine_pose.py`](src/vision/engine_pose.py), [`detector_factory.py`](src/vision/detector_factory.py), [`src/decision/slots.py`](src/decision/slots.py) |
| 10. 구역 점유 | 원본 영상의 잔존 물체 확인과 CLEAR 누적; 현재 방식 채택 보류 | [`src/observation/area_occupancy.py`](src/observation/area_occupancy.py) |
| 11. 저장 | SQLite Journal·검사 Evidence·이력 | [`src/journal/sqlite.py`](src/journal/sqlite.py) |
| 12. MOCK 응답 | 저장된 결과 확인 후 Result 확인 → Done 확인, Request 상태 관리 | [`src/control/production_plc.py`](src/control/production_plc.py) |

`src/contracts`는 공통 자료형, `src/recipe`는 제품별 모델·검사 규칙의 로딩/검증, `src/quality`는 영상 품질 조건입니다. 각 모듈은 독립 실행 프로그램이 아닙니다. `launch_live.py`가 상위 객체를 조립하고 하위 기능을 호출합니다.

```text
브라우저 /auto → integration_api → ProductionRuntime
                                  ├─ Track·요청·검사 연결
                                  └─ InspectionService
                                       ├─ Worker (카메라 소유자 1개)
                                       │    └─ 영상 → AI → 부품 판정
                                       └─ Journal/Evidence 저장
저장 확인 → MOCK Result 확인 → Done 확인 → Request OFF 확인
제품·손·손잡이의 유효한 이탈 확인 → Track 종료 → 다음 제품
```

Request OFF만으로 제품 이탈을 판정하지 않습니다. 카메라 장애·STOP·미완료 검사·불명확한 전송 결과를 빈 화면으로 해제하지 않습니다. `production`은 실행 모드의 이름이며, 실제 PLC 허가를 뜻하지 않습니다.

## 어디를 고치면 되는가

| 바꾸려는 것 | 위치 | 변경 후 우선 확인 |
|---|---|---|
| AUTO 화면 문구·배치 | `apps/edge_service/auto_hmi.html` | 해당 화면 |
| 제품 진입·검사·종료 순서 | `src/runtime/production.py` | 저장된 관련 전이/실패 사례 |
| 같은 제품 ID 유지 | `src/tracking`, `src/integration` | 관련 이동·가림 재생 |
| 작은 잔여물·빈 화면 판별 | `src/observation/area_occupancy.py` | 작은 손잡이와 실제 빈 화면 반례 둘 다 |
| 카메라/프레임 유효성 | `src/camera`, `src/vision/inspection_worker.py` | 최신성·장애·동일 frame 연결 |
| 장치 경로·카메라 ID | 배포 위치의 `config/runtime.json`, `config/station.json` | 기동 파일 점검 + 해당 장치 |
| 제품 모델·Pose·검사 규칙 | `assets/products`의 승인된 package | 이번 정리에서는 변경하지 않음 |

`config/`는 편집 원본의 기본 설정·참조 자산입니다. 배포 시에는 코드 밖 `assets/runtime_config`로 묶고 `current/config` 링크로 연결합니다. 기준 이미지 추가나 승인 값 변경은 폴더 정리 작업에 포함되지 않습니다. 진단 모듈은 기존 운영 화면에서 import하므로 유지하며, 대용량 기록은 평상시 끕니다.

관리/실행 명령과 장치별 설정은 [배포 안내](../notebook/deployment/README.md)에 모았습니다. 과거 H6/H7 주석 사본보다 이 실제 소스를 먼저 읽으세요.

현재 실제 환경의 관측 버전은 [environment.observed.json](environment.observed.json)에 있습니다. 소스 최신 여부, 배포된 release, 실행 환경, 실물 수용 상태는 각각 확인합니다.
