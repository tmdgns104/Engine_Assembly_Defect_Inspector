# GITHUB-DEPLOYMENT-001 — GitHub에서 두 장비로 설치

Status: PUBLISHED / CHECKOUT_VERIFIED / FRESH_HARDWARE_UNVERIFIED — 2026-09-30

## 요구와 범위

사용자는 발표용 GitHub 저장소를 현재 진척까지 갱신하고, Windows 노트북용 파일은 `notebook/`, Jetson Orin Nano용 실행 파일과 현재 모델은 `jetson/`에 포함해 다운로드 후 설치·실행할 수 있도록 요청했다. 현재 모델의 GitHub 포함도 명시적으로 요청했다.

기존 두 장비 구조를 유지한다. 현재 TensorRT 모델 두 개, 해당 Recipe·Pose·기동 검증 자산만 공개 실행 자산으로 포함한다. 촬영 원본 전체, 운영 DB, 개인 접속 설정, E04, 과거 후보와 기구 설계의 별도 작업은 포함하지 않는다. 기존 로컬 자산은 보존한다. 실제 Jetson/PLC 변경·재학습·모델 재빌드는 수행하지 않는다.

## 구현 계획

1. 모델·운영 자산을 `jetson/products`에 해시 그대로 포함하고 패키징 원본을 연결한다.
2. Jetson 최초 설치와 Windows 환경 준비/촬영 실행 경로를 추가한다. 기존 설치·데이터는 덮어쓰지 않고 새 설치의 PLC 기본값은 MOCK이다.
3. 발표 README에 실제 기능, 최신 벤치 결과, 알려진 미해결 사항, 장비/환경 조건과 설치 명령을 기록한다.
4. 로컬 전용 파일 없이 Git 스냅샷에서 자산·패키징·집중 회귀를 검증하고, 공개 파일/이력을 점검한 뒤 지정 GitHub에 반영한다.

## 수용 기준

- Git clone 및 GitHub ZIP에 두 현재 모델과 필요한 Pose/기동 자산이 실제 바이너리로 존재하며 SHA-256이 기존 manifest와 일치한다.
- 새 Windows 경로에서 촬영 코드와 안내 자산을 로드하고 집중 회귀가 통과한다.
- Jetson 설치 파일 검증·MOCK 기본값·기존 설치 덮어쓰기 거부를 검증한다. 새 물리 장치의 GPU/카메라 실행은 실제 수행하지 않았다면 UNVERIFIED로 남긴다.
- GitHub 공개 branch의 SHA가 로컬 출판 commit과 일치한다. 비밀/로컬 설정/운영 데이터/보호 자료는 추가하지 않는다.

## 검증 결과

지원 기준은 현재 Orin Nano의 TensorRT 10.3 / CUDA 12.6이다. 구형 Jetson Nano와 다른 TensorRT 환경은 같은 실행 계획의 호환 대상으로 주장하지 않는다.

- 원래 제품 자산 17파일을 복사하고 SHA-256을 대조했다. 모델 10,092,164 / 13,556,092 bytes를 일반 Git blob으로 포함했다.
- Git index에서 export한 깨끗한 소스로 Windows 집중 회귀 68건 PASS. Linux/WSL 배포 회귀 25건 PASS. 이후 설치 경로/환경 보존 보완은 최종 Linux 설치 5건 PASS로 확인했다.
- Linux 테스트는 실제 파일 복사, 111파일 해시, `current/config` 링크, `launch_live --check-only`, 기존 설치 거부까지 수행했다. x86_64 WSL이며 Orin GPU/카메라 검증은 아니다.
- aarch64/Python 3.10 의존성 wheel 전체 해석/다운로드 PASS. Windows Python 3.13 새 venv에 촬영 의존성 설치 PASS.
- 모델·Pose·해시를 가진 JSON의 CRLF 바이트는 `.gitattributes -text`로 보존한다. 소스의 LF 정규화로 배포 release ID는 `engine-dev-82b71a21ad98dda7`이며, 기존 장치의 `engine-dev-745e95e832c6b402`와 구분한다.
- 최종 구현 tree 공개 감사: 1,169 objects, 텍스트 blob 785개, credential pattern 발견 0, 대용량 제한 위반/압축파일/보호 자료 열람 0. `git diff --cached --check` PASS.
- 검증 중 별도 촬영 작업이 소스를 추가 수정했다. 이번 출판은 검증 snapshot으로 고정하고 이후 worktree 변경·기구 설계 작업은 보존한다. 별도 EXE는 build input과 snapshot 해시가 불일치해 새 배포로 업로드하지 않는다.
- 새 장치 실물 실행, 실제 컨베이어 연속 운전/기존 미해결 PLC·점유 문제는 UNVERIFIED/OPEN이다. 상세: `docs/verification/GITHUB-DEPLOYMENT-001.json`.

## GitHub 반영 확인

- 공개 `master` 구현 commit: `ce49b15ba67064f3651679cfa57280afca9bf4bb`. push 성공 후 `git ls-remote` SHA가 로컬과 동일했다.
- GitHub Contents API에서 두 model.plan의 실제 크기 10,092,164 / 13,556,092 bytes와 Git blob ID를 확인했다.
- [GitHub Actions 36658234340](https://github.com/tmdgns104/Engine_Assembly_Defect_Inspector/actions/runs/36658234340) SUCCESS: Ubuntu 22.04/Python 3.10 새 checkout·의존성 설치·모델/자산 검사·배포 회귀·bundle 생성·shell syntax.
- Windows 새 venv에서도 `pip check`와 촬영 GUI 집중 5건 PASS. 깨끗한 소스에서 만든 bundle은 111파일 / 21,229,569 bytes이며 파일별 해시를 다시 확인했다.
- 모델 포함 다운로드·새 설치 파일 검증·합성 회귀·원격 출판 기준은 PASS. 새로운 물리 장치의 GPU/카메라 수용은 여전히 UNVERIFIED이며 이 Task에서 기존 장비를 변경하지 않았다.
- 후속 완료 기록 commit은 문서만 갱신하며 이미 통과한 구현 CI를 반복하지 않는다.
