# Architecture (V0 Baseline)

## 개요

```
Camera
 ↓
Image Quality Gate
 ↓
Detector
 ↓
Recipe Engine
 ↓
Decision Engine
 ↓
PASS / FAIL / REVIEW / ERROR
 ↓
Edge Journal
 ↓
Web HMI

Mock PLC
 ↓
Inspection Request
 ↓
Edge Service
```

V0에서는 실제 하드웨어가 없으므로 `ReplayCamera`와 `FakeDetector` 중심으로 구성하고,
런타임 인터페이스는 V1/V2 교체가 가능하게 분리한다.

## Training / Runtime 경계

- `training/` : 데이터셋 구성, 실험, 모델 훈련, 평가, 체크포인트/실험 산출 관리
- `src/`, `apps/`, `config/`, `recipes/`, `tests/` : Runtime/API/Journal/Control 기반 검사 애플리케이션
- 동일 레이어에서의 상호의존은 YAML/파라미터 계약을 통해 최소화

## Detector 구조

- `Detector` 인터페이스
  - `FakeDetector`
  - `PyTorchDetector`
  - `ONNXDetector`
  - `TensorRTDetector` (V1 Jetson 단계)

## Camera 구조

- `Camera` 인터페이스
  - `ReplayCamera`
  - `SampleImageCamera`
  - `V4L2Camera` (Jetson 단계)
