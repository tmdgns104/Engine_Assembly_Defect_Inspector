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

- Training/Runtime 분리 구조 유지.
- 인터페이스 우선:
  - `Detector`는 Fake/PyTorch/ONNX/TensorRT를 수용.
  - `Camera`는 Replay/Sample/V4L2를 수용.
- V1 교체 지점은 최소화:
  - Dataset / Classes / Trained Model / Recipe / Evaluation Set
- AI 판정 상태는 항상 `PASS / FAIL / REVIEW / ERROR`.
- 물리 엔진의 세부 규격(부품명/slot 수/좌표/임계치)은 엔진 도착 전까지 확정하지 않음.

## V0 상태

- `V0-T01` 부트스트랩은 완료.
- `PLAN-REVISION-001` 반영으로 V0 Task 순서를 재정의.
- 구현 시작은 `V0-T02`부터이며, 현재는 계획 단계 수정만 수행.
