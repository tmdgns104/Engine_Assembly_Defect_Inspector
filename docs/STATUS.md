Current Phase:
V0 Proxy Inspection System — 진행 중, 전체 완료 아님

Completed:
V0-T01, PLAN-REVISION-001, PLAN-AUDIT-001, V0-T02, V0-T03, V0-T04
HUMAN-CAPTURE-001-PREP: DONE / VERIFIED (촬영 준비 범위)
WINDOWS-CAPTURE-001: DONE / VERIFIED (구현·자동 테스트·합성 입력 GUI 확인 범위)

Current Task:
WINDOWS-CAPTURE-001 — Windows 노트북 USB 카메라 촬영 화면

State:
DONE / VERIFIED — 프로그램 완료; 실제 USB 카메라 연결 확인·배치·촬영은 사용자 실행 대기

Product Selection:
완료: earbud_case_v0 — 열린 케이스 안의 실제 L/R 이어폰

Capture Tool / Configuration:
JSON profile 선택, v1 호환 + v2 설정 사본/해시, 네 시나리오 지원 완료.
Windows 촬영 창: 제품/상태 선택, DSHOW/MSMF 후보 선택, 실시간 미리보기,
원본 PNG 한 장 저장, 묶음/배치 관리, 기존 기록 검증·수량 복원.
Windows 전체 92/92 테스트 성공 (기존 56개 보존 + 추가 36개).
실제 Tk 창의 합성 입력 화면 확인 완료. 실제 USB 카메라 프레임은 미검증.
실행: scripts/start_capture_windows.cmd (기존 프로젝트 .venv, 추가 설치 없음).

Confirmed Formal Captures:
0장 (2026-09-13 검증 시 로컬 data/proxy/raw PNG/manifest 0개; 이번 자동 실제 촬영 없음)
첫 준비 목표는 네 상태 각 한 장. 총수집량은 첫 사진 검토 후 결정한다.
과거 81장 계획 및 90장 제안을 현재 확정 수량이나 실적으로 사용하지 않는다.

Human Placement / Photo Review:
미실행 / 미실행

V0-T05 / Labeling:
TODO / NOT STARTED — 실제 촬영과 사진 검토 전 시작하지 않음

Next Task:
HUMAN-CAPTURE-001 — Windows 노트북 + USB 카메라
scripts/start_capture_windows.cmd 실행 → 후보 연결/화면 확인 → 정상 배치 → 첫 정상 사진 한 장 저장·검토

Evidence / Boundaries:
- 현재 촬영 화면 계약: tasks/windows-capture-001.md; 사용 안내: training/capture_windows/README_KR.md.
- 현재 검증: docs/verification/WINDOWS-CAPTURE-001.txt. 92/92 PASS, 보호 tracked 파일 150개 해시 일치, 설치 패키지 42개 버전 유지.
- 선행 준비 계약: tasks/human-capture-001-prep.md.
- 준비 검증: docs/verification/HUMAN-CAPTURE-001-PREP.txt; 보호 파일 229개 해시 일치, 기존 v1 sample 3장 검증 성공.
- 검사 명세·촬영 순서: training/datasets/proxy/earbud_case_v0/README.md.
- 기존 V0-T02 GPU smoke, T03 공통 계약, T04 수집 도구·사용자 실행 하드웨어 검증은 완료 상태와 원래 Evidence를 유지한다.
- T04 CAMERA_SMOKE 3장은 USER-EXECUTED / VERIFIED인 과거 관측이며 정식 데이터에서 제외한다. 현재 카메라 모델·노드·지원 포맷은 미확인이다. 당시 노드/FPS를 현재 값으로 가정하지 않는다.
- 이번 Windows 작업: 실제 카메라 자동 접근·촬영, Jetson 접속, CAD 수정, 환경 설치, 라벨링/분할/학습/튜닝/평가/변환/PLC 제어 없음.
- 합성 sample 검증은 실제 촬영·검사 성공·모델 성능 검증으로 집계하지 않는다.
- Detector/Decision/DB/HMI 구현은 기존 후속 Task 범위다. 준비 완료는 V0 완료가 아니다.
