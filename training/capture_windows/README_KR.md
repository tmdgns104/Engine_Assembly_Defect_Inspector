# Windows 제품 데이터 촬영

노트북 카메라의 실시간 화면을 보면서 사람이 선택한 상태를 한 장씩 저장한다. 제품 JSON을 바꾸면 엔진 모형에도 같은 도구를 사용한다.
**선택한 상태는 촬영자가 기록한 정답이며 AI 판정 결과가 아니다.** 검출·라벨링·DB·최종 검사 HMI는 없다.

## 실행

`D:\OneDevice_Team_project\scripts\start_capture_windows.cmd`를 더블클릭한다.
자신의 위치에서 프로젝트를 찾고 기존 `.venv` Python을 사용한다. 가상환경 활성화나 실행 시 설치는 필요 없다.
실패하면 콘솔에 이유를 남기고 Python 종료 코드를 보존한다.

동일한 직접 실행 명령(프로젝트 루트):

```powershell
.venv\Scripts\python.exe -X utf8 -m training.capture_windows
```

선택 인자: `--profile training/datasets/proxy/earbud_case_v0/profile.json --output-root data/proxy/raw`.
기존 Python3.13.5 / OpenCV5.0.0 / Pillow12.3.0 / Tk8.6을 사용하며 추가 설치는 없다.
시작 시 카메라를 자동으로 열지 않는다. 왼쪽 스크롤바로 아래 배치/수량 영역까지 볼 수 있다.

## 첫 정상 사진 한 장

1. 제품이 **열린 이어폰 케이스 / earbud_case_v0**인지 확인한다. 다른 제품은 `제품 설정 선택`에서 profile.json을 고른다.
2. 후보 인덱스, DSHOW 또는 MSMF, 요청 해상도를 선택하고 `연결`을 누른다. 인덱스0이 외부 USB 카메라라는 뜻은 아니다.
   화면으로 장치를 확인하고, 다르면 `연결 해제`가 끝난 뒤 다른 후보를 직접 선택한다. 자동 탐색/폴백은 없다.
3. **실제 영상 크기**를 확인한다. 요청과 다르면 경고하며 원본을 강제로 resize하지 않는다.
   FPS는 장치 보고값으로 실측 처리속도가 아니다. 미지원 FPS/FOURCC와 미확인 장치 이름은 미확인으로 표시한다.
4. 조명·배경·높이·케이스 방향을 조건란에 적고 `새 촬영 묶음`을 누른다.
5. 열린 케이스의 실제 L/R 자리에 양쪽 이어폰을 놓는다. `정상 (NORMAL)`을 선택하고 손을 뺀 뒤 `한 장 저장`을 누른다.
6. **저장 완료** 뒤 `최근 저장 사진 보기`로 구도·초점·반사·실제 상태를 검토한다.

첫 사진 검토 뒤 같은 조건/묶음에서 다음 상태로 진행한다. L/R은 실물 표시 기준이며 영상의 좌우로 정하지 않는다.

| 선택 상태 | 실제 배치 |
|---|---|
| 정상 / NORMAL | 열린 케이스 양쪽 자리에 이어폰 있음 |
| 왼쪽 누락 / MISSING_LEFT | 왼쪽만 제거, 오른쪽과 케이스 유지 |
| 오른쪽 누락 / MISSING_RIGHT | 왼쪽을 되돌리고 오른쪽만 제거, 케이스 유지 |
| 양쪽 누락 / MISSING_BOTH | 양쪽 제거, 케이스 유지 |

첫 네 장은 구도·저장 흐름 확인용이다. 충분한 학습 데이터나 AI 검사 성공이 아니다. 81장/90장을 확정 목표로 사용하지 않는다.

## 학습용 수집 전에 확인할 조건

2026-09-13 실제 HCAM01L에서 네 상태 각1장의 저장 흐름을 확인했다. 학습 데이터의 충분성·검사 성능 검증은 아직 없다.
카메라 높이/각도/고정 위치와 기본 조명을 정하고 원본에서 슬롯 구분·반사·가림·선명도를 먼저 확인한다.
물체 위치·방향과 조명은 실제 사용에서 허용할 범위로 정한다. 각 조건에서 네 상태를 고르게 수집해 특정 상태만 어둡거나 다른 각도가 되지 않게 한다.
카메라 자세·주요 조명 조건 변경은 새 session, 물체를 실제 다시 놓거나 상태를 바꾸는 것은 새 episode다.
같은 배치의 burst를 독립 자료로 계산하지 않는다. 이후 평가에 쓸 별도 촬영 묶음도 계획하되 지금 split/labeling/training은 하지 않는다.
정확한 필요 수량은 범위와 이후 별도 묶음의 오류 분석으로 정한다. 사진 수나 단순 증강만으로 부족한 실제 조건을 대신했다고 판단하지 않는다.
근거: [Ultralytics 수집 조건 지침](https://docs.ultralytics.com/yolov5/tutorials/tips-for-best-training-results/),
[편향된 조건과 실제 환경 평가](https://docs.ultralytics.com/guides/model-testing/).

## 촬영 묶음과 물체 배치

- **촬영 묶음(session)**: 같은 제품 설정·실제 카메라·해상도·조명·배경의 연속 촬영. UTC+난수 ID로 폴더 충돌을 피한다.
- **물체 배치(episode)**: 한 번 실제 배치한 상태. 상태 선택을 바꾸거나 `새 배치`를 누르면 새 ID다. 같은 배치를 여러 장 찍으면 같은 episode를 유지한다.
- 실제 재배치는 사람이 `새 배치`를 눌러 기록한다. 물체 이동을 자동 인식하지 않는다.
- 제품/장치/요청·실제 해상도/주요 조건을 바꾸면 새 묶음이다. 높이·노출 등을 외부에서 바꾼 경우도 포함한다.
- `기존 촬영 묶음 열기`에서 session 폴더를 고르면 이미지·기록·해시 검증 후 수량을 복원한다. 같은 장치/조건인지 사람이 확인해야 이어서 촬영하며 새 배치로 시작한다.
  USB 재연결/부팅 후 인덱스는 물리 장치 identity가 아니므로 화면으로 재확인한다.
- 세션 정보 없는 기존 CLI v1/v2 기록은 검증·열람만 한다. 기존 기록을 변환하거나 새 프로필로 해석하지 않는다.
  실제 카메라는 sample 묶음에 추가할 수 없다. 다시 제품 설정을 선택하고 새 묶음으로 촬영한다.

## 저장과 재검증

기본 위치: `D:\OneDevice_Team_project\data\proxy\raw\`

```text
<session_id>/
  session-info.json
  manifest.jsonl
  <episode_id>/images/<capture_id>.png
```

PNG는 원본 크기/픽셀을 무손실 저장하며 UI·문구·박스·좌우 반전·crop·resize가 없다. 미리보기만 축소한다.
같은 카메라 입력 경로의 최신 프레임을 사용한다. 수신 후1초 초과, 끊김, 상태/배치 변경 이전 프레임,
저장 중 중복 클릭과 동일 프레임 재저장은 차단한다. 연결 ID·순번은 메모리에서 관리한다.
`captured_at`은 UTC 소프트웨어 수신 시각이며 센서 노출 시각을 보장하지 않는다.

기존 `make_record → save_capture → verify_session`으로 PNG·manifest·재로드·크기·해시를 확인해야 완료/수량을 갱신한다.
전체 묶음을 검사하므로 큰 묶음은 완료까지 오래 걸릴 수 있다. 저장과 검증은 background에서 실행한다.

`session-info.json`의 `session_info_schema_version=1`: session ID/UTC 생성 시각, 제품 사본/정규 JSON 해시,
hostname, 입력 종류, 촬영 조건, 카메라 index/backend/요청·실제 크기/장치 보고 FPS·FOURCC를 보존한다.
장치 이름은 확인된 매핑이 없어 null이다. 시작 관측 설정이며 모든 동적 속성의 telemetry는 아니다.
`session.validate_info`가 검증한다. manifest는 기존 v2 그대로이며 임의 필드를 추가하지 않았다. v1도 유지한다.
scenario/objects_removed는 수집 정답이다. 향후 Runtime이 이를 읽어 정상/비정상을 결정하면 안 된다.

기존 검증 명령에서 `<실제_SESSION_ID>`를 폴더 이름으로 바꾼다.

```powershell
.venv\Scripts\python.exe training/scripts/verify_proxy_captures.py --output-root data/proxy/raw --session-id <실제_SESSION_ID>
```

## 오류와 종료

- 연결 실패는 후보/backend, Windows 카메라 권한, 다른 앱 점유를 확인한다. 다른 프로그램을 임의로 종료하지 않는다.
- 정상 해제는 소유 작업 프로세스에서 `release()`한다. native 호출이 멈추면2초 유예 후 **이 앱의 카메라 프로세스만** 종료하여 OS 자원을 정리한다.
  이는 정상 release 완료와 구분하여 오류 문구를 남긴다. 연결 timeout은15초이며 다른 장치로 전환하지 않는다.
- 저장/검증 실패는 성공 수량을 올리지 않고 해당 묶음 추가 저장을 막는다. 오류의 폴더·PNG·manifest를 확인한다.
  PNG/불완전 JSONL/`.capture.lock`을 자동 삭제하지 않는다. 먼저 백업하고 writer 종료 여부와 verifier 결과로 복구를 판단한다.
  파일은 저장됐지만 검증만 실패했을 수도 있으므로 바로 중복 촬영하지 않는다.
- 종료는 진행 중인 저장을 마친 뒤 닫는다. 강제 전원 종료/디스크 장애까지 원자적 저장을 보장하지 않는다.
- 사진/기록은 Git 제외 경로다. 자동 테스트는 임시 합성 sample만 사용한다.

## 엔진으로 재사용

제품 ID·부품·촬영 상태는 새 profile.json에서 정한다. 실물 도착 전 엔진 부품명/개수는 확정하지 않는다.
선택적 display.json은 `display_schema_version=1`, `product_name`, `scenario_labels`를 가지며 없으면 원래 ID/상태 이름을 표시한다.
표시 이름은 핵심 저장 규칙과 해시에서 분리된다. 입력·화면·session/episode·PNG/JSONL·검증은 재사용한다.
Runtime 모델/Recipe는 별도다.

## 코드와 테스트

`__main__.py`(시작) → `app.py`(화면/선택) → `camera.py`(단일 입력 소유) → `session.py`(묶음/기존 저장기) 순서로 읽는다.
카메라 프로세스, 저장 스레드, Tk 화면 스레드를 분리했다. preview queue는 제한되며 종료 시 미전달 프레임을 버릴 수 있다.
종료한 프로세스/채널은 재사용하지 않는다. 버튼만 실제 데이터 저장 요청을 만든다.

```powershell
.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
```

모의 카메라/가상 제품 테스트는 실제 USB 카메라나 엔진 검사 성공이 아니다. 실기기는 사용자의 다음 실행에서 확인한다.
기술 근거: [OpenCV backend 선택](https://docs.opencv.org/4.13.0/d0/da7/videoio_overview.html),
[Python 프로세스 종료/queue 주의](https://docs.python.org/3.13/library/multiprocessing.html).
