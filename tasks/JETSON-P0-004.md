# JETSON-P0-004 — TensorRT Backend

Status: **DRAFT / NOT_STARTED**. 앞 Task: P0-003. 다음: P0-005.

## 문제와 목표

TensorRT10.3은 설치되어 있지만 Detector 구현과 package validator/Worker는 PyTorch에 고정되어 있다. 공통 DetectionResult 계약을 유지하면서 새 backend 선택 경계와 TensorRT adapter를 검증한다. 설치·import 상태와 실제 engine 실행 결과를 구분한다.

## 착수 전 결정과 예정 범위

- 변환 대상 모델, ONNX/opset·precision·shape·batch, TRT/CUDA 호환성, workspace/memory, 출력 decoding/NMS와 허용 오차를 먼저 고정한다. 새 dependency/변환·장치 실행 범위는 그 Task에서 확인한다.
- 현재 earbud package와 best.pt는 불변 대조군이다. 별도 새 candidate package/engine 경로를 만들고 명시 manifest/hash/build provenance를 남긴다. app_v007을 덮어쓰지 않는다.
- Detector Protocol을 재사용하고 backend factory/package 검증 확장, 동일 전처리·원본 pixel boxes·클래스 순서·frame ID·오류 의미를 유지한다. CPU fallback이나 빈 검출로 실패를 숨기지 않는다.
- calibration/precision 자료는 허용된 train/validation만 사용하며 봉인 Test·정답을 열람하지 않는다. 이번 초안은 INT8/학습/전체 Dataset 평가 권한이 아니다.

## 수용 초안

PyTorch와 같은 대표 입력의 preprocess tensor·raw/output decode·NMS·최종 판정 parity를 고정 오차로 검증한다. 잘못된 shape/class/engine hash/환경을 거부하고 engine 로드·실제 GPU 추론의 성공을 따로 기록한다. P0-003 계측으로 동일 입력·배치·warm-up·동기화·반복·startup을 맞춰 지연과 메모리를 비교한다. 기존 Runtime 회귀·late-result/취소·증거 연결과 baseline 파일 hash를 보존한다.

산출물 예정: 새 TensorRT adapter/후보 package, build manifest와 parity/성능 evidence, `docs/verification/JETSON-P0-004.json`. P0-001에서는 engine 변환·추론·설치0이며 이 초안으로 자동 시작하지 않는다.
