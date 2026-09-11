# On-Device AI 기반 엔진 모형 조립 검사 시스템

이 저장소는 `V0 → V1 → V2` 로드맵으로 구성됩니다.  
`PLAN-REVISION-001` 기준의 **V0 Proxy Inspection System**을 단계적으로 구현하며, 현재 GPU smoke와 공통 Runtime 계약을 검증했습니다.

## 현재 실행 상태

- Phase: `V0 Proxy Inspection System`
- Completed planning task: `PLAN-REVISION-001` (DONE / VERIFIED)
- Latest implementation task: `V0-T04` — DONE / VERIFIED
- Completed implementation tasks: `V0-T01`, `V0-T02`, `V0-T03`, `V0-T04` (DONE / VERIFIED)
- Next action: `HUMAN-CAPTURE-001` — OBJ_A/B/C 선택·배치 후 S001의 NORMAL/MISSING_A를 단계별 촬영·검토. T05는 TODO / NOT STARTED.

공통 계약은 [docs/contracts.md](docs/contracts.md), 최신 실행 상태는 [docs/STATUS.md](docs/STATUS.md)를 참조합니다. 실제 Camera/Detector Adapter와 Runtime 실행 앱은 아직 구현하지 않았습니다.

Dataset 수집용 CLI와 Session/Episode/Pilot 계획은 [Proxy Capture Workflow](training/datasets/proxy/README.md)에 있습니다. Windows 테스트 40개와 사용자가 실행한 Jetson HCAM0 실기기 smoke 3장을 검증했습니다. [검증 기록](docs/verification/V0-T04.txt)에 출처를 구분했습니다. 정식 Pilot은 **0/81장, NOT STARTED**이며 CAMERA_SMOKE 3장은 포함하지 않습니다.

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
