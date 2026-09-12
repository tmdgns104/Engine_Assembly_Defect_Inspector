Current Phase:
V0 Proxy Inspection System — 진행 중, 전체 완료 아님

Completed:
V0-T01, PLAN-REVISION-001, PLAN-AUDIT-001, V0-T02, V0-T03, V0-T04
HUMAN-CAPTURE-001-PREP: DONE / VERIFIED (촬영 준비 범위)
WINDOWS-CAPTURE-001: DONE / VERIFIED (소프트웨어 + 최초 실제 USB 촬영 흐름)
WINDOWS-CAPTURE-002: DONE / VERIFIED (제품별 안내 촬영 소프트웨어)

Current Task:
WINDOWS-CAPTURE-002 — 제품별 배치·조명 안내와 사람 검토 게이트

State:
DONE / VERIFIED — 제품별 안내, 준비 확인, 저장 후 사람 검토, 재촬영 원본 보존, 진행 복원 구현.
111/111 자동 테스트 및 실제 Tk 창의 합성 입력 흐름 확인. 새 안내에 따른 실물 촬영은 사용자 실행 대기.
학습용 데이터 준비 완료를 뜻하지 않는다. 기존 WINDOWS-CAPTURE-001의 실제 네 장 검증은 보존한다.

Product Selection:
완료: earbud_case_v0 — 열린 케이스 안의 실제 L/R 이어폰

Capture Tool / Configuration:
JSON profile 선택, v1 호환 + v2 설정 사본/해시, 네 시나리오 지원 완료.
Windows 촬영 창: 제품/상태 선택, DSHOW/MSMF 후보 선택, 실시간 미리보기,
원본 PNG 한 장 저장, 묶음/배치 관리, 기존 기록 검증·수량 복원.
Windows 전체 92/92 테스트 성공 (기존 56개 보존 + 추가 36개).
후속 안내 기능: capture-guide.json, 조건별 새 묶음, 모든 상태의 단계 안내, 준비/원본 검토 게이트.
새 전체 테스트 111/111 (원래 92개 + 안내 기능 19개). 검토 기록은 버전 있는 별도 JSONL이며 기존 manifest는 유지한다.
실제 Tk 창의 합성 입력 검증 이후, HCAM01L / DSHOW 후보2 / 1280×720 / MJPG 영상 수신과 PNG 저장을 확인했다.
장치 보고 FPS는 미확인(null)이다. 후보 번호는 현재 열거 결과이며 영구 장치 identity가 아니다.
실행: scripts/start_capture_windows.cmd (기존 프로젝트 .venv, 추가 설치 없음).

Confirmed Formal Captures:
4장 (2026-09-13): NORMAL 1 / MISSING_LEFT 1 / MISSING_RIGHT 1 / MISSING_BOTH 1.
Session: S20260912T171113_B362774D. 같은 묶음, 실제 배치별 E0001~E0004.
사용자가 실물 배치와 준비를 확인했고, 사용자 요청에 따라 Codex가 GUI에서 상태 선택·저장을 수행했다.
기존 verifier의 reload/크기/기록/해시 검증 성공. 사진은 로컬 Git 제외 경로에만 있다.
첫 준비 목표는 네 상태 각 한 장. 총수집량은 첫 사진 검토 후 결정한다.
과거 81장 계획 및 90장 제안을 현재 확정 수량이나 실적으로 사용하지 않는다.

Human Placement / Photo Review:
4개 상태의 사용자 배치 완료 / Codex가 실제 원본 4장을 열어 확인.
열린 케이스와 각 이어폰 상태는 보이나 노이즈·부드러운 윤곽이 관찰되어 구도/저장 확인용으로 유지한다.
최종 촬영 품질과 확대 수집 조건의 사용자 승인은 아직 없다.

V0-T05 / Labeling:
TODO / NOT STARTED — 실제 촬영과 사진 검토 전 시작하지 않음

Next Task:
HUMAN-CAPTURE-001 — Windows 노트북 + USB 카메라
기존 네 장을 참고해 조명·카메라 고정·구도를 정하고 앱의 「기준 구도·조명 확인 → 새 안내 촬영」으로 진행한다.
실제 조건을 기록하고, 배치 준비 확인 → 한 장 저장 → 원본 검토를 사람이 수행한다. 필요할 때 다음 조건을 선택한다.
카메라 높이/각도와 기준 조명을 먼저 정하고, 각 허용 조명·물체 위치/방향 조건마다 네 상태를 고르게 수집한다.
같은 배치의 burst로 수량을 채우지 않으며 실제 상태와 환경 변화가 뒤섞이지 않게 session/episode를 보존한다. T05는 자동 시작하지 않는다.

Evidence / Boundaries:
- 안내 촬영 계약: tasks/windows-capture-002.md; 검증: docs/verification/WINDOWS-CAPTURE-002.txt.
- 기존 실제 PNG 4장과 manifest/session-info 총6개 파일 SHA256 일치. 이 사진은 안내 완료 건수로 소급 집계하지 않는다.
- 현재 촬영 화면 계약: tasks/windows-capture-001.md; 사용 안내: training/capture_windows/README_KR.md.
- 현재 검증: docs/verification/WINDOWS-CAPTURE-001.txt. 92/92 PASS, 보호 tracked 파일 150개 해시 일치, 설치 패키지 42개 버전 유지.
- 후속 실기기 검증: docs/verification/WINDOWS-CAPTURE-001-HARDWARE.json. 실제4장과 state/episode/크기/SHA256 연결, 재연결/GUI 수량 복원 확인. 단순 장치 목록 인식과 실제 프레임 수신·저장을 구분한다.
- 선행 준비 계약: tasks/human-capture-001-prep.md.
- 준비 검증: docs/verification/HUMAN-CAPTURE-001-PREP.txt; 보호 파일 229개 해시 일치, 기존 v1 sample 3장 검증 성공.
- 검사 명세·촬영 순서: training/datasets/proxy/earbud_case_v0/README.md.
- 기존 V0-T02 GPU smoke, T03 공통 계약, T04 수집 도구·사용자 실행 하드웨어 검증은 완료 상태와 원래 Evidence를 유지한다.
- T04 CAMERA_SMOKE 3장은 USER-EXECUTED / VERIFIED인 과거 관측이며 정식 데이터에서 제외한다. 현재 카메라 모델·노드·지원 포맷은 미확인이다. 당시 노드/FPS를 현재 값으로 가정하지 않는다.
- 이번 Windows 후속 작업은 사용자 승인 후 지정 USB 카메라를 연결하고, 실제 배치 준비 확인마다 한 장씩 저장했다. 자동 burst 촬영, Jetson 접속, CAD 수정, 환경 설치, 라벨링/분할/학습/튜닝/평가/변환/PLC 제어 없음.
- 합성 sample 검증은 실제 촬영·검사 성공·모델 성능 검증으로 집계하지 않는다.
- Detector/Decision/DB/HMI 구현은 기존 후속 Task 범위다. 준비 완료는 V0 완료가 아니다.
