# T02 GPU Smoke Notes

## 목적과 범위

V0-T02는 Windows PC의 Python → PyTorch CUDA → GPU → 학습 → validation → checkpoint 저장 경로가 연결되는지 확인한다. 이번 RESUME는 기준 commit `486ed34`에서 중단된 문서화·검증을 마무리한다. 기존 성공 학습 1회를 재사용했으며 새 학습, validation 재실행, 설치, 다운로드는 수행하지 않았다. Jetson SSH·파일 수정·패키지 설치와 TensorRT 작업도 수행하지 않았다.

## 확인한 환경

| 항목 | 관측값 |
|---|---|
| 실행 위치 | Windows PC |
| Python / 가상환경 | 3.13.5 / `D:\OneDevice_Team_project\.venv` |
| Project PyTorch / CUDA | `2.11.0+cu128` / `12.8` |
| CUDA 사용 가능 | `True` |
| GPU / Driver | NVIDIA GeForce RTX 5070 Laptop GPU / 610.71 |
| Ultralytics | 8.4.146 |
| Global Python | `C:\Python313\python.exe` |
| Global PyTorch | `2.13.0+cpu`, CUDA `None`, CUDA 사용 가능 `False` |

`.venv`는 이 프로젝트가 사용할 Python 패키지를 분리하는 공간이다. 전역 CPU PyTorch를 바꾸지 않고 프로젝트에 CUDA PyTorch를 유지할 수 있다. 같은 PC라도 실행한 Python 경로에 따라 GPU 사용 가능 여부가 다르므로 모든 프로젝트 검증에서 `.venv\Scripts\python.exe`를 지정했다.

기존 환경 생성·설치는 이전 세션에서 완료했다. 아래는 환경 재구축 시 참고할 명령이며 이번에 실행한 명령이나 이전 설치 명령의 원문은 아니다. 기존 환경이 있는 RESUME에서는 실행하지 않는다.

```powershell
C:\Python313\python.exe -m venv .venv
.venv\Scripts\python.exe -m pip install torch==2.11.0+cu128 torchvision --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\python.exe -m pip install ultralytics==8.4.146
```

이번에 실제 실행한 환경 확인 명령:

```powershell
.venv\Scripts\python.exe --version
.venv\Scripts\python.exe -c "import sys, torch, ultralytics; print(sys.executable); print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0)); print(ultralytics.__version__)"
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
```

## 기존 성공 실행과 실패 실행

- Failed launch attempts: **1**. `python -m ultralytics ...`는 `No module named ultralytics.__main__`로 학습 전에 실패했다. 횟수와 당시 오류는 사용자 인수인계 기록에 근거한다. 보존된 학습 stdout에는 이 실패가 포함되어 있지 않다. 설치된 패키지에 `__main__.py`가 없음을 이번에 정적으로 확인했다.
- Successful smoke training runs: **1**. `from ultralytics import YOLO`를 사용하는 Python API 경로로 성공했다. 기존 실행 로그·단일 results.csv·checkpoint가 서로 일치한다.
- AMP 확인용 `weights/yolo26n.pt` 다운로드는 보조 점검이다. 실제 학습 모델은 `yolov8n.pt`이며 이를 두 번째 학습으로 세지 않는다.

아래는 `args.yaml`에서 복원한 핵심 호출 예시다. 원래 래퍼 전체의 복사본은 아니며 이번 RESUME에서는 실행하지 않았다. 다시 실행하면 성공 횟수가 늘어나므로 이 작업에서는 사용하지 않는다.

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
result = model.train(
    data="coco8.yaml", epochs=1, imgsz=320, batch=8,
    device=0, workers=0, project="training/outputs", name="t02_smoke",
)
```

기존 Ultralytics 설정으로 COCO8은 저장소 외부 dataset 디렉터리에 다운로드됐다. 재현 시 dataset 저장 위치는 그 환경의 설정을 확인해야 한다. 이번에는 설정이나 원본 데이터를 변경하지 않았다.

## 실험 기록과 결과

| 항목 | 기존 실행 Evidence |
|---|---|
| experiment_id / dataset | t02_smoke / COCO8, `coco8.yaml` |
| 모델 / epoch | yolov8n.pt / 1 |
| 이미지 / batch / workers | 320 / 8 / 0 |
| GPU 실제 사용 | 로그 `CUDA:0 (NVIDIA GeForce RTX 5070 Laptop GPU, 8151MiB)`와 epoch `GPU_mem 0.207G` |
| 하이퍼파라미터 | `args.yaml`: seed=0, amp=True, optimizer=auto; 로그에서 AdamW, lr=0.000119 선택 |
| 학습 완료 | `1 epochs completed`, `TRAIN_DONE` |
| 소요 시간 | 로그 `duration_sec 17.97`; CSV epoch 누적 시간 2.26436초와 측정 범위가 다름 |
| 최종 best.pt validation | 4 images / 17 instances, P=0.629, R=0.629, mAP50=0.616, mAP50-95=0.447 (stdout 반올림값) |
| epoch CSV validation | P=0.62933, R=0.63069, mAP50=0.61653, mAP50-95=0.44667 |
| 기존 validation inference latency | 로그 2.4 ms/image; 단일 tiny smoke 관측으로 배포 성능 기준이 아님 |
| 결론 | 환경 연결 및 기존 학습·validation·저장 성공 확인, V0-T02 PASS |

COCO8은 train 4장/validation 4장으로 빠르게 전체 연결을 확인하기 위해 사용했다. 1 epoch는 학습 데이터를 한 번 도는 최소 확인이며 모델 품질 개선이나 튜닝이 목적이 아니다. 최종 checkpoint validation과 epoch CSV 지표는 서로 다른 평가 단계이므로 반올림 차이를 합쳐 하나의 정밀 수치처럼 기록하지 않는다.

## 보존한 파일

기존 결과 디렉터리: `runs/detect/training/outputs/t02_smoke/`

- `args.yaml`, `results.csv`: 기존 학습 조건과 epoch·validation 결과.
- `weights/best.pt`, `weights/last.pt`: 각각 6,499,114 bytes. 실제 파일 존재와 SHA-256을 확인했다.
- `env-smoke-original.txt`: 정리 전 로그의 바이트 단위 보존본. quoting 오류 부분도 원본에 남겨 두었다.
- 저장소 루트 `env-smoke-log.txt`: GPU·완료·validation 원문 핵심 행을 포함한 작은 정리 로그.
- 이 폴더의 `verification.json`: 환경·ignore·단일 결과·checkpoint 무변경 확인 결과와 해시.

`.venv/`, `runs/`, `*.pt`, dataset 및 cache는 Git에서 제외한다. 원본과 checkpoint는 로컬에 보존하고 문서·작은 로그·검증 요약만 commit한다. Git만 복제하면 로컬 checkpoint가 포함되지 않는다.

## 다음 단계

V0-T03 Core Contracts / Camera + Detector Interfaces는 **TODO**, 이번에 시작하지 않는다. V0-B는 기존 계획대로 **V0-T04**에서 직접 촬영하는 Proxy Dataset으로 시작한다. V1에서는 엔진 Dataset, 클래스, 모델, 레시피, 평가 데이터를 교체하며 COCO8 점수나 proxy 기준치를 엔진 검사 성능으로 사용하지 않는다.
