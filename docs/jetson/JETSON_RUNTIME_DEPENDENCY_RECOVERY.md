# JETSON-P0-001R — Runtime Dependency Compatibility Recovery

2026-09-16. **최소 수용 기준 PASS / PREPROCESS_READY**.

**격리 Candidate environment에서 기존 필수 NumPy→Torch 입력 경로 호환성을 회복했다.** 기존 app_v007/app_v1을 복구하거나 교체한 것은 아니다. 기존 환경은 NumPy2.2.6과 동일 실패를 유지하며, 별도 overlay를 선택한 프로세스에서만 NumPy1.26.4가 사용된다.

근거: [검증 JSON](../verification/JETSON-P0-001R.json), [Task](../../tasks/JETSON-P0-001R.md). 이전 감사 [Baseline](JETSON_RUNTIME_BASELINE.md)은 당시 관측 그대로 보존한다. 상세 stdout/stderr·파일별 SHA는 `runs/jetson_p0_001r/`에 있다.

## 원인 확인

`app_v1/pyvenv.cfg`는 `include-system-site-packages = true`, Python3.10.12다. `site.ENABLE_USER_SITE=true`여서 주요 ML 패키지는 venv 내부가 아니라 `~/.local`에서 선택된다. TensorRT는 시스템 경로다.

현재 torch2.8.0은 NumPy2.2.6에서 “NumPy1.x로 컴파일된 모듈은 NumPy2.x에서 실행할 수 없다”는 ABI 진단을 내고 `torch.from_numpy()`가 `RuntimeError: Numpy is not available`로 실패한다. torch/OpenCV/CUDA 파일을 그대로 둔 채 NumPy 선택만1.26.4로 바꾸면 이 함수와 CUDA 왕복이 통과한다. **현재 torch build와 NumPy2.2.6의 ABI 조합 불호환**을 원인으로 지지하는 통제 비교다. 과거 패키지 변경 시점·행위자·원래 wheel 빌드 과정은 확인하지 않았다.

기존 환경의 `torch.tensor(a)`와 `torch.as_tensor(a)`는 이번 작은 배열에서 PASS였다. 그러나 기존 Ultralytics 전처리는 `torch.from_numpy()`를 호출하므로 다른 함수로 바꾸거나 우회 구현을 채택하지 않았다. 원본 오류의 전체 stderr와 traceback은 `baseline.json` 및 `baseline_after.json`에 보존했다.

## 실제 Python 검색 경로

`sys.executable`:

```text
/home/jetson/oned_device_bench/envs/app_v1/bin/python
```

Candidate도 같은 실행 파일을 사용한다. 별도 완전한 venv가 아니라 NumPy 하나의 선택을 격리한 overlay다. 아래는 부수 효과가 있는 패키지를 import하기 전의 기본 검색 경로다.

```text
sys.path:
  ""  (실행 cwd)
  /usr/lib/python310.zip
  /usr/lib/python3.10
  /usr/lib/python3.10/lib-dynload
  /home/jetson/oned_device_bench/envs/app_v1/lib/python3.10/site-packages
  /home/jetson/.local/lib/python3.10/site-packages
  /usr/local/lib/python3.10/dist-packages
  /usr/lib/python3/dist-packages
  /usr/lib/python3.10/dist-packages

site.getsitepackages():
  /home/jetson/oned_device_bench/envs/app_v1/lib/python3.10/site-packages
  /home/jetson/oned_device_bench/envs/app_v1/local/lib/python3.10/dist-packages
  /home/jetson/oned_device_bench/envs/app_v1/lib/python3/dist-packages
  /home/jetson/oned_device_bench/envs/app_v1/lib/python3.10/dist-packages
  /usr/lib/python3.10/site-packages
  /usr/local/lib/python3.10/dist-packages
  /usr/lib/python3/dist-packages
  /usr/lib/python3.10/dist-packages

site.getusersitepackages():
  /home/jetson/.local/lib/python3.10/site-packages
```

`site.getsitepackages()` 목록은 Python이 보고한 후보이며 모두 `sys.path`에 있다는 뜻은 아니다. Candidate smoke는 새 프로세스에서 `sys.path.insert(0, overlay)`를 사용했다. Candidate의 `pip check`는 그 프로세스에만 `PYTHONPATH=overlay`를 지정했다. `.pth`, pyvenv.cfg, shell profile, 기본 서비스 launcher는 변경하지 않았다. OpenCV import 후 `cv2` native 탐색 경로가 프로세스 sys.path에 추가될 수 있으므로 초기 목록과 import 후 관측을 구별한다.

## 모듈의 실제 위치

| 모듈 | Current version / 실제 선택 경로 | Candidate version / 실제 선택 경로 |
|---|---|---|
| numpy | 2.2.6 · `/home/jetson/.local/lib/python3.10/site-packages/numpy/__init__.py` | 1.26.4 · `/home/jetson/oned_device_bench/env_candidates/numpy_compat_001/overlay/numpy/__init__.py` |
| torch | 2.8.0 · `/home/jetson/.local/lib/python3.10/site-packages/torch/__init__.py` | 동일 버전·동일 파일 |
| torchvision | 0.23.0 · `/home/jetson/.local/lib/python3.10/site-packages/torchvision/__init__.py` (metadata/spec) | 0.23.0 · 동일 경로 실제 import 확인 |
| cv2 | 실제 import5.0.0, distribution5.0.0.93 · `/home/jetson/.local/lib/python3.10/site-packages/cv2/__init__.py` | 동일 버전·동일 파일 |
| ultralytics | 8.4.118 · `/home/jetson/.local/lib/python3.10/site-packages/ultralytics/__init__.py` (metadata/spec) | 8.4.118 · 전용 config 아래 전처리 import 때 동일 파일 확인 |
| tensorrt | 10.3.0 · `/usr/lib/python3.10/dist-packages/tensorrt/__init__.py` | 동일 버전·동일 파일 |

기존 metadata 디렉터리는 각각 같은 site 경로의 `numpy-2.2.6.dist-info`, `torch-2.8.0.dist-info`, `torchvision-0.23.0.dist-info`, `opencv_python-5.0.0.93.dist-info`, `ultralytics-8.4.118.dist-info`, `tensorrt-10.3.0.dist-info`다. 전체 `Requires-Dist`, wheel tag, installer와 경로는 JSON에 기록했다. torch wheel tag는 `cp310-cp310-linux_aarch64`, torch가 보고한 CUDA는12.6, CUDA 장치는 Orin이다. 이번에는 L4T/CUDA/TRT를 변경하지 않았다.

## 설치와 격리 경계

새 경로만 생성했다.

```text
/home/jetson/oned_device_bench/env_candidates/numpy_compat_001/
  overlay/                     NumPy1.26.4와 numpy.libs, dist-info, bin
  wheels/                      원본 wheel1개
  config/ultralytics/           이번 전처리 import 전용 설정
  config/matplotlib/           격리 설정 경로
  cache/                       격리 캐시 경로
  tmp/                         pip 임시 작업 경로
  install_log.json             최초 pip 인자 오류 증거
  install_log_002.json         실제 download/install 명령과 결과
```

실제 pip22.0.2는 `--report`를 지원하지 않아 최초 명령이 패키지 설치 전 인자 파싱 단계에서 종료됐다. 빈 candidate 디렉터리와 오류 로그는 보존했다. pip를 업그레이드하거나 다른 NumPy 버전을 시도하지 않고, 같은1.26.4 wheel을 다운로드한 뒤 공개 SHA256을 대조하여 오프라인 설치했다.

실행된 성공 명령은 다음과 같다. 해당 candidate 경로는 이미 존재하므로 재실행하여 덮어쓰지 않는다.

```bash
/home/jetson/oned_device_bench/envs/app_v1/bin/python -B -m pip \
  --isolated --disable-pip-version-check download \
  --dest /home/jetson/oned_device_bench/env_candidates/numpy_compat_001/wheels \
  --no-deps --only-binary=:all: --no-cache-dir \
  --index-url https://pypi.org/simple numpy==1.26.4

/home/jetson/oned_device_bench/envs/app_v1/bin/python -B -m pip \
  --isolated --disable-pip-version-check install \
  --target /home/jetson/oned_device_bench/env_candidates/numpy_compat_001/overlay \
  --no-index --no-deps --no-compile --no-cache-dir \
  /home/jetson/oned_device_bench/env_candidates/numpy_compat_001/wheels/numpy-1.26.4-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
```

`TMPDIR`는 candidate의 `tmp`, `PYTHONDONTWRITEBYTECODE=1`을 사용했다. Python 실행 파일을 빌려 사용했을 뿐 설치 목적지는 기존 app_v1 site-packages가 아니다. 전이 의존성 설치·삭제0.

- wheel: `numpy-1.26.4-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl`
- 크기: 14,219,016 B.
- SHA256: `d209d8969599b27ad20994c8e41936ee0964e6da07478d6c35016bc386b66ad4`.
- PyPI 해당 릴리스 JSON의 파일 SHA256과 다운로드 파일 SHA256 일치. URL과 명령 stdout은 `install_compatible.json`에 기록.

Candidate 전처리 import에는 `YOLO_CONFIG_DIR=<candidate>/config/ultralytics`, `MPLCONFIGDIR=<candidate>/config/matplotlib`, `XDG_CACHE_HOME=<candidate>/cache`, `TORCH_HOME=<candidate>/cache/torch`, `YOLO_AUTOINSTALL=false`와 candidate cwd를 사용했다. 생성된 실제 Ultralytics 설정은 `<candidate>/config/ultralytics/Ultralytics/settings.json`이다. 기존 `~/.config/Ultralytics/settings.json` hash는 이번 전후 동일하다.

## Compatibility Matrix

| 검사 | Current NumPy2.2.6 | Candidate NumPy1.26.4 |
|---|---|---|
| import numpy | PASS | PASS |
| import torch | PASS, NumPy ABI 경고 발생 | PASS, 진단 stderr 없음 |
| import cv2 | PASS (5.0.0) | PASS (동일5.0.0) |
| import tensorrt | PASS (10.3.0) | PASS (동일10.3.0) |
| torch.from_numpy | **FAIL: Numpy is not available** | **PASS** |
| torch.tensor | PASS | PASS |
| torch.as_tensor | PASS | PASS |
| CUDA available | PASS/true | PASS/true |
| NumPy→from_numpy→CUDA 연산→CPU→NumPy | NOT_RUN: bridge 실패, Candidate만 실행 | **PASS** |
| OpenCV+NumPy cvtColor/resize | PASS | **PASS** |
| 저장 이미지→실제 전처리→FP32 tensor | NOT_RUN | **PREPROCESS_READY** |
| 전체 pip metadata 일관성 | FAIL: 기존 pynacl→cffi 누락 | **FAIL: 기존 누락 + OpenCV numpy>=2 선언 충돌** |

CPU bridge 입력은 `np.zeros((1,3,2,2), dtype=np.float32)`다. Candidate CUDA smoke는 `arange(12)`의 같은 shape 배열을 실제 `cuda:0`에 전송하여 `x*2+1`을 계산한 뒤 CPU NumPy 배열로 반환했다. 실제값 `[1,3,5,7,9,11,13,15,17,19,21,23]`과 기대값이 정확히 일치했다. CUDA synchronize를 포함했지만 시간을 성능 수치로 측정하지 않았으며 benchmark가 아니다.

OpenCV memory smoke는4×6 BGR uint8 상수 배열 `(7,31,127)`을 RGB로 바꿔 `(127,31,7)`을 확인하고3×2로 resize, grayscale4×6도 확인했다. 파일/카메라를 열지 않았다.

## 기존 입력 경로 전처리 smoke

앞 단계가 모두 통과한 뒤 기존 승인 정상 검사 `5031fbaf16a94877b5b6aa46f9e90c03`의 raw PNG1장만 읽었다. 원본 DB에 연결하지 않고 P0-001의 보존된 asset metadata를 사용했으며 파일 SHA를 먼저 대조했다.

- 이미지: `/home/jetson/oned_device_bench/data/app_v1/assets/5031fbaf16a94877b5b6aa46f9e90c03/215fc0dd6f7a4fc19fbee249cfdd5642.png`
- 원본 SHA256: `04380e88c2802d39826da972d2fdb30eaba03e0c7a17713d5178434fa16c2b18`, 전후 동일.
- 실제 경로: PNG bytes read-only → OpenCV decode BGR720×1280×3 → 설치된 `BasePredictor.preprocess()`/`pre_transform()`/`LetterBox` → FP32 RGB/255 NCHW `[1,3,640,640]` CPU tensor.
- 기존 app_v007은 `PyTorchDetector.detect()`에서 Ultralytics predict를 호출한다. 이번에는 그 라이브러리의 실제 전처리 메서드만 호출했고 predictor 생성자·YOLO/model·Service·Camera를 생성하지 않았다. shape/rect=false/fp16=false는 불변 package 설정을 사용했다. model descriptor의 stride32는 auto=false일 때 resize에 영향을 주지 않는다.
- 독립 계산:1280×720→640×360 INTER_LINEAR resize → 위/아래140픽셀 값114 padding → RGB/transpose/contiguous/FP32÷255. 실제 tensor와 최대 절대차 **0.0**. dtype/shape/연속 메모리/유한값/범위0..1 확인.
- tensor SHA256: `15d3ced144392ec1ae64f0b051a71ab5b218430c82ec21892ed1665242828299`.
- **best.pt 로드·inference0**, 새 촬영0, 원본 수정0. 전처리 성공은 정확도·추론속도·실 카메라 E2E 성공이 아니다.

현재 기본 환경을 새 프로세스로 다시 실행하면 NumPy2.2.6 경로와 from_numpy 실패가 그대로 재현된다. Candidate 선택이 기본 환경에 지속 적용되지 않았음을 확인했다.

## OpenCV5의 범위와 남은 제한

OpenCV5의 현재 사용 함수는 Candidate NumPy에서 실제 통과했으므로 OpenCV를 downgrade하지 않았다. 다만 설치된 `opencv-python5.0.0.93`의 `Requires-Dist`는 Python≥3.9에서 `numpy>=2`다. `pip check`는 Candidate에서 이 충돌을 실제 보고했다. 이 선언을 지우거나 무시한 전체 환경 PASS로 바꾸지 않는다.

Current/Candidate 모두의 `pynacl1.5.0 requires cffi` 누락은 기존 환경에서 발견된 별도 metadata 문제다. 이번 입력 경로 smoke와 직접 연결되지 않아 변경하지 않았다. 새 cffi 또는 다른 dependency를 설치하지 않았다.

따라서 **P0-002의 격리 Candidate 기반 설계·개발은 진행 가능**하나, **실제 카메라 Runtime 실행/운영 승격은 아직 BLOCKED**다. 후속 Task에서 app_v008-dev 또는 별도 후보 Runtime의 선택 경로·의존성 계약·실제 기동/모델 smoke를 검증해야 한다. 이번에는 그러한 Runtime을 만들거나 기존 launcher를 바꾸지 않았다. app_v007을 복구됐다고 보고하거나 자동 재시작하지 않는다.

## 변경 및 보존 증거

원격에서 새 파일이 생긴 승인 경로는 `env_candidates/numpy_compat_001/`이다. 최종922파일/62,896,161B이며 overlay918파일, wheel1개, install log2개, 전용 Ultralytics 설정1개다. 빈 config/cache/tmp 디렉터리도 생성했다. 파일별 목록·SHA는 `runs/jetson_p0_001r/candidate_files_manifest.json`, 그 manifest hash는 검증 JSON에 있다. 임시 pip 작업은 candidate/tmp를 사용했다.

| 기존 보호 대상 | 전후 결과 |
|---|---|
| app_v007 release50파일 | **변경0 / PASS** |
| earbud package7파일 | **변경0 / PASS** |
| best.pt | **변경0**, SHA `49f533e4e4e5846d1582564d8efbb38a647ad10348a976db9085d94df16250c1` |
| Edge SQLite 본체 | **변경0**, SHA `dcd31eb7a79d13ce357ab95729a2b22fba6c974a1a6b3541c1c786b7498b1cbd`; WAL/SHM는 전후 없음 |
| Edge assets72파일 | **변경0 / PASS** |
| app_v1 환경1998파일 | **변경0 / PASS** |
| 기존 NumPy/torch/torchvision/OpenCV/Ultralytics/TRT 코드·metadata·native libs 및 .pth | **전후 hash 동일** |
| 기존 Ultralytics 사용자 settings | **변경0**, SHA `fc81409e60d90731183224e6188332f6dc68b012ddd2084d5c5e08c96fcceb4d` |
| PC DB/WAL/SHM·이미지 및 기존 사용자 변경 | 최종 로컬 보존 검증 참조; 원본 DB 연결0 |

원격24개 보호 경로의18181파일 항목을 비교했다. 중첩 경로가 있으므로 이 수를 고유 파일 수로 해석하지 않는다. app 프로세스는 전후 모두 없었고 시작/중지0이다.

Windows 변경은 새 보고서·검증JSON·Task, STATUS 결과 블록과 `runs/jetson_p0_001r/` 진단/evidence다. 기존 STATUS 본문은 그대로 보존한다. P0-001 문서·P0-002~007 초안과 엔진 Dataset 작업은 변경하지 않는다. git diff --check 및 새 산출물 검증 결과는 JSON에 기록한다. commit/push, git reset/clean, apt, CUDA/TRT 재설치, PLC, MQTT 변경 없음.
