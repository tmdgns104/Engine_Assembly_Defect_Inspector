Current Phase:
V0 Proxy Inspection System — 진행 중, 전체 완료 아님

Completed:
V0-T01, PLAN-REVISION-001, PLAN-AUDIT-001, V0-T02, V0-T03, V0-T04
HUMAN-CAPTURE-001-PREP: DONE / VERIFIED (촬영 준비 범위)

Current Task:
HUMAN-CAPTURE-001-PREP — 검사 기준 설정 / 데이터 촬영 준비

State:
DONE / VERIFIED — 준비 완료; 사람의 장치 확인·배치·촬영 대기

Product Selection:
완료: earbud_case_v0 — 열린 케이스 안의 실제 L/R 이어폰

Capture Tool / Configuration:
JSON profile 선택, v1 호환 + v2 설정 사본/해시, 네 시나리오 지원 완료.
Windows 전체 56/56 테스트 성공 (기존 40개 무수정 + 추가 16개).

Confirmed Formal Captures:
0장 (로컬 data/proxy/raw PNG/manifest 0개; 이번 실제 촬영 없음)
첫 준비 목표는 네 상태 각 한 장. 총수집량은 첫 사진 검토 후 결정한다.
과거 81장 계획 및 90장 제안을 현재 확정 수량이나 실적으로 사용하지 않는다.

Human Placement / Photo Review:
미실행 / 미실행

V0-T05 / Labeling:
TODO / NOT STARTED — 실제 촬영과 사진 검토 전 시작하지 않음

Next Task:
HUMAN-CAPTURE-001 — Jetson에서 현재 카메라 확인 → 정상 배치 → 첫 정상 사진 촬영·검토

Evidence / Boundaries:
- 현재 준비 계약: tasks/human-capture-001-prep.md.
- 준비 검증: docs/verification/HUMAN-CAPTURE-001-PREP.txt; 보호 파일 229개 해시 일치, 기존 v1 sample 3장 검증 성공.
- 검사 명세·촬영 순서: training/datasets/proxy/earbud_case_v0/README.md.
- 기존 V0-T02 GPU smoke, T03 공통 계약, T04 수집 도구·사용자 실행 하드웨어 검증은 완료 상태와 원래 Evidence를 유지한다.
- T04 CAMERA_SMOKE 3장은 USER-EXECUTED / VERIFIED인 과거 관측이며 정식 데이터에서 제외한다. 현재 카메라 모델·노드·지원 포맷은 미확인이다. 당시 노드/FPS를 현재 값으로 가정하지 않는다.
- 이번 Windows 작업: 장비 접속, CAD 수정, 환경 설치, 라벨링/분할/학습/튜닝/평가/변환/배포/PLC 제어 없음.
- 합성 sample 검증은 실제 촬영·검사 성공·모델 성능 검증으로 집계하지 않는다.
- Detector/Decision/DB/HMI 구현은 기존 후속 Task 범위다. 준비 완료는 V0 완료가 아니다.
