# Jetson 배포 도구 — 노트북에서 실행

`package_candidate.py`는 기존 후보 패키징 코드를 옮겨 정리한 것입니다. `runtime_allowlist.json`에 적힌 파일만 묶습니다. 압축파일 생성 후 모든 파일을 다시 읽어 SHA256을 확인합니다. 이 명령은 Jetson에 접속하거나 현재 프로그램을 교체하지 않습니다.

## 배포 묶음 만들기

프로젝트 루트에서 실행합니다. Python 표준 라이브러리만 사용합니다.

```powershell
python -B -X utf8 notebook/deployment/package_candidate.py --output dist/jetson/engine-runtime.tar.gz
```

같은 출력이 이미 있으면 덮어쓰지 않습니다. 개발 중 묶음은 `dist/jetson` 한 곳에서 관리하고, 실제 사용한 이전 릴리스는 노트북 `archives`로 보관합니다.

Git에는 바이너리 자산을 넣지 않습니다. 로컬 배포 묶음에는 다음 실제 의존성을 반드시 포함합니다. 파일 내용은 이번 정리에서 변경하지 않았습니다.

- `products/ENGINE_Z3005_5/dynamic_parts_005`: model.plan, manifest/recipe/설정, 기동 self_test.png, Pose reference JSON·D001 이미지·bank.
- `products/ENGINE_Z3005_5/envelope_v007_fp16`: 모델과 manifest/설정/기동 self-test. 두 제품 폴더의 상대 위치를 유지합니다.
- `jetson/config/area_references`: 현재 개발본에서 읽는 기준 이미지. **현 방식 채택은 보류 상태**이며 기준을 더 등록하라는 안내가 아닙니다.

필수 파일이 없으면 패키징은 실패합니다. Git clone 뒤 임의의 모델이나 빈 이미지로 대체하지 않습니다. 이미 보관한 해시 검증 배포 묶음에서 같은 자산을 복원합니다.

## Jetson의 목표 구조

```text
oned_device_bench/
├─ current/                  실행 Python·HMI·release.json 한 벌
│  └─ config -> ../assets/runtime_config
├─ assets/
│  ├─ runtime_config/        점유·MOCK 설정과 기준 이미지
│  └─ products/              모델·Recipe·Pose·기동 self-test
├─ config/
│  ├─ runtime.json           이 장치의 자산·설정·데이터·overlay 경로
│  └─ station.json           이 장치의 카메라 ID·station 설정
├─ data/                     신규 장치 Journal·Evidence·로그
├─ envs/app_v1/              확인된 실행환경; 코드 배포로 덮어쓰지 않음
├─ env_candidates/numpy_compat_001/overlay/  현재 실제 의존성; 보존
└─ tmp/verify/               필요한 Jetson 검증 동안만 임시 사용
```

기존 Jetson의 `live_data`는 그대로 둡니다. `runtime.json`의 `data_root`를 기존 위치에 연결할 수 있습니다. 운영 DB를 복사·초기화하거나 기존 이력 경로를 임의로 바꾸지 않습니다. 기존 데이터 경로 연결은 코드가 과거 후보를 import한다는 의미가 아닙니다.

`runtime.example.json`과 `station.example.json`을 읽고 **장치별** 설정을 코드 밖에 준비합니다. 예제 경로는 `oned_device_bench/config` 기준입니다. `station.json`의 카메라 by-id는 다른 장치에서 확인해야 합니다. 설정 예제를 복사해도 보정/빈 화면 승인 상태를 True로 만들지 않습니다.

## 확인·기동·종료

아래는 정상 설치 후 명령입니다. 현재 장비의 자동 교체 완료 명령으로 오해하지 마세요. 이번 소스 정리만으로 기존 실행 중 프로세스를 바꾸지 않았습니다.

```bash
cd /home/jetson/oned_device_bench
envs/app_v1/bin/python -B -X utf8 current/launch_live.py \
  --package assets/products/ENGINE_Z3005_5/dynamic_parts_005 \
  --station config/station.json --data-root data --check-only
envs/app_v1/bin/python -B -X utf8 current/manage_live.py start --config config/runtime.json
envs/app_v1/bin/python -B -X utf8 current/manage_live.py status --config config/runtime.json
envs/app_v1/bin/python -B -X utf8 current/manage_live.py stop --config config/runtime.json
```

`--check-only`는 파일·해시·MOCK 조건만 확인하며 카메라·추론·DB를 열지 않습니다. 실제 시작 후 `/api/v1/release`는 **시작 시 확인한** release ID와 경로·해시를 표시합니다. `/api/v1/health`의 camera_ready와 단독 Worker, 실제 모델 로드, 이력·저장·MOCK 기본 동작까지 확인해야 설치 완료입니다. AUTO 시작과 장면 승인은 별도이며 자동으로 수행하지 않습니다.

다른 Jetson의 JetPack/CUDA/TensorRT/GPU 조합이 같다고 가정하지 않습니다. 현 model.plan은 기존 Orin Nano, TensorRT 10.3 / CUDA 12.6 환경의 산출물입니다. 다른 환경의 기동·추론은 미검증이며 이 정리 과정에서 재빌드하지 않았습니다.

현재 장치에서 직접 확인한 Python·FastAPI·NumPy·OpenCV·TensorRT 버전은 [`environment.observed.json`](../../jetson/environment.observed.json)에 있습니다. 기존 `app_v1`과 NumPy overlay를 재사용하며, 이 관측 목록은 다른 Jetson의 자동 설치 스크립트가 아닙니다.

노트북 브라우저 연결은 SSH 키를 별도 보관한 뒤 기존 SSH 터널을 사용합니다.

```powershell
ssh -N -L 18771:127.0.0.1:18771 <user>@<jetson-address>
```

화면: `http://127.0.0.1:18771/auto`. 주소·키·사용자명은 Git에 고정하지 않습니다.

## 실제 교체와 복귀 조건

현재 후보의 종료 판정 채택이 보류되어 `current` 전환은 아직 실행하지 않았습니다. 검증된 배포 대상이 정해지면 기존 `verification/area_clearance/deploy_area.py`의 작업 중단 조건과 managed stop/start 순서를 유지하여 이 묶음을 설치합니다. **옛 deploy_area.py에 새 형식의 tar를 넘기지 않습니다.** 현재 버전은 옛 후보 형식만 받으며 단일 경로 설치 부분의 적용·실물 확인이 남아 있습니다.

교체 전에는 현재 실행 명령·해시, 활성 검사/요청/저장, 복구 묶음의 노트북 백업을 확인합니다. 정상 종료와 카메라 해제를 확인한 뒤 제한된 임시 공간의 패키지를 교체하고, 실패 시 직전 코드·설정·경로로 복귀합니다. 운영 데이터와 Python 환경은 교체 대상이 아닙니다.

기존 파일 삭제는 **노트북 백업 검증 + 새 실행본 확인 + 정확한 삭제 목록/용량 제시 + 사용자 1회 승인** 뒤에만 합니다. 노트북에만 이전 버전을 보관하므로 현장 즉시 복귀에는 노트북 또는 별도 전달한 복구 묶음이 필요합니다.
