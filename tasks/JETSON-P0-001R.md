# JETSON-P0-001R — Runtime Dependency Compatibility Recovery

Status: **PASS_MINIMUM_ACCEPTANCE / PREPROCESS_READY** (2026-09-16). 검증 수준 STANDARD; 기존 환경/원본 보존은 필수 gate. 운영 승격 미수행, 전체 dependency metadata 일관성은 FAIL이다.

## 목표와 승인 범위

기존 app_v007·app_v1 환경을 비교 기준으로 보존하고, 현재 torch↔NumPy 실패를 최소 재현한다. NumPy1.26.4만 새 `env_candidates/numpy_compat_001/overlay`에 설치하여 CPU bridge→작은 CUDA 왕복→OpenCV memory-only→기존 저장 이미지 전처리를 단계별 검증한다. Candidate 실행 프로세스에서만 import 우선순위를 바꾼다. 모델 inference는 이번에 하지 않고 PREPROCESS_READY까지 검증한다.

## 금지 / 불변 조건

app_v007 및 app_v1 직접 변경·pip install/uninstall, 기존 ~/.local 라이브러리 변경, apt/CUDA/TRT 재설치, 기존 package/DB/model/image 수정, 새 카메라 촬영, PLC 접근, MQTT 변경, git reset/clean/commit/push를 하지 않는다. NumPy1.26.4 실패 시 다른 패키지를 연쇄 교체하지 않는다. 원본 DB는 연결하지 않고 byte hash로 보존을 확인한다. Ultralytics 버전은 metadata/spec로 조회하고 전처리 import가 필요할 때만 candidate 전용 config/cache를 사용한다.

## 예정 검증 / Evidence

1. sys.executable/sys.path/site 경로·6모듈 metadata/spec·실제 import 경로와 original file SHA.
2. 기존 NumPy2에서 from_numpy/tensor/as_tensor 실패 원문 보존.
3. 별도 --target/--no-deps/--no-compile/--no-cache-dir 설치 및 wheel hash·전체 변경 목록.
4. Candidate compatibility matrix·CPU bridge·CUDA 실제 연산/CPU 반환·OpenCV 색변환/resize.
5. 기존 정상 승인 검사 이미지1장과 실제 Ultralytics 전처리 호출을 이용한 FP32 RGB/255 NCHW640 입력 smoke. 이미지/모델 변경0, 추론0.
6. 원격 release/environment/package/DB/assets 및 Windows 사용자 변경 전후 hash. git diff --check.

산출물: [복구 보고서](../docs/jetson/JETSON_RUNTIME_DEPENDENCY_RECOVERY.md), [검증 JSON](../docs/verification/JETSON-P0-001R.json), 이 Task. 상세 증거: runs/jetson_p0_001r/.

## 실행 결과

- Current: app_v1 Python이 ~/.local NumPy2.2.6/torch2.8/OpenCV5를 선택, TRT10.3은 시스템 경로. `from_numpy` FAIL을 전후 재현했다. tensor/as_tensor PASS를 우회로 채택하지 않았다.
- Candidate: 새 overlay NumPy1.26.4만 선택. NumPy/torch/cv2/TRT import, from_numpy/as_tensor/tensor, CUDA available 및 작은 ndarray→CUDA 실제 연산→CPU 왕복, cvtColor/resize **PASS**.
- 저장된 정상 검사 raw1장의 실제 Ultralytics 전처리 결과 `[1,3,640,640]` FP32, 독립 resize/pad/RGB/255 계산과 차이0.0, **PREPROCESS_READY**. model inference0·camera0·DB 연결0.
- 원격 release50/earbud7/model/DB/assets72/app_v1환경1998 및 기존 라이브러리·설정 해시 동일. Python 프로세스 한정 overlay이며 기본환경은 NumPy2.2.6 그대로다.
- Candidate922파일/62,896,161B 생성. 첫 pip22 `--report` 파싱 실패는 설치 전 종료; 로그 보존 후 같은 NumPy wheel SHA를 검증해 --target 설치 성공. pip/torch/OpenCV 교체 없음.
- **별도 한계:** OpenCV5 메타데이터 numpy>=2와 Candidate1.26.4가 충돌하여 pip check FAIL. 기존 pynacl→cffi 누락도 양 환경에서 존재. 사용 함수의 실제 smoke PASS와 전 dependency 일관성을 구분하며 추가 설치하지 않았다.
- 기존 사용자 변경 보존, STATUS 기존 본문 보존, 최종 git diff --check 및 문서/JSON 검증은 verification JSON의 final_verification을 따른다.

## 수용 및 다음 단계

사용자 최소 수용 NumPy import/torch import/from_numpy/CUDA availability/실제 CUDA smoke/OpenCV smoke 및 원본 보존은 PASS. 정확한 완료 표현은 **격리 Candidate environment에서 기존 필수 NumPy→Torch 입력 경로 호환성을 회복했다**이다.

P0-002 Candidate 기반 설계·개발은 진행 가능하다. 실제 카메라 Runtime 실행은 별도 후보 Runtime 선택/의존성 계약/모델·기동 검증 전 **BLOCKED**이며 이번에 app_v008-dev를 만들지 않았다. 기존 app_v007 복구·배포·실물 검사 완료를 주장하지 않는다.
