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
- `jetson/config/area_clearance.json`: 현재 검정 작업면 점유 설정. 고정 빈 기준 이미지를 읽지 않으며 다른 작업면에서 동일 성능은 미검증입니다.

필수 파일이 없으면 패키징은 실패합니다. Git clone 뒤 임의의 모델이나 빈 이미지로 대체하지 않습니다. 이미 보관한 해시 검증 배포 묶음에서 같은 자산을 복원합니다.

## Jetson의 목표 구조

```text
oned_device_bench/
├─ current/                  실행 Python·HMI·release.json 한 벌
│  └─ config -> ../assets/runtime_config
├─ assets/
│  ├─ runtime_config/        점유 설정과 실제 참조 자산
│  └─ products/              모델·Recipe·Pose·기동 self-test
├─ config/
│  ├─ runtime.json           이 장치의 자산·설정·데이터·overlay 경로
│  └─ station.json           이 장치의 카메라 ID·station 설정
├─ data/                     신규 장치 Journal·Evidence·로그
├─ envs/app_v1/              확인된 실행환경; 코드 배포로 덮어쓰지 않음
├─ env_candidates/numpy_compat_001/overlay/  현재 실제 의존성; 보존
└─ tmp/verify/               필요한 Jetson 검증 동안만 임시 사용
```

현재 Jetson은 정상 종료 뒤 `live_data` 전체를 노트북에 백업하고 `data/engine_dynamic_pose_002`로 옮겼습니다. SQLite와 Evidence를 함께 보존했고 검사 88건·이미지 352건의 DB 행이 백업과 동일합니다. `runtime.json`의 `data_root`는 이 위치를 가리킵니다. 다른 기존 장치를 옮길 때는 그 장치의 데이터를 별도로 백업하며 현재 장치 DB를 복제해 시작하지 않습니다.

`runtime.example.json`과 `station.example.json`을 읽고 **장치별** 설정을 코드 밖에 준비합니다. 예제 경로는 `oned_device_bench/config` 기준입니다. `station.json`의 카메라 by-id는 다른 장치에서 확인해야 합니다. 설정 예제를 복사해도 보정/빈 화면 승인 상태를 True로 만들지 않습니다.

## 확인·기동·종료

현재 장치에서 확인한 관리 명령입니다. `current`의 실제 릴리스는 `engine-dev-1203e23f30adda37`이며, 실제 PLC 세 BOOL 태그만 쓰는 벤치 시험 모드입니다.

```bash
cd /home/jetson/oned_device_bench
envs/app_v1/bin/python -B -X utf8 current/launch_live.py \
  --package assets/products/ENGINE_Z3005_5/dynamic_parts_005 \
  --station config/station.json --data-root data/engine_dynamic_pose_002 --check-only --plc-bench
envs/app_v1/bin/python -B -X utf8 current/manage_live.py start --config config/runtime.json
envs/app_v1/bin/python -B -X utf8 current/manage_live.py status --config config/runtime.json
envs/app_v1/bin/python -B -X utf8 current/manage_live.py stop --config config/runtime.json
```

`--check-only`는 파일·해시·선택한 Gateway 조건만 확인하며 카메라·추론·DB를 열지 않습니다. 실제 시작 후 `/api/v1/release`는 **시작 시 확인한** release ID와 경로·해시를 표시합니다. `/api/v1/health`의 camera_ready와 단독 Worker, 실제 모델 로드, 이력·저장·선택한 Gateway 동작까지 확인해야 설치 완료입니다. AUTO 시작은 별도이며 자동으로 수행하지 않습니다.

다른 Jetson의 JetPack/CUDA/TensorRT/GPU 조합이 같다고 가정하지 않습니다. 현 model.plan은 기존 Orin Nano, TensorRT 10.3 / CUDA 12.6 환경의 산출물입니다. 다른 환경의 기동·추론은 미검증이며 이 정리 과정에서 재빌드하지 않았습니다.

현재 장치에서 직접 확인한 Python·FastAPI·NumPy·OpenCV·TensorRT 버전은 [`environment.observed.json`](../../jetson/environment.observed.json)에 있습니다. 기존 `app_v1`과 NumPy overlay를 재사용하며, 이 관측 목록은 다른 Jetson의 자동 설치 스크립트가 아닙니다.

노트북은 `device.example.json`을 Git 제외 경로 `targets/current.json`으로 복사해 실제 주소·기존 키 경로를 채운 뒤 `notebook/OPEN_ENGINE_HCAM.cmd`를 실행합니다. 내부 `open_live.ps1`은 현재 실행 경로와 release ID가 맞는지 확인합니다. 키를 새로 만들거나 보안 정책을 바꾸지 않습니다. 기존 `runs/engine_dynamic_pose_002/OPEN_ENGINE_HCAM.cmd`도 현재 바로가기로 연결했습니다. 수동 터널 명령은 다음과 같습니다.

```powershell
ssh -N -L 18771:127.0.0.1:18771 <user>@<jetson-address>
```

화면: `http://127.0.0.1:18771/auto`. 주소·키·사용자명은 Git에 고정하지 않습니다.

## 실제 교체와 복귀 조건

`deploy_area.py`는 기존 area 배포기의 해시·정상 종료·카메라 소유 확인을 재사용합니다. 최초 설치와 기존 `current` 업데이트를 구분합니다. 최초 설치 모드는 `current/assets/config`가 이미 있으면 덮어쓰지 않고 중단합니다.

새 장치 최초 설치 순서는 노트북 패키징 → `tmp/deploy`에 패키지·이 배포기·장치 설정만 업로드 → 기존 관리 경로 정상 종료/카메라 해제 → 보존할 데이터와 환경 준비 → 아래 명령입니다. archive SHA와 station 내용은 배포 대상에 맞게 확인합니다. `station.example.json`과 다른 카메라 설정은 해당 장치용 묶음에 반영해야 합니다.

```bash
envs/app_v1/bin/python -B -X utf8 tmp/deploy/deploy_area.py \
  --base /home/jetson/oned_device_bench \
  --archive tmp/deploy/engine-runtime-layout-001.tar.gz --sha256 <노트북에서 확인한 SHA256> \
  --station <기존 장치 station.json> --runtime-settings tmp/deploy/runtime.json
```

이미 `current`가 있는 장치에서는 활성 검사·요청·저장을 확인하고 managed stop 후, 노트북에 직전 release 패키지를 보존한 상태로 `--update-current`를 사용합니다. 임시 업로드 경로는 `tmp/deploy` 한 곳이며, 업데이트 설정은 기존 `runtime.json`에서 `plc_bench` 선택만 달라질 수 있습니다. 배포기는 코드 해시와 보존 자산을 확인하고 직전 `current`를 임시 복구본으로 둡니다. 새 release로 managed start·camera_ready·Gateway·HMI·이력 경로를 확인한 뒤 임시 복구본/업로드 파일을 노트북 백업과 대조해 정리합니다.

```bash
envs/app_v1/bin/python -B -X utf8 tmp/deploy/deploy_area.py \
  --base /home/jetson/oned_device_bench \
  --archive tmp/deploy/PACKAGE.tar.gz --sha256 SHA256_FROM_PC \
  --runtime-settings tmp/deploy/runtime.json --update-current
envs/app_v1/bin/python -B -X utf8 current/manage_live.py start --config config/runtime.json
```

교체 전에는 현재 실행 명령·해시, 활성 검사/요청/저장, 복구 묶음의 노트북 백업을 확인합니다. 정상 종료와 카메라 해제를 확인한 뒤 제한된 임시 공간의 패키지를 교체하고, 실패 시 직전 코드·설정·경로로 복귀합니다. 운영 데이터와 Python 환경은 교체 대상이 아닙니다.

현재 장치의 복귀 자료는 노트북 `archives/jetson/runtime_only_inventory.json`의 원본 경로→백업 tar member/기존 PC 파일 대응표에 있습니다. 종료된 현재 코드·설정을 보존한 뒤 필요한 직전 코드·모델·설정만 그 대응표로 복원하고, 같은 현재 운영 데이터를 연결하여 기동합니다. 예전 DB 백업으로 현재 DB를 덮어쓰지 않습니다. 이번 경로 전환 직전으로 되돌리는 경우 기존 `candidates/engine_dynamic_pose_002/manage_live.py start`를 사용하며 `live_data`는 현재 데이터 위치로 연결해야 합니다. DB 백업 tar는 장애 복구용이며 코드 rollback 때 자동 복원하지 않습니다.

기존 파일 삭제는 **노트북 백업 검증 + 새 실행본 확인 + 정확한 삭제 목록/용량 제시 + 사용자 1회 승인** 뒤에만 합니다. 노트북에만 이전 버전을 보관하므로 현장 즉시 복귀에는 노트북 또는 별도 전달한 복구 묶음이 필요합니다.

2026-09-28 정리 결과: 승인 목록 34,141개 항목 삭제, 실제 여유 공간 약 58.17GB → 79.64GB. `candidates`에는 이력 보존 대상 데이터 407파일만 남겼으며 실행 코드가 없습니다. `diagnostics`·`build_staging`에는 파일 없는 옛 디렉터리만 남아 있습니다. 미승인 경로를 추가 삭제하지 않았습니다. `tmp`는 비어 있고 `envs/app_v1`·NumPy overlay는 실제 사용 중이므로 보존합니다. 운영 코드의 옛 후보 경로 의존은 확인되지 않았습니다.
