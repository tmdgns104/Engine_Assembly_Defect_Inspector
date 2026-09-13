# JETSON-BENCH-001 실행 인계

현재: **Jetson 저장 사진 GPU smoke4장 및 USB 미리보기 READY. 사람 기준 자리/실제 네 상태 시험 대기.**
사용자 최신 범위에 따라 기존 Baseline만 사용한다. 전체 DB/MES/PLC는 후속이다.

## Windows에서 지금 할 일

이미 SSH 터널이 실행 중이다. 브라우저에서 **http://127.0.0.1:8767** 을 연다.
브라우저 자동 조작 연결은 없어 실제 렌더링은 사람 확인 대기다.
현재 영상 확인 후 양쪽 부품을 정상 자리에 넣은 열린 케이스를 화면 중앙에 놓고 카메라를 고정한다.
촬영 조건 체크→`정상 기준 자리 촬영`→보라색 자리/실물 일치 확인→`보라색 기준 자리 확인 완료` 순서로 기준을 정한다.
이후 각 검사마다 열린 케이스/두 자리 가시성/손 제거만 체크하고 `검사하기`를 누른다. 정답 상태를 앱에 입력하지 않는다.
실물 시험은 NORMAL → L 누락 → R 누락 → 양쪽 누락. 물체 배치는 한 단계씩 안내한다.

### 터널을 다시 열어야 할 때만 (Windows PowerShell)

```powershell
ssh -N -o BatchMode=yes -o IdentitiesOnly=yes -o ExitOnForwardFailure=yes -i "$env:USERPROFILE/.ssh/oned_device_jetson_bench_ed25519" -L 127.0.0.1:8767:127.0.0.1:8767 jetson@192.168.50.2
```

현재 터널 PID는 `runs/jetson_bench_001/tunnel_v001.pid`에 있다. 수동 터널은 Ctrl+C로 종료한다.
Jetson 주소는 이번 접속에서 확인한 값이며 다른 연결에서는 다시 확인한다.

### 인증 준비 이력 (완료, 반복 실행 불필요)

PowerShell에서 아래 한 명령을 실행한다. OpenSSH 비밀번호는 터미널에만 입력한다.
전용키를 생성하고 기존 authorized_keys를 보존하며 공개키를 추가한다.
호스트키 검증은 그대로 유지한다. 현재 실행 중인 SSH 프로세스에서 확인한 주소이며 영구 주소라고 가정하지 않는다.

```powershell
D:\OneDevice_Team_project\.venv\Scripts\python.exe -B -X utf8 D:\OneDevice_Team_project\scripts\connect_jetson_bench.py jetson@192.168.50.2
```

이 도우미는 키 생성 후 비밀번호 인증이 거절됐다. 사용자가 기존 Jetson 터미널에서 공개키를 등록해 현재 키 인증은 실제 성공했다. 비밀번호를 코드·채팅·로그에 저장하지 않는다.

## Jetson에서 시작·종료

기존 Python3.10 + PyTorch2.8.0 CUDA12.6 + Ultralytics8.4.118 + OpenCV4.8.0/GStreamer 사용. 추가 패키지 설치0.
대상 디렉터리: `/home/jetson/oned_device_bench/releases/bench_v001`.

```bash
cd /home/jetson/oned_device_bench/releases/bench_v001
bash scripts/start_jetson_bench.sh
```

시작 명령은 이미 실행 중이면 거부한다. READY는 `/api/status`로 별도 확인한다. 종료:

```bash
cd /home/jetson/oned_device_bench/releases/bench_v001
bash scripts/stop_jetson_bench.sh
```

시작·종료·재시작 명령을 실제 확인했다. 재시작 시 물리 구도 보장을 위해 기준 자리 확인은 다시 필요하다.
카메라 단절 시 ERROR로 유지하며 자동 재연결/재판정하지 않는다. 연결 복구 후 위 명령으로 중지·시작한다.
로그: `runs/bench_live/service.*.log`; 원본/검사 기록: `runs/bench_live/inspections/<request_id>/`.
저장 성공한 요청은 원본 PNG3장·overlay.jpg·result.json을 보존한다. 저장 오류는 PASS 게시를 차단한다. DB 완료를 뜻하지 않는다.

## 준비된 파일

- `scripts/probe_jetson_bench.py`: Jetson에서 실제 실행한 환경/실제 CUDA 연산/카메라 노드·포맷 점검.
- `scripts/prepare_jetson_bench.py`: 원래 Baseline 해시/클래스/기존 ONNX 구조와 B03 네 대표 원본을 검증한다. 기존 출력 덮어쓰기 거부.
- `runs/jetson_bench_001/staging_v001/manifest.json`: 모델과 원본 해시, ONNX 입력/출력.
- 같은 폴더 `smoke_expectations.json`: 평가 코드만 사용할 provenance/기대 상태. Detector에 전달하지 않는다.
- 원본 Baseline: `training/experiments/earbud_case_v0_20260913_v001/baseline/weights/best.pt`.

실제 환경/저장 사진 결과/USB 타임스탬프는 Windows의 `runs/jetson_bench_001/`에도 보존한다. 모델과 배포 소스8개 해시 일치 확인. 제품 설정과 사람이 확인한 검사 자리는 모델 입력 ROI crop과 별개다.

## 현재 검증

Windows 준비 집중 테스트3개, Windows/Jetson 계약19개씩, BENCH 집중11개씩 통과. 모델 SHA256은 원래 baseline_result와 일치한다.
ONNX FP32 입력 `[1,3,640,640]`, 출력 `[1,7,8400]`, NMS 노드0.
ONNX 메타데이터 확인은 parity가 아니다. PT 경로이므로 ONNX parity/TensorRT는 NOT_RUN.
Jetson PT 대표4장 smoke 및 실제 USB 미리보기·증가 PTS12개 PASS. 첫 추론5888ms/이후3장52~59ms는 cold/warm 구분한 소수 smoke 관측이며 정식 벤치마크가 아니다.
실제 사람 기준 자리·USB 네 상태 판정/저장·물리 단절·실제 중복 HTTP 요청 시험은 대기다. 소프트웨어 테스트의 중복/저장오류 PASS와 구분한다.
