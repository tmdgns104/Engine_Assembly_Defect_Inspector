# WINDOWS-CAPTURE-001 — Windows 공통 데이터 촬영 화면

Status: DONE / VERIFIED (소프트웨어 구현·자동 테스트·합성 입력 GUI 확인)
Actual USB Camera: USER_EXECUTION_PENDING
Baseline: 7cdc739c9ffba33a0ea67fea7ddac5af12572e7b

## 요구와 구조
- Windows 노트북 + 사람이 선택한 USB 카메라. 제품 JSON을 읽는 공통 Tkinter 수집 도구를 `training/capture_windows/`에 추가한다. Runtime Camera/Detector/HMI는 구현하지 않는다.
- 기존 `load_profile`, `make_record`, `save_capture`, `verify_session`을 재사용하며 PNG/manifest 저장을 UI에 복제하지 않는다. 기존 v1/v2 schema와 Linux V4L2 경로를 유지한다.
- 카메라 작업 프로세스 하나가 명시한 인덱스와 DSHOW/MSMF만 연다. 자동 탐색/폴백 없음. 정상 종료 시 release하고, native 호출이 멈추면 UI가 종료 유예 후 **자신의 카메라 작업 프로세스만** 종료한다. 종료된 채널은 재사용하지 않는다. 카메라 이름/인덱스 매핑은 미확인으로 둔다.
- Tk 주 스레드는 UI와 상태 선택만 처리한다. 저장/기존 묶음 검증은 직렬 background 작업으로 실행한다. 수신 UTC/monotonic/순번/연결 ID를 관리하고 최신 원본 프레임만 저장한다.
- 표시 이름은 제품 옆 `display.json`에서 선택적으로 읽으며 핵심 프로필·정답 규칙과 분리한다. 상태 변경/재배치는 새 episode, 제품·카메라·요청/실제 해상도·주요 조건 변경은 새 session이다.
- GUI 세션은 버전1 `session-info.json`에 프로필 사본/해시, 실제 backend/index, 요청·실제 해상도, 보고 FPS/FOURCC, 환경과 조건을 보존한다. manifest에는 새 필드를 추가하지 않는다.
- 기존 묶음은 전체 검증 후 수량 복원. GUI 세션과 동일한 조건을 사람이 확인해야 계속 촬영하며 재개 시 새 배치를 만든다. 세션 정보가 없는 기존 CLI v1/v2 기록은 검증/열람하고 새 묶음으로 촬영한다.
- 원본에는 UI/반전/crop/resize 없음. 저장 완료 후 전체 세션 재검증이 성공해야 성공 표시. 부분 실패는 파일을 보존하고 해당 묶음 추가 저장을 막는다.

## 보호 / 검증
- CAD/STL/원본 사진, src/contracts, 기존 테스트56개, 기존 ML 설치, v1/v2 저장·검증 코드 보존.
- 합성/모의 테스트만 자동 실행. 실제 카메라 선택·배치·촬영은 사람의 다음 작업. Jetson/학습/라벨링/분할/AI 판정/PLC 없음. V0-T05 TODO 유지.
- baseline: Python3.13.5 / OpenCV5.0.0 / Pillow12.3.0 / Tk8.6; 기존56개 PASS. 새 의존성 없음.
- 추가 테스트: backend선택/해제, 연결·읽기 실패/멈춤, stale/중복 차단, session/episode 전환, 네 상태와 다른 제품, 저장 실패/복구, 원본 보존, 기존 verifier, 실제 Tk 창 모의 입력.
- 기존 전체 unittest + 새 테스트, 가능한 GUI 직접 열기/시각 확인, 보호 파일/패키지·Git ignore 검증. 검증 뒤 선택 commit/push. 전역 Skill/Hook 구조 변경 없음.

## 결과 / Evidence
- 전체 92/92 PASS: 기존56개 + 새 카메라/저장 테스트29개 + Tk 화면 테스트7개. 기존 테스트/저장기/검증기/프로필/schema 무수정.
- 실제 Tk 창을 열어 초기 화면과 합성 입력 preview·저장·수량 화면을 확인했다. 합성 저장은 임시 경로의 sample이며 정식 Dataset에 포함하지 않는다.
- 실행 도구를 프로젝트 외부 현재 경로에서 확인: `--help` 종료0, 잘못된 프로필 종료1 유지. 시작 시 실제 카메라를 열지 않는다.
- 보호 tracked 파일150개와 설치 패키지42개의 이름/버전 일치. 정식 data/proxy/raw PNG/manifest는 검증 시0개. Git ignore 확인 완료.
- 검증 기록: `docs/verification/WINDOWS-CAPTURE-001.txt`; 한국어 안내: `training/capture_windows/README_KR.md`.
- 사용자는 USB 카메라가 노트북에 연결되어 있다고 알렸다. 후보 선택·실제 영상 수신·장치 해제·실제 PNG 저장은 아직 검증하지 않았다. 모의 성공과 구분한다.
- 다음 사람 작업: `scripts/start_capture_windows.cmd` 실행 → 외부 USB 화면 확인 → 새 촬영 묶음 → 양쪽 이어폰이 있는 정상 배치 → 한 장 저장·사진 검토.
- V0-T05는 TODO / NOT STARTED. 라벨링·분할·학습·최종 검사 HMI는 시작하지 않았다.
