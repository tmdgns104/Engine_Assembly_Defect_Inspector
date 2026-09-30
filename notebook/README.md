# 노트북에서 쓰는 코드

노트북은 개발·촬영·데이터 준비·학습·패키징을 맡습니다. Jetson의 실제 검사 기능은 [`../jetson`](../jetson/README.md)에 있습니다.

| 위치 | 역할 / 시작점 |
|---|---|
| [`start_capture.cmd`](start_capture.cmd) | 기존 Engine Dataset Wizard V1을 실행하는 Windows 바로가기 |
| [`OPEN_ENGINE_HCAM.cmd`](OPEN_ENGINE_HCAM.cmd) | Jetson `current` 확인 → SSH 터널 → 기존 `/auto` 화면. Jetson 부팅 AUTO는 장치에서 관리 |
| [`training/capture_windows/__main__.py`](training/capture_windows/__main__.py) | 인자 처리 → Tk 화면 생성 → 종료 |
| [`training/capture_windows/wizard_app.py`](training/capture_windows/wizard_app.py) | 촬영 화면과 사용자 동작 |
| [`training/capture_windows/camera.py`](training/capture_windows/camera.py) | 노트북 USB 카메라의 연결·프레임 수신 |
| [`training/capture_windows/wizard.py`](training/capture_windows/wizard.py) | 수집 시작·저장·재개 |
| [`training/capture_windows/engine_exports.py`](training/capture_windows/engine_exports.py) | 원본을 보존하는 라벨링 인계·내보내기 |
| `training/datasets/` | 제품·촬영 순서 JSON. 촬영 이미지 폴더가 아님 |
| `training/scripts/` | 데이터 검증·라벨 변환·학습/평가 도구. 명시적으로 실행할 때만 작동 |
| [`deployment/`](deployment/README.md) | Jetson 운영 파일을 목록에 따라 묶는 노트북 전용 도구 |
| [`deployment/maintain_tunnel.ps1`](deployment/maintain_tunnel.ps1) | 노트북 로그인 중 유선 우선·Tailscale 대체 SSH 터널을 유지. 카메라·검사는 실행하지 않음 |
| `tests/` | 합성 입력으로 실행하는 기존 촬영 도구 시험. Jetson 배포 제외 |

호출 순서는 `start_capture.cmd → __main__.py → WizardApp → Collection/CameraClient → 저장·내보내기`입니다. 촬영 도구는 AI 자동 검사 화면이 아니며, 처음 시작할 때 카메라나 촬영을 자동 시작하지 않습니다.

## 다른 노트북에서 실행

저장소 전체 ZIP을 풀거나 clone한 뒤 **`setup_capture.cmd`를 한 번 실행**하세요. Python 3.13 x64(Tcl/Tk·Python launcher 포함)가 필요합니다. 설치 후 `start_misassembly.cmd`는 최신 간편 촬영, `start_capture.cmd`는 기존 Wizard V1을 엽니다. 카메라 영상·해상도·촬영자·저장 위치를 최초 설정에서 지정합니다. 간편 촬영의 새 기본 계획은 10° 간격 총 654장이고, 기존 수집은 원래 계획을 유지합니다. 두 앱의 원장/검토 절차는 구분합니다.

Windows x64 Python 3.13의 Tk 지원과 [촬영 의존성](requirements-capture.txt)이 필요합니다. 현재 작업 PC에서 확인된 버전이며, 다른 PC에서 카메라 동작까지 검증했다는 뜻은 아닙니다.

```powershell
cd notebook
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-capture.txt
.\start_capture.cmd
```

이미 프로젝트 루트의 `.venv`가 있으면 바로가기에서 그것을 재사용합니다. 설치는 운영자가 위 명령을 선택할 때만 수행하며, 실행기가 의존성을 자동 설치하지 않습니다.

새 촬영의 기본 저장 위치는 `notebook/data/engine/raw`입니다. **기존 프로젝트의 `data/engine/raw`는 이동하거나 지우지 않았습니다.** 기존 수집은 원래 폴더에서 이어 엽니다. 필요하면 `start_capture.cmd --output-root <기존 원본 폴더>`로 지정하세요. 두 PC가 같은 수집 폴더를 동시에 수정하지 않습니다. E04/Test Reserved는 보호합니다.

학습은 별도 GPU 환경·자료·명시적 설정이 필요합니다. 이번 폴더 정리에서 재학습, 모델 변환, EXE 재빌드는 하지 않았습니다. `training/scripts`의 학습 설정 경로는 해당 명령을 실행하기 전에 실제 입력에 맞춰 확인합니다.

현재 AI 검사용 모델은 [`../jetson/products`](../jetson/products/README.md)에 포함되어 있습니다. 노트북 촬영 앱은 이 TensorRT 모델을 실행하지 않습니다. 간편 촬영의 안내 사진/계획은 `training/capture_windows/assets`에 포함됩니다. 최신 촬영 소스 및 기존 EXE의 검증 범위는 [Task](../tasks/ENGINE-MISASSEMBLY-CAPTURE-001.md)를 참조하세요.

## Jetson 운영 화면 접속

Jetson 설치 및 서버 시작을 먼저 완료합니다. 별도 촬영 Python 환경 없이도 Windows OpenSSH와 브라우저로 화면을 볼 수 있습니다.

```powershell
ssh -N -L 18771:127.0.0.1:18771 실제사용자@Jetson주소
```

호스트 지문을 확인하고 인증하면 `http://127.0.0.1:18771/auto`를 엽니다. 이 SSH 창을 닫으면 화면 연결은 끊어지지만 Jetson의 서버는 계속 실행됩니다.

키 기반 바로가기는 `deployment/device.example.json`을 `deployment/targets/current.json`으로 복사한 뒤 실제 SSH 주소·사용자·기존 키 경로·Jetson 설치 경로를 입력하고 `OPEN_ENGINE_HCAM.cmd`를 실행합니다. 기본 사용자 `jetson`이 아닌 장치는 `remote_base`도 수정하세요. 개인 키와 실제 주소는 커밋하지 않습니다. 로그인 자동 터널 등록은 선택 사항이며 [배포 안내](deployment/README.md)에 있습니다.

경로 정리 확인에 사용한 기존 시험:

```powershell
.venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests -p test_engine_portable.py -v
```

Git에는 `data`, `logs`, 운영 DB, 배포 압축파일을 넣지 않습니다. 현재 승인된 공개 범위의 실행 모델만 `jetson/products`에 포함합니다. 장치별 SSH 키·접속 설정은 별도로 관리합니다.
