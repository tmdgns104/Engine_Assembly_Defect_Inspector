# On-Device AI 기반 엔진 모형 조립 검사 시스템

이 저장소는 `V0 → V1 → V2` 로드맵으로 구성됩니다.  
현재는 `PLAN-REVISION-001` 기준의 **V0 Proxy Inspection System** 계획을 정비한 상태입니다.

## 현재 실행 상태

- Phase: `V0 Proxy Inspection System`
- Completed planning task: `PLAN-REVISION-001` (DONE / VERIFIED)
- Current implementation task: `NONE`
- Next implementation task: `V0-T02` (수행 대기)

## V0 목표 (재정의)

V0는 단순 가짜 모델 데모가 아니라 다음 3단계로 구성됩니다.

1. ML 환경 smoke test (`V0-A`)  
2. Proxy dataset로 ML/inspection workflow 연습 (`V0-B`)  
3. Camera + 품질 게이트 + Detector + Recipe + Decision + Journal + API + HMI를 실제 벤치에서 연동 (`V0-C`)

V1은 런타임 재설계 없이 교체 지점만 바꾸어 진행합니다.

- Dataset / Classes / Model / Recipe / Evaluation Set

## 제약

- V0 단계에서 엔진 부품명/좌표/임계치 같은 실제 엔진 스펙은 확정하지 않습니다.
- V0에서 만들어지는 임계치/지표는 proxy 목적 전용입니다.
- `PASS / FAIL / REVIEW / ERROR` 4-state를 유지합니다. `EMERGENCY STOP`은 AI 판정에 포함하지 않습니다.
