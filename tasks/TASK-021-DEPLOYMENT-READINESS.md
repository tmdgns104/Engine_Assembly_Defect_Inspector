# TASK-021 — PLC 자동 반복검사 현장 배포 준비

기준: 52ba2d4bac83949766af837067592488742ba501. 상태: PACKAGE_VERIFIED / FIELD_AUTOMATIC_BLOCKED.

수행: 깨끗한 Git checkout의 설치·배포 회귀·패키지 검증, 필수 자산 목록과
기존 운영본 대조, 실제 Journal의 이전 제품 이탈 근거 및 자동 모드 차단 분석,
ARM64 격리 검증, 후속 최대 3제품 현장 시험·배포·복원 계획.

운영 current/설정/서비스/PLC/EDS/모델/Journal은 변경하지 않는다.
제품별 승인이나 알고리즘을 추가하지 않는다. 미검증 자격을 TRUE로 만들지 않는다.
CI 성공과 통신·제품 이탈·무인 운전 현장 검증을 구분한다.

증거: runs/engine_standalone_plc_autostart_001/v001_20261007T052746Z/tag_data_link_008/deployment_readiness_021/

확인한 원인: HEAD의 area_clearance는 기준 사진 없는 DARK_SURFACE_SELF_OBSERVED이나
allowlist에 로컬 과거 사진 9장이 남아 있었다. 로컬 dirty 설정은 별개로 보존한다.
필수 조립 검사 자산은 기존 비공개 동결 자산 28개이며, 공개 checkout의 기본 MOCK
패키지와 현장 통합 패키지를 명시적으로 구분하여 누락을 탐지해야 한다.

종료: 검증 및 Commit/Push 후 STOP_FOR_FIELD_DEPLOYMENT_APPROVAL. 다음 작업 자동 진행 금지.

결과: ARM64 Runtime287 + 배포31 PASS, 동결 자산28개 일치, 통합 패키지172파일.
운영 Release4920568 유지. 이전 제품 이탈 기록0건·온라인 PLC/timeout/출구/Class1 미검증.
보고서: docs/PLC_AUTOMATIC_DEPLOYMENT_READINESS_REPORT.md. GitHub Actions38553379628 SUCCESS 확인. STOP_FOR_FIELD_DEPLOYMENT_APPROVAL로 종료.
