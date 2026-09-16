# JETSON-P0-002R — CUDA Allocator Gate C Root Cause Isolation

2026-09-16. **FAILURE_NOT_REPRODUCED_WITH_CONTROLLED_EVIDENCE**.

최종 분류는 **CASE G — INTERMITTENT / ROOT_CAUSE_UNCONFIRMED**다. 서로 다른 새 process 23개에서 allocation, kernel, Conv2d, 모델 load/move/warmup, Ultralytics 및 기존 PyTorchDetector까지 모두 PASS였다. 이번 실행의 최초 실패 단계와 최초 실패 allocation 크기는 없다. P0-002에서 관측한 실패를 취소하거나, 원인이 해결되었다고 판단하지 않는다.

Evidence: [JETSON-P0-002R.json](../verification/JETSON-P0-002R.json). Raw: `runs/jetson_p0_002r/`. 실제 Fresh Frame/Conveyor 검증은 이번에 수행하지 않았다.

## 환경과 격리

- Jetson Orin Nano, L4T 36.4.7, Linux 5.15.148-tegra, Python 3.10.12.
- Interpreter: `/home/jetson/oned_device_bench/envs/app_v1/bin/python`.
- NumPy 1.26.4: `env_candidates/numpy_compat_001/overlay/numpy/__init__.py`를 process-local sys.path로 선택.
- torch 2.8.0: `/home/jetson/.local/lib/python3.10/site-packages/torch/__init__.py`; CUDA 12.6, cuDNN 9.3.0 (`90300`). torch git metadata: `3a67bf9c620e8958a1677e68779be08eb34dafa3`.
- OpenCV 5.0.0 / Ultralytics 8.4.118 / TensorRT 10.3 기존 설치 유지. OpenCV metadata `numpy>=2`와 candidate 1.26.4 충돌도 유지한다.
- 새 파일은 `/home/jetson/oned_device_bench/diagnostics/p0_002r_cuda/`에만 작성하도록 제어했다. 기존 P0-002 candidate, launcher, gate JSON을 변경하지 않았다.

테스트마다 새 Python process를 순차 실행하고 종료했다. CPU-only case는 CUDA query도 하지 않았으며 `cuda.is_initialized()==False`를 확인했다. GPU case는 import 직후 host snapshot을 먼저 기록하고, 명시적인 `cuda_runtime_query` 단계에서 availability/count/name/mem_get_info를 읽었다. 그 뒤 각 작업 전후와 종료 시 host/CUDA 상태를 기록했다. 하나의 case가 끝나기 전에 다음 GPU case를 실행하지 않았다.

각 case의 YOLO_CONFIG_DIR, MPLCONFIGDIR, XDG_CACHE_HOME, TORCH_HOME, TMPDIR와 **CUDA_CACHE_PATH**를 진단 경로로 지정했다. CUDA_CACHE_PATH는 driver cache의 쓰기 위치 격리용이며 allocator 정책 변수가 아니다. PYTORCH_CUDA_ALLOC_CONF, PYTORCH_ALLOC_CONF, PYTORCH_NVML_BASED_CUDA_CHECK, CUDA_VISIBLE_DEVICES, CUDA_MODULE_LOADING, CUBLAS_WORKSPACE_CONFIG, CUDNN_CONV_WSCAP_DBG는 모두 미설정 상태를 유지했다. backend 설정도 변경하지 않았다.

캐시 삭제/empty_cache, 패키지 설치·교체, image/batch 축소, CMA/swap/전력 설정 변경, reboot는 없었다. 단, 새 process와 독립 cache 및 사전 CUDA query는 원래의 camera+imports+model 복합 process와 조건이 다르므로 **원래 실행 전체의 완전한 재현이라고 부르지 않는다**.

## 단계별 결과와 메모리

모든 allocation은 FP32이며 16/32/64/128/256은 MiB(2²⁰ bytes) 기준이다. allocation과 zero fill을 별도 step으로 기록하고 synchronize 뒤 양 끝 값이 0인지 확인했다. kernel 검사는 elementwise 기대값과 64×64 matrix product 전체 기대값을 검사했다. 성능 benchmark는 하지 않았다.

Conv2d(3,8,3)는 CPU와 CUDA를 별도 process에서 실행했다. 1×3×640×640 입력에 weight=1, bias=0, input=1을 사용하여 1×8×638×638 출력의 모든 값이 27인지 확인했다.

| Case | 결과 | 종료 MemAvailable (kB) | 종료 CmaFree (kB) | CUDA allocated / reserved (bytes) |
|---|---|---:|---:|---|
| cpu_tensor | PASS | 3,969,600 | 0 | NOT_RUN (CPU only) |
| runtime_info | PASS | 3,930,260 | 0 | 0 / 0 |
| cuda_tiny | PASS | 3,919,072 | 0 | 512 / 2,097,152 |
| cuda_640 | PASS | 3,913,144 | 0 | 4,915,200 / 20,971,520 |
| alloc_16 | PASS | 3,912,608 | 0 | 16,777,216 / 16,777,216 |
| alloc_32 | PASS | 3,902,588 | 0 | 33,554,432 / 33,554,432 |
| alloc_64 | PASS | 3,864,320 | 0 | 67,108,864 / 67,108,864 |
| alloc_128 | PASS | 3,779,804 | 0 | 134,217,728 / 134,217,728 |
| alloc_256 | PASS | 3,774,892 | 3,544 | 268,435,456 / 268,435,456 |
| elementwise | PASS | 3,767,656 | 6,636 | 1,024 / 2,097,152 |
| matrix | PASS | 3,734,812 | 2,564 | 8,552,448 / 23,068,672 |
| cpu_conv | PASS | 3,814,748 | 7,772 | NOT_RUN (CPU only) |
| cuda_conv | PASS | 3,710,004 | 4,396 | 4,916,736 / 23,068,672 |
| model_sha | PASS | 4,065,896 | 26,040 | NOT_RUN (CPU only) |
| model_cpu_load | PASS | 3,818,364 | 272 | NOT_RUN (CPU only) |
| model_structure | PASS | 3,824,532 | 736 | NOT_RUN (CPU only) |
| model_cuda_move | PASS | 3,791,040 | 2,468 | 12,230,656 / 33,554,432 |
| model_warmup | PASS | 3,497,640 | 136 | 23,663,616 / 60,817,408 |
| ultra_cpu_load | PASS | 3,836,056 | 31,404 | NOT_RUN (CPU only) |
| ultra_prepare | PASS | 3,805,000 | 31,684 | 12,230,656 / 33,554,432 |
| ultra_zero | PASS | 3,334,668 | 0 | 12,142,080 / 60,817,408 |
| ultra_image | PASS | 3,331,360 | 0 | 12,142,592 / 60,817,408 |
| project_adapter | PASS | 3,298,756 | 0 | 12,142,592 / 60,817,408 |

각 case의 모든 import/step 전후 값, CUDA free/total·allocated/reserved·max allocated/reserved는 verification JSON에 포함했다. 위 표는 process 종료 직전 snapshot이므로 서로 동일한 시스템 상태에서 비교한 성능 지표가 아니다.

전체 case snapshot 범위: MemAvailable **3,298,252–4,200,456 kB**, CmaFree **0–32,152 kB**. model warmup 종료 시 MemAvailable 3,497,640 kB / CmaFree 136 kB, project adapter 종료 시 3,298,756 kB / 0 kB였다. CmaFree=0에서도 작은 allocation부터 128 MiB allocation과 최종 Detector가 PASS한 관측이 있으므로, CmaFree 하나만으로 실패를 설명할 수 없다. host memory availability와 CUDA allocator의 reserved/allocated도 같은 의미의 값이 아니다.

import 전 `free -b`, `/proc/meminfo`, nvidia-smi, /proc에서 읽을 수 있는 Python/CUDA library mapping 및 camera owner를 수집했다. tegrastats는 전후 각각 약 3초 동안 읽고 해당 관측 process만 종료했다. 전후 camera owner는 없었고 카메라를 열지 않았다. nvidia-smi는 Orin/driver 540.4.0/CUDA12.6을 보고했으나 memory usage는 Not Supported였다. /proc 권한 밖 process의 GPU 사용 여부는 완전한 관측이 아니다.

## 모델 / Ultralytics / 프로젝트 경계

승인된 earbud 모델: `releases/app_v007/deployment/products/earbud_case_v0/app_v001/`의 manifest가 지정한 best.pt. SHA256은 `49f533e4e4e5846d1582564d8efbb38a647ad10348a976db9085d94df16250c1`로 전후 동일하다.

Raw model은 `torch.load(map_location='cpu', weights_only=False)`로 승인된 checkpoint를 읽었다. pickle class 복원 때문에 설치된 Ultralytics 클래스는 import되지만 YOLO.predict/AutoBackend는 사용하지 않았다. CPU object를 FP32/eval로 준비하고, 별도 process에서 구조(DetectionModel, 3,011,433 parameters, 225 modules), CUDA 이동, zero FP32 1×3×640×640 forward 1회를 각각 검증했다. 파일은 저장하지 않았다. raw warmup 출력 tensor들은 finite였다.

그 다음에만 Ultralytics YOLO CPU load → CUDA preparation → synthetic zero BGR image의 predict → 기존 승인 이미지의 predict → 기존 PyTorchDetector 순으로 수행했다. 각 predict case는 public API 호출 1회다. 라이브러리 내부의 native warmup과 실제 prediction이 함께 수행될 수 있으므로 전체 forward 1회라고 주장하지 않는다.

승인 이미지: `data/app_v1/assets/5031fbaf16a94877b5b6aa46f9e90c03/215fc0dd6f7a4fc19fbee249cfdd5642.png`. 원본은 읽기 전용이다. 기존 app_v007의 PyTorchDetector는 수정 없이 CUDA `input_shape=[1,3,640,640]`, detection 3개를 반환했다. 이는 Detector 경로 smoke이며 검출 정확도·Recipe 판정·Fresh Frame·candidate DB cycle 수용이 아니다. 모든 23개 case의 stderr는 비어 있었고 NvMap error 12가 재발하지 않았다.

## NVML 관측과 해석 한계

실제 torch process에 매핑된 NVML은 `/usr/lib/aarch64-linux-gnu/nvidia/libnvidia-ml.so.1`이다. 별도 read-only ctypes query에서 초기화, device count(1), device handle 조회는 성공했다. compute-process count 조회의 unversioned/v2/v3 API는 모두 **return code 3, Not Supported**였다. library 교체와 NVML 환경 변수 변경은 없었다. [NVIDIA NVML device query 명세](https://docs.nvidia.com/deploy/nvml-api/api/group__nvmlDeviceQueries.html)

torch git metadata에 해당하는 upstream allocator에서 동일한 `NVML_SUCCESS == r` 조건은 `reportProcessMemoryInfo`의 compute-process 조회 결과 검사다. NVML 초기화는 별도 assertion이며, 이 함수는 allocation 실패의 process memory 보고 경로에서 호출된다. 따라서 원래 오류가 allocation 실패를 보고하는 도중 발생한 **추가 오류일 가능성**은 있지만, 원래 물리 allocation 실패가 왜 생겼는지는 확인되지 않았다. [PyTorch allocator 소스](https://github.com/pytorch/pytorch/blob/3a67bf9c620e8958a1677e68779be08eb34dafa3/c10/cuda/CUDACachingAllocator.cpp#L1025-L1077), [NVML symbol 선언](https://github.com/pytorch/pytorch/blob/3a67bf9c620e8958a1677e68779be08eb34dafa3/c10/cuda/driver_api.h#L55-L61)

설치 binary의 오류 line1131과 upstream의 동일 조건 line1063은 일치하지 않는다. vendor/build patch 전체와 원래 C++ backtrace를 확인하지 않았으므로 exact source-line 대응은 미검증이다. 직접 측정한 NVML 초기화 성공은 현재 관측이며 과거 오류 당시의 초기화 상태까지 증명하지 않는다. NvMap error12를 메모리 부족/CMA 부족/단편화/driver 결함 중 하나로 확정하지 않는다.

## 보존과 다음 단계

전후 SHA 비교: app_v007 50파일, app_v1 env 1,998파일, earbud package 7파일/best.pt, 기존 DB/assets 72파일, 기존 사용자 패키지/settings, P0-001R candidate 922파일, P0-002 candidate 38파일 모두 변경 0. 기본 CUDA cache와 후보 data root도 그대로다. current symlink 변경 0, 원본 DB connection 0. 새 진단 경로 inventory는 87파일이며 각 SHA는 verification에 있다.

보존 비교는 명시한 보호 경로와 cache에 한정한다. 자율적으로 갱신되는 전체 OS 로그까지 동일했다고 주장하지 않는다. Windows의 Fresh Frame Runtime 소스와 P0-002 evidence도 동일하다. 진단이 쓰지 않은 `tasks/engine-dataset-codex-support.md`의 동시 해시 변경은 별도로 기록하고 현재 내용을 보존했다. 나머지 시작 시 수집한 보호 파일은 동일하다.

진단 Task는 CASE G 근거 확보로 완료한다. 기존 102 tests는 이번에 재실행하지 않았다(구현 변경 0). 진단 산출물 검증 및 `git diff --check`를 수행한다. commit/push 없음.

**P0-002 actual Fresh Frame 재개는 현재 BLOCKED**다. 독립 process의 Detector PASS만으로 이전의 보호된 실패 Gate 기록을 덮어쓰지 않는다. 다음 별도 Task에서 원래 camera/Worker/model이 함께 있는 Candidate Runtime Gate를 메모리 관측과 함께 재확인하고 수용해야 한다. 지금 근거만으로 패키지·allocator 설정 교체 방식을 선택하지 않는다.
