Current Phase:
V0 Proxy Inspection System — 진행 중, 전체 완료 아님

Completed:
V0-T01, PLAN-REVISION-001, PLAN-AUDIT-001, V0-T02, V0-T03, V0-T04
HUMAN-CAPTURE-001-PREP: DONE / VERIFIED (촬영 준비 범위)
WINDOWS-CAPTURE-001: DONE / VERIFIED (소프트웨어 + 최초 실제 USB 촬영 흐름)
WINDOWS-CAPTURE-002: DONE / VERIFIED (제품별 안내 촬영 소프트웨어)
DATASET-WIZARD-001: DONE / VERIFIED (전체 계획 수집 길잡이 소프트웨어)

Current Task:
DATASET-WIZARD-001 — 전체 수집 계획 자동 안내와 묶음 사람 확인

State:
DONE / VERIFIED — 계획/setup/조명/배치/상태 자동 순서, 준비 후 한 장 저장·검증,
품질 보조, 묶음 사람 확인·재촬영·정확한 재개·그룹 용도 예약·라벨링 인계 목록 구현.
130/130 자동 테스트 (기존111 + 추가19), 실제 Tk 창의 합성 입력/비교/확대 확인.
새 계획의 실제 USB 촬영은 사용자 실행 대기, 본수집 확정 0. 학습용 데이터 준비 완료를 뜻하지 않는다.
기존 WINDOWS-CAPTURE-001의 실제 네 장 및 WINDOWS-CAPTURE-002의 원래 Evidence는 보존한다.

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
현재 기본 화면: 「시작 / 이어하기」 수집 길잡이. 수동/한 조건 도우미는 고급 설정 또는 --manual로 유지.
기준 사진2장 → 준비 시험12장 → 본수집 초기240장(4회차×3조명×5배치×4상태).
스탠드가 없으면 준비 시험4장/본수집80장으로 조정하며 제외 이유를 보존한다. 충분한 학습량의 보장이 아니다.
수집 계획/이벤트는 별도 v1 파일이며 기존 manifest v1/v2와 GuidedRound의 사진별 검토 정책은 유지한다.

Confirmed Formal Captures:
4장 (2026-09-13): NORMAL 1 / MISSING_LEFT 1 / MISSING_RIGHT 1 / MISSING_BOTH 1.
Session: S20260912T171113_B362774D. 같은 묶음, 실제 배치별 E0001~E0004.
사용자가 실물 배치와 준비를 확인했고, 사용자 요청에 따라 Codex가 GUI에서 상태 선택·저장을 수행했다.
기존 verifier의 reload/크기/기록/해시 검증 성공. 사진은 로컬 Git 제외 경로에만 있다.
이 네 장은 최초 구도·저장 흐름 확인용이다. 새 수집 길잡이의 준비/본수집 수량에 소급 편입하지 않는다.
과거 81장 계획 및 90장 제안을 현재 확정 수량이나 실적으로 사용하지 않는다.

Human Placement / Photo Review:
4개 상태의 사용자 배치 완료 / Codex가 실제 원본 4장을 열어 확인.
열린 케이스와 각 이어폰 상태는 보이나 노이즈·부드러운 윤곽이 관찰되어 구도/저장 확인용으로 유지한다.
최종 촬영 품질과 확대 수집 조건의 사용자 승인은 아직 없다.

V0-T05 / Labeling:
TODO / NOT STARTED — 실제 촬영과 사진 검토 전 시작하지 않음

Next Task:
HUMAN-CAPTURE-001 — Windows 노트북 + USB 카메라
「시작 / 이어하기 → 새 수집 계획」으로 카메라·조명·기준 영역·실물 L/R을 확인한다.
사람은 안내된 물리 배치와 준비 버튼, 묶음 사진 확인을 수행한다. 프로그램이 다음 조건·저장·검증·수량·재개를 관리한다.
먼저 정상/빈자리 기준과 준비 시험을 실제 확인한다. 이후 계획은 여러 시간/날짜로 나눠 진행하고,
B03/B04는 같은 연속 촬영을 이름만 바꿔 독립 자료로 취급하지 않는다. 본수집 확정 0/240 또는 조명 선택 후 0/80.
같은 배치의 burst로 수량을 채우지 않으며 실제 상태와 환경 변화가 뒤섞이지 않게 session/episode를 보존한다. T05는 자동 시작하지 않는다.

Evidence / Boundaries:
- 수집 길잡이: tasks/dataset-wizard-001.md; docs/verification/DATASET-WIZARD-001.json; training/capture_windows/DATASET_WIZARD_KR.md.
- 130/130 PASS. 기존 실제 원본/기록을 포함한 보호 파일149개 해시 일치, 패키지42개 버전 유지. 이번 새 실제 촬영0장.
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
