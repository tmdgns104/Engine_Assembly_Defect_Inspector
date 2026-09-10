# Architectural Decisions

## 1) V0 계획 재정의 (PLAN-REVISION-001)

- 결정: V0를 `Proxy Inspection System`으로 재정의한다.
- 이유: V0의 역할을 Fake mock 단계에 머무르지 않게 하고, V1 전환 비용이 낮은 런타임을 미리 완성하기 위함.

## 2) V0-A, V0-B, V0-C 단계 분리

- 결정: COCO8 기반 smoke, proxy dataset 기반 workflow 학습, Jetson end-to-end 통합을 구분한다.
- 이유: 실제 엔진 데이터셋이 없어도 파이프라인 구조를 먼저 검증할 수 있고, V1 교체 지점을 명확히 한다.

## 3) 인터페이스 우선 설계 고정

- 결정: Detector/Camera 계약을 ONNX/Framework 구현보다 먼저 정의한다.
- 이유: V1/V2에서 구현체 교체 시 런타임 재설계 위험 감소.

## 4) Proxy 기준치는 공식 임계치로 사용하지 않음

- 결정: V0에서 실험한 품질 임계치/정책은 `demo/proxy threshold`로 분류한다.
- 이유: 실제 엔진 조도/거리/고정도/포즈가 정해지기 전 임계치를 engine 기준으로 오인 사용하지 않기 위함.

## 5) V1/V2 분기 보장

- 결정: V1은 데이터/클래스/모델/레시피 교체 중심으로 진행하고, V2는 MockPLC→RealPLC로만 확장한다.
- 이유: 소프트웨어 아키텍처 재작성 없이 단계적 확장 가능.
