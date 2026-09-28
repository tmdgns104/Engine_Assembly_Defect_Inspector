# Project: On-Device AI 기반 엔진 모형 조립 검사 시스템

## Vision

이 프로젝트는 `V0 → V1 → V2` 로 진행합니다.

- **V0 Proxy Inspection System**: 실제 엔진 없이도 전체 ML workflow와 inspection runtime을 실제 구조로 연습.
- **V1 Engine Vision Inspection**: 엔진 도착 후 Proxy asset를 실제 asset로 교체.
- **V2 PLC/Conveyor Integration**: Mock PLC에서 실제 PLC/Conveyor/Sensor/Motor Driver로 확장.

## V0 정의 (재정의)

V0는 실전 대비를 위해 3단계로 수행합니다.

- `V0-A`: 최소 public dataset(COCO8 수준)으로 Python/PyTorch/CUDA/RTX 5070/훈련 루프 검증.
- `V0-B`: 임시 물체로 구성한 Proxy dataset을 만들어 데이터 획득/라벨링/분할/학습/평가/내보내기/런타임 통합 연습.
- `V0-C`: Jetson에서 Proxy 모델까지 전체 런타임을 연결해 PASS/FAIL/REVIEW/ERROR 흐름을 검증.

## 핵심 원칙

- 현재 개발·검증 방식은 [구현 우선 + 변경 영향에 맞춘 검증](../CODEX_INSPECTION_APP_V1_KO.md#현재-작업-원칙--2026-09-28-사용자-지시)을 따른다. 기존 문서의 검증 빈도·범위와 기록 시점이 상충하면 이 최신 원칙을 적용한다.
- 2026-09-28 운영 요구: 카메라의 작은 흔들림 때문에 빈 기준 사진 재등록을 반복해야 하는 종료 방식은 채택하지 않는다. v004 고정 배경 비교는 실무 채택 보류이며, 불확실한 관측을 CLEAR로 바꾸거나 Track·검사 연결을 삭제해서 해결하지 않는다. 대체 방식의 구현·검증은 별도 설계 결정이 필요하다.

- Training/Runtime 분리 구조 유지.
- 인터페이스 우선:
  - `Detector`는 Fake/PyTorch/ONNX/TensorRT를 수용.
  - `Camera`는 Replay/Sample/V4L2를 수용.
- V1 교체 지점은 최소화:
  - Dataset / Classes / Trained Model / Recipe / Evaluation Set
- AI 판정 상태는 항상 `PASS / FAIL / REVIEW / ERROR`.
- 물리 엔진의 세부 규격(부품명/slot 수/좌표/임계치)은 엔진 도착 전까지 확정하지 않음.
- V0는 Proxy dataset를 학습 주 데이터셋으로 사용하고 COCO8은 V0-A smoke-only로만 제한.

## 학습형 V0 완료 조건

V0는 실제 구현 가능한 상태가 되어야 하며, 단순 문서 정리가 아니라 다음 항목을 실제로 달성해야 한다.

- ML 환경 설정 → Proxy 데이터 캡처 → 라벨링 → 그룹 분할 → Baseline 학습 → Tuning → Validation/Test 구분 → 최종 평가 → ONNX + parity → Runtime 통합 → Journal 저장 → API/HMI → Jetson E2E → Failure/Recovery → Packaging → Benchmark → TensorRT 리허설 판단 → V1 전환 준비.

## V0 상태

- `V0-T01` 부트스트랩은 완료.
- `PLAN-REVISION-001` 반영으로 V0 Task 순서를 재정의.
- `V0-T02`는 기존 Windows PC GPU smoke 결과 검증과 기록을 마쳐 DONE / VERIFIED.
- `V0-T03` 공통 Runtime 계약과 인터페이스는 DONE / VERIFIED이며, 실제 Adapter는 아직 구현하지 않았다.
- `V0-T04`는 수집 도구·계획·metadata와 사용자 실행 Jetson 실기기 smoke 3장 검증을 완료해 DONE / VERIFIED다.
- Proxy 제품은 열린 케이스 안의 이어폰 `earbud_case_v0`로 선택했다. 촬영 준비와 실제 수집 상태는 `docs/STATUS.md`, 검사 명세는 `training/datasets/proxy/earbud_case_v0/README.md`를 참조한다. 전체 수집량은 첫 네 장 검토 뒤 정하며 V0-T05는 실제 촬영·사진 검토 전까지 미시작이다.
