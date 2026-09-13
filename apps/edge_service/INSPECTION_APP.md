# 공통 검사 앱 V1 — 실행과 인계

Windows에서 개발하며, 실제 카메라·PyTorch CUDA·원기록은 Jetson이 소유한다. Windows PC Service는 별도 SQLite 사본과 조회 화면만 소유한다. `bench_v001`은 변경하지 않은 복구 기준이다. 최종 실행 릴리스와 시험 결과는 `docs/verification/INSPECTION-APP-V1-20260914.json`을 본다.

## 접속과 실행

현재 검사 화면: **http://127.0.0.1:8768**. PC 기록 화면: **http://127.0.0.1:8769**.
화면은 SSH 터널/loopback 전용이며 토큰 없는 쓰기를 거부한다. 현재 운영자 세션 토큰이 정비·검사 권한도 갖는 단일 운영자 범위다. 다중 계정/RBAC는 구현 범위 밖이다.

Windows PowerShell (프로젝트 루트):
```powershell
& scripts/start_inspection_pc.ps1
& .venv/Scripts/python.exe -B -X utf8 scripts/inspection_client.py status
& .venv/Scripts/python.exe -B -X utf8 scripts/inspection_client.py packages
```
검사 화면 터널이 없을 때 한 번 실행한다. 이미 해당 포트를 소유한 SSH가 있으면 중복 실행하지 않는다.
```powershell
ssh -N -o BatchMode=yes -o IdentitiesOnly=yes -o ExitOnForwardFailure=yes -i "$env:USERPROFILE/.ssh/oned_device_jetson_bench_ed25519" -L 127.0.0.1:8768:127.0.0.1:8768 jetson@192.168.50.2
```
`start_inspection_pc.ps1`은 PC 수집기와 Jetson→PC 역방향 터널을 숨김 실행한다. 새 설치에는 공유 토큰 파일을 별도로 준비해야 하며, 현재 검증된 토큰은 두 장비의 data_root에만 있다. 토큰·DB·사진은 Git 대상이 아니다. 토큰을 채팅에 입력하지 않는다.

Jetson SSH 터미널:
```bash
cd /home/jetson/oned_device_bench/releases/app_v005
bash scripts/start_inspection_app.sh
```
유휴/요청 종료 확인 후 종료:
```bash
bash scripts/stop_inspection_app.sh
```
스크립트는 Service와 기록된 자식 프로세스의 종료까지 확인한다. 종료 확인 실패 시 다음 카메라 소유자를 시작하지 않는다. Windows PC 수집 종료는 `scripts/stop_inspection_pc.ps1`이다. 수집 중단은 Jetson 원기록을 삭제하지 않는다.

## 실제 검사 순서

1. 현재 미리보기에서 제품을 준비한다. 선택한 제품·기준 구도·모든 자리 가시성·손 제거를 사람이 확인한다.
2. `기준 사진 촬영`으로 표시된 기대 자리와 실제 부품을 확인한 뒤 `표시된 기준 자리 확인`을 누른다. 버튼은 사람 확인이며 자동 승인하지 않는다. 자리 위치가 맞지 않으면 검사하지 않고 Recipe/촬영 조건을 준비한다.
3. 준비 완료 후 `검사하기`. 현재 영상과 선택한 저장 결과는 별개다. 결과 상세의 당시 package·request·observations·assets를 확인한다.
4. 네 상태 실물 시험은 정상 → L 누락 → R 누락 → 양쪽 누락으로 사람이 한 번에 한 행동씩 진행한다. 현재 이 수용 시험은 대기다.

모든 기준이 확실할 때만 PASS, 수량 부족 근거가 있을 때 FAIL, 관찰/정렬/식별/검출 불확실이면 REVIEW, 카메라·모델·저장 실패는 ERROR다. 같은 클래스의 여러 자리/수량을 지원하며 검출 하나를 여러 자리로 세지 않는다. 가시성은 사람 보조 모드이며 손·가림·닫힌 뚜껑·제품 방향 자동 인식은 미검증이다. 보이는 자리의 확정 불량과 다른 자리의 미확인을 함께 기록한다.

## 제품 교체

`config/products/<제품>/`의 classes/preprocessing/recipe/capture를 준비하고 신뢰한 모델·대표 원본을 새 버전 폴더로 묶는다.
```powershell
& .venv/Scripts/python.exe -B -X utf8 -m scripts.build_product_package --documents <설정폴더> --model <모델.pt> --self-test <대표원본.png> --output <새릴리스폴더> --product <제품ID> --release <릴리스ID> --model-version <모델버전>
```
출력이 이미 있으면 덮어쓰지 않는다. 현재 지원: PyTorch detect/Ultralytics xyxy, FP32 RGB/255 letterbox, top-view MJPG 카메라, presence_count. 다른 출력·정밀도·전처리·검사 알고리즘은 명시적 Adapter 확장이 필요하다. 입력 크기는 패키지의 `[height,width]`에서 읽는다.

검증된 로컬 목록에서 선택하거나 동일 CLI를 사용한다.
```powershell
& .venv/Scripts/python.exe -B -X utf8 scripts/inspection_client.py activate earbud_case_v0/app_v001
```
진행 중 검사·Mock 사이클·ACK 대기에서는 교체하지 않는다. 구 Worker 종료 확인 → 새 모델 실제 로딩/자체 점검 → 전체 패키지 선택 저장 순서다. 실패하면 구 패키지 전체 복원을 시도하며 실패 상태에서는 READY가 아니다. 세션은 바뀌고 패키지/촬영/Recipe/설비에 맞는 기준 확인이 필요하다. 기록은 당시 사본을 유지한다. 새 프로세스는 마지막 성공 선택을 읽는다.

ENGINE_Z3005_5는 모델·슬롯 미준비로 비활성이다. ENGINE_Z3005_3은 별도 제품이다. 다른 이름·4클래스·동일 클래스 2자리/수량2+1 fixture 시험은 공통 코드 시험이며 엔진 실물 성능이 아니다.

## 원기록과 PC 수집

- Jetson: `/home/jetson/oned_device_bench/data/app_v1/journal.sqlite3`, `assets/<inspection_id>/`, `logs/`.
- PC: `D:\OneDevice_Team_project\runs\inspection_app_v1\pc\journal.sqlite3`, `assets/`와 수집 로그.
- 원래 BENCH 기록: `/home/jetson/oned_device_bench/releases/bench_v001/runs/bench_live/inspections/` 그대로 보존.
- 실행 증거: Windows `runs/inspection_app_v1/`. 검토·원본·모델 바이너리는 Git에 올리지 않는다.

Service만 원장 writer다. 원본 영속화 → 결과/asset/event/outbox SQL commit 후 조회된다. 파일과 SQLite가 단일 트랜잭션은 아니므로 고아 파일/미완료 요청을 보존·식별한다. SQLite WAL/FK/FULL, 원결과 불변, request 복합키와 전체 본문 충돌 검사, outbox 상한/디스크 하한을 사용한다. 자동 원본 삭제 OFF다. 백업은 서비스를 종료한 뒤 data_root 전체 또는 SQLite backup API와 연결 자산을 사용한다. 실행 중 `.sqlite3` 하나만 복사하지 않는다.

PC 이벤트 ACK는 이미지 ACK와 다르다. 이미지 전송 전에는 SYNC_PENDING. 동일 ID/내용은 한 번만 집계하고 변조는 quarantine으로 분리한다. PC 장애는 제한 내 outbox 재전송으로 복구한다. 현재 화면은 PC가 실제 장비 READY를 관측하지 않았다고 명시한다. UTC 저장/한국 시각 표시. `attempts`에는 기준 촬영도 포함되므로 생산 검사 수는 `inspection_attempts`와 구분한다. `released`와 `mock_released`도 별개다.

## Mock와 복구

Mock 제어는 실제 PLC/모터를 쓰지 않는다. 복구 확인 → 매 제품 START → POSITIONING → SETTLING → WAIT_RESULT → RELEASE/HOLD/FAULT → 가상 처리 종료 → 종료 기록 ACK → IDLE다. START 유지나 통신 복구로 다음 제품을 만들지 않는다. 사람 가시성 확인 없이 실물 Mock START를 수행하지 않는다.

RESULT_ACK: 결과 한 번 소비. CYCLE_ACK: 가상 처리 종료를 Edge 원장에 저장. PC ACK: PC DB/이미지의 독립 수신 확인. FAIL/REVIEW는 HOLD 후 회수/격리, ERROR는 FAULT 후 ABORTED다. 원 AI 판정은 처분과 별도로 남는다. Mock RELEASED는 실제 배출이 아니다. 취소 접수와 Worker 종료는 구분하고, 늦은 PASS는 게시하지 않는다. 재시작 후 미종료 Mock 사이클은 명시적 복구로 ABORTED 처리하며 자동 START하지 않는다.

## 검증 범위와 미완료

실제 Jetson GPU·USB 진단 촬영·PNG/SQLite 조회·PC 중단/복구 전송·같은 Baseline 재활성화·Service/Worker 종료를 시험했다. Worker 강제 종료, 잘못된 패키지 복원, ACK 유실/늦은 결과/timeout은 명시적 fixture 시험이다. 브라우저 실제 렌더링·사람 기준 자리·네 상태 수용·물리 USB 단절·실물 Mock 사이클은 대기다. B04·추가 학습·ONNX/TensorRT·실 엔진·실 PLC는 실행하지 않았다.

성능: 구 버전 `inspection_total_ms`는 저장 전 Worker 결과 수신 시점이었으므로 전체 검사 지연으로 쓰지 않는다. 새 버전의 `INSPECTION_DURABLE_TIMING` 이벤트는 Edge 단조 시계로 DB commit 완료까지 측정한다. PC와 Jetson 시각을 빼지 않는다. 진단 n=3은 작은 개발 관측이며 정상 제품의 P95 수용 시험을 대신하지 않는다.
