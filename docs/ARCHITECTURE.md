# Architecture (V0 Proxy Inspection System)

```
V0-A (Proxy Dataset Smoke):
Training Environment (PyTorch/Python/CUDA/GPU)

V0-B:
Camera Capture
    ↓
Image Quality Gate
    ↓
Detector (interface -> Fake/PyTorch/ONNX/TensorRT)
    ↓
Recipe Engine
    ↓
Decision Engine
    ↓
PASS / FAIL / REVIEW / ERROR
    ↓
Journal + Evidence
    ↓
REST API
    ↓
Web HMI

Manual Request + Mock PLC Adapter
    ↓
Edge Service

V0-C:
Jetson Runtime (V4L2 + trained proxy model)
    ↓
Quality + Detector + Recipe + Decision + Journal + API + HMI
```

## 핵심 구조 원칙

- `Training`과 `Runtime`은 분리한다.
- 인터페이스 계약이 먼저 정의되어야 하며, 구현체는 뒤따라 교체 가능해야 한다.
- Detector/Camera는 런타임에서 직접 참조하지 않고 contract를 통해 주입한다.
- V1은 proxy 자산을 엔진 자산으로 대체해 런타임을 재사용한다.
- V2는 MockPLC를 RealPLC로 교체해 자동화 파이프라인만 확장한다.

## Training / Runtime 경계

- `training/`:
  - config, dataset metadata, experiments, scripts
  - 모델 훈련/평가/튜닝/실험 결과
- `src/`, `apps/`, `recipes/`, `config/`, `tests/`:
  - Runtime, API, HMI, Journal, control contracts

## Detector contract

- `Detector` 인터페이스
  - `FakeDetector`
  - `PyTorchDetector`
  - `ONNXDetector`
  - `TensorRTDetector` (Jetson)

## Camera contract

- `Camera` 인터페이스
  - `ReplayCamera`
  - `SampleImageCamera`
  - `V4L2Camera` (Jetson)

## 배포 패키지 경계(문서화 대상)

기본적으로 Jetson에는 아래만 전달한다.

- `deployment/model/model.onnx`
- `deployment/classes.yaml`
- `deployment/recipe.yaml`
- `deployment/camera.yaml`
- `deployment/runtime.yaml`
- `deployment/manifest.json`
