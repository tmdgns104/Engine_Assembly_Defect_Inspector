# TASK-017 — 실제 조립 검사 integrity 계약 수정

상태: **ISOLATED_FIX_VERIFIED / STOP_FOR_DEPLOY_APPROVAL** (2026-10-14).
공식 소스 기준 commit: `011a3f46478b02f34b68a34073ac79241975d1e9`.
이 문서를 포함한 수정 commit은 Git 이력에서 확인하며, 노트북 run의
`GITHUB_VERIFICATION.json`에 실제 push SHA를 별도로 기록한다.
Jetson 운영 Release는 **`engine-integrated-90a914423826735a` 그대로**이다.
운영 적용·서비스 재시작·새 현장 시험·결과 송신은 하지 않았다.

## 실제 원인과 재현

검사 `9edd7bf904094733b9f92908bf566c17`의 기존 Journal 조회본, 세 원본 PNG,
원래 `assembly/result.json`을 보존했다. 검증에는 별도 복사본만 사용했다.

호출 경로는 `GStreamerCamera.capture()` → `inspection_worker.detect_frame()` →
`Journal.finish()/detail()` → `AssemblyInspector`가 상속한
`ShadowObserver.process_one()`이다. 정지 검사 경로의 GStreamer `frame_info`에는
frame ID/epoch/sequence/PTS/monotonic 시각이 있지만 `integrity`는 없었다.
Worker는 `freshness.get('integrity', {'valid': True})`를 내부에서 사용하고
원래 freshness를 저장했다. 조립 검사는 `fresh['integrity']['valid']`를 직접 읽었다.
따라서 유효한 원본의 해시 확인을 통과한 뒤, 첫 모델 호출 전에 KeyError가 발생했다.
ContinuousFrames 또는 일부 시험 fixture가 integrity를 제공하여 경로 차이를 놓쳤다.

수정 전 실제 저장 자료로 `KeyError: 'integrity'`를 재현했고 모델 호출은 0회였다.
해당 세 프레임은 같은 camera epoch의 sequence `8833, 8837, 8840`이며,
source PTS는 `663941479372, 664109468388, 664277474795 ns`였다.
세 파일/픽셀 SHA와 기존 quality.valid를 확인했다. 원본 파일과 Journal 내용은 수정하지 않았다.

## 변경한 계약

| 항목 | 변경 전 | 변경 후 |
|---|---|---|
| Worker 무결성 | 누락 시 내부 기본 True, 미저장 | 실제 BGR에 기존 `KNOWN_STRIPE_PATTERN_V1` 실행 후 freshness에 저장 |
| observation 표식 | 없음 | `frame_evidence_contract=RAW_FRAME_INTEGRITY_V1`, `worker_generation` |
| Journal | observations와 asset SHA/frame ID 저장 | 기존 JSON 저장·조회 사용, SQL/DB 스키마 변경 없음 |
| 조립 입력 | integrity 직접 조회 | 파일 SHA → 픽셀 SHA → 동일 프레임/시각/epoch/세대/치수 확인 후 모델 호출 |
| 구형 integrity 누락 | KeyError | 확인된 PNG로 같은 무결성 검사 재수행, `VERIFIED_RAW_PNG_REPLAY` 근거 기록 |
| 신형 필드 누락·알 수 없는 버전 | 구분 없음 | 명시적 `EVIDENCE_*` 오류, Assembly ERROR 저장 |
| 영상 품질 불량 | 기존 quality/무결성 조건 | 기존 false를 유지하며 `quality_valid=False` 전달 |

새 observation 예시(식별자는 설명용):

```json
{
  "frame_evidence_contract": "RAW_FRAME_INTEGRITY_V1",
  "worker_generation": "current-worker",
  "frame_id": "current-frame",
  "freshness": {
    "frame_id": "current-frame",
    "camera_epoch": "current-camera",
    "sequence": 1,
    "source_pts_ns": 123,
    "estimated_source_monotonic": 10.0,
    "received_monotonic": 10.01,
    "integrity": {
      "valid": true,
      "reason": null,
      "horizontal_discontinuities": 0,
      "detector": "KNOWN_STRIPE_PATTERN_V1"
    }
  },
  "quality": {"valid": true},
  "input_pixel_sha256": "actual-BGR-pixel-hash"
}
```

True는 원본 검사 결과이며 기본값이 아니다. 이전 무결성 false는 재검사로 true가 되지 않는다.
구형 기록도 quality·frame ID·epoch·source PTS·원본/픽셀 해시가 있어야 한다.
누락된 품질·시각·카메라 정보를 PNG에서 추정하지 않는다. 손상/누락/모순은 ERROR로 남긴다.
PNG 재검사는 알려진 줄무늬 패턴 검증이며 센서 노출 시각이나 모든 영상 손상의 보증이 아니다.

변경 파일과 함수:

- `jetson/src/camera/frame_integrity.py`: `measured_integrity()`, 계약 표식 추가. 기존 검출 수식/임계값 불변.
- `jetson/src/vision/inspection_worker.py`: `detect_frame()`에서 실제 측정·세대·계약 저장.
- `jetson/src/vision/assembly_evidence.py`: `_frame_metadata()`, `load_assembly_frames()`로 증거 검증 분리.
- `jetson/src/vision/misassembly_shadow.py`: `process_one()`이 검증된 입력과 quality_valid를 사용하고 근거 보존.
- `notebook/tests/test_assembly_frame_contract.py`: Worker/Journal/Assembly와 오염·누락·중복 발행 회귀.
- `notebook/deployment/replay_assembly_evidence.py`: 비공개 저장 자료를 실제 frozen 모델로 재생하는 오프라인 검증 도구.

`assembly_inspection.py`의 비동기 예외 처리·ERROR 저장, `sqlite.py`의 원자적 완료,
`integrated_decision.py`의 기존 결합 정책은 수정하지 않았다.
Pose/Crop/TensorRT/모델·매핑·임계값·3프레임 정책, PLC/EDS/OpENer 소스와 실행 파일도 불변이다.

## 검증 결과

| 검증 | 결과 및 한계 |
|---|---|
| 실제 자료의 수정 전 오류 재현 | PASS: KeyError, 모델 호출 0 |
| 새 Worker → 실제 SQLite/PNG 저장 → Assembly 호출 | PASS: GStreamer처럼 integrity 없는 카메라 fixture 사용 |
| SHA 변조, identity/epoch/source/세대 불일치, 중복 observation, 신형 누락, quality 누락 | PASS: 모델 호출 전 거부 / 명시적 ERROR |
| quality 또는 무결성 false, PNG 줄무늬 | PASS: 정상으로 승격하지 않고 보수적 REVIEW 유지 |
| 최종 PASS/FAIL/REVIEW/ERROR와 중복 poll | PASS: 각각 PLC 0/1/1/1 + Done 의도 유지, 최종 기록/발행 요청 1회 |
| Windows 새 테스트 | 7 PASS. Windows read-only fd fsync만 시험 shim 사용; 장치 내구성 증거로 사용하지 않음 |
| Jetson 네이티브 회귀 | **211/211 PASS**: 이전 204 + 신규 7, fsync shim 없음, 38.919초 |
| 실제 세 PNG의 frozen CUDA 재생 | **검사 경로 PASS**, 동일 ID/PTS/epoch/파일·픽셀 SHA 유지 |
| 현재 환경의 AI 정상 판별 | **미해결**: 아래 REVIEW 원인 참조 |
| 실제 현장 새 한 제품 사이클 | **NOT_RUN**: 새 승인 필요 |

초기 native 실행은 임시 overlay의 `config/plc_reference.json` 참조 누락으로 3개 fixture가 오류였다.
운영 설정을 변경하지 않고 참조를 연결한 뒤 전체 211개가 통과했다. 실패 로그도 보존했다.

실제 모델 재생에서 세 프레임 모두 기존 줄무늬 검출은 0개, integrity.valid=true였다.
그러나 frozen 조립 전처리는 `PRODUCT_COUNT_NOT_ONE` / `TEMPORAL_SINGLE_PRODUCT_REQUIRED`,
products=[]를 반환했다. 네 부품 분류기는 로드·class mapping 확인을 마쳤으나,
유효한 제품/pose/crop 조건이 충족되지 않아 부품 분류 추론은 실행되지 않았다.
세 프레임 결과는 **REVIEW**, 기존 검사 FAIL과의 실제 결합도 **REVIEW**다.
정상 pose/PASS를 재사용하거나 결과를 바꾸지 않았다. 원래 운영 Journal의 ERROR는 그대로다.
이번 결과는 cold-start 및 현장 제품 검출 문제가 해결됐다는 증거가 아니다.

재생 도구는 Python 네트워크/카메라 장치/SQLite 접근 차단을 둔다.
첫 재생은 외부 HTTPS 접속 시도 1건을 차단하여 격리 gate가 실패했다.
설치된 Ultralytics가 지원하는 `YOLO_OFFLINE=true`를 **재생 프로세스에만** 적용한 뒤
접속 시도 0건으로 통과했고 동일 REVIEW 결과를 얻었다. 운영 환경과 모델은 변경하지 않았다.
최종 재생 전체 7.754초는 모델 로드·파일 검증·저장 포함이며 현장 응답 지연으로 해석하지 않는다.

## 운영 보존과 별도 미해결 사항

- 운영 113개 파일 SHA, frozen 자산 28개 SHA, 설정과 서비스 정의 불변.
- `engine-inspector.service` enabled/active, MainPID 24786, NRestarts 0; 카메라 Worker PID 24830 유지.
- 원래 조립 ERROR 기록은 그대로 표시되며 프로세스 ready와 검사 정확도는 별개다.
- SQLite 안전 backup API로 Journal/승인 원장을 복사했고 integrity_check=ok.
  기존 검사 행과 승인 원장 논리 내용 불변; 승인 상태 REVOKED, 재사용/초기화 없음.
- 최종 읽기: Request/Result/Done/Mc_Run LOW, EStop_OK/Stop_PB HIGH,
  OpENer DISARMED, Result/Done/완료 누계 각각 기존 1회 그대로. 물리 정지의 새 실측은 하지 않았다.
- 조사 시작과 종료 사이 Class1 연결번호 7→13. 원인·검증 부하와의 인과관계는 미분리다.
  timeout/lease/RPI/재접속 정책은 변경하지 않았다. 별도 통신 문제로 남기며 신뢰성 PASS로 보고하지 않는다.

## 배포 최소 범위와 복원

현재는 **미배포**다. 다음 운영 적용에는 새 승인이 필요하다.

1. 이 변경 commit과 기존 전체 runtime을 기준으로 정식 배포 manifest/Release ID를 생성한다.
   기능 변경은 위 Python 4파일(3수정+1추가)뿐이며, OpENer 바이너리/모델/설정은 보존한다.
   별도 TASK 전체 Candidate를 새 개발 원본으로 만들지 않는다.
2. 적용 직전 현장 정지·감독 확인, PLC Request/Result/Done 및 소유권을 재확인한다.
3. current 전체/실제 설정/systemd/Release/SHA와 일관된 SQLite 백업을 노트북에 확인한다.
4. 승인된 한 서비스만 정상 종료하고, 전체 구성 manifest에 맞춰 단일 current를 전환한다.
   실행 중인 프로그램에 개별 파일을 섞어 덮어쓰지 않는다. 이후 같은 서비스 시작·SHA/카메라/모델/PLC 확인.
5. 기존 소비 승인 원장을 보존한다. 새 첫 제품 시험은 별도의 현장 감독·물리적 시운전·결과 발행 승인 후 진행한다.
   실제 REVIEW/ERROR도 현 계약상 NG·Done이므로 벨트 재가동 가능성을 포함해 승인받는다.
6. 실패 시 서비스 정상 종료 후 노트북 직전 전체 실행본/원래 설정으로 복원한다.
   운영 Journal·승인 원장·모델을 과거 시점으로 되돌리지 않는다. 재시작 후 안전 대기 상태 확인.

복원 자료(노트북, 이번에 SHA 재확인):

- 직전 전체 current: `contract_classification/RELEASE_BUNDLE.tar.gz`,
  SHA `27fca7ce3fee4127c197e0eefbaf4f4c6adab122bf2929abb6020d6580e1c61f`.
- 보존 설정/서비스/이전 원장 backup: `contract_classification/OPERATING_BACKUP.tar.gz`,
  SHA `73ae4ccfc7cb5e936511b0472999eeb35f343692d8c41278023e306ad5a71da8`.
- 이번 최신 일관성 DB 복사: TASK017 `native_results/FINAL_journal.sqlite3`, `FINAL_approvals.sqlite3`.
  이는 복구 증거이며 승인 소비 상태를 되돌리기 위한 파일이 아니다. 실제 rollback 실행은 NOT_RUN.

## 증거 위치와 공개 범위

노트북 기준 폴더:
`runs/engine_standalone_plc_autostart_001/v001_20261007T052746Z/tag_data_link_008/assembly_integrity_017/`.

`BEFORE_REPRODUCTION.json`, `EVIDENCE_MANIFEST.json`, `TEST_RED.txt`,
`native_results/NATIVE_TESTS.log`, `native_results/replay_offline/REPLAY_VERIFICATION.json`,
`native_results/FINAL_VERIFICATION.json`, `RETRIEVAL_VERIFICATION.json`에 근거를 보존한다.
최종 native 증거 archive SHA:
`899cd1041abccf3d207e5536581414bb5f8cb8188f6d1cf99b5ffcecd5ba2390`.
51개 회수 파일의 SHA와 검증 소스 일치를 확인했다.

GitHub에는 소스·생성형 fixture 테스트·재생 도구·이 보고서만 올린다.
운영 DB, 현장 PNG, 개인 설정, 승인 원장, 비공개 run 파일은 올리지 않는다.
운영 배포·현장 재시험·모델 개선·Class1 원인 수정은 이번 Task에서 실행하지 않는다.
