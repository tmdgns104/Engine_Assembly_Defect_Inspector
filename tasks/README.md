# V0 Task Map (PLAN-REVISION-001)

| Task ID | Task Name | Phase | Status | Allowed Next |
|---|---|---|---|---|
| V0-T01 | Bootstrap / Repo Foundation | V0 | DONE | V0-T02 |
| V0-T02 | ML Environment + Tiny GPU Smoke Test | V0 | DONE / VERIFIED | V0-T03 |
| V0-T03 | Core Contracts / Camera + Detector Interfaces | V0 | DONE / VERIFIED | V0-T04 |
| V0-T04 | Proxy Inspection Dataset Plan + Capture Tool | V0 | DONE / VERIFIED | HUMAN-CAPTURE-001; collect/review formal images before T05 |
| HUMAN-CAPTURE-001-PREP | 검사 기준 설정 / 이어폰 첫 촬영 준비 | V0 | DONE / VERIFIED | HUMAN-CAPTURE-001: 현재 장치 확인 → 첫 정상 사진 |
| WINDOWS-CAPTURE-001 | Windows 공통 USB 카메라 촬영 화면 | V0 수집 도구 | DONE / VERIFIED (소프트웨어) | HUMAN-CAPTURE-001: Windows 첫 정상 사진·실기기 확인 |
| V0-T05 | Labeling + Dataset Validation | V0 | TODO | V0-T06 |
| V0-T06 | Grouped Train / Val / Test Split | V0 | TODO | V0-T07 |
| V0-T07 | Baseline Training | V0 | TODO | V0-T08 |
| V0-T08 | Small Tuning Experiments | V0 | TODO | V0-T09 |
| V0-T09 | Evaluation + Error Analysis | V0 | TODO | V0-T10 |
| V0-T10 | ONNX Export + Parity Check | V0 | TODO | V0-T11 |
| V0-T11 | Runtime Detector Integration | V0 | TODO | V0-T12 |
| V0-T12 | Image Quality + Recipe + Decision | V0 | TODO | V0-T13 |
| V0-T13 | Journal / Evidence Persistence | V0 | TODO | V0-T14 |
| V0-T14 | REST API + Web HMI | V0 | TODO | V0-T15 |
| V0-T15 | Manual Request + Mock PLC Adapter | V0 | TODO | V0-T16 |
| V0-T16 | Jetson Camera End-to-End | V0 | TODO | V0-T17 |
| V0-T17 | Failure / Recovery Tests | V0 | TODO | V0-T18 |
| V0-T18 | Jetson Packaging / Startup | V0 | TODO | V0-T19 |
| V0-T19 | Benchmark | V0 | TODO | V0-T20 |
| V0-T20 | V0 Final Review / V1 Readiness | V0 | TODO | V1-Ready |

Notes:
- PLAN-REVISION-001 applies to all tasks.
- Task filenames are aligned to purpose by this audit.
- V0-T02 GPU smoke, V0-T03 core contracts and V0-T04 capture workflow verified. T04 hardware evidence is USER-EXECUTED / VERIFIED.
- 제품 준비: [HUMAN-CAPTURE-001-PREP](human-capture-001-prep.md). 현재 촬영 도구: [WINDOWS-CAPTURE-001](windows-capture-001.md). 다음은 Windows 노트북 + USB 카메라에서 첫 정상 사진 촬영·검토다. 수집 수량·완료 근거는 [STATUS](../docs/STATUS.md) 참조. V0-T05 이후는 TODO이며 자동 시작하지 않는다.
