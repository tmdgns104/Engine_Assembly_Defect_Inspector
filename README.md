# 엔진 조립 검사 프로젝트

**코드를 수정할 때는 `jetson/` 또는 `notebook/`에서 시작하세요.** 날짜나 `candidate` 이름으로 최신 버전을 고르지 않습니다.

VS Code에서는 [`Engine_Assembly.code-workspace`](Engine_Assembly.code-workspace)를 열면 Jetson·Notebook·문서·기구 설계가 각각 표시됩니다. 대용량 자료와 과거 후보를 소스 탐색창에 섞지 않습니다.

| 폴더 | 실행 장치 / 역할 | 처음 읽을 파일 |
|---|---|---|
| [`jetson/`](jetson/README.md) | Jetson Orin Nano: 카메라, AI 검사, 제품 추적, 결과 저장, 운영 화면, MOCK 요청 처리 | [`launch_live.py`](jetson/launch_live.py) → [`bootstrap.py`](jetson/src/runtime/bootstrap.py) |
| [`notebook/`](notebook/README.md) | Windows 노트북: 개발, 학습용 촬영·데이터 준비·학습, Jetson 배포 묶음 제작 | [`start_capture.cmd`](notebook/start_capture.cmd), [`deployment/`](notebook/deployment/README.md) |
| `hardware/` | 카메라 설치물·치수·기구 설계 | 해당 설치물 안내 |
| `docs/`, `tasks/` | 계약·과거 결정·작업 기록. 예전 문서의 경로는 당시 기준 | 현재 소스 설명은 위 두 README 우선 |
| `runs/`, `archives/`, `data/`, `dist/` | 노트북에만 보관하는 실험, 백업, 원본, 배포 산출물 | 실행 소스 선택에 사용하지 않음; Git 제외 |

```mermaid
flowchart LR
  N[노트북: 촬영·개발·학습] --> P[notebook/deployment: 필요한 파일만 패키징]
  P --> J[Jetson: launch_live.py]
  J --> R[Runtime: 제품·요청·검사 순서]
  R --> W[Worker 하나: 카메라·AI]
  W --> S[검사 Service: 저장·결과]
  S --> M[MOCK Result → Done]
  B[노트북 브라우저] --> H[Jetson 운영 화면 /auto]
  H --> R
```

노트북 브라우저는 Jetson의 화면을 보여 줍니다. 실제 검사 카메라·모델·Journal은 Jetson이 소유하며, 정상 검사에 노트북 파일 공유가 필요하지 않습니다. Windows 촬영 프로그램은 노트북에 연결한 카메라로 학습 자료를 수집하는 별도 도구입니다.

## 현재 버전과 검증 상태

2026-09-28 정리 기준입니다. `jetson/apps`, `jetson/src`, `jetson/config`의 94개 파일은 실제 설치본 `area_clearance_v004_exit_native_support_dev_black_ref003`과 바이트가 같습니다. 경로를 인자로 받는 시작·관리 파일은 기존 실행기를 정리한 것입니다. 출처와 복사 해시는 [`source_baseline.json`](notebook/deployment/source_baseline.json), 배포 포함 목록은 [`runtime_allowlist.json`](notebook/deployment/runtime_allowlist.json)에 있습니다.

- **개발 소스:** `jetson/`, `notebook/`. 앞으로 이 위치를 수정합니다.
- **현재 Jetson 실행 경로:** 아직 `candidates/engine_dynamic_pose_002/fixes/ENGINE-PRODUCT-TRACK-ROBUSTNESS-002/runtime_candidate`입니다. `current` 전환 완료를 뜻하지 않습니다.
- **현재 설치본 식별:** candidate manifest `624ac23530aae2e0969c221d466ca2c08bd3db836789902a9b4091ce0f76fc6f`; 점유 설정 `dd60948fdd5fd4c01f719e8dc7a891c35f5a5c0074a633f7054971014704e224`.
- **검증 한계:** v004 원본 재생은 통과했으나, 검정 매트 실물 회차에서 작은 손잡이 보존 후 완전 제거 시 자동 종료가 실패했습니다. ref003의 새 실물 연속 경로는 NOT_RUN입니다. 고정 빈 배경 의존 방식의 채택은 보류했으며 AUTO는 정지 상태입니다.
- **출력:** MOCK / `physical_output_enabled=false`. PASS는 Result=0, FAIL·REVIEW·ERROR는 Result=1. 실제 PLC·생산 정확도 승인이 아닙니다.

소스 정리·패키징 통과와 검사 기능의 실물 수용은 별개입니다. Pose REVIEW, 대용량 진단 기록 중 관측 지연의 기존 한계도 해결된 것으로 표시하지 않습니다.

## 실행과 다른 장치 배포

- Windows 촬영: [`notebook/README.md`](notebook/README.md).
- Jetson 모듈을 위에서 아래로 읽기: [`jetson/README.md`](jetson/README.md).
- 파일 묶음 제작·장치별 설정·기동·복귀: [`notebook/deployment/README.md`](notebook/deployment/README.md).
- 기존 테스트 화면: SSH 터널을 연결한 노트북에서 `http://127.0.0.1:18771/auto`.

Git에는 소스·설정 형식·배포 목록을 보관합니다. TensorRT 모델, Pose bank, 승인 기준 이미지, 촬영 원본, 운영 DB는 별도 파일입니다. **Git clone만으로 모델·승인·장치 환경이 준비되지는 않습니다.** 필요한 운영 자산은 해시가 확인된 로컬 배포 묶음으로 전달하며, 장치마다 카메라와 실행환경을 확인합니다.

기존 루트 `apps/`, `src/`, `training/`, `scripts/`와 `docs/code_reading/`은 이전 경로/설명용 사본입니다. 로컬 원본은 보존하며 새 개발 시작점으로 사용하지 않습니다. 과거 검증 기록의 경로와 해시는 당시 그대로 유지합니다.
