# 설정 중앙화와 기록 조회 — 2026-10-18 개발본

현재 운영: `engine-integrated-32c484ac6aeb07f1` · 기존 값 유지 설정 중앙화·기록 검색·부품 미결합 강조 UI 적용, 재부팅 준비 확인. 실물 수용은 실제7회이며 10회 완료는 아니다.

## 설정을 수정하는 곳

`jetson/src/config.py`에 한국어로 의미·소비 경로·단위·변경 위험을 설명합니다. 파일 import는 카메라·모델·DB·네트워크에 접근하지 않습니다. 제품/부품 confidence, NMS, 움직임·품질·자세 기준, 추적, 저장·진단 자원, 미리보기, IPC 및 서비스 주기를 기존 값 그대로 이관했습니다. 같은 숫자라도 의미가 다른 시간/점수는 별도 상수입니다.

| 구역 | 실제 소비 경로 | 값의 출처/적용 |
|---|---|---|
| 검출·슬롯·자세 기본값 | configuration → configure_products → 검증된 preprocessing/recipe/pose → Detector/EngineInspector | 현재 frozen package의 기존 값. 생성물 직접 편집 금지 |
| 촬영·품질·전체 기한 | standalone_service → station_settings → InspectionService → Worker | 저장된 운영 station과 동일함을 대조 |
| 움직임·ORB·정규화 | engine_inspector, engine_pose, engine_rectification | 기존 소스의 동일 리터럴 이관 |
| 제품 추적 | production_profile.tracker_config → SingleActiveTrackerConfig | 기존 정규화 이동·소실·영역 진입 값 |
| 저장·큐·로그·미리보기 | Journal, 진단 writer, InspectionService, Worker, RuntimeLog | 기존 소스 기본값. 최종 운전 디스크 여유는 line_profile 값 유지 |
| PLC/IPC | opener_cyclic + 검증된 기존 C 바이너리 | Python 소비값 연결. 400ms 및 승인/결과 lease는 고정 계약, C 재빌드 없이 변경 불가 |
| 이력 검색 | HistoryReader/history_api | 신규 기능의 페이지·CSV·조회 시간 상한 |

다음은 일반 보정 상수로 옮기지 않습니다: 배열 인덱스·좌표 수학·프레임/패킷 무결성 규칙, PLC 바이트/극성/래더, 오류 상태 이름, 인증정보, 장치 IP/USB 경로/승인 기록, 승인된 실제 검사영역 geometry, 모델·Pose 기준 배열·동결 참고 오조립 소스/학습 통계. 이들은 기존 계약/장치 설정/해시 자산입니다. 옛 BENCH·MOCK fixture, 학습/평가 CLI와 동결 분석 소스의 실험별 값까지 운영 config를 덮어쓰도록 통합하지 않습니다. 핵심 운전값 이관이며 저장소의 모든 숫자를 자유 조절 변수로 바꾼 작업은 아닙니다.

## 값 보존과 적용

이번에는 기준값을 변경하지 않았습니다. 촬영 3초·안정 0.6초·새 원본 3장·400ms ready lease·모델 640 입력을 제한 계약으로 검증합니다. 잘못된 자료형·NaN·범위·시간예산 충돌은 후보 오류이며 다른 기본값으로 숨기지 않습니다.

제품 패키지 값 변경이 필요할 때 기존 자산을 복제해 생성합니다:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 notebook/deployment/configure_products.py --output runs/새로운_제품후보
```

기본값으로 생성하면 파일 바이트가 원본과 같아야 합니다. 변경 후보는 manifest/pose SHA를 재계산하고 기존 로더를 통과해야 합니다. 운영 시작·패키지 교체에서 config와 엔진 패키지 불일치를 거부합니다. 생성은 배포 승인이 아니며 기존 운영 패키지를 덮어쓰지 않습니다.

설정은 프로세스 시작 때 고정합니다. 편집 후 서비스/Worker를 함께 재시작해야 하며 운전 중 자동 reload는 없습니다. Worker만 새 설정으로 다시 시작되면 부모와 SHA 불일치를 차단합니다. 새 검사 `package_json.configuration`에 당시 값·SHA를 보존하고 `/api/v1/configuration`은 해당 서버의 시작 시점 값을 제공합니다. 과거 DB에는 없던 설정을 소급해서 만들어 넣지 않습니다.

배포는 기존 STOP·검사/저장/전송 유휴·백업 검증 경계에서 수행합니다. 현재 미채택 `jetson/config/area_clearance.json` 로컬 후보는 별도 보존하며 이번 Git 공개본에 끼워 넣지 않습니다. 공개 트리는 기존 채택된 파일을 유지합니다. 기존 C 바이너리/모델은 변경하지 않습니다.

## 웹과 DB

기존 현장 화면의 카메라/마지막 저장 검사 구분, 기록 메뉴와 유지보수 접기를 정리했습니다. `/history`는 제품·기간·원판정·상태·ID/오류 검색, 상세·이미지·당시 모델, 원판정과 PLC 값 분리, 페이지 이동, CSV 내보내기를 제공합니다. 기준 진단은 제품 검사와 구분합니다. 검색은 별도 SQLite 읽기 전용 연결을 쓰며 Journal writer lock을 사용하지 않습니다. 삭제·원판정 편집·운전 제어 API는 추가하지 않습니다.

노트북 DB 사본 조회는 [DB 안내](../database/README.md)를 따릅니다. 현재 DB 사본에는 사진 파일이 없으므로 이미지 누락 안내가 정상이며 실제 카메라 고장으로 표시하지 않습니다. 저장된 오류는 원래 이유대로 남습니다. 검색 화면 구현은 기존 검출 실패·카메라 재부팅 문제를 해결했다는 뜻이 아닙니다.

검증 결과는 `docs/verification/CONFIG-UI-HISTORY-20261018.json`에 기록합니다. Jetson 적용·재부팅·실제7건 저장/PLC 완료를 확인했습니다. 이번 작업은 GPU 성능 개선이나 장시간 안정성 인증이 아닙니다. 케이스별 50회 보정·추가 학습은 후속 작업입니다.

부품 카드의 crop는 해당 검사에 저장된 원본 프레임과 기본 부품 검사의 신뢰 가능한 슬롯 좌표를 사용합니다. 누락된 부품의 자리도 표시하며, 위치 근거가 없으면 사진 없음으로 남깁니다. 원본 방향·모델 입력·임계값은 바꾸지 않습니다. 미결합 여부는 크게, 오조립은 작은 참고 글씨로 표시합니다.
