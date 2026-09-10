# Project: On-Device AI 기반 엔진 모형 조립 검사 시스템

## Vision

현재 V0에서는 실제 하드웨어 없이도 전체 ML Workflow를 재현할 수 있는 기반을 만든다.  
V1에서는 실제 엔진 데이터셋/레이블/모델/레시피로 교체하고, V2에서는 PLC/컨베이어/센서/모터 드라이버로 확장한다.

## Phase

- V0: Learning / Bench Foundation
- V1: Engine Vision Inspection
- V2: PLC / Conveyor Integration

## 핵심 원칙

- 학습용(Training) 코드와 실제 검사(Runtime) 코드 분리
- V1 교체 포인트 최소화
  - Dataset
  - Classes/Labels
  - Trained Model
  - Recipe
  - Evaluation Dataset
- Detector/Camera는 인터페이스 기반으로 구성해 교체 가능하게 함
- 판단은 `PASS / FAIL / REVIEW / ERROR` 4상태로 통일

## V0 결과

V0-T01은 프로젝트 부트스트랩과 Task 설계 완료가 목표이며, 본 실행에서 V0-T02는 시작하지 않는다.
