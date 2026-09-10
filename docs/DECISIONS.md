# Architectural Decisions

## 1) V0에서 V0-T01만 완료

- 결정: 이번 실행은 `V0-T01` 부트스트랩에만 한정
- 이유: 데이터/학습 파이프라인 구현 전에 프로젝트 기반을 안정화하고 Task를 선형으로 분해하기 위함

## 2) Training과 Runtime 분리

- 결정: 학습 산출물(데이터셋/실험/체크포인트)과 Runtime(감지/판정/API/UI)을 디렉터리 레벨에서 분리
- 이유: V1/V2 전환 시 교체 지점 최소화 및 Jetson 배포 범위 축소

## 3) Interface First 설계

- 결정: Detector와 Camera를 인터페이스로 먼저 고정하고 Fake/PyTorch/ONNX/TensorRT 등을 플러그인으로 추가
- 이유: V1에서 실제 모델로 즉시 전환 가능한 구조 확보

## 4) Demo Dataset는 조사만 수행

- 결정: V0-T01에서 대규모 Dataset 다운로드는 수행하지 않음
- 이유: 과도한 네트워크/시간 소비 방지 및 Task 정합성(부트스트랩 범위)
