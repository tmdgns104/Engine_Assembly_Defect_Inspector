# JETSON-BENCH-001

Status: IN PROGRESS — 2026-09-13 사용자 최신 요청 우선.

Latest checkpoint (09-13 → 09-14): SSH 인증 해결. 기존 Jetson PyTorch CUDA 경로 실제 B03 대표4장 smoke PASS. USB 미리보기 READY 및 소스 PTS12개 증가 확인. 최소 웹/판정/파일 기록 구현, Windows·Jetson 계약19개/집중11개 각각 PASS, 배포8파일 해시 일치. 서비스와 SSH tunnel 실행 중. 사용자 브라우저 확인→정상 기준 자리→실물4상태/단절/중복 검사 대기. 이전 인증 대기 기록은 아래 이력으로 보존한다.

Evidence: docs/verification/JETSON-BENCH-001-20260913.json, runs/jetson_bench_001/smoke_v001/result.json, camera_timestamp_check.json, deployed_checksums_and_tests.txt.
실제 모델/원본을 Jetson에서 처리했으며 ONNX/TensorRT는 사용하지 않았다. DB 없음. 추가 학습/B04/엔진/PLC 시험 없음.

목표: Windows 브라우저에서 Jetson USB 미리보기와 실제 GPU 검사 결과를 확인한다.
순서: 기존 Baseline 검증 → Jetson 환경/단일 GPU backend → B03 대표 원본 네 장 smoke → USB BENCH 화면 → 사람 배치 네 상태 및 단절/중복 요청 시험.

범위: Camera/Detector 계약을 재사용한 최소 adapter, 제품 설정, 단일 camera/model worker, 로컬 바인딩 웹 화면, 요청별 PNG/JSON 기록, 배포/종료 안내와 관련 테스트.
제외: 재학습/ROI 추가실험/B04/전체 MES·DB복제·PLC/CAD/전역 정책 수정. DB·PLC는 후속 요구로 유지한다.

수용 기준:
- 원래 baseline_result의 best.pt SHA256 일치, 대상 전송 해시 확인.
- Jetson GPU 실행 및 provenance로 선정한 B03 네 장 smoke 기록. ONNX 경로를 사용하지 않으면 parity 미실행.
- 단일 worker가 모델/카메라 소유, 새 프레임·중복 요청 거부·단절 오류·저장 실패 처리.
- 설정 기반 자리 판정, 사용자 가시성 확인과 한계 표시, 판정/검출 분리.
- 노트북 브라우저 실제 화면과 정상/L누락/R누락/양쪽누락 결과 및 저장 파일 확인.
- 자동 테스트와 실제 장비 검증을 구분. 접속 불가 시 최소 준비까지만 하고 실제 실행은 대기.

현재: Baseline 해시 일치. 기존 ONNX FP32[1,3,640,640] → [1,7,8400], 클래스3개·NMS 노드0. ONNX checker/세션 메타데이터 확인, 추론/parity 미실행. B03 BASE CENTER 네 상태 원본4장과 분리된 평가 정답 준비.

현재 실행 중인 SSH 프로세스에서 대상 경로를 찾았지만 BatchMode 인증1회 거절. 전용키 추가용 scripts/connect_jetson_bench.py 사용자 터미널 실행 대기. 키 생성·대상 권한 변경은 아직 실행하지 않았다. 환경과 GPU backend 미확정, 실제 장비·웹 화면 미검증.

검증: 프로젝트 .venv Python으로 `-B -X utf8 -m unittest discover -s tests -p test_jetson_bench_prepare.py -v` → 3 PASS. 첫 모듈 지정 실행은 tests가 package가 아니어서 import 실패했고 discovery로 수정했다. 구문/키 추가 명령의 보존성/실제 staging 해시·provenance·정답 분리 검증 범위이며 SSH 동작 검증은 아니다.

다음: 전용키 BatchMode 접속 → scripts/probe_jetson_bench.py 대상 실행 결과 보존 → 기존 PyTorch CUDA가 가능하면 그 경로만 구현. 불가하고 TensorRT가 적합할 때만 ONNX 경로. 인증 대기 중 전체 Windows 시스템으로 확장하지 않는다.

접속 후속 확인: 사용자는 접속 완료를 알렸으며 수동 SSH 프로세스가 존재한다. 도구 첫 접속 시 전용키가 없었으나 이후 파일이 생성된 것을 확인했다. 키 생성 명령은 기존 파일 덮어쓰기 질문에서 종료코드1로 끝났고 덮어쓰지 않았다. 현재 전용키를 명시한 BatchMode도 인증 거절이며 원격 환경은 아직 읽지 못했다. 사용자에게 이미 접속한 Jetson 터미널에서 공개키 추가 명령 하나를 안내한다. 사용자 수동 접속과 도구 인증 성공을 구분한다.
