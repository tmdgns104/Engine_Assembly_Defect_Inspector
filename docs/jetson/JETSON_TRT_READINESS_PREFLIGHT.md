# JETSON-P0-004A — TensorRT Readiness & Design Preflight

판정: **PREFLIGHT_COMPLETE_IMPLEMENTATION_NOT_AUTHORIZED** (2026-09-16). 설치·소스·설계 준비 점검 완료이며 TensorRT backend 구현/engine 생성/실행 성공 판정이 아니다. P0-003 Runtime/raw/측정값은 FROZEN이다.

사용자의 [지정 대화](https://chatgpt.com/c/6aa23182-dfe4-83ee-9ab4-be9e20b06b3b)와 다음 범위를 협의하고, 응답을 실제 저장소/설치 소스에 대조했다. 외부 모델/Fast 변경 권고는 채택하지 않았다. SSH2회는 stdlib metadata/spec·파일 read/hash·dpkg-query뿐이었다. framework import0, Camera/GPU/inference/export/build0, 새 Jetson 파일0, 환경 변경0. 문서와 Windows raw evidence만 작성했다.

## 현재 계약과 변경 지점

정확한 함수 시작/종료 행과 SHA는 `runs/jetson_p0_004a/source_contract.json`에 있다.

| 근거 | 현재 계약 | 다음 Candidate 변경 후보 |
|---|---|---|
| `src/contracts/interfaces.py::Detector` | `detect(CameraFrame)->DetectionResult`; constructor/metadata interface는 없음 | 기존 Protocol 유지, 생성과 readiness metadata를 별도 최소 경계로 제안 |
| `src/contracts/models.py::DetectionResult` | frame_id, detections tuple, model_version, inference_ms. backend/precision 전용 필드 없음 | 기존 필드의 의미 보존; package/별도 provenance에 source PT와 engine identity 구별 |
| `src/vision/pytorch_detector.py` | SHA 확인, CUDA 강제, YOLO.to(cuda:0), predict/기존 synchronize2회 | 기존 PyTorch 구현은 보존하고 새 TRT 구현 추가 후보 |
| `src/vision/inspection_worker.py::worker_main:69-78` | concrete PyTorch import/생성 | **FACTORY_INSERTION_POINT**. Package 선언→factory→Detector, Worker가 Camera/GPU/context/stream/buffer 소유 |
| 같은 Worker:88-93 | backend=pytorch, detector.torch.cuda 직접 참조 | adapter-neutral readiness metadata 후보. Service가 GPU 소유권을 가져가지 않음 |
| `src/recipe/package.py::load_package` | schema1, detector dict=pytorch/detect/ultralytics_xyxy 고정; 정확한5개 files+선택 self_test | legacy branch 유지, 별도 strict TRT branch. 기존 package migration 없음 |

`DetectionResult`의 box는 원본 이미지의 nonnegative xyxy pixel, class id/name은 기존 순서, frame_id는 입력과 동일해야 한다. 정상 empty detection과 실행 실패는 다르다. TRT failure는 DetectorError로 연결하고 빈 결과/CPU/PyTorch 자동 fallback으로 숨기지 않는다. `TENSORRT_BACKEND_REQUESTED + INVALID_ENGINE → readiness FAIL`; silent fallback은 별도 명시 승인 없이 금지하는 계약 후보다.

## 설치 상태와 실행 증거 구분

| 항목 | 현재 metadata/spec/file 관측 | 의미/제약 |
|---|---|---|
| TRT Python | 10.3.0, `/usr/lib/python3.10/dist-packages/tensorrt/__init__.py` | 이번 import/deserialize/build0 |
| libnvinfer10/libnvonnxparsers10/TRT dpkg | 10.3.0.30-1+cuda12.5 | 라이브러리 존재 확인, 모델 parser compatibility UNKNOWN |
| trtexec | `/usr/src/tensorrt/bin/trtexec` PRESENT | 바이너리 실행 안 함, 자체 version UNKNOWN |
| ONNX | 1.22.0 PRESENT, `~/.local/lib/python3.10/site-packages/onnx` | import/API/export 검증 아님 |
| ONNX Runtime | 1.23.2 PRESENT, 같은 user-site/onnxruntime | provider/실행 가능 여부 새 검증 없음 |
| torch.onnx | torch2.8.0 user-site/torch/onnx/__init__.py PRESENT | submodule import0 |
| onnxsim/onnxslim/onnx_graphsurgeon/polygraphy | 현재 interpreter 검색 경로에서 ABSENT | 시스템 전체 부재라는 뜻 아님. 설치하지 않음 |
| Python/L4T/CUDA/GPU | 기존 증거 Python3.10.12/L4T36.4.7/CUDA12.6/Orin CC8.7/aarch64 | 이번 CUDA 초기화 없음. L4T와 핵심 package metadata는 재대조 |

실제 경로/version/라이브러리 symlink와 source SHA는 `toolchain_inventory.json`, `remote_readonly.json` 참조. P0-003 대비 비교한 핵심 버전 drift 없음. NumPy 기본2.2.6과 overlay1.26.4/OpenCV5 metadata 충돌은 유지한다. 설치 상태는 production dependency 승인과 다르다.

## Export·container·reader·profile

설치 Ultralytics8.4.118 소스24개를 실행 없이 읽었다. 원본은 `installed_ultralytics/`, SHA는 수집 당시 protected inventory와 대조했다.

| 경계 | 설치 소스 근거와 발견 |
|---|---|
| direct export | `engine/exporter.py:1357`의 export_engine은 GPU를 요구하고 export_onnx 후 onnx2engine 호출. ONNX 중간 파일을 생략하지 않음 |
| 출력 위치 | model의 sibling `.onnx`/`.engine` 경로 사용. 향후에도 보호 package 안 모델을 대상으로 직접 exporter를 실행하면 안 됨 |
| 의존성 | export_onnx:1028-1036의 ONNX>=1.12,<2; simplify=True이면 onnxslim>=0.1.82 요구. 현재 onnxslim 없음은 **해당 경로의 조건부 blocker** |
| 자동 설치 | utils/checks.py:531/625의 check_requirements와 utils/__init__.py:70의 AUTOINSTALL 기본true. TensorRT helper에는 check_tensorrt 복구 경로도 존재. 실제 호출0 |
| precision 옵션 | onnx2engine은 quantize=16을 FP16 후보로 처리. 예전 half=True 명령을 복사하지 않음 |
| writer | utils/export/engine.py:452-456: metadata가 있으면4-byte little-endian signed length + JSON + plan bytes. direct exporter가 metadata를 전달 |
| reader | nn/backends/tensorrt.py:51-62:4-byte length→JSON→남은 bytes deserialize. UnicodeDecodeError만 seek0으로 되돌림. 임의 파일에 대한 안전한 format autodetect 보장이 아님 |
| profile | utils/export/engine.py:331-339: dynamic=True일 때만 min/opt/max profile 생성; max식이 workspace에도 의존. 현재640 입력에서 build profile을 추정하지 않음 |
| parse/build | parser.parse_from_file:319-321, build_serialized_network:444-448. 모두 NOT_RUN |

Base `cfg/default.yaml` literal은 imgsz640/batch16/dynamicFalse/simplifyTrue/quantize·opset·workspace null/nmsFalse다. model.export가 overrides를 합친 최종값을 뜻하지 않는다. 향후 build에서는 shape/batch/dynamic/simplify/precision/opset/workspace/NMS를 명시하고 **FIXED_640_CANDIDATE**도 승인 전 후보로만 둔다.

**EXPORT_PATH=DECISION_PENDING**. 두 경로를 비교했다.

| 후보 | 이점 | 확인해야 할 경계 |
|---|---|---|
| Ultralytics direct engine export | 기존 exporter/metadata/loader와 통합 가능 | ONNX 중간 생성, 자동 설치, metadata-prefixed container, output/NMS 규칙, 기존 package overwrite 위험 |
| explicit ONNX→TRT build | export/parser/build artifact와 option/provenance를 따로 검증 가능 | 직접 TRT adapter/전처리·postprocess, plugin/API/stream/buffer/format 계약 구현 필요 |

최소 `artifact_format=trt_plan` 또는 `ultralytics_metadata_prefixed_engine`를 명시하고 loader와 일치시켜야 한다. 새 custom reader라면 header 길이/파일 경계/JSON/schema/plan 영역을 검증해 fail closed하고 raw-plan 추측 fallback을 하지 않는 설계를 제안한다. 어떤 loader를 쓸지는 미정이다. **PARSER_COMPATIBILITY=UNKNOWN, REQUIRED_PLUGINS=UNKNOWN/NOT_IDENTIFIED**다.

## 기존 ONNX와 모델 범위

`training/experiments/earbud_case_v0_20260913_v001/baseline/weights/best.onnx` SHA는 `ef8b5918b69c7ca4d073e0564f696688e2292b957d3fab852dd680cbe928e209`로 기존 `runs/jetson_bench_001/staging_v001/manifest.json` 기록과 동일하다. 해당 기록의 source PT SHA는 현재 package best.pt의 `49f533e4e4e5846d1582564d8efbb38a647ad10348a976db9085d94df16250c1`과 같다.

과거 metadata는 exporter8.4.146/opset12/input `[1,3,640,640]` float/output `[1,7,8400]` float/NMS nodes0/end2end=false다. 당시 parity NOT_RUN, inference_executed=false였다. 이번에는 bytes hash만 재확인했고 graph checker/ONNX Runtime도 재실행하지 않았다. Jetson exporter8.4.118과 다르므로 **기존 파일이 있다는 이유로 export/parity 승인 artifact로 승격하지 않는다**. 출력7의 의미나 xywh/xyxy/score 조합도 shape만으로 확정하지 않는다.

대상은 earbud 기술 대조 모델이다. 최종 엔진 제품 모델/정확도/latency readiness는 NOT_EVALUATED다.

## Package·전후처리·provenance 후보

현재 files.model.path/SHA, classes, preprocessing, recipe, capture, optional self_test 구조를 유지한다. 기존 PyTorch schema1을 바꾸지 않고 별도 TRT package branch에 artifact format/input/output/precision/runtime compatibility/build provenance를 엄격히 추가하는 방향을 제안한다. 새 package/schema version/field 이름과 model_version의 engine identity 매핑은 **DESIGN_CANDIDATE**, 아직 승인·구현하지 않았다.

입력은 현재 package대로 BGR→RGB, float32 NCHW/255, letterbox linear/padding114,640×640, rectFalse/cropFalse/augmentationFalse, batch1, confidence0.25/NMS IoU0.7이다. 클래스는0 earbud_left/1 earbud_right/2 case. PyTorch 전처리와 NMS는 Ultralytics 내부다. raw TRT adapter에는 동등 전처리가 필요하고, Ultralytics loader 재사용 시에도 exact resize/rounding/padding/좌표 역변환 parity를 증명해야 한다.

Decode/NMS ownership은 **DECISION_PENDING**: project-side decode/NMS, 검증된 Ultralytics-compatible postprocess 재사용, engine embedded NMS를 비교할 수 있다. 현재 raw ONNX에는 NMS가 없다는 과거 증거만 있으며 실제 parser/plugin/NMS 포함 새 출력 계약은 미정이다.

Provenance는 PT SHA→ONNX SHA→engine SHA와 exporter/build tool source/version/options, artifact container, input/output name/shape/dtype, batch/profile, precision/TF32 관련 flag, workspace, plugin/library, TRT/CUDA/L4T/GPU CC, build host/time, package version을 연결한다. 다른 장치/버전 portability는 UNKNOWN이며 **ENGINE_COMPATIBILITY_TARGET_BOUND**를 제안한다. FP32/FP16은 후보, accepted precision NONE, INT8/calibration/DLA는 초기 범위 밖이다.

Health는 Worker ready metadata→Service 기존 health의 backend 영역에 adapter-neutral provenance를 전달하는 후보이고, inspection은 package snapshot/별도 provenance로 연결하는 후보이다. legacy timing 필드를 GPU kernel 시간으로 재해석하지 않는다. UI/API/DB schema는 변경하지 않았다.

## Parity 입력·오류·수용 계획

안전한 기존 후보2개를 명시 경로·SHA로 확인했다(`parity_input_inventory.json`).

1. 기존 승인 저장 raw `data/app_v1/assets/5031fbaf16a94877b5b6aa46f9e90c03/215fc0dd6f7a4fc19fbee249cfdd5642.png`, SHA `04380e88c2802d39826da972d2fdb30eaba03e0c7a17713d5178434fa16c2b18`.
2. 기존 package `self_test.png`, SHA `d64f17077d1c5060df7d7e663ee8c9fdbd4614191d2bdd9f9f4a51ab2cd62b4d`.

이는 입력 경로 기술검증 후보이며 물리 view/calibration/정확도 승인이나 독립 정답셋이 아니다. 추가 reference/calibration/Dataset/E04/holdout을 열지 않았고 새 촬영0이다.

향후 parity는 preprocess shape/dtype/layout/range/value, 가능한 raw output 비교, finite value, class/confidence/box/count의 순서 무관 일대일 대응, frame_id/오류/provenance, 동일 Recipe view 정책을 검사한다. 절대/상대오차·confidence delta·box IoU tolerance는 모두 **TOLERANCE_TBD_FROM_EMPIRICAL_PARITY_EVIDENCE**다. repeatability/precision별 pilot 관측으로 후보를 만들고 별도 수용 절차에서 고정한다. 임의 숫자를 도입하거나 holdout에 맞춰 조정하지 않는다.

future self-test: file exists/hash→명시 container/header→deserialize→I/O shape/dtype/name→승인 입력1개→finite DetectionResult→backend identity. 단순 self-test PASS는 accuracy parity PASS가 아니다. 오류 후보 ENGINE_MISSING/HASH_MISMATCH/DESERIALIZE_FAILED/BINDING_CONTRACT_MISMATCH/INPUT_CONTRACT_MISMATCH/INFERENCE_FAILED/OUTPUT_CONTRACT_MISMATCH/SELF_TEST_FAILED를 DetectorError로 연결한다. 자동복구/fallback은 넣지 않는다.

## Blocker와 후속 Task 초안

| 분류 | 항목 | 다음 해소 단계 |
|---|---|---|
| READY | 현재 계약/source/provenance, 설치 파일 관측, frozen P003 | 정적 근거 사용 가능이라는 의미 |
| NEEDS_IMPLEMENTATION | factory, TRT adapter, package branch, neutral ready metadata | 아래 B/C 승인 범위 |
| MISSING_DEPENDENCY | onnxslim(선택한 simplify=True 경로만) | 설치0 유지; 경로 결정 후 별도 필요성 판단 |
| UNKNOWN | 실제 ONNX parser/plugin 적합성, build memory, final output decode, resolved defaults, engine portability | 승인된 D/E의 고정 설정·실제 증거 필요 |
| NEEDS_HUMAN_APPROVAL | 새 architecture/package/identity 매핑, export/build 범위, precision와 parity 수용 기준 | 기존 원본 보호를 유지하는 구체 변경안으로 별도 결정 |
| NOT_APPLICABLE | INT8/최종 엔진 모델/PLC/MQTT/production SLA | 이번 Task 밖 |

- **P0-004B 초안:** 새 Candidate factory+legacy-compatible package branch, synthetic tests. root/기존 candidate 수정0. artifact format/identity/health 계약 먼저 결정.
- **P0-004C 초안:** TRT adapter와 invalid-artifact/error tests. decode/NMS ownership·stream/buffer lifecycle 결정 전 구현하지 않음.
- **P0-004D 초안:** 명시 승인된 별도 input copy/export/build. fixed shape/profile/precision/opset/workspace/format, no install, bounded memory/fail-stop를 먼저 고정.
- **P0-004E 초안:** 승인 입력 parity pilot→tolerance 확정→별도 검증. 기존 PT/ONNX/container provenance 대조.
- **P0-004F 초안:** 동등 조건의 새 PyTorch/TRT paired runtime 비교. P0-003 과거 p50을 새 TRT p50으로 나눠 속도 향상을 주장하지 않음. frozen P0-003은 역사적 기준으로 유지.

위 B~F는 **SCOPED / NOT_STARTED**, 실행 명령이 아니다. 새 의존성/변환·장치 실행·architecture 변경을 이번 사전 점검이 승인하지 않는다.

## 보존·검증

원격 보호36그룹 + overlay/current, 로컬462개 runtime/test/기존 evidence/P003 문서/raw/PC mirror 파일 전후 내용 SHA 동일. 추가 reader/default source3개도 기존 보호 inventory SHA와 일치했다. 결과 검증은 AST 정의 위치, metadata/manifest/hash/반환 계약/보호 대조이며 실제 GPU 테스트를 새로 했다는 뜻은 아니다. git diff --check PASS; 원본 수정/commit/push0.

현재 ROOT_CAUSE_UNCONFIRMED, production threshold NOT_DEFINED, conveyor NOT_RUN, OpenCV5/NumPy1.26.4 metadata conflict는 그대로다. 외부 대화 리뷰는 근거 해석에 사용했고 실제 source/측정의 독립 검증으로 세지 않았다.
