# 다른 Jetson에 현재 통합 검사 프로그램 설치

`jetson/` 폴더 전체를 복사하면 코드·UI·모델 7개·기준 자산·설정 양식·과거 SQLite가 함께 전달됩니다. 설치 입력은 **`portable/operating_runtime.tar.gz`**, 기준 운영본은 **`engine-integrated-32c484ac6aeb07f1`**입니다. 바깥의 개발 소스를 재조합하지 않아 미채택 후보 설정이 섞이지 않습니다.

새 장치의 OS/GPU 환경·USB 카메라·촬영 구도·PLC 연결은 아래 순서로 준비합니다. 파일 복사는 다른 장치의 실제 운전 검증까지 대신하지 않습니다. 설치기는 기존 설치를 덮어쓰거나 패키지·네트워크·PLC·서비스를 자동 변경하지 않습니다. **기존 `setup.sh/install.py`는 과거 CORE MOCK 설치용이며 이 통합 운영 설치에는 사용하지 않습니다.**

## 1. 환경과 장치 설정

| 항목 | 운영 기준 / 새 장치에서 확인할 내용 |
|---|---|
| 보드·OS | Jetson Orin Nano, Linux aarch64, Ubuntu22.04, L4T36.4.7 관측 |
| GPU | CUDA12.6, TensorRT10.3, Python3.10.12 관측 |
| Python | NumPy1.x, CUDA용 torch + 호환 torchvision, Ultralytics, OpenCV, Pillow, FastAPI/Uvicorn/Pydantic |
| 영상 | 시스템 PyGObject/GStreamer `v4l2src/jpegdec/videoconvert/appsink`; USB MJPG 1280×720 / 30fps |
| 계정 | 실제 운영 계정, sudo 및 `video`/`render` 장치 접근 권한 확인 |
| 저장 | 설치 공간 + 검사 사진 공간 확보. 기존 최소 여유1GB 보호 유지 |
| PLC | 같은 라인 교체용: Jetson192.168.50.2, PLC192.168.50.3, NIC `enP8p1s0` |
| 웹 | 기본 `127.0.0.1:18771`, 노트북은 SSH 터널 |

기존 장치와 새 장치를 같은 IP로 동시에 연결하지 않습니다. 다른 주소·NIC·PLC 프로그램이면 별도 계약 검증이 필요하며 설치기는 네트워크를 임의 변경하지 않습니다.

JetPack은 [NVIDIA 설치 안내](https://docs.nvidia.com/jetson/jetpack/6.2/install-setup/index.html), GPU용 torch/torchvision은 [Jetson PyTorch 설치](https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/index.html)와 [호환 버전표](https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform-release-notes/pytorch-jetson-rel.html)를 따릅니다. 일반 PC/CPU wheel로 대체하거나 시스템 CUDA/TensorRT를 프로젝트 설치 과정에서 교체하지 않습니다.

TensorRT plan은 기본적으로 생성 환경에 의존합니다([NVIDIA 호환성 문서](https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/engine-compatibility.html)). 같은 Orin Nano라도 아래 실제 모델 실행 점검이 필요합니다. 실패하면 환경·오류를 보존하며 재학습/엔진 재생성을 자동 수행하지 않습니다.

## 2. 파일 검사와 신규 폴더 준비 — Jetson

다운로드한 `jetson/`의 **상위 폴더**에서 실행합니다. 카메라를 다른 프로세스로 열지 않고 목록/지원 모드부터 확인합니다.

```bash
python3.10 -B -X utf8 jetson/install_operating.py --verify
ls -l /dev/v4l/by-id/
v4l2-ctl --list-devices
```

`v4l2-ctl` 부재는 카메라 미지원과 다릅니다. 설치돼 있으면 선택한 현재 노드에 `v4l2-ctl --device /dev/videoN --list-formats-ext`를 실행합니다. 가능하면 실제 `/dev/v4l/by-id/...-video-index0` 경로를 씁니다.

카메라 경로와 station ID를 실제 값으로 바꾸고, **sudo 없이 운영 계정**으로 실행합니다.

```bash
python3.10 -B -X utf8 jetson/install_operating.py --prepare --camera /dev/v4l/by-id/실제카메라-video-index0 --station-id engine-cell-02
```

기본 설치 위치는 `~/oned_device_bench`이며 `--base /home/실제계정/oned_device_bench`로 지정할 수 있습니다. 기존 `current/assets/config/data/history`가 있으면 중단합니다. 실패한 `.portable-*`와 오류를 보존하며 기존 폴더를 지워 재시도하지 않습니다.

```text
~/oned_device_bench/
├── current/          검증된 실행 코드·UI·장치별 release.json
├── assets/           모델 7개·기준 자산
├── config/           새 카메라·station·PLC·환경 설정
├── data/             비어 있는 새 검사 원장/Evidence 위치
├── history/          과거 journal.sqlite3·snapshot.json
├── templates/        원래 장치 설정의 출처 보관본
├── service/          이 계정·경로로 생성한 systemd unit
├── installation.json 설치/현장 설정 확인 영수증
└── envs/app_v1/      별도로 준비할 GPU Python 환경
```

`history/journal.sqlite3`는 2026-10-18 보관 시점의 368건 SQLite입니다. 새 장치의 활성 DB로 복사하지 않습니다. 당시 사진은 포함되지 않아 과거 사진 링크는 열리지 않을 수 있습니다. 새 검사는 새 원장과 사진을 `data/`에 만듭니다.

## 3. Python 환경과 저장 사진 GPU 점검 — Jetson

기존 검증된 GPU 환경은 보존합니다. 환경이 필요한 새 장치에서만 시스템 TensorRT/GStreamer를 사용하는 격리 환경을 만듭니다.

```bash
python3.10 -m venv --system-site-packages ~/oned_device_bench/envs/app_v1
```

공식 호환표에 맞는 CUDA torch/torchvision을 해당 환경에 준비한 뒤 [requirements-runtime.txt](requirements-runtime.txt)의 웹/영상 의존성과 Ultralytics를 확인합니다. 설치 후보는 먼저 아래 dry-run으로 확인합니다.

```bash
~/oned_device_bench/envs/app_v1/bin/python -m pip install --dry-run -r jetson/requirements-runtime.txt ultralytics
```

기존 GPU torch/torchvision·시스템 패키지를 교체하는 계획이면 실행하지 않습니다. 충돌이 없는 설치 계획을 확인한 경우에만 같은 명령에서 `--dry-run`을 제거해 **새 환경에** 설치합니다. JetPack별 wheel이 달라 설치기가 임의의 torch 버전을 선택하지 않습니다. Windows/다른 Jetson의 venv 폴더는 복사하지 않습니다.

설치가 끝나면:

```bash
~/oned_device_bench/envs/app_v1/bin/python -B -X utf8 jetson/check_operating.py
~/oned_device_bench/envs/app_v1/bin/python -B -X utf8 ~/oned_device_bench/current/standalone_service.py --config ~/oned_device_bench/config/standalone.json --check-only
~/oned_device_bench/envs/app_v1/bin/python -B -X utf8 jetson/check_operating.py --gpu-smoke
~/oned_device_bench/envs/app_v1/bin/python -m pip freeze > ~/oned_device_bench/environment.freeze.txt
```

첫 검사는 CUDA 연산·torchvision CUDA NMS를, 두 번째는 설정/패키지 파일만 확인합니다. 세 번째는 개발용 self-test 사진으로 TensorRT2개·PyTorch5개를 GPU에서 실행하며 기존 서비스가 실행 중이면 거부합니다. 카메라·PLC를 열지 않습니다. 이 결과는 모델 호환성이며 새 장치 검사 정확도는 아닙니다. CPU fallback을 GPU 성공으로 세지 않습니다.

## 4. 새 카메라 기준 등록 — Jetson + 노트북 화면

설비는 실제 STOP으로 유지합니다. 먼저 기존 수동 기준 등록 화면만 실행합니다. 아래 명령은 **실제 카메라와 GPU를 사용하지만 물리 PLC에는 연결하지 않습니다**. `--plc-bench`나 `--mock-auto-request`를 추가하지 않습니다. systemd 서비스와 동시에 실행하지 않습니다.

```bash
~/oned_device_bench/envs/app_v1/bin/python -B -X utf8 ~/oned_device_bench/current/launch_live.py --package ~/oned_device_bench/assets/products/ENGINE_Z3005_5/dynamic_parts_005 --station ~/oned_device_bench/config/station.json --data-root ~/oned_device_bench/data/engine_dynamic_pose_002 --port 18771
```

노트북에서 아래 SSH 터널을 열고 `http://127.0.0.1:18771/`로 접속합니다.

```powershell
ssh -N -L 18771:127.0.0.1:18771 실제계정@192.168.50.2
```

STOP 상태에서 정상 엔진 전체가 실제 검사 위치의 화면 안에 보이도록 놓고 손을 뗍니다. 가시성 확인 → **기준 엔진 등록** → 저장된 원본과 LEFT/RIGHT PIPE·EXHAUST·SYMBOL 영역 확인 → **기준 엔진 확인** 순서로 진행합니다. 기준 후보의 `REVIEW`는 사람의 확인 대기이며 제품 PASS/FAIL 실적이 아닙니다. 오류 또는 후보가 없는 기록은 승인하지 않습니다.

같은 서버의 `http://127.0.0.1:18771/auto`에서 정지 상태로 검사영역 편집을 켜고 실제 검사 위치가 포함되도록 영역을 지정·확인하여 저장합니다. 이 영역은 새 기준 등록 해시와 연결됩니다. 운전/Mock START 버튼은 누르지 않습니다. 파일의 `confirmed` 값을 직접 바꾸지 않습니다.

설정을 마친 뒤 모형을 벨트 밖으로 내리고, Jetson의 위 수동 서버 터미널에서 **Ctrl+C**로 종료합니다. 이 과정의 기준 진단·새 원본3장·사람 확인·영역 기록은 새 `data/`에 남습니다. 과거 `history/`의 승인/검사 기록은 사용하지 않습니다.

## 5. 현장 설정과 서비스 등록 — Jetson

설비를 실제 STOP·빈 벨트 상태로 두고 카메라 고정·조명·엔진 전체 가시 범위와 PLC 계약을 확인합니다. 기준 이미지가 있어도 이전 장치의 구도 승인/성공 실적을 복사하지 않습니다. 최종 판정은 필수 부품 존재/미결합이며 오조립은 참고입니다.

확인할 기존 PLC 계약:

- Assembly100 Jetson→PLC:4byte, Result/Done 각 UINT16 BOOL. `Result=false` OK, `true` NG. Result 후 다음 주기에 Done.
- Assembly150 PLC→Jetson:8byte, `Inspection_Request`, `EStop_OK`, `Mc_Run`, `Stop_PB`. Configuration151:10byte. RPI50ms.
- `Stop_PB=true`는 운전 시 STOP 회로가 해제된 값입니다. `true`를 STOP 누름으로 재해석하지 않습니다. `EStop_OK=true`는 정상 회로입니다.
- 실제 START → 빈 벨트 운전 확인 → 모형 투입 순서입니다. PhotoSensor/Sensor_Ready는 PLC 내부 순서로 위 4개 입력과 별개입니다.
- Python 준비 신호400ms, 촬영3초/안정0.6초/새 원본3장, 요청·저장·중복 보호는 유지합니다.

세 조건을 실제 확인한 뒤 실행합니다. 설정 허가만 기록하며 PLC/모터를 직접 시작하지 않습니다.

```bash
~/oned_device_bench/envs/app_v1/bin/python -B -X utf8 jetson/install_operating.py --enable-plc --confirm-stopped --confirm-camera-setup --confirm-plc-contract
```

설치기는 정지된 서비스·종료된 수동 서버·실제 NIC 주소·카메라 노드를 확인합니다. 새 원장에서 현재 패키지/카메라의 기준 진단·사람 확인·원본3장 해시·확인된 검사영역을 읽습니다. 기준 진단 외 제품 검사 이력이 있거나 최초 설정이 이미 끝났으면 재설정을 거부합니다. DB 행이나 승인 사실을 만들어 넣지 않으며, 설정 전 사본을 보존하고 실제 새 기준 해시를 설정에 연결합니다. 새 장치 설정 ID는 `engine-install-*`, `source_release`는 계속 `engine-integrated-32c484ac6aeb07f1`이며 새 장치 실물 검증은 `NOT_VERIFIED`로 남습니다.

기존 unit/카메라 자동실행 cron이 없는지 확인하고 새 unit을 등록합니다. 이미 있는 unit은 덮어쓰지 않습니다.

```bash
test ! -e /etc/systemd/system/engine-inspector.service && sudo install -m 0644 ~/oned_device_bench/service/engine-inspector.service /etc/systemd/system/engine-inspector.service
sudo systemctl daemon-reload
sudo systemctl enable --now engine-inspector.service
systemctl status engine-inspector.service --no-pager
journalctl -u engine-inspector.service -n 80 --no-pager
```

다른 카메라 프로세스나 `manage_live.py start`를 함께 실행하지 않습니다. systemd `active`만으로 준비 성공이라 판단하지 말고 새 영상·모델 준비·PLC 연결·요청 대기를 확인합니다.

## 6. 화면·실물 확인·재부팅

노트북 PowerShell에서 호스트 지문을 확인한 뒤:

```powershell
ssh -N -L 18771:127.0.0.1:18771 실제계정@192.168.50.2
```

브라우저 **http://127.0.0.1:18771/line** → `검사 사진·이력`으로 조회합니다. 영상·추론·저장은 Jetson에서 실행되므로 노트북을 분리해도 계속 동작합니다. 터널 창을 닫으면 노트북 화면 연결만 끊깁니다.

새 장치에서 정상/알려진 결품을 각각 검사해 원본3장·판정/이유·SQLite·Result/Done·실제 배출을 대조합니다. 기존 장치7회 결과를 새 장치 시험으로 쓰지 않습니다. STOP·빈 벨트·검사/저장 유휴에서만 `sudo reboot` 후 자동 기동·새 영상·PLC 준비를 확인합니다. 기존의 간헐적 USB 영상 수신 실패가 이 복사 작업으로 해결됐다는 의미는 아닙니다.

수동 확인/종료:

```bash
systemctl status engine-inspector.service --no-pager
journalctl -u engine-inspector.service -n 80 --no-pager
sudo systemctl stop engine-inspector.service
```

원인 확인·복구 후 STOP·유휴에서만 `sudo systemctl reset-failed engine-inspector.service && sudo systemctl start engine-inspector.service`를 실행합니다. 시작 제한 초기화는 원인 수리나 기록 삭제가 아닙니다.

## 검증 범위

설치 검증은 파일 해시·원본 보존·장치 설정·손상 거부·Linux 파일 배치를 확인합니다. 새 Orin Nano 실제 GPU·카메라·PLC·재부팅은 **미실행**입니다. [검증 기록](../docs/verification/JETSON-PORTABLE-OPERATING-001.json)과 [모델 출처](products/README.md)를 참조하세요. 기존 소스/모델 이용 조건을 유지합니다.
