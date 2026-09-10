# Requirements

## 범위

본 저장소의 V0는 다음만 다룬다.

- V0-T01(부트스트랩): 문서, 디렉터리, Task 분해, 환경 확인, 구조 기초 수립
- V0-T02 및 이후 학습/실행 코드는 별도 실행 단계에서 진행

## 기능 요구사항

- Object Detection 기반 파이프라인을 V0에서 경험할 수 있어야 함
- V1 교체 기준을 반영한 구조 설계를 해야 함
  - Dataset / Classes / Model / Recipe / Evaluation Dataset는 교체 지점
  - Detector/Camera/Quality/Decision/Journal 등은 인터페이스 중심으로 구성
- 결과 상태는 `PASS`, `FAIL`, `REVIEW`, `ERROR` 만 사용
- EMERGENCY STOP은 AI 판정 상태에 포함하지 않음
- 대규모 binary(Model/데이터) commit 금지

## V0 타겟 모듈

- Camera Adapter (Replay/Sample/V4L2)
- Image Quality Gate
- Detector Interface (Fake, PyTorch, ONNX, TensorRT 대상)
- Recipe Engine
- Decision Engine
- Journal 저장
- Web HMI + REST API
- Mock PLC
- ONNX Inference 예비 구성
- Jetson 배포 스크립트 기초
