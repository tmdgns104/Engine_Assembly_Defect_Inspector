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

## Train / Validation / Test 원칙 (V0)

- Train: 모델 가중치 업데이트용.
- Validation: 임계치 선택, 하이퍼파라미터 비교, 모델 선택용.
- Test: 마지막 고정 분할(sealed test), 1회만 최종 검증.
- Test 결과를 보고 조정이 발생하면 그 Test는 더 이상 최종 holdout으로 간주하지 못한다.

## ML 데이터 흐름 (V0)

- T02: COCO8 tiny smoke (환경 점검 전용).
- T04~T06: Proxy dataset capture/label/grouped split.
- T07: Baseline.
- T08: 2~3개 소규모 tuning.
- T09: Validation 중심 평가 + Error analysis, Test는 1회 최종 검증.
- T10: ONNX export + parity.

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

Windows에서 학습/실험 산출물(원본 이미지, 라벨, 로그, 실험체크포인트)은 보존하고,
Jetson에는 runtime 실행에 필요한 최소 산출물만 배포한다.

TensorRT:
- V0에서는 proxy ONNX를 대상으로 `ONNX -> TensorRT` 빌드/추론 절차를 rehearsal.
- 엔진 모델용 TensorRT 엔진은 V1/실제 데이터에서 재생성한다.
