# JETSON-P0-004A — TensorRT Readiness & Design Preflight

Status: **DONE / PREFLIGHT_COMPLETE_IMPLEMENTATION_NOT_AUTHORIZED**. P0-003 runtime/raw/수치 FROZEN.

사용자의 지정 ChatGPT 대화와 계속 협의하라는 요청으로 다음 준비 작업을 분리했다. 외부 제안은 기존 보호 규칙과 source에 대조했으며, 외부 모델/Fast 변경 권고는 채택하지 않았다.

목표는 현재 Detector/factory/package 경계, 설치 도구, export 형식·부작용, parity/provenance 및 다음 구현 계약을 문서화하는 것이다. Runtime 구현/새 package 생성/ONNX export/TRT build·추론/카메라/설치/환경 변경/PLC/MQTT/commit/push는 수행하지 않는다. SSH는 stdlib metadata/spec·파일 읽기·hash·dpkg-query만 사용하며 framework import0/새 Jetson 파일0을 유지한다.

산출물:

- `docs/jetson/JETSON_TRT_READINESS_PREFLIGHT.md`
- `docs/verification/JETSON-P0-004A.json`
- `runs/jetson_p0_004a/`의 source/package/toolchain/export/parity/preservation 기록

완료 기준: source 위치와 SHA를 근거로 Detector 계약/factory 삽입점/validator 제한을 설명하고, 설치와 실행을 분리한 tool inventory, export 두 경로와 파일 형식, input/output/provenance/self-test/error 계약, 안전한 기존 parity 입력 및 미정 tolerance, 다음 구현 Task 분해와 보호 SHA를 기록한다. UNKNOWN은 이유와 해소 단계가 있으면 preflight 완료를 막지 않지만 구현·빌드 승인은 의미하지 않는다.

## 완료

Detector Protocol/Worker concrete 생성+metadata/factory 위치와 strict PyTorch package 제한을 확인했다. TRT10.3/ONNX1.22/ORT1.23.2/trtexec 파일 존재, conditional simplifier 부재, installed exporter/reader의 metadata-prefixed engine 형식과 dynamic profile/자동 설치 경계를 기록했다. 기존 동일 PT 계열 ONNX SHA도 과거와 동일하나 parity NOT_RUN이다. Export/NMS/loader 선택은 DECISION_PENDING, precision 승인 NONE/tolerance TBD, parity 입력2개는 기술검증 후보뿐이다.

SSH2회 read-only metadata/source/hash 수집, framework import/GPU/camera/export/변환0, 새 Jetson 파일0. 보호36그룹+overlay/current/로컬462파일 변경0, P003 FROZEN 유지, git diff --check PASS. B~F는 문서 안 초안이며 구현 NOT_STARTED. 지정 대화의 writer→reader→profile→parser 검토 의견을 설치 소스로 확인해 반영했다. 원인 UNCONFIRMED 및 production 미수용 경계를 유지한다.
