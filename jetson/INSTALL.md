# 새 Jetson Orin Nano에 설치

이 저장소에는 실제 운영 중인 부품/엔진 검출 TensorRT 모델과 필수 Pose 자산이 들어 있습니다. 모델을 따로 요청할 필요가 없습니다. 최초 설치 스크립트는 기존 설치와 데이터가 있으면 중단하고, 시스템 설정이나 PLC를 변경하지 않습니다.

## 1. 장치 환경

- Jetson Orin Nano, Linux aarch64, Python 3.10.
- TensorRT 10.3 및 CUDA 12.6을 제공하는 JetPack 6.2 계열. [NVIDIA JetPack 안내](https://developer.nvidia.com/embedded/jetpack-sdk-621).
- Python venv/pip, 시스템 TensorRT Python 바인딩, PyGObject, GStreamer의 `v4l2src/jpegdec/videoconvert/appsink`.
- USB 카메라의 1280×720 MJPG 30 FPS 모드와 장치 접근 권한. `/dev/v4l/by-id/`에서 실제 카메라를 선택합니다.

JetPack/OS는 운영자가 먼저 준비합니다. 설치 스크립트는 sudo, apt, 네트워크 설정, 서비스/cron 등록을 실행하지 않습니다. Python venv가 없으면 운영자가 `python3.10-venv`, 영상 구성요소가 없으면 `python3-gi`, `gir1.2-gst-plugins-base-1.0`, `gstreamer1.0-plugins-base`, `gstreamer1.0-plugins-good`의 설치 상태를 확인해야 합니다.

현재 장치의 관측 버전은 [environment.observed.json](environment.observed.json)에 있습니다. 기존 장치는 NumPy 호환 overlay를 사용하지만 새 설치는 자체 venv와 [고정 의존성](requirements-runtime.txt)을 사용합니다. NumPy 1.26과 패키지 의존성이 맞는 OpenCV 4.10/Pillow 10.4를 선택했으며, aarch64/Python 3.10 wheel 해석·다운로드 검증과 실제 Orin GPU 실행 검증을 구분합니다. 새 환경에서 GPU/카메라 실행은 아래 마지막 단계로 확인합니다.

## 2. 다운로드와 파일 검사

저장소 전체를 clone하거나 Download ZIP을 풀고 루트에서 실행합니다. 설치 파일은 `jetson/` 안에 있으므로 이 폴더만 다른 장치로 복사해도 설치할 수 있습니다.

```bash
python3.10 -B -X utf8 jetson/install.py --check-only
ls -l /dev/v4l/by-id/
```

첫 명령은 모델·Recipe·Pose 해시와 배포 목록을 확인합니다. Git LFS 포인터나 빠진 파일은 정상 모델로 인정하지 않습니다. 두 번째 결과 중 연결한 카메라의 `video-index0` 경로를 선택합니다. 다른 PC의 카메라 번호나 사용자명을 그대로 복사하지 않습니다.

## 3. 최초 설치

```bash
bash jetson/setup.sh /dev/v4l/by-id/실제카메라-video-index0
```

`실제카메라` 부분은 앞에서 확인한 경로로 바꿉니다. 기본 설치 위치는 로그인한 사용자의 `~/oned_device_bench`입니다. 다른 경로는 `ENGINE_INSTALL_BASE=/원하는/경로 bash jetson/setup.sh ...`로 지정합니다. 사용자명 `jetson`이나 노트북의 절대 경로를 가정하지 않습니다.

설치 과정: 파일 검증 → `envs/app_v1` venv → 고정 Python 의존성 → 환경 점검 → 파일별 해시 대조 → 새 장치 설정. 카메라나 서버를 자동 시작하지 않습니다. 오류 시 출력된 경로를 확인하고 보존된 임시 설치 자료를 조사합니다. 기존 `current/assets/config/data`는 덮어쓰지 않습니다.

Python 환경 준비 도중 중단됐다면 `setup.sh`는 남아 있는 환경을 자동 수정하지 않습니다. 이 설치에서 만든 환경임을 확인한 뒤 `~/oned_device_bench/envs/app_v1/bin/python -m pip install -r jetson/requirements-runtime.txt`로 준비를 마치고, 같은 Python으로 `jetson/install.py --camera /dev/v4l/by-id/실제카메라-video-index0`를 실행합니다. 기존 운영 장치 환경에는 적용하지 않습니다.

```text
~/oned_device_bench/
├── current/          실행 코드·HMI·release.json
├── assets/           제품 모델·Pose·공통 설정
├── config/           이 장치의 runtime.json·station.json
├── data/             새 장치의 Journal·Evidence
└── envs/app_v1/      이 장치의 Python 환경
```

소스 ZIP/clone은 설치 입력입니다. 설치 후 런타임은 `current`만 사용하며 소스 저장소, 노트북 공유 폴더, 이전 후보가 필요하지 않습니다. 소스·검증 이력은 노트북에 보관합니다. 설치기의 환경 점검은 TensorRT 바인딩·필요한 CUDA 라이브러리·GStreamer 플러그인 존재를 확인하며 모델의 실제 GPU 추론 성공을 대신하지 않습니다.

## 4. 시작과 확인

```bash
cd ~/oned_device_bench
envs/app_v1/bin/python -B -X utf8 current/manage_live.py start --config config/runtime.json
envs/app_v1/bin/python -B -X utf8 current/manage_live.py status --config config/runtime.json
```

Jetson 브라우저: **http://127.0.0.1:18771/auto**.

`/api/v1/release`의 실제 release ID, `/api/v1/health`의 카메라 준비 상태, 모델 시작 오류, 화면 영상을 확인합니다. 카메라 고정·초점·조명·검정 작업면·검사 영역을 해당 장치에서 확인하고 화면의 승인/운전 절차를 수행합니다. 이 과정 없이 다른 장치의 보정·승인 상태를 복사하지 않습니다.

최초 설치는 `MOCK` / `STATIONARY` / 물리 출력 비활성입니다. AUTO 시작은 화면에서 작업면을 확인한 뒤 선택합니다. 실제 PLC 연결은 별도 벤치 설정과 검증이 필요하며 기본 설치가 장비 출력을 허가하지 않습니다.

종료:

```bash
envs/app_v1/bin/python -B -X utf8 current/manage_live.py stop --config config/runtime.json
```

활성 검사·요청·저장이 있으면 관리기가 종료를 거부할 수 있습니다. 먼저 화면에서 정지하고 상태를 확인합니다. 기존 설치의 업데이트/복귀는 [노트북 배포 안내](../notebook/deployment/README.md)를 사용하며 최초 설치를 재실행해 덮어쓰지 않습니다.

## 다른 노트북에서 화면 열기

```powershell
ssh -N -L 18771:127.0.0.1:18771 실제사용자@Jetson주소
```

SSH 장치 지문을 확인하고 접속한 뒤 노트북의 `http://127.0.0.1:18771/auto`를 엽니다. 카메라·추론·DB는 Jetson에서 계속 실행됩니다. 편리한 바로가기와 로그인 터널 등록은 [Windows 안내](../notebook/README.md#jetson-운영-화면-접속)를 참조하세요.
