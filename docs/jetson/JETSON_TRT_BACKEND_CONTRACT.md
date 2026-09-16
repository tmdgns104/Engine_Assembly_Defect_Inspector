# JETSON-P0-004B — Backend Factory & Package Contract

Status: **BACKEND_CONTRACT_IMPLEMENTED_CANDIDATE_ONLY**.
Windows candidate architecture/synthetic verification only. **TRT_RUNTIME_NOT_RUN**.
P0-003 Runtime/raw/수치와 P0-004A evidence는 FROZEN이며 재측정하지 않았다.

## 기준과 변경 범위

`runs/jetson_p0_003/runtime/`의 32개 파일이 당시 Jetson 배포 기록
`runs/jetson_p0_003/deploy.json`의 모든 SHA와 정확히 일치했다. 이를 바이트 복사한
`runs/jetson_p0_004b/candidate_runtime/`만 수정했다. root 소스를 baseline으로 추정하지 않았다.
원격 P003 candidate SHA도 읽기 전용 전후 inventory와 대조했다.

| Candidate 파일 | 변경 |
|---|---|
| `src/vision/detector_factory.py` | 새 `create_detector(package, *, latency_enabled=False)`와 `RuntimeDetector` Protocol |
| `src/vision/inspection_worker.py` | concrete 생성과 `.torch/.device/.input_shape` 접근을 factory/metadata 호출로 대체 |
| `src/vision/pytorch_detector.py` | detached JSON `runtime_metadata()`만 추가; 기존 세 메서드 AST 동일 |
| `src/recipe/package.py` | 명시 backend 선택, schema2 선언 검증, legacy default와 snapshot provenance |

기존32개 중29개 byte 동일,3개 수정,1개 추가,삭제0. `src/contracts/` 전체와
Fresh Frame/Camera/Service/Journal/PC Sync/Health API/Web UI 구현은 candidate에서도 그대로다.
Root `src/apps/config/scripts/tests`와 기존 package/model/DB/assets는 변경하지 않았다.

## 선택과 소유권

`load_package`는 schema/path/hash/선언 일관성만 검증한다. Factory는 검증된 package를 받아
backend를 먼저 판정한 뒤 구현을 선택한다. Camera/GPU/context/stream/buffer 소유권은 기존
Worker process에 남는다. Service/DB 소유권을 factory로 옮기지 않았다.

| 선언 | 결과 |
|---|---|
| schema1 + 기존 유효 PyTorch detector 계약 | PyTorchDetector |
| schema1 + backend만 누락 + 정확히 `task=detect, output=ultralytics_xyxy` + 나머지 legacy package 검증 통과 | `PYTORCH_LEGACY_DEFAULT` → PyTorchDetector |
| backend 명시 `pytorch` | 명시값 우선, schema1 PyTorch 계약을 검증한 뒤 선택 |
| backend 명시 null/unknown | `UNSUPPORTED_BACKEND`, default하지 않음 |
| schema2 backend 누락 | `BACKEND_CONTRACT_INVALID`, default하지 않음 |
| schema2 명시 `tensorrt`의 유효 선언 | `TENSORRT_BACKEND_NOT_IMPLEMENTED` |

Factory의 TensorRT/unknown 거부는 adapter/framework import와 모델 파일 read보다 먼저다.
Package validator는 원래처럼 hash 계산을 위해 artifact를 읽는다. 이 두 경계를 혼동하지 않는다.
PyTorch constructor 실패도 그대로 전파하고 재시도/CPU/TRT→PyTorch fallback을 하지 않는다.
TensorRTDetector, reader, deserialize, bindings, execution은 구현하지 않았다.

## Worker metadata와 기존 결과 의미

`RuntimeDetector(Detector, Protocol)`은 기존 detect 계약을 상속하고
`runtime_metadata() -> dict`만 요구한다. Worker 의존성은 이 RuntimeDetector 계약이다.
기존 범용 Detector Protocol을 확장 강제하지 않아 다른 mock 계약을 깨지 않는다.

PyTorch metadata는 backend/device/gpu/input_shape/artifact_sha256/source_model_sha256,
`observed_runtime.{torch,cuda}`, `timing.{latency_enabled,last_reported_speed,startup_timestamps_ns}`다.
문자열/숫자/list/dict/null만 반환하며 mutable 값은 복사한다. torch/YOLO/CUDA native 객체를
반환하지 않는다. Worker는 hostname/camera_pipeline/load_self_test_ms만 기존처럼 덧붙인다.

`DetectionResult`와 `to_dict`는 byte 동일이다. frame_id, original-image xyxy, class mapping,
model_version의 기존 PyTorch model SHA 의미, DetectorError/empty detection 의미를 유지한다.
`PyTorchDetector.__init__/_observe_input/detect` AST 동일을 확인했다. latency 기본 OFF,
legacy inference_ms, 선택적 Results.speed 복사, 기존 synchronize2회/추가0도 유지한다.
Factory 시간은 detector의 legacy timer에 포함되지 않는다. timing 값을 순수 GPU kernel
시간으로 재해석하지 않으며 P003 H2D null/host timing 등의 의미도 바꾸지 않는다.

## Candidate package schema2

기존 schema1 manifest와 snapshot은 그대로 유효하다. 새 구조는 schema1의 의미를
암묵 변경하지 않기 위해 **schema_version=2, detector.backend=tensorrt** 별도 branch로 만들었다.
P004A에서 이름이 미정이던 항목은 기존 `detector`, `files.model.path/sha256`, snake_case와
`model_version`을 재사용했다. artifact identity를 중복된 ID 체계로 만들지 않았다.

| 필드 | 계약 |
|---|---|
| model_version | 모델 계열/학습 가중치의 사람이 정한 version. TRT artifact 자체 identity가 아님 |
| files.model.path / sha256 | 실행 artifact 상대경로/실제 바이트 SHA. package-root 탈출/중복 경로 거부 |
| files.model.artifact_format | `trt_plan` 또는 `ultralytics_metadata_prefixed_engine`, 필수 |
| detector.source_model_sha256 | 원본 모델 provenance,64자 lowercase SHA256. 원본 모델 재로드/파일 존재 검사 아님 |
| detector.input | `shape=[1,3,H,W]`, `layout=NCHW`, dtype float32/float16; preprocessing size/dtype와 일치 |
| detector.precision | 필수지만 null 또는 fp32/fp16 선언 가능. default/accepted precision 없음; INT8 거부 |
| detector.output | 이번 schema2에서는 명시 null만 허용: DECISION_PENDING |
| preprocessing.nms_location | 이번 TRT branch는 명시 null만 허용: DECISION_PENDING |
| detector.provenance.build | 필수 tool/version/options. tool/version은 미관측 null 허용, options는 유한 JSON object |
| detector.provenance.build_environment | 필수 tensorrt/cuda/l4t/gpu_compute_capability/plugins. 미관측 null 허용 |

기존 BGR→RGB, letterbox/linear/padding114, NCHW/255, rect/crop/augmentation false,
confidence/NMS IoU 범위, Recipe/Capture 규칙을 재사용한다. schema2의 입력 shape/dtype는
선언 검증일 뿐 build profile/precision의 수용이 아니다. fp16 precision과 float32 I/O의 조합도
자동 부정하지 않는다. 실제 kernel precision과 input dtype는 다른 개념이며 후속 검증 책임이다.

`build_environment`는 package에 기록된 빌드 환경 선언이다. `runtime_metadata.observed_runtime`은
현재 adapter가 읽은 실행 환경 값이다. 둘을 같은 runtime 관측으로 합치지 않는다.
plugins=null은 UNKNOWN이며 빈 list 선언이 실제 plugin 불필요를 증명하지 않는다.
선택되지 않은 exporter/builder/options/version을 발명하지 않았다.

**SCHEMA_VALID ≠ RUNTIME_READY**. 합성 fixture는 **CONTRACT_VALID_NON_EXECUTABLE**이다.
가짜 바이트 `synthetic-not-a-real-engine`의 SHA/path/선언만 검사하며 확장자가 `.pt`여도
명시 format대로 계약을 읽는다. 모든 TensorRT factory 요청은 여전히 실패한다.
미래 adapter activation gate는 실행에 필요한 output/NMS/precision/provenance의 미결정 값,
container/IO/compatibility/self-test를 명시적으로 검증해야 한다. 이번에 그 gate를 구현하지 않았다.

## Format·provenance·오류

확장자, 첫4-byte, UnicodeDecodeError로 format autodetect하지 않는다.
**FUTURE_READER_VALIDATION_REQUIRED**: metadata-prefixed 형식을 명시 선택한 future reader는
4-byte 길이 존재, 길이 bounds/부호·파일 범위, JSON decode와 required metadata shape,
남은 plan bytes>0을 검사해야 한다. raw-plan 추측 fallback은 금지다. 이번 parser 호출0이다.

기존 explicit-PyTorch snapshot은 baseline과 완전히 같다. backend 누락 legacy와 새 TRT
snapshot에는 declared_backend/resolved_backend/resolution_basis를 추가한다. 전체 manifest가
기존 Journal package_json에 들어가므로 backend+format+artifact SHA+source model SHA+
빌드 선언이 durable provenance에 남는다. synthetic Journal admit/finish/read-back에서 확인했다.
DB schema migration0, user_version1 유지. 실제 TRT DetectionResult model_version 매핑은
adapter 후속 계약이며 이번에 구현하지 않았다.

현재 오류는 기존 PackageError/DetectorError에 `UNSUPPORTED_BACKEND`,
`BACKEND_CONTRACT_INVALID`, `ARTIFACT_FORMAT_UNSUPPORTED`, `ARTIFACT_HASH_MISMATCH`,
`TENSORRT_BACKEND_NOT_IMPLEMENTED`를 사용한다. 미래 ENGINE_DESERIALIZE_FAILED,
BINDING_CONTRACT_MISMATCH, INFERENCE_FAILED는 문서 후보뿐이다.

## 검증과 한계

- **114/114 baseline regression semantics ported to candidate harness PASS**, fail/error/skip0.
  원본 tests는 무수정. task-local Worker test 파일1개의 mock class1개를 constructor keyword와
  runtime_metadata 계약에 맞게 확장했다(Worker test methods2개에서 사용). 기존 assert AST 동일.
  나머지 tests와 P003 latency12는 원본을 읽어 실행했다. 114 test ID를 기존 기록과 대조했다.
- **28/28 새 backend tests PASS**, fail/error/skip0. default/explicit/unknown, no fallback/import/read,
  fake artifact format/hash/path/fields/provenance/NaN, Journal snapshot, Worker fault-before-camera,
  default timing과 factory 전후 mocked PyTorch/Recipe 동등성, metadata 복사, original result byte 동일 검사.
- actual candidate module origins를 assert하고 기록했다. 주요 package/worker/detector/factory,
  Camera/Journal/Service/PC Sync까지 candidate를 import했다. subprocess 계약 검사도 candidate cwd/PYTHONPATH.
- 실제 torch/Ultralytics/TensorRT/ONNX framework import를 금지한 harness에서 forbidden attempts0.
  PyTorch 기능 비교의 torch/YOLO는 test-local stub이며 실제 모델/장치 실행이 아니다.
- Camera/GPU/모델 inference/TRT import/export/build/배치0. Windows numpy/cv2의 기존 memory-only
  synthetic tests만 수행했다. Jetson은 stdlib SHA 읽기만, 파일 생성/변경0.

초기 test-first 실행은 factory 부재로 RED였다. 새 Journal fixture의 raw evidence 누락과
mock monotonic 값 개수 부족은 fixture만 정정했고 최초 실패를 보존했다. provenance의 NaN
허용을 새 RED test로 확인한 뒤 candidate validator에서 명시 거부하도록 수정했다.
원격 첫 hash harness는 없는 current symlink를 무조건 readlink해 실패했으며,
기존과 같은 absent=null 의미로 교정했다. 장치/framework 실행 실패나 재시도가 아니다.

최종 raw는 `runs/jetson_p0_004b/`의 baseline inventory/candidate diff/changed files,
factory_contract/package_contract/test_existing_114/test_backend_contract/import_origins/preservation 참조.
git diff --check PASS, HEAD 동일, commit/push0. 보호 파일 전후 SHA와 P004A 분류를 유지했다.

## 미결정 항목과 다음 경계

| 항목 | 상태 |
|---|---|
| EXPORT_PATH | DECISION_PENDING |
| PRECISION | DECISION_PENDING; accepted NONE |
| DECODE_NMS_OWNERSHIP | DECISION_PENDING |
| PARSER_COMPATIBILITY | UNKNOWN |
| REQUIRED_PLUGINS | UNKNOWN |
| PARITY_NUMERIC_TOLERANCE | TBD |
| FINAL_ENGINE_PRODUCT_MODEL | NOT_EVALUATED |

P004A의 READY/NEEDS_IMPLEMENTATION/NEEDS_HUMAN_APPROVAL/MISSING_DEPENDENCY/UNKNOWN/
NOT_APPLICABLE 분류 원본은 그대로다. factory/package/metadata만 이번 사용자 승인 범위에서
candidate 구현으로 진전됐다. TensorRT adapter/export/수용 승인으로 확대하지 않는다.
기존 ROOT_CAUSE_UNCONFIRMED, OpenCV5↔NumPy1.26.4 metadata 충돌, production threshold 미정,
physical conveyor NOT_RUN도 유지한다. **P0-004C는 별도 승인 전 자동 시작하지 않는다.**
