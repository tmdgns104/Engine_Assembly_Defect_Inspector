# Runtime 공통 계약 — V0-T03

## 계약을 먼저 정하는 이유

상위 Runtime이 Camera와 Detector의 입력·출력 형식에만 의존하도록 한다. 모델·카메라가 교체될 때 Recipe / Decision / Journal / API를 함께 다시 만드는 일을 줄이기 위해서다. 기존 `ARCHITECTURE.md`의 인터페이스 우선 구조를 구체화하며, 이번에는 실제 backend나 판정·저장 엔진을 구현하지 않는다.

```text
Camera.capture() → CameraFrame → Detector.detect(frame) → DetectionResult
                                                          ↓
                                               Recipe / Decision / Journal / API
InspectionRequest → Runtime → InspectionResult
```

## 코드와 공통 규칙

`src/contracts/enums.py`는 이름, `models.py`는 데이터와 검증·직렬화, `interfaces.py`는 Protocol과 공통 예외를 정의한다. 공개 import는 `from src.contracts import ...`를 사용한다. Python 3.13 표준 라이브러리만 사용하며 Pydantic·ML·카메라 패키지를 import하지 않는다.

모델은 `frozen=True` dataclass다. 컬렉션은 tuple로 받아 외부 list 수정으로 결과가 바뀌는 것을 막고, `to_dict()`에서는 새 list/dict로 변환한다. 타입 오류는 `TypeError`, 범위·내용 오류는 `ValueError`다. 필수 문자열은 공백만으로 구성될 수 없다. 수치는 내장 int/float만 허용하고 bool, NaN, 무한대는 거부한다. Adapter가 tensor나 framework scalar를 Python 값으로 변환한다.

## BoundingBox / Detection / DetectionResult

| 계약 | 실제 필드 | 의미·불변 조건 |
|---|---|---|
| BoundingBox | `x1, y1, x2, y2: float` | 원본 이미지의 좌측 상단 원점, xyxy pixel edge 좌표. 모두 유한·0 이상, `x1 <= x2`, `y1 <= y2` |
| Detection | `class_id: int`, `class_name: str`, `confidence: float`, `bounding_box: BoundingBox` | class_id는 0 이상, confidence는 0~1 양끝 포함 |
| DetectionResult | `frame_id: str`, `detections: tuple[Detection, ...] = ()`, `model_version: str \| None = None`, `inference_ms: float \| None = None` | 입력 frame_id 유지, inference_ms는 유한·0 이상. 빈 detections도 정상 관측 결과 |

좌표는 소수 pixel도 허용하며 우측·하단 경계는 width/height까지 표현할 수 있다. 같은 좌표로 면적이 0인 box도 `<=` 규칙에 따라 허용한다. box 자체에는 이미지 크기가 없으므로, 이미지 영역 내 좌표인지 확인하고 resize/letterbox 좌표를 원본으로 복원하는 일은 Adapter 책임이다. xywh·normalized 좌표·tensor·`Results.boxes`를 상위 계층으로 전달하지 않는다. 엔진 slot·부품 좌표·tolerance는 정의하지 않는다.

Detector는 검출 관측을 반환한다. 빈 detections는 물리적 부품 누락 판정이나 backend 오류를 뜻하지 않는다. 추론 실패는 `DetectorError`로 보고한다. inference_ms의 측정 구간은 향후 Adapter가 함께 문서화해야 하며 이 필드는 성능 합격 기준이 아니다.

## CameraFrame / FrameMetadata / 시간

| 계약 | 실제 필드 |
|---|---|
| FrameMetadata | `frame_id: str`, `captured_at: datetime`, `width: int`, `height: int`, `source: str \| None = None` |
| CameraFrame | `image: object`, `frame_id: str`, `captured_at: datetime`, `width: int`, `height: int`, `source: str \| None = None` |

width/height는 1 이상의 정수이고 원본 image 크기를 나타낸다. source는 선택적인 문자열 식별자다. 임의 객체를 담는 metadata dict는 제공하지 않는다. frame_id는 Camera가 관측 단위를 식별할 수 있게 발급하고 Detector가 그대로 반환한다.

**image payload는 in-memory runtime data이며, 외부 결과 직렬화 대상은 metadata/evidence reference다.** `CameraFrame.to_metadata()`는 `FrameMetadata`를 반환하고, 그 객체의 `to_dict()`만 JSON으로 변환한다. CameraFrame에는 `to_dict()`가 없다. `dataclasses.asdict(frame)`이나 `json.dumps(frame)`로 image까지 보내는 사용은 지원하지 않는다.

image는 None을 제외한 불투명한 객체이며 특정 cv2·ML 타입에 고정하지 않는다. 과도한 Generic 없이 `object`로 경계를 나타냈다. 실제 pixel layout, 색 순서, 메모리 장치, payload와 metadata의 크기 일치는 연결되는 Camera/Detector Adapter가 합의·검증한다. 이 Protocol만으로 모든 image 표현 사이의 호환성이 보장되지는 않는다. Camera는 소비자가 처리하는 동안 유효한 buffer를 제공해야 한다. frozen wrapper가 mutable image 내부까지 동결하거나 복사하지는 않는다.

captured_at와 requested_at는 timezone-aware datetime만 허용한다. 생성 시 UTC로 정규화하고 `isoformat()`으로 `2026-09-10T03:30:00+00:00`처럼 직렬화한다. naive datetime을 로컬 시간으로 추정하지 않고 거부한다.

## Camera / Detector 인터페이스

| Protocol | 호출 | 계약 |
|---|---|---|
| Camera | `capture() -> CameraFrame` | 유효한 프레임 반환. 입력 소진·장치 실패·닫힌 상태는 CameraError |
| Camera | `status() -> bool` | True=준비됨, False=닫힘/사용 불가. 검사 판정 상태와 다름 |
| Camera | `close() -> None` | 자원 해제, 반복 호출 안전. 실패는 CameraError |
| Detector | `detect(frame: CameraFrame) -> DetectionResult` | 같은 frame_id와 원본 이미지 좌표 반환. 실패는 DetectorError |

공유 구현·상속 계층이 필요 없으므로 ABC 대신 `typing.Protocol`을 선택했다. 향후 ReplayCamera / SampleImageCamera / V4L2Camera와 Fake / PyTorch / ONNX / TensorRT Detector가 같은 서명을 따른다. Backend 예외를 공통 예외로 바꾸는 일도 Adapter 책임이다.

`runtime_checkable`의 `isinstance()`는 멤버 존재 확인용이며 서명·반환값·의미까지 검증하지 않는다. 테스트는 dummy 객체의 메서드를 실제 호출하여 반환 계약, frame_id 연결과 close 동작도 확인한다. 실제 Adapter와 장비의 준수 여부는 구현되는 Task에서 별도 검증한다. Dummy는 테스트 파일 안에만 있다.

## InspectionRequest / InspectionResult / Reason

| 계약 | 실제 필드 | 의미 |
|---|---|---|
| InspectionRequest | `request_id: str`, `run_mode: RunMode`, `requested_at: datetime` | manual 버튼과 PLC가 동일한 요청 형식 사용 |
| RunMode | `MANUAL="manual"`, `PLC="plc"` | 호출 출처만 구분. PLC 주소·모터 제어 없음 |
| InspectionResult | `request_id: str`, `status: ResultStatus`, `reasons: tuple[Reason, ...] = ()`, `evidence_refs: tuple[str, ...] = ()`, `frame_meta: FrameMetadata \| None = None` | 같은 request_id로 요청과 결과 연결 |
| Reason | `code: ReasonCode \| str`, `message: str` | 안정적인 코드와 사람이 이해할 설명. 둘 다 비어 있을 수 없음 |

run_mode/status는 해당 Enum 인스턴스를 받는다. 외부 문자열을 받는 Adapter는 `RunMode(value)` / `ResultStatus(value)`로 검증 후 변환한다. 임의 control_hints와 별도 결과 timestamp는 아직 소비자가 없어 추가하지 않았다.

evidence_refs는 저장된 이미지·로그 등의 문자열 참조다. Contract는 파일을 읽거나 존재 여부를 확인하지 않는다. Camera 실패로 프레임이 없으면 frame_meta=None인 ERROR를 만들 수 있다. 요청 발급과 결과 상관관계 보장은 향후 Runtime 책임이며 계약이 ID의 전역 유일성을 생성·검증하지는 않는다.

ReasonCode의 최소 공통 집합은 `LOW_IMAGE_QUALITY`, `LOW_CONFIDENCE`, `MISSING_REQUIRED_OBJECT`, `UNEXPECTED_OBJECT`, `CAMERA_ERROR`, `DETECTOR_ERROR`, `PERSISTENCE_ERROR`다. 향후 V1 domain 코드는 Reason의 비어 있지 않은 문자열로 확장할 수 있다. 이번에는 엔진 전용 코드를 추가하지 않는다.

## PASS / FAIL / REVIEW / ERROR

| 상태 | 향후 판정 의미 |
|---|---|
| PASS | 정상 검사 완료, 충분한 판정 근거, 불확실성 없음, 필수 evidence 저장·연결 성공 |
| FAIL | 충분한 관찰 근거 아래 요구 조건 불충족. 미검출만으로 자동 결정하지 않음 |
| REVIEW | 낮은 품질·불충분한 시야·낮은 확신 등으로 사람 확인 필요 |
| ERROR | Camera / Detector / 저장 시스템 등 검사 실행 자체 실패 |

결과 상태는 정확히 이 네 개다. Emergency Stop은 향후 V2의 장비·안전 제어 상태이며 포함하지 않는다.

현재 생성자에서 검사하는 **구조적 최소 조건**은 PASS의 frame_meta와 하나 이상의 비어 있지 않은 evidence reference, FAIL/REVIEW/ERROR의 설명 reason이다. 이 조건 통과가 실제 PASS 적합성이나 저장 성공의 증거는 아니다. Reference만 써놓고 저장에 실패한 결과를 PASS로 내보내면 안 된다. 충분한 관찰·불확실성·reason/status 일관성·필수 evidence 전체의 정상 저장 여부를 검증하는 로직은 T12/T13에서 구현한다. 이 Task는 Recipe/Decision/Persistence 로직을 넣지 않는다.

## 직렬화와 교체 경계

BoundingBox, Detection, DetectionResult, FrameMetadata, InspectionRequest, Reason, InspectionResult는 명시적인 `to_dict()`를 제공한다. 결과에는 dict/list/string/number/None만 있으며 `json.dumps(value.to_dict(), allow_nan=False)`로 JSON을 만들 수 있다. 선택 필드는 None을 JSON null로 유지한다. JSON에서 계약으로 복원하는 범용 parser나 FastAPI schema는 이번 범위가 아니다.

V1은 Dataset·클래스·학습 모델·Recipe·평가 데이터를 교체한다. Runtime이 Ultralytics Results, torch.Tensor, ONNX Session output, TensorRT binding, OpenCV VideoCapture, V4L2 객체를 알아야 하는 구조로 바꾸지 않는다. V2는 Mock PLC 대신 실제 PLC 입력 Adapter가 같은 InspectionRequest를 만들도록 한다. 장비 주소·센서·모터·Emergency Stop은 별도 control 경계에 남긴다.

## 검증과 읽기 순서

저장소 루트에서 `.venv\Scripts\python.exe -m unittest discover -s tests -v`로 실행한다. 테스트는 숫자·중첩 타입·UTC·JSON·payload 제외·dummy 준수를 확인한다. 실제 backend·카메라·저장 성공은 이 테스트의 검증 범위가 아니다.

처음에는 `enums.py` → `models.py` → `interfaces.py` → `tests/test_contracts.py` 순서로 읽는다. 실행 근거와 환경 보존 결과는 [V0-T03 verification](verification/V0-T03.txt), 학습 요약은 [V0-T03 학습 기록](learning-notes/V0-T03.md)을 참조한다.
