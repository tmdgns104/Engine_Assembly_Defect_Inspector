# On-Device AI 기반 엔진 모형 조립 검사 시스템

이 저장소는 `V0 → V1 → V2` 로드맵으로 구성됩니다.  
`PLAN-REVISION-001` 기준의 **V0 Proxy Inspection System**을 단계적으로 구현하며, 현재 GPU smoke와 공통 Runtime 계약을 검증했습니다.

## 현재 실행 상태

- Phase: `V0 Proxy Inspection System`
- Completed planning task: `PLAN-REVISION-001` (DONE / VERIFIED)
- Current implementation task: `NONE`
- Completed implementation tasks: `V0-T01`, `V0-T02`, `V0-T03` (DONE / VERIFIED)
- Next implementation task: `V0-T04` (TODO, 미시작)

공통 계약은 [docs/contracts.md](docs/contracts.md), 최신 실행 상태는 [docs/STATUS.md](docs/STATUS.md)를 참조합니다. 실제 Camera/Detector Adapter와 Runtime 실행 앱은 아직 구현하지 않았습니다.

## 계약 코드와 테스트

- `src/contracts/enums.py`: 결과 상태·실행 모드·공통 reason code
- `src/contracts/models.py`: 데이터·불변 조건·JSON 변환
- `src/contracts/interfaces.py`: Camera/Detector 인터페이스
- `tests/test_contracts.py`: 장비 없이 실행하는 계약 테스트

위 순서로 코드를 읽으면 데이터 흐름을 따라갈 수 있습니다. 저장소 루트에서 기존 가상환경으로 실행합니다.

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

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
