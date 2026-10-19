# On-Device AI 엔진 조립 검사

## 다른 장치 설치와 학습 코드 — 2026-10-19

다른 Orin Nano에는 **`jetson/` 폴더 전체**를 복사하고 [통합 설치 안내](jetson/INSTALL_OPERATING_KO.md)를 따릅니다. 검증된 운영본32c4 코드·모델7개·SQLite 보관본이 포함되며 OS/GPU 환경·카메라·PLC는 해당 장치에서 설정합니다. 신규 장치 설치 검증과 실제 장치 운전 검증은 구분합니다. 현재 운영 Jetson에는 변경을 적용하지 않았습니다.

노트북의 수집·라벨링·데이터셋 구성·실제 엔진 학습 소스는 [학습 과정 안내](notebook/training/README_KO.md)에 연결했습니다. 소스 게시이며 재학습이나 전체 원본 데이터 공개가 아닙니다.

## 최신 작업 — 2026-10-18

운영 설정을 [`jetson/src/config.py`](jetson/src/config.py)에서 한국어 설명과 함께 관리하고, 기존 값을 유지하도록 소비 코드를 연결했습니다. 기존 현장 화면 `/line`을 정리하고 SQLite 검색·상세·CSV 내보내기 화면 `/history`를 추가했습니다. [설정·기록 조회 안내](docs/CONFIGURATION_AND_HISTORY_KO.md)를 참고하세요.

최신 운영본은 `engine-integrated-32c484ac6aeb07f1`입니다. 설정·기록 기능 적용 후 실제 혼합 **7회(PASS4/FAIL3, ERROR0)**에서 저장과 PLC 완료를 확인했고 사용자가 시험을 종료했습니다. 이후 UI 두 파일만 반영하고 실제 재부팅·카메라·모델·PLC 준비를 확인했습니다. **10회 완료나 장시간 무오류 보증은 아닙니다.** 부품 위치 사진과 미결합 여부를 크게, 오조립을 작은 참고 정보로 표시합니다. [검증 결과와 한계](docs/verification/CONFIG-UI-HISTORY-20261018.json), [이전 안정화 기록](docs/STABILIZATION_CLOSEOUT_20261018.md)을 보존합니다. 통합 응답시간 약10~14초와 간헐적인 USB 복구 필요성은 남아 있습니다.

사용 중 검출 모델 두 개와 참고 오조립 모델·동결 자산을 [assets 안내](assets/README.md)에 정리했습니다. 실제 SQLite의 일관된 보관본은 [database 안내](database/README.md)를 따릅니다. 실행 중인 DB를 Git 작업용 파일로 쓰지 않으며, 보관본으로 장치 원장을 덮어쓰지 않습니다. 원본 검사 사진은 이 Git 배포에 포함하지 않습니다.

## 과거 통합 운영 기록 — 2026-10-14

개발 원본은 [jetson/](jetson/README.md) 한 벌입니다. 실제 실행은 `current/`의 `engine-integrated-90a914423826735a`를 `engine-inspector.service` 하나가 감독하며 Python과 OpENer를 같은 Release로 관리합니다. 노트북에는 이전 후보·복구 자료를 보존합니다.

[프로그램 실행 흐름](jetson/INTEGRATED_RUNTIME.md)과 [이번 검증 결과](notebook/deployment/JOURNAL_COMPATIBILITY_VERIFICATION.md)를 먼저 읽으세요. 과거 Journal35 차단은 해결됐고 실제 한 제품의 요청→검사 처리→PLC NG·Done→컨베이어 재가동을 확인했습니다. **AI 최종 결과는 조립 모듈 오류로 ERROR였고, 정상 판별·연속 운전·재부팅·노트북 OFF 검증은 완료되지 않았습니다.** 아래 9월 및 이전 배포 설명은 당시 범위이며 현재 채택 상태는 이 문단과 최신 통합 문서를 따릅니다.

<!-- standalone-install-20261007 -->
2026-10-07 현재 장치: `engine-dev-780822e39a6316f3` 전체 통합본과 `engine-inspector.service`를 설치해 실행 중입니다. 카메라·모델 준비와 150파일 해시를 확인했습니다. **PLC V3 미적용 및 현장 profile 미검증으로 자동공정은 아직 동작하지 않습니다.** 기존 cron과 별도 launcher를 중복 시작하지 마세요. 실제 재부팅·반복 사이클·노트북 OFF는 NOT_RUN입니다. [현재 근거와 다음 단계](runs/engine_standalone_plc_autostart_001/v001_20261007T052746Z/CHECKPOINT.md).


**Jetson Orin Nano가 USB 카메라 영상에서 엔진의 조립 상태를 검사하고, 노트북은 촬영·개발·운영 화면 접속을 맡는 프로젝트입니다.** 검사 결과는 `PASS / FAIL / REVIEW / ERROR`로 저장하며, 제품 추적과 PLC 요청을 연결합니다.

**현재 검출 모델2개와 참고 분류 관련 모델5개, 기준 자산을 포함합니다.** `git clone`과 GitHub의 **Code → Download ZIP** 모두 실제 파일을 받습니다. 현재 운영 모델은 Git LFS나 별도 다운로드가 필요하지 않습니다.

## 다운로드와 시작

```bash
git clone https://github.com/tmdgns104/Engine_Assembly_Defect_Inspector.git
cd Engine_Assembly_Defect_Inspector
```

ZIP을 사용하면 먼저 전체 압축을 풉니다. 두 장비에 같은 저장소를 받아도 됩니다. 아래 설치 작업은 각 장비에서 수행합니다.

| 장비 | 들어 있는 파일 | 처음 할 일 |
|---|---|---|
| Windows 10/11 x64 노트북 | [`notebook/`](notebook/README.md): 촬영 앱, 데이터 준비·학습 도구, SSH 화면 연결, 패키징·시험 | Python 3.13 x64 설치 → `notebook/setup_capture.cmd` → `notebook/start_misassembly.cmd` |
| Jetson **Orin Nano** | [`jetson/`](jetson/INSTALL_OPERATING_KO.md): 통합 운영 코드·UI·모델7개·SQLite 보관본 | 지원 환경 준비 → `python3.10 jetson/install_operating.py --verify` → 문서의 신규 장치 설정·서비스 등록 |

Jetson 설치는 `~/oned_device_bench/current`에 실행 코드를, `assets`에 모델을 배치합니다. 장치별 설정과 새 원장은 별도 보존합니다. 설치 안내대로 systemd를 시작하고 현장 화면 `http://127.0.0.1:18771/line`을 엽니다. 노트북에서는 SSH 터널을 사용합니다. 이전 CORE MOCK의 `setup.sh/manage_live.py`와 통합 서비스를 중복 실행하지 않습니다.

지원 기준은 **Orin Nano / Linux aarch64 / Python 3.10 / TensorRT 10.3 / CUDA 12.6**입니다. 기존 Jetson Nano(Orin이 아닌 구형 모델)는 이 TensorRT 모델의 실행 대상이 아닙니다. [NVIDIA는 직렬화된 TensorRT 엔진의 플랫폼·GPU·버전 호환에 제약이 있음을 명시합니다.](https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/engine-compatibility.html) 모델은 포함되어 있지만 OS·드라이버·Python과 연결한 카메라의 설정은 장치에서 준비해야 합니다.

## 시스템 구성

```mermaid
flowchart LR
    N[Windows 노트북<br/>촬영 · 데이터 준비 · 학습] --> P[검증한 제품 모델 · Recipe]
    P --> J[Jetson Orin Nano]
    C[USB 카메라] --> J
    J --> E[엔진 검출 → Pose 정렬<br/>부품 검출 → 3프레임 판정]
    E --> D[SQLite Journal · Evidence]
    D --> G[MOCK 또는 명시적 PLC 벤치<br/>Result 확인 → Done 확인]
    B[노트북 브라우저] -->|SSH 터널| H[Jetson /auto 운영 화면]
    H --> J
```

검사 카메라·AI·Journal은 Jetson에서 실행됩니다. 노트북이 꺼져도 Jetson에서 이미 시작한 서버는 독립적으로 실행됩니다. 노트북의 촬영 앱은 학습 자료를 수집하는 별도 프로그램입니다.

## 포함 모델

| 모델 | 역할 | 파일 크기 | SHA-256 앞 12자리 |
|---|---|---:|---|
| [`dynamic_parts_005/model.plan`](jetson/products/ENGINE_Z3005_5/dynamic_parts_005/model.plan) | 부품 검출과 조립 판정 입력 | 10,092,164 bytes | `743ce54b4d5c` |
| [`envelope_v007_fp16/model.plan`](jetson/products/ENGINE_Z3005_5/envelope_v007_fp16/model.plan) | 엔진 전체 위치 검출 | 13,556,092 bytes | `c82f2658ac20` |

두 모델의 manifest·Recipe·전처리·기동 점검 이미지, D001 Pose 기준 이미지와 Pose bank도 함께 있습니다. 기존 운영 자산의 바이트/해시를 유지했습니다. 설치 전 아래 명령은 GPU·카메라·PLC 없이 파일과 해시를 검사합니다.

```bash
python jetson/install.py --check-only
```

학습 원본 전체, 운영 DB, 개인 SSH 설정, 보호된 E04 자료는 배포하지 않습니다. 모델 및 외부 의존성의 출처·사용 범위는 [모델 안내](jetson/products/README.md)를 확인하세요.

## 현재 진척 — 2026-09-30

| 항목 | 확인된 결과 | 남은 검증 / 제한 |
|---|---|---|
| Jetson 검사·웹 HMI | TensorRT 검사, 단일 카메라 Worker, SQLite/Evidence, 제품별 Track, `/auto` 구현 | 새 장치에서 카메라·GPU·작업면 확인 필요 |
| 정지 제품 PLC 벤치 | 9월 28일 PASS → FAIL → PASS 세 제품을 별도 요청·저장·종료 | 생산 정확도와 실제 배출 동작을 의미하지 않음 |
| 이동 검사 | MOCK에서 고유 3프레임 검사·ACK·제품 이탈 후 다음 제품 대기 확인 | 실제 컨베이어 속도·연속 제품 미검증 |
| 실제 PLC 이동 벤치 | 9월 29일 REVIEW 저장 후 Result=1 / Done=1·요청 해제 확인 | 빈 작업면 오점유로 자동 종료가 막힌 사례, Sysmac 표시와 CIP 읽기 불일치 미해결 |
| Windows 촬영 | 기존 Wizard와 간편 촬영 소스 포함. 10° 간격 총 654장 계획. 최종 EXE GUI 7항목·HCAM 40프레임 미리보기 확인 | 실물 엔진 원본 저장·타 PC 조작·후속 학습은 미검증 |
| GitHub 배포 | 모델 포함, 장비별 설치·파일 점검 도구, 공개 스냅샷 검증 절차 | 모든 PC/Jetson에서 실물 실행을 완료했다는 의미는 아님 |

기존 Jetson의 마지막 기록된 실행 릴리스는 `engine-dev-745e95e832c6b402`입니다. 이 저장소의 설치용 패키지 ID는 포함된 파일 해시로 새로 계산되며 기존 장치에 자동 적용되지 않습니다. 새 설치는 **MOCK**, 물리 출력 비활성입니다. PASS의 PLC Result는 0, FAIL·REVIEW·ERROR는 1이며 저장 완료 전에 결과를 보내지 않습니다.

세부 근거: [이동 검사 Task](tasks/ENGINE-CONVEYOR-MOTION-001.md), [촬영 Task](tasks/ENGINE-MISASSEMBLY-CAPTURE-001.md), [GitHub 배포 Task](tasks/GITHUB-DEPLOYMENT-001.md), [누적 STATUS](docs/STATUS.md). 과거 완료 기록과 미해결 한계를 구분합니다.

## 개발·발표 자료

- [Jetson 코드 읽는 순서](jetson/README.md) · [새 Jetson 설치](jetson/INSTALL.md) · [Windows 사용법](notebook/README.md)
- [노트북에서 패키징 및 기존 장치 업데이트](notebook/deployment/README.md)
- [프로젝트 범위](docs/PROJECT.md) · [아키텍처](docs/ARCHITECTURE.md) · [결정 기록](docs/DECISIONS.md)
- `hardware/`는 설치물 설계, `docs/`·`tasks/`는 계약과 검증 기록입니다. 이전 경로를 적은 과거 문서는 당시 증거로 보존합니다.

소스 수정은 `jetson/`와 `notebook/`에서 시작합니다. `runs/`, `archives/`, `dist/`와 옛 루트 소스 사본은 개발·복구용 로컬 자료이며 새 실행 원본이 아닙니다.
