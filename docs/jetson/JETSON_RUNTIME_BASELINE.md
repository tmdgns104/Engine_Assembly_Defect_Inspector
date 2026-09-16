# JETSON-P0-001 — Jetson Runtime Baseline

감사일: 2026-09-16 (KST). 상태: **AUDIT_COMPLETE_WITH_FINDINGS / 기존 실행 가능성 수용 미충족**.
이 문서는 현재 관측을 고정한다. app_v007 재배포·복구·환경 설치 또는 다음 기능 구현을 승인하지 않는다.

## 기준과 범위

- Windows 저장소: `D:\OneDevice_Team_project`, HEAD `f6403fca07cbb92ad89d59a1c3161ef0bb31a71b`. 시작부터 사용자 미커밋 변경이 있었다.
- 우선 근거: 이번 Task 지시 → [STATUS](../STATUS.md) 최신 기록 → [현재 검사 Task](../../tasks/inspection-app-v1.md) → [실행 안내](../../apps/edge_service/INSPECTION_APP.md) → 실제 코드/대상 파일/DB. PROJECT·REQUIREMENTS·ARCHITECTURE·DECISIONS의 오래된 TODO와 계획은 현재 구현 증명이 아니다.
- 현재 원본: `/home/jetson/oned_device_bench/releases/app_v007`. Windows와 공통으로 존재하는 **49파일의 바이트 SHA256 일치**. 원격 전체 50파일(캐시 제외)의 전후 해시를 고정했다.
- 기존 `release_files.json`의 `release_id=app_v005`와 4개 오래된 해시는 실제 app_v007과 불일치한다. 누락/변경 목록은 검증 JSON에 보존했다. 이 파일을 최신 릴리스 증명으로 사용하지 않는다. 원본은 수정하지 않았다.
- 수집 경로: 기존 SSH 키·host 검증 유지, GET 상태 조회, 메타데이터/파일 해시, 읽기 전용 SQLite, 장치 모드 열거. 카메라 스트리밍·새 촬영·모델 추론·서비스 시작/중지·패키지 활성화·실 PLC 접근 없음.
- 기계 판독 근거: [JETSON-P0-001.json](../verification/JETSON-P0-001.json). 상세 진단: `runs/jetson_p0_001/{before_failed_remote_parse,before,supplement,after}.json`, `focused_tests.log`.

## 현재 Jetson 환경

| 항목 | 2026-09-16 실제 관측 | 해석/한계 |
|---|---|---|
| 장치 | NVIDIA Jetson Orin Nano Engineering Reference Developer Kit Super | `/proc/device-tree/model` |
| L4T | `/etc/nv_tegra_release`: R36, REVISION 4.7, GCID 42132812, BOARD generic, EABI aarch64, DATE Thu Sep 18 22:54:44 UTC 2025; kernel variant oot | `nvidia-l4t-core=36.4.7-20250918154033`; `nvidia-jetpack` 메타패키지는 조회되지 않음. JetPack 세부 버전을 추정 확정하지 않음 |
| uname -a | `Linux jetson-07 5.15.148-tegra #1 SMP PREEMPT Thu Sep 18 15:08:33 PDT 2025 aarch64 aarch64 aarch64 GNU/Linux` | Ubuntu 22.04.5 LTS |
| Python | 3.10.12, GCC 11.4.0 | 기본 `/usr/bin/python3`와 앱 `/home/jetson/oned_device_bench/envs/app_v1/bin/python` 모두 직접 확인 |
| torch / CUDA | torch 2.8.0, `torch.version.cuda=12.6`, `cuda.is_available()=true` | 사용자 site-packages torch를 앱 venv도 참조. CUDA 연산·모델 추론은 이번에 실행하지 않음 |
| GPU | Orin, compute capability 8.7, SM 8, torch 보고 메모리 7619 MB | 공유 메모리 구조; 전용 VRAM으로 별도 합산하지 않음 |
| TensorRT | Python 10.3.0, dpkg `libnvinfer10`/`python3-libnvinfer`/`tensorrt` 10.3.0.30-1+cuda12.5 | 설치/import 확인만. Runtime backend는 PyTorch; engine build/load/inference 없음 |
| OpenCV | 실제 import 5.0.0, distribution `opencv-python=5.0.0.93` | `/home/jetson/.local/lib/python3.10/site-packages/cv2`; 과거 OpenCV4.8.0 기록과 달라짐 |
| NumPy / Ultralytics | NumPy 2.2.6 / Ultralytics 8.4.118, torchvision 0.23.0 | torch import의 NumPy ABI 경고, 합성 배열 `torch.from_numpy()` 실제 실패 |
| Web 의존성 | FastAPI 0.115.12 / uvicorn 0.34.3 | 앱 venv의 distribution metadata 확인 |
| GStreamer | CLI 및 GI 1.20.3, v4l2src/jpegdec/videoconvert/appsink 조회 성공 | OpenCV build는 GStreamer NO, FFmpeg YES, V4L2 YES. 앱은 GI GStreamer를 직접 사용하므로 OpenCV 옵션만으로 카메라 실패를 단정하지 않음 |
| RAM | 총 7,990,013,952 B, available 4,508,581,888 B | 한 시점의 `free -b`; 실행 중 최대 사용량/누수 시험 아님 |
| Swap | 총 3,995,000,832 B, used 240,386,048 B | 구성 변경 없음 |
| Disk | `/dev/mmcblk0p1`, 총 124,252,487,680 B, used 35,474,845,696 B, available 83,480,969,216 B, Use 30% | 앱 data_root가 위치한 `/` 기준. 지속 감시/쓰기 성능 측정 아님 |
| 앱 프로세스 / health | app_v007 Service/Worker 프로세스 없음; `127.0.0.1:8768` health/metrics/UI 모두 connection refused | 관측 시작/종료 모두 중지. 과거 실행 성공을 현재 health PASS로 대체하지 않음 |
| systemd | OS systemd와 일반 서비스는 동작. 앱 관련 system/user unit 및 실제 unit 파일 경로 검색 일치 없음 | 현재 시작 방식은 nohup shell script. 앱 자동 시작/Restart unit은 없음 |
| PC 수집 / 터널 | PC `127.0.0.1:8769` connection refused, Jetson `18769` listener 없음 | 저장된 과거 동기화는 완료됐지만 현재 동기화 연결은 중지 |

### 실행 가능성 판정

**“현재 app_v007이 기존과 동일하게 실행 가능”을 PASS로 선언하지 않는다.**

1. 기본 Python과 실제 앱 venv에서 현재 torch가 NumPy 2.2.6 ABI 경고를 냈다. 앱 venv의 작은 합성 배열을 `torch.from_numpy()`로 변환한 결과 `RuntimeError: Numpy is not available`였다. 카메라 BGR ndarray를 모델 입력으로 전달하는 현재 경로의 필수 호환성 점검이 FAIL이다.
2. 앱은 감사 전후 모두 중지되어 실제 health READY·모델 자체 추론·새 촬영은 UNVERIFIED다. 이번에는 원장 세션 증가와 미리보기 촬영을 일으키는 시작 스크립트를 실행하지 않았다.
3. 패키지 무결성, Python 28파일 메모리 내 compile, 시작/종료 shell `bash -n`, Windows 기존 Runtime 격리 시험 61개는 PASS다. 이들은 대상 장치 E2E 성공을 대신하지 않는다.
4. OpenCV4.8→5.0 및 NumPy 호환성 문제를 누가/언제/어떤 설치로 만들었는지는 조사·추정하지 않았다. 환경 복원·고정은 이번 범위 밖이며 설치를 변경하지 않았다.

## 카메라 기준

현재 장치 `/dev/v4l/by-id/usb-Jieli_Technology_USB_Composite_Device-video-index0` → `/dev/video0`, index1 → `/dev/video1`. USB ID `4c4a:4a55`, V4L2 표시 `USB Composite Device: HCAM0`. 연결 존재와 모드 열거만 확인했으며 카메라를 열어 프레임을 받지 않았다.

| 픽셀 형식 | 지원 해상도 | 열거된 FPS |
|---|---|---|
| MJPG | 1280×720 / 640×480 / 480×320 | 각 30 |
| YUYV | 640×480 | 22 |
| YUYV | 320×240 | 30 / 25 |

중복 열거는 표에서 합쳤고 원시 출력은 Evidence에 보존했다. 현재 제품 프로필은 **MJPG 1280×720 @30**, 입력은 **FP32 NCHW 1×3×640×640**, BGR→RGB/255, letterbox/linear/padding114, crop=false, rect=false, confidence0.25/NMS IoU0.7이다.

카메라 코드는 GI의 `v4l2src do-timestamp=false → image/jpeg → jpegdec → videoconvert → BGR → appsink(max-buffers=1, drop=true, sync=false)`를 사용한다. PTS 단조 증가와 최대 1초 age 검사, worker 단계 최대 0.35초 age, 요청 수락 후 0.15초 간격의 새 관측 3회를 요구한다. `estimated_source_monotonic`은 수신 시점과 GStreamer PTS age로 추정하며 **센서 노출 시각은 검증되지 않았다**.

설정 근거: [inspection_station.json](../../config/inspection_station.json), [GStreamerCamera](../../src/camera/gstreamer_camera.py), [worker_main](../../src/vision/inspection_worker.py). 고정 자리·사람 가시성·reference IoU0.65는 정지 대상 기준이다. Moving Conveyor에서 제품 이동/다음 제품 혼합/프레임 처리 중 age 증가는 별도 검증이 필요하다.

## 제품·모델·원장 고정

활성 선택은 DB `service_state.active_package`에서 확인했다. 현재 프로세스에 로드되었다는 뜻은 아니다.

| 대상 | 기준 |
|---|---|
| 제품 | `earbud_case_v0`, package release `app_v001`, model version `baseline_20260913_v001` |
| 경로 | `/home/jetson/oned_device_bench/releases/app_v007/deployment/products/earbud_case_v0/app_v001` |
| Manifest SHA256 | `a461349449314af8a2b0f83bc3a323eb3c9dc4226b9c05669ea89ecf1ef5030a` |
| best.pt SHA256 | `49f533e4e4e5846d1582564d8efbb38a647ad10348a976db9085d94df16250c1` |
| 클래스 | earbud_left / earbud_right / case |
| 패키지 검증 | 원래 loader의 경로·6참조 파일 hash·클래스·preprocess·recipe 검증 PASS, 패키지 전체 7파일 전후 동일 |
| Edge DB | `/home/jetson/oned_device_bench/data/app_v1/journal.sqlite3` |
| Edge DB SHA256 | `dcd31eb7a79d13ce357ab95729a2b22fba6c974a1a6b3541c1c786b7498b1cbd` |
| PC DB | `runs/inspection_app_v1/pc/journal.sqlite3` |
| PC DB SHA256 | `42f67cde08aaa4db17432058fdd3521a7199a1dfd4afe740ca486d6b49226302` |
| PC WAL SHA256 | `b6f9fe984e7b8a36d8421b5321c5b553e4d92a79caead4476fabf344626c870c` |

양측 DB `integrity_check=ok`, `foreign_key_check=[]`. Edge18건·PC18건의 ID/요청JSON/결과JSON이 일치한다. 기준 진단 REVIEW17건과 제품 검사 PASS1건이며 마지막 요청 수락 시각은 `2026-09-14T05:27:16.661508+00:00`이다.

정상 검사 `5031fbaf16a94877b5b6aa46f9e90c03`을 포함한 모든 원장 행의 감사 전후 hash가 동일하다. 양측 자산은 각 72개(raw PNG54/overlay18에 대응하는 총수; 종류별 근거는 frame_assets), 실제 파일→DB의 SHA256 144회 대조 불일치0, 자산 metadata도 동일하다. Edge outbox34개/asset72개와 PC asset72개는 모두 ACKED, 미전송0, 양측 event ID34개 일치다. 신규 전송이나 PC 재연결 시험은 하지 않았다.

기존 차이 1건: `a44a968e2a914a47a54e7ecc5a3383c4`의 관계형 `accepted_at`은 Edge `2026-09-13T15:51:01.699300+00:00`, PC `2026-09-13T15:51:03.004451+00:00`이다. 결과 JSON은 동일하다. 과거 STATUS에도 기록된 차이를 수정하지 않았으며 DB 파일 전체가 서로 같다고 주장하지 않는다.

승인 calibration1행은 남아 있지만 최신 기준 진단은 `9ac7a9c5012a4279a584228402b77fb9`다. 기존 승인 행 존재만으로 READY를 판단하면 안 된다. Service는 최신 기준 진단 ID와 승인 source ID 일치를 요구한다(`inspection.py:71`, `:78`).

## 기능별 재사용 경계

아래 “엔진 변경”은 **검사 대상 제품을 엔진으로 교체하는 경우**이며 TensorRT engine 변환과 다르다. 위치는 Windows와 배포본 hash가 일치한 코드다. 재사용 가능은 현재 물리 수용 완료를 뜻하지 않는다.

| 기능 | 현재 구현 위치 / 근거 | 재사용 여부 | 엔진 제품 변경 필요 | Moving Conveyor 변경 필요 |
|---|---|---|---|---|
| Camera | `src/contracts/interfaces.py:17`, `src/camera/gstreamer_camera.py:10`, `inspection_worker.py:100` | GI/V4L2 단일 소유, latest queue, PTS 검사 재사용 | camera/capture 프로필·광학 조건 재검증 | 요청/trigger 시각 계약, 이동 제품 식별·버퍼·age 재검증 |
| Quality | `src/quality/image.py:4`, station quality, `src/decision/slots.py:76` | 밝기/선명도·REVIEW 정책 재사용 | 엔진 조명/재질/영역 임계치 검증 | 이동 blur/노출·ROI 품질, 인식 가능한 창 검증 |
| Preprocess | `src/recipe/package.py:120`, `src/vision/pytorch_detector.py:45` | 명시적 설정/검증 재사용; 연산은 Ultralytics 내부 | 새 모델과 동일 전처리·크기 계약 필요 | ROI/좌표 변경 시 원본 mapping 검증; TensorRT 시 parity 필요 |
| Detector | `src/contracts/interfaces.py:34`, `src/vision/pytorch_detector.py:10`, `inspection_worker.py:63` | 반환 계약/PyTorch adapter 재사용 | 모델·클래스·hash·self-test 교체; 현재 NumPy 호환성 선결 | 지연 예산·시점별 결과 상관관계; backend factory는 추가 필요 |
| Recipe | `src/recipe/package.py:39`, `src/decision/slots.py:18`, `src/decision/calibration.py` | 다중 slot·수량·독점 배정·불확실 판정 재사용 | 새 slot/클래스/수량/threshold/calibration 필수 | 고정 reference/slot으로 이동 대상 추적 불가; 정합 방식 설계 필요 |
| State Machine | `apps/edge_service/inspection.py:31`, `src/control/mock_cell.py:5`, `mock_port.py` | worker generation, 취소/늦은 결과 차단, Mock cycle 재사용 | 같은 판정/요청 계약이면 핵심 재작성 불필요 | 현재 단일 active job+busy 거부/정지·settling 가정; trigger 주기·제품 혼합·overflow 계약 필요 |
| SQLite | `src/journal/sqlite.py:33`, `:124`, `:149`, `:205` | FK/WAL/FULL, 복합 ID, 저장 후 게시, 원문 보존 재사용 | package snapshot 중심, schema 변경 필요성은 새 계약에 따름 | 처리량·cycle 연결·timeout/유실 검증; migration은 별도 Task |
| Evidence | `inspection_worker.py:29`, `sqlite.py:149`, `apps/edge_service/bench.py:atomic_write` | raw PNG/overlay/hash·파일 선행 저장 재사용 | 표시 클래스/자리와 새 reference 검증 | trigger/frame/제품 ID, drop·취소 이유 기록 확장 |
| PC Sync | `src/journal/sync.py:10`, `collector.py:14`, `apps/pc_service/collector_api.py` | event/asset 별도 ACK·재시도·멱등·quarantine 재사용 | package snapshot 전송으로 기본 재사용 | 대역폭/backlog/재접속 시험; MQTT는 별도 미구현 |
| Health API | `apps/edge_service/inspection.py:186`, `inspection_api.py:51` | state/camera/worker/package/storage/PC 상태 재사용 | 새 backend self-test/준비조건 연결 | PLC freshness/watchdog·disk 수치·지연 지표 확장 |
| Web UI | `apps/edge_service/inspection.html`, `inspection_api.py:45`; PC `collector.html` | 제품 선택·기준 승인·이력/원본·Mock 표시 재사용 | 이름/slot은 package 사용, 새 작업자 절차 검증 | 연속 흐름·늦은 프레임·PLC 연결/차단 상태 표시; 이번 화면 실렌더 UNVERIFIED |

## 저장/시간/제어 의미

Service가 원장 단일 writer이고 Worker는 카메라·GPU만 소유한다. 원본 저장 후 SQL commit, 그 뒤 결과 조회/소비가 가능하다. PC는 별도 DB를 가진다. RESULT_ACK, CYCLE_ACK, PC event ACK, PC asset ACK는 서로 다른 완료 조건이다. Mock RELEASE는 실제 배출 증명이 아니다.

기존 시간은 detector의 CUDA synchronize 포함 `inference_ms`, `worker_total_ms`, `worker_result_received_ms`, `INSPECTION_DURABLE_TIMING.request_to_durable_result_ms`다. 마지막 값만 결과 SQL commit 이후까지 측정하며 시작점은 `Journal.admit()` 후의 `accepted_monotonic`이므로 HTTP 도착/초기 DB admit 비용까지 포함하지 않는다. Worker 시간은 PNG/JPEG evidence encode 전이다. 전처리·H2D·순수 추론·NMS·encode·DB·전송·PLC ACK별 구분과 P95/99는 미완성이다. 이번 latency/FPS/throughput은 **UNMEASURED**이며 과거 n=3 진단을 성능 수용으로 재사용하지 않는다.

## 보존 검증과 읽기 전용 예외

**보존 PASS:** Jetson app_v00750파일/패키지7파일/이미지72개, Windows src24/apps12/config9/scripts25/earbud package7/PC 이미지72개, 두 DB 본체·PC WAL 및 모든 테이블 논리 hash. 기존 미커밋 tracked14파일도 문서 상태 추가 전 전후 동일하다. STATUS에는 이번 결과 블록만 덧붙이고 이전 본문을 보존한다. untracked 엔진 촬영 자료/봉인 평가 자료는 열람하거나 수정하지 않았다.

**전체 읽기 전용 수용은 FAIL:** 다음 두 부수 효과를 감추지 않는다.

1. 최초 버전 진단의 `import ultralytics`가 `/home/jetson/.config/Ultralytics/settings.json` 스키마 자동 갱신 경고를 냈고 해당 mtime은 감사 중 `2026-09-16T05:08:56.388080+00:00`이다. 이전 설정 hash/내용은 확보하지 못했다. 현재 hash는 `fc81409e60d90731183224e6188332f6dc68b012ddd2084d5c5e08c96fcceb4d`. 이후 버전은 distribution metadata만 조회했고 재import·추정 복원은 하지 않았다. app_v007/제품 파일 변경과 구분한다.
2. 최초 PC SQLite `mode=ro` 조회 때 기존 WAL의 `journal.sqlite3-shm` hash가 `67737af7757a9bc2585c56f6fefa61b74f9b75a732b9c9e176ae2c706479c3cf` → `a79fbf464cbb775a0e8097429c135ebd20788f3d9024b015cde1d0aa8f5fdf94`로 변경됐다. 읽기 동작의 공유 메모리 bookkeeping이며 DB 본체·WAL·원장 행 hash는 동일하다. SHM 삭제/되돌리기·checkpoint·VACUUM은 하지 않았다. Jetson은 WAL이 없어 `mode=ro&immutable=1`로 확인했다.

후속 읽기 전용 진단은 import 전 부수 효과를 확인하고 버전은 metadata를 우선한다. WAL이 있는 DB는 원본 sidecar를 건드리지 않는 안정된 복사본에서 조회하는 절차를 먼저 준비한다. 임의 `immutable=1`로 활성 WAL을 무시하여 최신 행을 누락시키면 안 된다.

## 다음 단계

[Gap 분석](JETSON_RUNTIME_GAP_ANALYSIS.md)과 [P0-002 초안](../../tasks/JETSON-P0-002.md)을 따른다. 순서는 P0-002 Fresh Frame → P0-003 Latency → P0-004 TensorRT → P0-005 Mock PLC → P0-006 Heartbeat → P0-007 OMRON이다. 모두 DRAFT이며 이번에 시작하지 않았다. 대상 실행 전 환경 호환성 문제의 별도 승인된 해결과 재검증이 필요하다.
