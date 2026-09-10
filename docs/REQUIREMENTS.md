# Requirements

## 프로젝트 범위 (현재)

- V0는 `PLAN-REVISION-001` 기준으로 **실행 계획 수립**이 완료된 상태에서 `V0-T02`부터 시작한다.
- 이 계획 수립 단계에서는 다음을 수행하지 않는다.
  - 대형 데이터셋 다운로드
  - 모델 학습/평가/온전성 검증 실행
  - ONNX 변환, Jetson 배포 실행
  - PLC/Conveyor 하드웨어 구현

## 핵심 요구사항

- V0는 `V0-A`에서 ML 환경 smoke test, `V0-B`에서 proxy dataset 기반 workflow 연습, `V0-C`에서 런타임 통합 연습을 모두 포함한다.
- `V0`에서는 proxy 모델의 결과를 V1의 실제 엔진 모델로 교체하기 쉬운 구조를 먼저 만든다.
- 교체 지점은 최소화:
  - Dataset
  - Classes / Labels
  - Trained Model
  - Recipe
  - Evaluation Dataset
- 인터페이스 기반 구조 유지:
  - Detector interface: Fake / PyTorch / ONNX / TensorRT
  - Camera interface: Replay / SampleImage / V4L2
- 판정 결과는 항상 `PASS / FAIL / REVIEW / ERROR`.
- `EMERGENCY STOP`은 AI 판정 enum에 포함하지 않는다.
- 대규모 바이너리(모델/훈련 원천 데이터)는 기본 Git 커밋에서 제외한다.
- V0의 실제 학습 데이터는 Proxy dataset이며, public 데이터는 smoke test 용도로만 사용한다.
- 학습 기록은 `docs/ML_LEARNING_GUIDE.md`의 최소 템플릿으로 각 T02~T10 task에서 작성한다.

## V0 타겟 모듈

- Camera adapter and camera quality checks
- Detector contracts + adapters
- Recipe engine
- Decision engine
- Journal persistence (SQLite/evidence)
- REST API
- Web HMI
- Mock PLC request contract
- Jetson deployment package boundary design
- Failure/recovery testing baseline
