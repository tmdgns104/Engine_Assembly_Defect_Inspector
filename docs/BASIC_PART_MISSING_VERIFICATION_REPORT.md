# 기본 부품 누락 검사 검증 — V1 판단

## 최신 실제 현장 검증 및 정책 수정

사용자가 승인한 배기 결품 한 제품 시험을 완료했다. 실제 검사 `5a0708cf246041d2a80a24c402c47f37`에서 새로운 원본 3장 모두 배기 슬롯 MISSING, 나머지 세 슬롯 PRESENT이며 기본 판정은 **FAIL / EXHAUST_TOP_MISSING**이었다. pose·슬롯 할당·영상 품질이 유효했고 PNG/픽셀 SHA 및 frame ID를 실제 Journal과 대조했다.

- 당시 Release `engine-integrated-a542b0df44800e81` / source `a005df502f635dcdbf15fb043e5a01db7ea908c9`.
- 조립 검사 세 프레임은 `SEED_INSUFFICIENT_SPATIAL_BODY_SUPPORT`로 정렬 실패, 부품 분류 미실행, 조립 REVIEW. 종전 결합 정책은 최종 REVIEW를 저장했다. 기본 FAIL과 통합 REVIEW를 구분한다.
- PLC 실제 송신: NG Result sequence 5285 → 다음 패킷 Done sequence 5286, 간격 50.38ms. Request 해제·출력 초기화와 현장 사용자의 벨트 재가동 및 마지막 STOP 확인. PLC 내부 로직 소비는 직접 읽지 않았다.
- 요청→통합 최종판정 9.834초, 요청→Result 9.894초. 원시 저장 commit 301.48ms. 검사 구간 표본의 health ready=true, 발행 시점까지 기록된 누적 최대 갱신 간격 216.32ms. 해당 연결 Class1 timeout 0.
- 결과 반환 후 약 22.9초에 카메라 Worker 교체와 `CAMERA_OR_OBSERVATION_STREAM_UNAVAILABLE`/DISARMED가 별도로 발생했다. 이 한 제품 결과를 연속 운전 안정성 PASS로 확대하지 않는다.
- 실제 원본 검출 그림: 비공개 `runs/basic_parts_missing_verification_001/recovery/ACTUAL_EXHAUST_MISSING.png`; 세부 검증 `FIELD_VERIFICATION.json`.

이후 사용자 지시에 따라 어느 검사든 확정 FAIL이면 최종 FAIL로 결합하도록 수정했다. PC/ARM64 각각 28개 회귀 PASS, 저장된 해당 검사 재결합은 FAIL. 운영 적용 Release `engine-integrated-2719dff19eb79478`, source `887ea3f2eb1ffd141e9c3641e222da4e6438138b`, 185파일 SHA 일치. 과거 실제 검사의 저장 REVIEW/원본 FAIL/PNG/송신 이력은 보존했으며 새로운 PLC 요청이나 결과 송신은 수행하지 않았다. 세부 규칙은 `CONFIRMED_FAIL_COMBINATION_FIX.md` 참조.

아래 저장 영상 검증과 시작 전 차단은 시간순 이전 기록이다. 기존 미송신 중단 검사 `60aa99de9b8a409fac7682572a06b5f6`은 사용자 추가 승인 후 요청별 누적 송신 기준을 검증하는 최소 수정으로 독립 ABORTED 처리했고, 미완료 차단 1→0을 확인했다. 원본·승인 기록을 수정하거나 가짜 final을 만들지 않았다.

2026-10-15. **저장된 실물 배기 결품은 현재 기본 부품 검사기에서 FAIL로 확인됐다.** 정상→결품→정상 복원 3개 장면의 기존 선택 20/23/26번 원본을 사용했다. 결과를 보고 프레임을 고르지 않았다.

| 실제 장면 | 프레임별 부품 검사 | aggregate_three 결과 | 기대 일치 |
|---|---|---|---|
| 정상 | 3/3 네 슬롯 PRESENT | PASS / ALL_REQUIRED_PARTS_PRESENT_3_FRAMES | PASS |
| 은색 배기만 분리 | 3/3 배기 MISSING, 나머지 PRESENT | FAIL / EXHAUST_TOP_MISSING | PASS |
| 정상 배기 복원 | 3/3 네 슬롯 PRESENT | PASS / ALL_REQUIRED_PARTS_PRESENT_3_FRAMES | PASS |

단일 결품 프레임의 REVIEW/AWAITING_THREE_FRAME_CONFIRMATION은 실패가 아니라 기존 3프레임 확인 대기다. 세 장을 결합하면 FAIL이다. AssemblyInspector의 MISSING은 이 결과에 사용하지 않았다.

## 실행 경로와 변경 여부

- 실제 `/home/jetson/oned_device_bench/current`를 직접 import했다. Release `engine-integrated-a8d842b879cd14ea`, 운영 185파일 SHA 일치. 해당 기본 검사 소스 5개도 노트북 jetson/과 일치했다.
- `EngineInspector.detect(parts_detector=...)` → 기존 `EnginePoseEstimator.estimate` → 해당 원본 전체 자세 보정 → 실제 부품 TensorRT 검출 → `engine_dynamic.inspect_frame` → `aggregate_three`.
- 실제 부품 plan SHA `743ce54b4d5c7b8a36addf3dbff50fa693ec4a509b31b476f68efc69f1bf2d6c`; envelope plan SHA `c82f2658ac20d06985a647c15e551c681e394451cfa1c53baed64f639bcebf83`.
- Pose 설정 SHA `1787dd7206b45f4ae4b6484a4b1883d2543f2c3da2d5e283f9c0e97c263e8afe`; D001 SHA `6dc94539570259d7747d8cc2b4d5fb0ed3d782b6b5a881408f427cd80c39f561`.
- 모델 입력 640×640, BGR→RGB, letterbox, confidence>0.25, NMS IoU0.45. 제품/부품 판정 confidence0.5、slot overlap0.4、3프레임 유지. 품질 기준 blur25、brightness35–225 유지.
- ARM64 Python3.10.12 / OpenCV5.0.0 / TensorRT10.3.0, 실제 GPU 실행. 모델 로드 포함 도구 전체5.30초. 서비스가 대기 중인 저장 영상 재생 시간이므로 현장 처리시간/throughput 성능 수치로 사용하지 않는다.
- 카메라를 열지 않았고 Assembly/Runtime/Journal/IPC 발행기를 생성하지 않았다. 운영 소스·설정·모델·서비스·PLC는 변경하지 않았다. C boot/connection/request3、Result2/Done2/Completed2가 재생 전후 동일했다.
- 재생용 motion 상태는 기록하되 강제 stable=True로 만들지 않았다. 요청 신선도·실물 Tracking·실제 정지 조건과 추가 운영 `assess_dynamic` 정책을 통과했다는 주장은 하지 않는다. 이번 판정은 사용자가 지정한 기본 검사/aggregate_three 결과다.

## 촬영 조건 및 원본 보존

모두 실제 1280×720 BGR 손실 없는 PNG다. 사용자 확인: 벨트 STOP·손 제거、네 부품 정상 → 배기만 분리 → 정상 복원. 카메라/조명 유지 지시하에 촬영했으며 정상 장면은 조명 추가 후 자료다. 장면 사이 몸체 위치가 달라 완전히 동일한 자세의 대조라고 단정하지 않는다. 촬영은 10월15일 KST10:20:37.996、11:01:27.918、11:18:59.563에 시작하는 선택 프레임이다. 현재 4.5초 이송의 정지 위치에 일반화하지 않는다.

- normal: `runs/assembly_ai_022/lighting_comparison/light_{20,23,26}.png`
- missing: `runs/assembly_ai_022/missing_exhaust_control/missing_{20,23,26}.png`
- restored: `runs/assembly_ai_022/restored_exhaust_control/restored_{20,23,26}.png`
- 원본 아카이브 SHA、선택 JSON SHA、원본 frame_id/sequence/epoch/source_pts_ns/worker_generation은 private `runs/basic_parts_missing_verification_001/input/manifest.json`에 기록했다. 원본 파일·메타데이터를 수정하지 않았다. 포착 과정 일부 누락은 기존 기록대로 유지하며 전체 연속 프레임 보존으로 주장하지 않는다.

## 프레임별 결과

아래 pose OK는 기존 검사기의 수치 기준 통과다. 독립적인 수동 기하 정답 검증을 새로 완료했다는 뜻은 아니다. 슬롯 순서는 왼쪽파이프/오른쪽파이프/배기/심볼이다.

| 장면/번호 | 각도° / scale | matches/inliers | median 오차px | slot_states | assignment_reliable | reason_code |
|---|---|---|---|---|---|---|
| 정상 20 | -93.37 / 0.865 | 49/16 | 1.055 | PRESENT/PRESENT/PRESENT/PRESENT | true | ALL_REQUIRED_PARTS_PRESENT |
| 정상 23 | -98.84 / 0.899 | 46/14 | 1.044 | PRESENT/PRESENT/PRESENT/PRESENT | true | ALL_REQUIRED_PARTS_PRESENT |
| 정상 26 | -99.16 / 0.902 | 51/17 | 1.188 | PRESENT/PRESENT/PRESENT/PRESENT | true | ALL_REQUIRED_PARTS_PRESENT |
| 배기 결품 20 | -89.06 / 0.860 | 69/36 | 1.236 | PRESENT/PRESENT/MISSING/PRESENT | true | AWAITING_THREE_FRAME_CONFIRMATION |
| 배기 결품 23 | -91.15 / 0.747 | 71/33 | 1.032 | PRESENT/PRESENT/MISSING/PRESENT | true | AWAITING_THREE_FRAME_CONFIRMATION |
| 배기 결품 26 | -89.73 / 0.857 | 91/39 | 1.396 | PRESENT/PRESENT/MISSING/PRESENT | true | AWAITING_THREE_FRAME_CONFIRMATION |
| 정상 복원 20 | -99.62 / 0.857 | 51/26 | 1.491 | PRESENT/PRESENT/PRESENT/PRESENT | true | ALL_REQUIRED_PARTS_PRESENT |
| 정상 복원 23 | -99.34 / 0.758 | 58/27 | 1.141 | PRESENT/PRESENT/PRESENT/PRESENT | true | ALL_REQUIRED_PARTS_PRESENT |
| 정상 복원 26 | -101.33 / 0.847 | 56/22 | 1.203 | PRESENT/PRESENT/PRESENT/PRESENT | true | ALL_REQUIRED_PARTS_PRESENT |

9장 모두 품질·제품 단일 검출·기존 pose·할당 신뢰도 통과. 이번 세 장면에서 ENGINE_POSE_UNCERTAIN/검출 실패/슬롯 오할당에 의한 차단은 없었다.

## V1 완성 가능 범위

**배기 결품 검출을 V1 기능으로 삼을 근거는 확보했다. 전체 V1 완성은 아직 미확인이다.** 기본 검출기를 다시 개발하거나 이번 결과에 맞춰 임계값을 조정할 필요는 없다. 오조립을 최종 정책에서 제외하는 변경은 수행하지 않았다.

추가 현장 시험으로 현재 검사 위치의 배기 결품 1회 근거는 확보했다. 정상 복원의 실제 요청 결과와 다른 세 슬롯의 단독 결품 자료는 남아 있다. 한 실물의 같은 장면 3장은 세 개의 독립 결품 사례가 아니며 정확도·재현율을 추정할 표본이 아니다.

## 추가 승인된 실물 1회 시험: 시작 전 차단

사용자가 현장 STOP·작업 영역·방호·감독을 확인하고 배기 결품1회 시험을 승인했다. 그러나 START 안내 전에 기존 별도 요청의 미완료 기록을 확인했다. **아직 새 현장 시험을 실행하지 않았다.**

- 이전 검사 `60aa99de9b8a409fac7682572a06b5f6`: KST17:05:16 접수、17:05:27 원시 Journal COMPLETE、3프레임 기본 PASS. 저장 중 STORAGE_DEADLINE_EXCEEDED로 ready=false/PYTHON_NOT_READY 취소. Assembly 미실행、통합 최종판정 없음、새 Result/Done 없음.
- C REQUEST_RECEIVED→TRIAL_ABORTED_NO_NEW_DONE 사이 누적 Result/Done/Completed는 모두2→2. 이 요청이 실제 미송신이라는 근거이며 0으로 바꾸면 안 된다.
- 현재 STOP/Request OFF/출력0、Worker/Assembly 유휴、C DISARMED. 미완료1건으로 JOURNAL_UNFINISHED_INSPECTION.
- Reset preflight는 이미 닫힌 이전 완료검사 d6982a...만 대상으로 보며 CONTEXT_RECOVERY_ALREADY_RECORDED. 새 미완료검사는 이 UI 경로로 정리하지 못한다.
- 기존 `aborted_recovery.validate_evidence`는 실패 이벤트의 누적 송신 count가0인 경우와 새 adapter boot만 허용한다. 이 첫 요청 전용 가정 때문에 현재 누적2에서 실패한 요청은 정당한 무송신 증거가 있어도 그대로 복구할 수 없다. 사용자에게 새로운 제품별 승인 권한을 요구해서 해결할 문제는 아니다.

## 필요한 최소 복구 범위(미적용)

기본 검사/모델/PLC 정책을 바꾸지 않고、기존 중단 정리에서 해당 요청 시작 시 누적 count와 종료 count의 동일성을 검증할 수 있어야 한다. boot/connection/request/PID 일치、취소 이벤트、원시 결과 SHA、현장 STOP·출력0·유휴、원본 보존과 늦은 결과 재발행 금지를 함께 유지해야 한다. 단순 unfinished 제외、count=0 위조、가짜 final、DB 초기화는 안 된다. 정상 검사마다 복구를 요구해서도 안 된다.

이는 현재 사용자가 제한한 기본 검사 성능 확인을 넘어 운영 중단 복구 코드/서비스 적용 범위다. 배기 FAIL 원본 증거와 분리하여 보고하며 별도 범위 확인 없이 운영 파일/서비스를 변경하지 않았다. 위 복구가 완료되기 전 START를 반복하지 않는다. 저장 지연 자체의 완화·timeout 확대도 이번에 수행하지 않았다.

## 재현/보관

- 개발 도구: `notebook/diagnostics/replay_basic_part_presence.py` (운영 allowlist에 추가 안 함)
- 비공개 증거: `runs/basic_parts_missing_verification_001/`의 input manifest、output RESULT/SHA256、FIELD_PREFLIGHT、PREFLIGHT_C events/status、BASIC_PARTS_COMPARISON.html/png.
- 새 그림은 실제 원본 위 기존 운영 검출 overlay이며 AI 생성·합성 결품이 아니다. raw·정답자료·설정·Journal은 GitHub에 올리지 않는다.
- 검증: 9PNG/pixel SHA、모델/소스 SHA、9개 frame_id/source time、같은 epoch와 증가PTS、3개 실제 aggregate 재계산、원격 산출물10파일 SHA、운영 요청/송신 불변 확인. 이전 LoFTR/형상/LK 결과는 보존하고 새 정렬 알고리즘은 추가하지 않았다.

## 원본 SHA-256

| 파일 | PNG SHA-256 | BGR pixel SHA-256 |
|---|---|---|
| normal_20.png | `5dd1e3d15b279fe256dec6b439a4ac16d757840e78005dfb4f62903a92555b12` | `25ed48e365c8a7ad9bbe76c4e5dcf5b3a580ac80c030f93b98e1c91599d17b37` |
| normal_23.png | `7c32f69af3dee79ca93416115d8c3e38aa988ac17bfdb01d23bb5454476018ca` | `c58630cc14dc04a13adf9018e3c1c37e6539d886ee09440098605c56ca4a3500` |
| normal_26.png | `d11cdb3c6603305b1a149d55717158c97d1540be9213a72ca4bf93d2d52c16ef` | `f187ac4390e8ab510f4e46bc290692c17971bfa4db847885ddc9d0f788e80f6f` |
| missing_exhaust_20.png | `385982e57a5133fa83b18fa48225d6cb1f45a647670a0d9b4336656dd3cd7a2d` | `3fda16d2ffcf596f4e831e52372ccb2bc965db15cd50005e67d3e03575cb8578` |
| missing_exhaust_23.png | `a5b1ad4aba9c8eec7b42da990f43a2b7a8d19cd48f9bcb3db4d944d72b1d3999` | `788ecc4f281f88aeda70d2bf307fa58b8b0fc946364c6852a614b7a6012b0919` |
| missing_exhaust_26.png | `dc8829c1bd2136ba88653f933e3e92a816d32d655f579a6475043eed299b7b34` | `29360d09eef5180c164185ad71194791d0c2432c9b6b06092a65e18e53d102c9` |
| restored_20.png | `fa1f70f6cedbc4e262e0480b3d634eaed6f6e6863ee8c26bbdcf0b0bca6cde29` | `58e616110ccf2668811262ced11f61ea3908c270c93a42f23dac36c1609a1a5c` |
| restored_23.png | `035d45274387841c420cc804eb7326275051e2f213e99dfe01b23a4c6f093816` | `cf85a40b75b78ec26412e60c2d391e6deb47c642d41ee1ed4ac03133d7d71792` |
| restored_26.png | `b3e41d4a9f6f2e0929300c38feb1454c3b5005de562b418e83e342355ff579f6` | `22ea0b7bff5a4c67c05ce44e1c28b3bf4a4a2d9da05357954056c11750f57967` |
