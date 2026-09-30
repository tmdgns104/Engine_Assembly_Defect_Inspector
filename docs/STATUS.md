Latest Task (2026-09-30, GITHUB-DEPLOYMENT-001):
**PUBLISHED / CHECKOUT_VERIFIED / FRESH_HARDWARE_UNVERIFIED.** 현재 TensorRT 모델 두 개와 Pose·기동 자산을 `jetson/products`에 포함하고, 자체 포함 목록/패키징·새 장치 설치기, Windows 환경 설치/간편 촬영 바로가기와 발표 README를 정리했다. Git export의 깨끗한 소스에서 Windows 68건·Linux 배포 25건·최종 설치 5건 PASS. 새 Windows venv의 pip check·GUI 5건 PASS. 공개 master 구현 `ce49b15`의 로컬/원격 SHA 일치 및 GitHub 모델 바이너리 크기를 확인했고 GitHub Actions 36658234340 SUCCESS. 실제 Jetson/PLC 변경 없음. 새로운 Orin·다른 노트북의 실물 수용은 UNVERIFIED. 동시 진행 중인 촬영 앱 추가 수정은 검증 snapshot 이후 변경으로 보존한다. 상세: `tasks/GITHUB-DEPLOYMENT-001.md`, `docs/verification/GITHUB-DEPLOYMENT-001.json`.

Latest Task (2026-09-30, ENGINE-MISASSEMBLY-CAPTURE-001 사용성/카메라 회귀 수정):
**WINDOWS_FROZEN_UI_AND_HCAM_PREVIEW_VERIFIED / TEAMMATE_PC_NOT_RUN.** 기존 큰 영상·정렬/360° 안내를 복원하고 TRAIN의 실제 ROI를 재사용했으며 꼬리 여유만 추가했다. 10° 새 오조립 504 + 기존 정상/결품 부족 각도 144 + 장치 정상 대조 6 = 654장 계획. 한 클릭 촬영, 준비/저장 중 단계 고정, 자동 다음 안내, 재촬영/재개 유지. EXE 시작 준비가 카메라 첫 영상 15초 한도를 소비하던 원인을 계측하고 준비(30초)/장치 첫 영상(15초) 대기를 분리했다. 저장 준비 후 새 프레임 선택으로 느린 파일 준비의 stale 실패도 수정했다. 집중 source 46건, source writer 8항목, 최종 추출 EXE GUI 7항목, 실제 HCAM01L로 열거된 DSHOW 후보 1의 1280×720 fresh 40프레임 PASS. 최종 ZIP CRC/상대경로/1100파일/41개 빌드 입력 해시 PASS. 전달: `dist/engine_misassembly_capture/20260930_102438/Engine_Misassembly_Capture.zip` (81,552,250 bytes, SHA-256 `a90ac39174d00f19be0c18d7c9182138c54eb97a741803be84fa104a4dce13bf`). 실물 엔진 원본 저장·팀원 PC·후속 검토/학습은 NOT_RUN. 이전 실패/원본/승인 보존, Jetson/PLC 변경 없음. 상세: `tasks/ENGINE-MISASSEMBLY-CAPTURE-001.md`.

Latest Task (2026-09-29, ENGINE-MISASSEMBLY-CAPTURE-001):
**PACKAGE_BUILT_AND_WINDOWS_SYNTHETIC_VERIFIED / PHYSICAL_CAMERA_NOT_RUN.** 기존 `notebook/training/capture_windows`에 클릭 선언과 저장 완료를 분리한 간편 촬영 정책, 상태별 54장 파일럿 계획, 학습용 NORMAL 출처 사진 및 복합 오조립 사진의 부품 부분 안내, Windows 독립 EXE/전달 ZIP을 추가했다. 기존 Wizard/촬영 회귀 47건과 소스 합성 점검, 추출 EXE 자가점검 8항목, ZIP CRC/입력 해시 PASS. 실제 USB 카메라 촬영·팀원 PC 조작·후속 라벨 검토/학습은 NOT_RUN. 배포: `dist/engine_misassembly_capture/20260929_173939/Engine_Misassembly_Capture.zip`; 상세: `tasks/ENGINE-MISASSEMBLY-CAPTURE-001.md`. 기존 수집 원본·승인 기록·Jetson/PLC 변경 없음.

Latest Task (2026-09-29, ENGINE-CONVEYOR-MOTION-001, PLC 상시 AUTO 종료 체크포인트):
**PARTIAL_BLOCKED / 컨베이어 입고 후 재개.** Jetson `current`는 `engine-dev-745e95e832c6b402`, 실제 PLC 이동 벤치 설정, 물리 출력 비활성이다. 직전 릴리스의 실제 재부팅에서 `@reboot` AUTO·HCAM·PLC ARMED 확인, 최신 릴리스는 부팅 코드 변경 없이 managed 배포 후 같은 `boot_live.py`로 AUTO 재가동. 노트북 `/auto` 터널 예약 작업의 배터리 중단 설정을 수정하고 HTTP 200·화면 복구 확인. 최신 실물 요청은 Track 1→고유 3프레임→durable REVIEW→PLC Result=1/Done=1 ACK→Request OFF/Done=0까지 확인했으나 제품 이동이 440ms 수집 구간에 없었다. Sysmac의 Result=0 표시와 PLC 직접 CIP Result=1 읽기가 불일치한다. 빈 Live에서도 작업면 우측 상단을 OCCUPIED로 오인해 Track 1 자동 종료가 막혀 있다. 관련 42개 시험 통과; 실제 이동 PASS·연속 제품·실제 컨베이어·PLC 프로그램의 내부 결과 사용은 미검증. 상세: `tasks/ENGINE-CONVEYOR-MOTION-001.md`.

Latest Task (2026-09-29, ENGINE-CONVEYOR-MOTION-001, PLC 상시 AUTO 후속):
Jetson `current`에 `engine-dev-92ea335890a447e0`과 명시적 `CONVEYOR_MOTION_PLC_BENCH`/`OMRON_CIP_BENCH` 설정을 적용했다. PLC가 꺼져도 빈 화면·정상 카메라에서 AUTO 추적을 시작하며, 유효한 Request=0 확인 후 요청 상승 시 같은 Track/Cycle을 고정해 이동 3프레임 검사를 시작한다. PC 관련 40개 테스트·기존 이동 저장 사례 PASS/REVIEW 보존·Jetson 실행 릴리스/단일 카메라 Worker/AUTO·PLC ARMED·Request=0 확인. 실제 재부팅과 새 릴리스에서 실물 요청→Result/Done 검증은 진행 중이다. 물리 출력은 비활성이고 실제 컨베이어·포토센서·배출은 미시험. 상세: `tasks/ENGINE-CONVEYOR-MOTION-001.md`.

Latest Task (2026-09-29, ENGINE-CONVEYOR-MOTION-001, 전체 시야 후속):
이동 MOCK Capture 영역을 전체 시야로 설정하고 같은 `engine-dev-76fbafd5473fd110`을 Jetson `current`에 적용했다(설정 SHA `661e22f9...abfd`). 합성 경계 잘림 거부·저장된 이동 REVIEW/PASS 보존·관련 10개 테스트 통과. 사용자 손 이동 1회에서 Track 1, 자동 요청, 고유 3프레임 PASS, MOCK ACK/Request OFF, 완전 이탈 뒤 자동 종료 및 다음 제품 대기 확인. 원본에 손이 있고 세 프레임 중심은 종전 영역 안에도 있었으므로 확장된 가장자리와 실제 벨트는 미검증. 관측 약 12 FPS이며 FPS 향상은 이번 설정 변경으로 달성되지 않았다. 증거: `tasks/ENGINE-CONVEYOR-MOTION-001.md`, `archives/jetson/engine-conveyor-motion-001/full-view-motion-inspection.json`.

Latest Task (2026-09-29, ENGINE-CONVEYOR-MOTION-001):
MOVING_BENCH_SOFTWARE_READY — 이동 자율 시험 Track 4에서 3초 frame 수집 deadline과 서비스 취소가 경합해 durable REVIEW 대신 `DEADLINE_EXCEEDED` FAULT가 발생했다. 실패 원본/상태를 노트북에 보존했다. 이동 모드에서만 수집 deadline(3초)과 결과 저장 대기(기존 검사 제한 15초)를 분리한 `engine-dev-76fbafd5473fd110`을 Jetson `current`에 적용하고 관련 36개 시험 통과. 수정 후 HCAM 이동 1회에서 unstable 고유 3프레임 PASS, MOCK durable Result/Done·ACK·Request OFF, 엔진 제거 후 Track 1 자동 종료와 다음 제품 대기 확인. 저장 원본에는 손이 보인다. 프레임 부족의 수정 분기는 focused 재현 시험으로 검증했고 실물 재발 시험은 하지 않았다. 이전 STATIONARY PASS와 이동 Track 2 PASS는 이전 릴리스 `engine-dev-bfb708658d0768f6`의 결과다. 실제 컨베이어·PLC는 미검증이며 기존 전체 회귀는 무관한 earbud fixture 6건 누락으로 미완료. Task/증거: tasks/ENGINE-CONVEYOR-MOTION-001.md, archives/jetson/engine-conveyor-motion-001/.

Latest Task (2026-09-16, JETSON-P0-004B):
DONE / BACKEND_CONTRACT_IMPLEMENTED_CANDIDATE_ONLY — P003 exact32 SHA baseline에서 새 Windows candidate만3수정+factory1추가. Legacy PyTorch/default/명시backend·schema2 TRT 선언·neutral metadata/Worker 연결 검증. TRT는 NOT_IMPLEMENTED, fallback/import/read0; schema-valid는 실행승인 아님. 기존114 regression semantics(원본 tests 보존, task-local mock1개 확장/기존 assert 동일)+새28 PASS, skip0/candidate import origins 확인. DetectionResult/PyTorch 기존 methods 불변, root/P003/P004A/package/DB/assets/PC mirror/Jetson37그룹 SHA 동일. GPU/camera/export/build/deploy0, HEAD/git diff --check PASS, commit·push0. Export/precision/NMS 미정·parser/plugins UNKNOWN/tolerance TBD, ROOT_CAUSE_UNCONFIRMED 유지. P004C 별도승인 전 NOT_STARTED. Report: docs/jetson/JETSON_TRT_BACKEND_CONTRACT.md; Evidence: docs/verification/JETSON-P0-004B.json.

Latest Task (2026-09-16, JETSON-P0-004A):
DONE / PREFLIGHT_COMPLETE_IMPLEMENTATION_NOT_AUTHORIZED — 지정 ChatGPT 대화와 협의한 읽기 전용 TRT 준비 점검. Detector/factory/package/health 경계와 legacy 호환 방향, installed exporter/reader/container/profile/자동 설치 경로, provenance/parity 계약을 정리했다. TRT10.3/ONNX1.22/ORT1.23.2/trtexec 파일 관측, simplify=True의 onnxslim 조건부 부재. 기존 ONNX SHA 동일하나 parity NOT_RUN; export/NMS/loader DECISION_PENDING, precision 승인 NONE/tolerance TBD. SSH2회 metadata/source/hash만, framework import/GPU/camera/export/build0, Jetson 새 파일0, 보호36그룹+overlay/current/로컬462파일 변경0. P003 Runtime/raw FROZEN 유지. 구현 B~F는 별도 초안/NOT_STARTED, 원인 UNCONFIRMED/production 미수용, commit·push0. Task: tasks/JETSON-P0-004A.md; Report: docs/jetson/JETSON_TRT_READINESS_PREFLIGHT.md; Evidence: docs/verification/JETSON-P0-004A.json.

Latest Task (2026-09-16, JETSON-P0-003):
DONE / LATENCY_INSTRUMENTATION_VERIFIED_LAB — R4 결과를 지정 ChatGPT 대화에 공유하고 사용자 계속 진행 요청 범위에서 candidate-only 계측 검증 완료. 새 R2 exact-copy Candidate의 Detector1파일만 optional metadata 추가, root runtime 변경0. 기존102+timing12=114 tests/collector selftest PASS. PID21354 단일 process19.837초, warmup1/warm10cycles/30observations, DB COMPLETE10/REVIEW10/publication10/late0/raw30+overlay10 SHA PASS. NvMap/NVML/allocator/Python/CUDA exception/epoch 변화/invalid selection0. monotonic_ns/기존 sync만 사용(추가0), H2D null·Ultralytics reported timing 별도. host detect p5054.075/p9591.272ms(n30), trigger→durable p50717.406/p95801.362ms(n10), production threshold NOT_DEFINED. 보호36그룹/overlay/current/Windows source/PC mirror/이전 evidence SHA 동일. ROOT_CAUSE_UNCONFIRMED/Conveyor NOT_RUN/commit·push0. P0-004/TRT 자동 착수 없음. Task: tasks/JETSON-P0-003.md; Report: docs/jetson/JETSON_LATENCY_INSTRUMENTATION.md; Evidence: docs/verification/JETSON-P0-003.json.

Latest Task (2026-09-16, JETSON-P0-002R4):
DONE / LONG_LIVED_RUNTIME_STABILITY_PASS_LAB — 단일 PID20883에서 Camera/Detector/CUDA/Journal/session 각1회 초기화 후30/30 full cycles, warmup1/fresh detect90, raw90/overlay30 SHA·ID 연결 PASS. SQLite integrity ok/COMPLETE30/publication30/late0, stderr·Python/CUDA exception·epoch 변화·invalid fresh selection0. process35.803초의30-cycle lab gate이며 endurance/production/root cause resolved가 아니다. MemAvailable2,179,752→2,177,436kB, CUDA allocated12,142,592→12,142,080B/reserved60,817,408B 동일. 원본34그룹/overlay/current/Windows source/PC mirror/이전 evidence SHA 동일, runtime source/환경/시스템/PLC/MQTT/commit·push 변경0. P0_003_ACTUAL_DEVICE_READY=true는 latency instrumentation 시작 한정; ROOT_CAUSE_UNCONFIRMED. Task: tasks/JETSON-P0-002R4.md; Report: docs/jetson/JETSON_LONG_LIVED_RUNTIME_SOAK.md; Evidence: docs/verification/JETSON-P0-002R4.json.

Latest Task (2026-09-16, JETSON-P0-002R3):
DONE / NVMAP_NOT_REPRODUCED_IN_BOUNDED_STAIRCASE — A~H 각1회+H 추가5회, 새 process13개 모두 stderr clean/exit0. Parent 실시간 pipe 수신 monotonic과 Child stage/memory456개, close/BEFORE_PROCESS_EXIT 이후 teardown까지 수집. warmup11/fresh detect28회, Recipe/encode/diagnostic Journal 추가 조합에도 NvMap/NVML/allocator 문자열0·Python exception0. 최초 발생 Case/interval과 직전 memory는 N/A, ROOT_CAUSE_UNCONFIRMED 유지. 계측 타이밍 영향·과거 오류 미해결을 명시하며 P0-003 BLOCKED. 보호33그룹/overlay/current 및 Windows source/PC mirror/이전 evidence SHA 동일. 새 파일은 diagnostics/p0_002r3_nvmap 안에만 생성; source/환경/camera 설정/PLC/MQTT/commit/push0. Task: tasks/JETSON-P0-002R3.md; Report: docs/jetson/JETSON_NVMAP_STAGE_DIAGNOSIS.md; Evidence: docs/verification/JETSON-P0-002R3.json.

Latest Task (2026-09-16, JETSON-P0-002R2):
DONE / REACCEPTANCE_PARTIAL_RUNTIME_ERROR_REPRODUCED — 통합 cold process10/10 PASS(카메라 열린 상태 Detector 전후5프레임, stderr0), 실제 LOCAL_TEST Fresh Frame10/10 PASS/잘못 선택0. 모델 cycle은 Recipe3프레임·REVIEW·raw3/overlay1 SHA·candidate SQLite commit 후 local publish까지 기능 PASS했지만 stderr NvMap error12 재현으로 D runtime 수용 FAIL. NVML assertion/예외 종료 없음, 정확한 출력 단계·물리 원인은 미확정. 오류 확인 후 추가 GPU 재실행·복구0. A 기존102 tests 유지(source 변경0/재실행 안 함), E conveyor NOT_RUN, P0-003_ACTUAL_DEVICE_READY=false/BLOCKED. app_v007/app_v1/overlay/기존 candidate/package/model/DB/assets/PC mirror/Fresh Frame source/settings 전후 SHA 변경0. 새 candidate32/data7/diagnostics85파일; 기존 사용자 변경 보존, commit/push0. Task: tasks/JETSON-P0-002R2.md; Report: docs/jetson/JETSON_INTEGRATED_RUNTIME_REACCEPTANCE.md; Evidence: docs/verification/JETSON-P0-002R2.json.

Latest Task (2026-09-16, ENGINE-DATASET-SKILL-SUITE):
DONE / LOCAL_ARTIFACT_CHECKS_PASS / TEAMMATE_EXECUTION_UNVERIFIED — 촬영 동행·설치/Pilot·카메라/관측 진단·Main/Challenge·검토/재촬영·재개/백업·Export/팀 인계·개발/배포 유지보수의8개 스킬과 공통 계약/시작 문구/목록 작성. 스킬 ZIP33,386 bytes와 기존 EXE/가이드 포함 통합 ZIP95,499,921 bytes를 dist/engine_dataset_wizard/20260916_skill_suite/에 생성. 기존113배포파일 byte 동일; 원본/소스/이전지원ZIP153파일 hash 동일. 스킬 원본8/해제본8 validation, YAML/UTF-8/상대링크/ZIP CRC·hash, 포장기9 tests PASS. 실제 화면·클릭 기능 추가나 EXE 재빌드/카메라 열기/데이터 변경/Jetson 작업/commit·push0. 팀원 PC의 스킬 발견·도구 접근·실제 촬영은 미검증. Task: tasks/engine-dataset-skill-suite.md; Evidence: docs/verification/ENGINE-DATASET-SKILL-SUITE.json.

Latest Task (2026-09-16, ENGINE-DATASET-CODEX-SUPPORT):
DONE / LOCAL_ARTIFACT_CHECKS_PASS / TEAMMATE_EXECUTION_UNVERIFIED — 팀원 앱에 영상이 보인다는 사용자 확인에 따라, Codex 관측 실패와 카메라 실패를 구분하는 프로젝트 스킬·시작 문구·적용 안내를 추가했다. 배포: dist/engine_dataset_wizard/20260916_codex_support/EngineDatasetWizard_CodexSupport.zip (9,149 bytes, 6파일). 기존 EXE에 추가하는 지침이며 화면·클릭 도구나 MCP를 설치하지 않는다. 원본/압축 해제 스킬 validation, UTF-8/YAML, ZIP CRC/원본바이트/덮어쓰기 거부 PASS; 기존 배포·촬영 소스152파일 hash 동일. EXE 재빌드/카메라 열기/데이터 변경/Jetson 작업/commit·push0. 팀원 화면 갱신·도구 접근·실제 촬영 재개는 미검증이며 원격 원인을 확정하지 않는다. Task: tasks/engine-dataset-codex-support.md; Evidence: docs/verification/ENGINE-DATASET-CODEX-SUPPORT.json.

Latest Task (2026-09-16, JETSON-P0-002R):
DONE / FAILURE_NOT_REPRODUCED_WITH_CONTROLLED_EVIDENCE — CASE G INTERMITTENT / ROOT_CAUSE_UNCONFIRMED. 새 process 23개에서 allocation(최대256 MiB), kernel, CPU/CUDA Conv2d, model CPU load/CUDA move/640 warmup, Ultralytics 및 기존 PyTorchDetector 모두 PASS. 최초 실패 단계는 재현되지 않았다. NVML 초기화 성공, compute-process query Not Supported(3); 원래 NvMap/allocator 실패 원인은 미확정이다. app_v007/app_v1/기존 package·model·DB·assets·사용자 패키지/settings·P0-001R overlay·P0-002 candidate 전후 SHA 변경0, Fresh Frame 소스 변경0. 새 diagnostics/p0_002r_cuda에만 진단 파일87개 생성. Windows 외부 Task 문서1개 동시 변경은 별도 기록하고 보존했다. 패키지/allocator/전력/CMA/swap 변경, camera open, PLC/MQTT, commit/push0. 다음은 원래 Candidate 복합 Runtime Gate 재현·재수용이며 P0-002 실제 Fresh Frame 재개는 BLOCKED. Task: tasks/JETSON-P0-002R.md; Report: docs/jetson/JETSON_CUDA_ALLOCATOR_DIAGNOSIS.md; Evidence: docs/verification/JETSON-P0-002R.json.

Latest Task (2026-09-16, JETSON-P0-002):
IMPLEMENTED / CONTRACT_TESTS_PASS / DEVICE_GATE_BLOCKED — Candidate Fresh Frame Trigger/epoch/PTS/age/취소/deadline 계약 및 Worker·Service·원장 연결 구현. 새 27 + 기존 Runtime 75 = 102 tests PASS. Candidate Gate A import/bridge/CUDA, B 카메라 memory-only 5 frames PASS. C는 기존 승인 이미지에서 Detector 1회 시도 중 CUDA allocator NVML_SUCCESS assertion으로 실패해 실제 Fresh Frame/모델 결합/Conveyor acceptance는 NOT_RUN. 별도 app_v008_dev_p0_002 소스 32파일·Python 30 compile 검사, 실패 Gate가 launcher 시작을 차단하여 후보 DB/검사 기록 0. app_v007/app_v1/earbud/model/기존 DB/assets/P0-001R overlay·PC mirror 전후 hash 비교는 verification 참조. 환경 재설치·PLC·MQTT·TRT 변환·Dataset 변경·commit/push 없음. 다음은 CUDA allocator 원인 확인 및 P0-002 Runtime Gate 재수용이며 P0-003 실제 성능 검증은 BLOCKED. Task: tasks/JETSON-P0-002.md; Contract: docs/jetson/JETSON_FRESH_FRAME_CONTRACT.md; Evidence: docs/verification/JETSON-P0-002.json.

Latest Task (2026-09-16, JETSON-P0-001R):
PASS_MINIMUM_ACCEPTANCE / PREPROCESS_READY ? ?? app_v007/app_v1? ???? env_candidates/numpy_compat_001/overlay? NumPy1.26.4? ????? ?? ????. ?? torch2.8/CUDA12.6/OpenCV5?? from_numpy??CUDA ???OpenCV memory smoke PASS, ?? ?? raw1?? ?? Ultralytics ??? [1,3,640,640] FP32 ? ?? ?? ??0.0. model inference/???/?????/DB??/PLC/MQTT0. ??release50/package7/model/DB/assets72/app_v1??1998 ? ?? ??????????? hash ??0; ?? NumPy2.2.6/from_numpy ??? ????? app_v007 ??? ???? ???. Candidate? pip check? OpenCV numpy>=2 ?? ??? ?? pynacl?cffi ???? FAIL; OpenCV downgrade? ?? ??0. P0-002 Candidate ?? ?? ??, ???? Runtime? ?? ????/?? ?? ? BLOCKED. Task: tasks/JETSON-P0-001R.md; Report: docs/jetson/JETSON_RUNTIME_DEPENDENCY_RECOVERY.md; Evidence: docs/verification/JETSON-P0-001R.json. commit/push0. ?? ??/?? ?? ??? ????.

Latest Task (2026-09-16, JETSON-P0-001):
AUDIT_COMPLETE_WITH_FINDINGS / Runtime ?? ?? ??? ? app_v007 ????????????PLC?MQTT?TRT ???commit/push ?? ?? ???21? Gap ?P0-002~007 ?? ??. ?? L4T36.4.7/torch2.8.0/CUDA12.6/TRT10.3.0; ??PC?? ??. OpenCV5.0/NumPy2.2.6 ???? torch.from_numpy? Numpy is not available? ??? ?? ?? ?? PASS? ???? ???. Windows Runtime fixture61???? Python28??/shell???????? PASS. ??release50/???7/?????144/DB???WAL???18???? hash ??. ?? import? Ultralytics ?????? ?? ???? PC read-only SQLite? SHM? ??? ??? ?? ??; ?? ?? hash? ???, ????0. ???release_files(app_v005)? ??accepted_at1? ??? ??. ?? P0-002 Fresh Frame? DRAFT?? ?? ?? ?? ?? ?? ??? ??? ????. Task: tasks/JETSON-P0-001.md; Baseline/Gap: docs/jetson/; Evidence: docs/verification/JETSON-P0-001.json. ?? ?? ?? ??? ??? ????.

Current Phase:
V0 Proxy Inspection System — 진행 중, 전체 완료 아님

Latest Task (2026-09-16, ENGINE-DATASET-WIZARD-V1-RELEASE):
DONE / V1 PREVIEW — EXE + 오프라인 상세/빠른 가이드 배포 ZIP 생성: dist/engine_dataset_wizard/20260916_v1_preview_r2/EngineDatasetWizard_Windows_x64.zip (95,466,551 bytes). 회전 각도 안내·Crank·Station·288계획·E04 잠금 유지. 첫 EXE의 긴 경로 저장 실패를 Collection 경로 정규화로 보완했고 Windows 설정은 변경하지 않았다. 전체281 tests(engine54, 기존 capture/Wizard65 포함)·실제 독립 EXE 합성 저장/재개/계약·일반 시작/종료 PASS. ZIP CRC/입력119해시·HTML3/이미지53경로 PASS. 현재 수집10파일/이전raw11 해시 동일, 실제앱은 정상 종료. 포장 중 촬영/라벨링/E04열람·unlock/commit·push0. 가이드는 DRAFT/TODO10 유지, 실제 전체 Pilot/Main 수용과 팀원 물리 PC는 미검증. 브라우저 도구의 로컬 HTML 보안 차단으로 브라우저 화면 배치도 UNVERIFIED. Main/Pilot0·현재 NORMAL1 PENDING/이전2 RETAKE·새 FAIL0 상태는 유지한다. 아래 배경 정리 대기 상태는 다음 촬영 재개 때 사람이 확인해야 한다. Task: tasks/engine-dataset-wizard-v1-release.md; Evidence: docs/verification/ENGINE-DATASET-WIZARD-V1-RELEASE.json.

Latest Task (2026-09-16, ENGINE-CAPTURE-GUIDE):
새 전체누락 촬영 전 배경 확인 대기: 사용자 제거 완료 뒤 L22에서 대상4개 제거/V8 유지가 보였다. 새 NORMAL L21 오른쪽에 있던 투명 비닐봉투가 사라져 부품 외 배경 차이가 생겼으므로 셔터 전에 중단했다. 봉투를 이전 오른쪽 가장자리 위치로 복원하도록 안내한다. 새 FAIL 저장0, 누적저장3/RETAKE2/Main0, Crank 사람 확인3항목 미체크 유지. 이 단계는 촬영 성공이나 품질 승인이 아니다.

초점 조절 후 NORMAL 기준 재촬영 저장: 사용자가 Crank0 준비 완료를 확인하여 실제 UI 확인/촬영을 실행했다. 새 capture_id 끝be47bd9a48d1, PNG1280×720/SHA256d209df343cbada32f4cc9115c7db42bbc11f170e800b01230628519e6af2ff0d, 품질경고0. 원본에서 문양/경계 개선을 확인했으며 최종 사람 사진 검토는 PENDING이다. 새 Capture ID·이전2원본/기존raw11 해시 보존·동일 바이트 Guide L21 PASS. 누적저장3(RETAKE2), Main/Pilot0. 현재 엔진은 정상이고 다음 MISSING_ALL_TARGETS Crank0 창3항목 미체크로 물리 제거 대기. Evidence: runs/engine_capture_live/focused_normal_verified.json.

초점 조절 후 새 기준 준비: 사용자 정상 재조립 완료와 L19 화면의 파이프2/배기구/문양 및 배기구 방향을 확인했다. 기존2건은 실제 Review UI에서 `초점 조절 전 흐림 · 새 기준 재촬영` 사유로 RETAKE 처리했고 PNG는 보존했다. 기존 설정 저장 경로로 새 setup `SETUP273F8A45848B416C` 생성, 품질/정렬 영역 유지. 현재 실제 Crank0 확인창3항목은 미체크이며 사람 확인 대기다. 새 Dataset 저장0, 누적2건 retained_retake, Main/Pilot0. 실제 RETAKE 화면 L20이 기존 합성20 예시를 대체한다. Evidence: runs/engine_capture_live/focus_retake_verified.json.

수동 초점 해결 관측: 사용자가 렌즈를 손으로 돌려 초점이 맞았다고 확인했다. 실제 Preview L18에서 L16보다 V8 글씨/빨간 부품 경계가 또렷해 보이며, 물리 조절은 사용자가 수행했다. 소프트웨어 AF/이미지 복원/높이 변경 없음. 기존 fixed focus 문구만으로 수동 조절 불가를 추정한 안내를 정정하고 상세/빠른 가이드·하드웨어 사양 근거에 보완했다. 현재 검사 대상 전체누락, 기준2장 미승인·원본 보존·Main/Pilot0. 다음은 정상 부품 복원 후 새 기준 설정/사진에서 전체 대상 선명도 확인이다.

초점 점검 제약 업데이트: 사용자 눈대중 렌즈~엔진 윗면20~30cm, 별도 거치대가 없어 높이 조절 불가. 제안한5cm 이동은 수행되지 않았으므로 카메라 이동/초점 개선으로 기록하지 않는다. 실제 UI 수집 일시정지·Preview 연결 유지, 렌즈 앞 보호필름/오염 확인부터 진행한다. 기준2장 미승인, 신규 Dataset 촬영 없음. 점검 전 실제 화면 L16을 가이드에 추가했고 문서/계약·이미지 검사 PASS(67 PNG/활성56/TODO11), DRAFT 유지.

초점 점검 중: 사용자가 원본 선명도 문제 해결을 요청했다. NORMAL 원본1280×720의 문양/경계 흐림을 확인했으며 원인은 아직 미확정이다. Windows에 HCAM01L 연결이 표시되고 프로젝트 사양은 fixed focus이나 현재 후보2와 장치명 연결/실제 초점 제어 지원은 미검증이다. 기존 사진 확대만 열었고 촬영·설정 변경·사람 승인 없음. 렌즈~엔진 윗면 거리를 확인한 뒤 조정할 예정이며 구도 변경 시 원본 보존 후 기준 사진/정렬을 새로 확인한다. 기준2장 PENDING, Main/Pilot0 유지.

실제 기준 사진2장 검토 대기: 사용자 전체누락 준비 및 새로 들어온 검은 케이블 정리 확인 뒤 MISSING_ALL_TARGETS setup_reference를 기존 UI로 저장했다. 두번째 capture_id 끝9a27055459af, SHA2568281c152b2d3e02c6aa43cd5ec8ca7e132ac28a82fb0a77116b160a1133e31c5. 두PNG1280×720/해시·동일목표조건·첫원본/기존raw11보존 PASS, 자동품질경고0. 현재 실제 사진묶음 창에서 정상/전체누락2장 비교·사람 최종 승인 대기이며 자동 승인하지 않았다. Main/Pilot승인0 유지. 실제리뷰 L15 추가, 가이드66 PNG/활성55/TODO11 DRAFT. Evidence: runs/engine_capture_live/reference_pair_verified.json.

실제 첫 Dataset 저장: 사용자 정상0 준비 완료 확인 후 기존 Wizard 각도 체크/촬영 버튼으로 NORMAL setup_reference1장을 저장했다. PNG1280×720·SHA256·기록 연결 PASS, 자동 품질 경고0, 사람 최종 사진 검토는 PENDING. 첫 실제 capture_id 끝 d2c2627adc8f, 원본 해시841791cfcbc31a650c7a222f1cad711b5a08886047a1c47cc8a22bea847dab59. Guide L12는 원본과 동일 바이트 복사본이고 기존 raw11은 그대로다. Main/Pilot승인0, 라벨링/E04열람/commit·push0. 다음은 MISSING_ALL_TARGETS 기준 사진을 위한 사람 부품 제거이며 현재 Crank 체크 미승인. Guide63 PNG/활성52/TODO11 DRAFT. Evidence: runs/engine_capture_live/first_capture_verified.json. 아래 촬영0 기록은 이전 시점이다.

회전 정렬 보완(사용자 요청): 스티커 없이 맞추는 하늘색 엔진 외곽·중심·배기구 화살표를 추가했다. 목표 Engine 각도에 따라 시계 방향 회전하며 노란 품질 영역은 고정이다. 0° 외곽을 기존 setup event의 선택 필드에 저장하고 이어하기로 복원한다. 원본/Annotation/각도 GT 자동 수정 없음. 미저장 설정 촬영 차단, 촬영 없는 정렬 미리보기 추가. 집중 geometry4/UI6, 전체278(engine51 포함), 문서5/계약·이미지/원본11해시 검사 PASS. 실제 USB0°/120° 표시 확인했지만 실물 엔진 회전·각도 정확도 수용은 아직 아니다. 같은 Collection에서 새 setup SETUPC97BBC14272D4C93 저장, 기존 setup 보존, 촬영0/Main0/라벨링0/E04열람0/commit·push0. 현재 Crank0 사람 체크 대기. 가이드61 PNG/활성50/TODO11로 DRAFT 유지. Evidence: docs/verification/ENGINE-ROTATING-ALIGNMENT.json.

현재 실행 보완: 사용자가 실제 Dataset을 만들면서 가이드를 작성하도록 지시했다. 가이드 전용 사진은 Dataset 촬영으로 세지 않는다. 실제 STATION_A Collection CCFB752B1D2A646A1을 만들고 USB 후보2/DSHOW/1280×720 연결 및 고정 영역 설정을 저장했다. 현재 실제 Crank Phase 사람 확인 창의 세 항목은 미확인 상태이며 첫 기준 촬영 전이다. capture attempts0 / Pilot 승인0 / Main 승인0. 새 실제 사용 화면5개는 images/engine_dataset_capture/live/에 별도 보존한다. native 클릭 도구 연결 실패로 기존 Tk 위젯을 호출하는 로컬 어댑터를 사용하며 저장·검토 로직과 계약은 변경하지 않았다. 전체273개 첫 실행은 UI Space-release1개 실패, 단독1개 및 전체273개 재실행 PASS; 원인 미확인과 최초 로그를 보존한다. 아래 가이드 전용 세션 기록은 당시 근거로 유지한다.

IN PROGRESS / DRAFT — docs/guides/ENGINE_DATASET_CAPTURE_GUIDE_KO.md와 QUICK_GUIDE_KO.md 작성. 실제 Wizard UI 및 계약/계획 기반 표·이미지 출처 검증을 추가했다. USB 후보2/DSHOW/1280×720에서 작업자가 각 상태를 확인한 뒤 실물 6상태 가이드 사진과 Preview 1장을 확보했다. 총50 PNG/활성39장, 실물 보완 TODO11개. 작업자가 배기구 역방향 장착을 지적하여 뒤에 만든 엔진 0°/CRANK_000 기준 3파일의 정상 기준 사용을 취소했다. 원본은 보존하고 해당 사진은 RETAKE 예시에만 사용한다. 잘못 승인한 기준 창을 닫고 재사용 차단 검증을 추가했다. 사용자가 정상 재장착 완료를 확인한 뒤 초기 NORMAL과 배기구 방향을 비교하고 새 기준 3파일을 별도 저장했다. 현재 기준은 06e, 이전 06c는 계속 사용 금지다. 테이프는 필수가 아니고 센서 각도 검증은 없다. 상단 배기구 재배치 전 사진은 보류하고 새 파일로 재촬영했으며 원본 둘 다 보존했다. 목표 각도·Crank는 사람 기준이고 사진 사이 위치 차이가 있다. 문서/계약 검사·가이드 테스트5개·diff 검사 PASS. 이 PASS는 문서 구조 검증이며 물리 정상 판정이 아니다. 실제 기준/사용 화면 보완 진행 중. Main 촬영/라벨링/E04 원본 열람/commit·push 없음, 기존 raw11파일 해시 재검사 동일. 현재 캡처 기록: runs/engine_capture_guide/; Task: tasks/engine-dataset-capture-guide.md. 실물 보완 전까지 완성된 실사용 가이드로 표시하지 않는다.

Latest Task (2026-09-16, ENGINE-DATASET-WIZARD-V1):
DONE / VERIFIED — 기존 360° Wizard/PNG writer/이벤트·재개·검토를 재사용해 Station/Crank/Ground Truth/정상Pair/라벨링 인계를 확장했다. profile v2/3클래스·6상태 유지, plan v3는 상태→Crank→각도 순서이며 Main288/Station(train144/val72/test72). 기본 YOLO216 / E03 Mask40, 두 Station 합성 전체 병합 Main576/YOLO432/Mask80 검증. E04 기본 잠금, 명시적 문구 unlock에도 학습/튜닝 금지. Challenge는 별도 REVIEW·training 제외. 공통 한글/ID 사전에서 Human 문서와 machine 계약을 생성하고 의미·행 연결 불일치는 export 실패. 전체268 tests PASS(Engine41 포함), UI 최소크기/버튼·합성 화면 확인 PASS, diff --check PASS. 기존 raw11파일(PNG2 포함) 동일, 신규 실제 촬영0/라벨링0/학습0/commit·push0. 실장비/실각도·정합/최종 품질은 UNVERIFIED. 기존 EXE/ZIP은 V0 보존(재빌드0), V1 launcher: scripts/start_capture_engine_windows.cmd. 사용법: training/datasets/engine/engine_model_top_v0/README_V1_KR.md; Task: tasks/engine-dataset-wizard-v1.md; Evidence: docs/verification/ENGINE-DATASET-WIZARD-V1.json. 다음은 STATION_A 선택 후 Pilot 첫 화면의 사용자 확인이다.

Latest Task (2026-09-15, ENGINE-DATASET-WIZARD-PORTABLE):
DONE / VERIFIED — 팀원 Windows x64에서 Python/Tkinter 설치 없이 여는 엔진 데이터 수집 EXE/ZIP 생성. 기존 Wizard 진입점을 재사용하고 제품 설정은 EXE 안, 원본/검토·재개는 EXE 옆 data/engine/raw, 시작 로그는 logs에 분리했다. 배포: dist/engine_dataset_wizard/20260915_v1/EngineDatasetWizard_Windows_x64.zip (약74.8MB), 내부 EngineDatasetWizard.exe. 실제 단독 EXE를 한글·공백 폴더로 복사해 Python PATH/환경 변수 없이 다른 cwd에서 Tk·frozen camera worker·합성PNG2·hash·resume/검토 대기 검증 PASS. 일반 무인자 시작 창 응답 확인. 신규4/전체248 tests PASS, ZIP CRC PASS. 실제 촬영/라벨링/학습/Jetson/Runtime 변경/기존 데이터 접근0, commit/push 없음. 별도 물리 팀원 PC·실USB 수용은 미검증, EXE는 미서명. 빌드/사용: scripts/BUILD_CAPTURE_ENGINE_KR.md; Evidence: docs/verification/ENGINE-DATASET-WIZARD-PORTABLE.json. 아래 360도 구현과 실장비 실행 기록을 보존한다.

Latest Task (2026-09-14, ENGINE-DATASET-WIZARD-360-V0):
DONE / VERIFIED — Windows 엔진360° Dataset Wizard 구현·합성 검증 범위. 기존 Wizard/세션/PNG/검토·재개를 재사용했다. profile v2는 gray_pipe2/exhaust_top1/symbol_module1과6상태의 expected_counts/removed_slots를 명시하며 기존v1/이어폰 설정·순서 digest는 유지한다. plan v2의 회차→조명→상태→12목표각도 순서, 회차/상태 실제 재배치 사람 gate, 고정 ROI/원형 목표각도 UI, 부분 저장·검토 대기 resume, E04 일반 라벨 후보 제외를 구현했다. Train0+30n 144장/Val15+30n72장/Test8+30n72장=본수집288, 기준2+Pilot12는 별도. Challenge는 별도 설정/후속 수집 사양이며 main 촬영모드에 넣지 않는다.
최종 전체244개 PASS(실패0/오류0/skip0), 엔진17개 집중 PASS. 기존227개 테스트 무수정, 보호57파일 hash 동일. 실제 Tk 위젯과 실행 진입점은 합성 카메라로 확인했다. launcher: scripts/start_capture_engine_windows.cmd; 안내: training/datasets/engine/engine_model_top_v0/README_KR.md. 실제 엔진 폴더/촬영0, 라벨링0, 학습0, Jetson0, Runtime 변경0, 실제 B04/Test 접근0. 물리 각도 센서 검증·첫 Pilot 품질은 미검증이며 사람 첫 화면 확인 대기. commit/push 없음. Evidence: docs/verification/ENGINE-DATASET-WIZARD-360-V0.json 및 runs/engine_dataset_wizard_360_v0/. 아래 Jetson 실행·실물 수용 기록은 이전 작업으로 보존한다.

Latest Camera Reconnect (2026-09-14 14:13 KST):
사용자가 USB 분리·재연결을 알렸으며 실제 동일 by-id 장치는 존재하나 기존 Worker4242가 CAMERA_FRAME_TIMEOUT/RECOVERY로 종료된 상태를 확인했다. 진행 중 검사0에서 현재 manifest와 같은 earbud_case_v0/app_v001을 기존 활성화/Worker 복구 API로 다시 로드했다. 새 Worker4688, IDLE/camera_ready=true/error=null, cuda:0 자체 추론 및1280×720 미리보기2장 갱신 PASS. 미리보기에 열린 케이스가 보인다. 전후 이력13행 전체 본문과 manifest hash 일치, PC sync 오류0/대기자산0. 복구 전부터 기준 미승인 상태였으며 복구 후에도 calibration_confirmed=false/ready=false를 유지했다. 실제 검사는 정상 제품 기준 촬영·사람 자리 확인 후 가능하다. 신규 검사·승인 요청0, 물리 분리 순간 관찰/단절 중 검사 시험은 미실행. 카메라 재연결 복구 수용 PASS, 전체 실물 수용은 대기 유지. Evidence: runs/inspection_app_v1/camera_reconnect_20260914_1412/verification.json.

Latest Startup (2026-09-14 13:43 KST):
사용자 실행 요청으로 기존 전용 SSH 키 접속 후 Jetson app_v007 Service PID4229/Worker4242, Windows PC 수집기와 양방향 용도의 별도 SSH 터널을 시작했다. 실제 health IDLE/ready=true/camera_ready=true/error=null, PyTorch cuda:0/Orin/입력[1,3,640,640] 자체 추론 완료, USB1280×720 JPEG2장 디코딩·서로 다른 해시 확인. 기존 기준 승인 로드, PC sync error=null/pending_assets0. Edge/PC 이력 ID11개와 결과 본문은 일치하나 a44a968e2a914a47a54e7ecc5a3383c4의 accepted_at 필드는 서로 다름을 기록했으며 원인을 조사하거나 수정하지 않았다. 현재 영상은 제품 없는 흐린 회색 면이므로 실물 배치·초점 및 변경된 구도의 기준 재등록은 사람 확인이 필요하다. 신규 검사/기준 촬영 요청0. HTML/영상 HTTP200 확인, 브라우저 제어 연결이 없어 실제 화면 렌더는 UNVERIFIED. 수동 접속/실행/PC 수집/종료 안내를 apps/edge_service/INSPECTION_APP.md에 보완했다. 실행 재개 수용 PASS, 전체 실물4상태 수용은 기존 대기 유지. Evidence: runs/inspection_app_v1/startup_20260914/verification.json. 코드·모델·환경 설치 변경 없음.

Program Guide (2026-09-14):
사용자 요청에 따라 현재 app_v007/f6403fc의 프로그램 구조·기능·실행 절차를 설명하는 한국어 PPT 26장과 설명 노트를 제작했다. 산출물: runs/program_guide_ppt_20260914/output/OneDevice_프로그램_구조_실행가이드_app_v007_v2.pptx. 소스와 실제 정상1건 근거를 사용하고 기준 진단 REVIEW/제품 검사/Mock/실 엔진·PLC의 범위를 구분했다. 최종 파일 재읽기·26장 렌더 검토·표8개/노트26장/원본2이미지 해시 검사 PASS, 레이아웃 finding/warning0. 실제 PowerPoint 앱 표시는 UNVERIFIED. 신규 프로젝트 시험·모델·장비 실행은 없으며 실물 수용 상태는 아래 그대로다. Evidence: runs/program_guide_ppt_20260914/PPT_RESULT.md 및 build/guide-verification.json.

Latest Physical Normal Inspection (2026-09-14):
사용자가 기준 진단 a7908d3c586f422c9648cbfc97feffac의 보라색 L/R 후보를 명시 승인했다. 별도 Jetson calibration 행 ce3a0337df5243109093e7eae9104ce7의 confirmed=true 및 좌표/기준 사진 연결을 직접 SQLite로 확인했다. 기존 기준 진단 REVIEW와 미승인 당시 후보 원문은 그대로 보존된다.
현재 정상 배치의 신규 제품 검사5031fbaf16a94877b5b6aa46f9e90c03: PASS / 모든 필수 자리와 수량 확인, L/R PRESENT, 결함/미확인0. 새 관측3회와 신규 원본3장+overlay1장, 승인 좌표 고정 사용 확인. Jetson 원장1행과 API 결과 일치, PC 같은 ID1행·결과 본문 일치, 원본/overlay4자산 SHA256 일치·양측 ACKED, 완료/저장시간 이벤트2개 PC 수신·ACKED. 기존9진단 행 해시와 기준 진단 원문 보존. Edge integrity ok/FK위반0.
검사 이력 API에서 같은 ID의 inspect/PASS를 확인했으나 브라우저 실제 이력 표시는 사용자 확인 대기다. 정상 실물 제품 검사1건 검증이며 전체 네 상태 수용 완료가 아니다. 다음은 화면 이력 확인 후 L 누락 한 행동 안내. 기대 normal/PASS는 별도 acceptance_context에만 기록했고 검사 입력에 넣지 않았다. 실 PLC/엔진 시험 아님. Evidence: runs/inspection_app_v1/physical_acceptance/5031fbaf16a94877b5b6aa46f9e90c03/verification.json.

Latest Physical Reference (2026-09-14):
사용자가 정상 케이스 중앙 배치와 두 자리 가시성·손 제거를 확인했다. app_v007에서 새 기준 진단 a7908d3c586f422c9648cbfc97feffac을 실행해 현재 좌표의 L/R 후보 생성, REVIEW/사람 자리 확인 대기를 확인했다. 원본3장+overlay1장 저장/해시 확인, PC 동일 ID 행과4자산 해시 일치. 상태 기대값은 별도 acceptance_context에만 저장했고 판정 입력에 전달하지 않았다. 후보 confirmed=false, 실제 기준 자리 승인은 아직 받지 않았으며 제품 검사도 시작하지 않았다. 원본/후보 사진을 열어 확인했으며 다음은 사용자 보라색 EXPECTED L/R 자리 확인이다. Evidence: runs/inspection_app_v1/physical_acceptance/a7908d3c586f422c9648cbfc97feffac/.

Latest Checkpoint (2026-09-14, CALIBRATION-FIX):
현재 실행 릴리스 app_v007. tasks/inspection-app-v1.md의 기준 등록 수정 범위는 구현·배포 완료, 실물 기준 자리 승인 및 네 상태 수용은 대기다. 검사 화면 http://127.0.0.1:8768 새로고침 후 재개한다.
화면 기록 c92f305afc9348df9ee030d2ec217a95의 실제 원본/관측3회를 확인했다. L/R·case 검출과 품질은 유효했으나 app_v005 reference_proposal이 과거 fixed region과 먼저 비교하여 L/R 모두 배정0이었다. 실행 Jetson 소스와 Windows HEAD878b956의 해시 일치를 확인했다. 실제 활성 패키지 경로는 app_v003의 불변 app_v001이며 manifest/model/recipe hash는 화면 기록과 같고 변경하지 않았다.
기준 등록만 현재 검출 좌표에서 후보를 생성하고 클래스·수량·품질·연속 관측을 검증한다. 동일 클래스 다중 자리 대응은 임의 배정하지 않고 한국어로 자리 지정 필요를 알린다. 후보와 일반 검사 overlay는 결과 calibration_used의 동일 정규화 좌표를 쓴다. 승인 기록은 제품/패키지/촬영/설비 설정 hash/cell/기준 inspection/frame에 연결된다. 새 기준 촬영을 시작하면 이전 승인으로 검사하지 않으며 재시작 후에도 새 승인까지 차단한다. 사람 확인 자동 승인0.
최종 Windows227개 PASS(48.312초), 최종 Jetson 변경 관련14개 PASS(10.011초), 이전 동일 코드 journal/package17개 PASS. Jetson TestClient는 httpx 부재로 UNVERIFIED; Windows API 시험 및 최종 실제 HTTP 승인 전409 CALIBRATION_REQUIRED/HTML 응답/카메라 cuda:0 확인. DOM 계약·한국어·원본 링크 검사 PASS는 실제 브라우저 렌더링 승인이 아니다.
기존 진단5건/이미지20개는 그대로 보존한다. 이번 대조 시 누적 기준 진단9건/이미지36개였으며 전후 전체 원장 행·이미지 해시와 PC36자산을 확인했다. 제품 검사0, 승인 calibration0, DB integrity ok/FK위반0. 실제 정상/L누락/R누락/양쪽누락 검사·DB·화면 수용은 미실행. 모델·신뢰도·겹침 기준·Recipe 불변, 학습/튜닝/실 PLC/실 엔진 미실행. app_v005/v006과 전환 전 data_root 전체 백업을 보존했다.
Evidence: docs/verification/INSPECTION-CALIBRATION-FIX-20260914.json 및 runs/inspection_app_v1/calibration_fix_v006/ (v006 진단/중간 배포와 최종 v007 증거 함께 보존). 다음: 정상 제품 배치 확인 → 현재 기준 사진 촬영 → 사람 자리 승인 → 정상 한 건의 동일 ID 원본/판정/Jetson DB/PC/이력 대조. 그 뒤 누락3상태를 한 행동씩 진행한다.

Latest Checkpoint (2026-09-14, INSPECTION-APP-V1):
현재 Task는 tasks/inspection-app-v1.md. CODEX_INSPECTION_APP_V1_KO.md의 공통 앱 범위로 DB/PC/Mock 제어를 구현했으며, 아래 과거 BENCH의 DB 제외/8767 실행 표기는 당시 기록이다. 현재 Jetson 릴리스 app_v005, 검사 화면 http://127.0.0.1:8768, Windows PC 조회 http://127.0.0.1:8769. 기존 bench_v001은 소스·모델·기록을 보존하고 종료했다.
제품 패키지 hash/schema/클래스/전처리/Recipe/촬영 검증, 같은 클래스 다중 슬롯·수량의 유일 배정, 별도 GPU/카메라 Worker 프로세스, Service 단일 SQLite writer와 PNG→commit→게시, 이력/asset 조회, 패키지 활성화/실패 복원, PC outbox·별도 DB·독립 이미지 ACK, Mock 요청/결과/종료 ACK·복구를 연결했다. Engine 모델/실물 슬롯은 미준비 비활성이다.
실제 Jetson cuda:0/Orin/입력[1,3,640,640], 기존 best.pt SHA256 49f533e4e4e5846d1582564d8efbb38a647ad10348a976db9085d94df16250c1 유지. 격리 app_v1 환경은 기존 사용자 torch2.8.0과 시스템 OpenCV4.8.0을 그대로 사용하며 FastAPI/uvicorn만 별도 설치했다. 실제 USB 기준 진단5건은 대상 부재로 전부 REVIEW, PNG15장+overlay5장·SQLite5행·PC20자산 해시 일치. 생산 검사0건이다. 사람 가시성을 자동 승인하지 않았다.
PC 실제 중단 중3건을 Edge에 보관하고 재연결 후 중복 없이 수집, outbox/이미지 대기0. 동일 Baseline 패키지 실제 재활성화·세션 변경·기존 이력 유지 확인. Service 종료 뒤 자식 Worker가 남던 실패를 보존하고 ASGI lifespan 정리로 수정, 부모/자식 종료와 재시작 확인. 실제 Windows 전체218개 PASS, 마지막 변경 관련14개 및5개 PASS, 최종 Jetson27개 PASS, 릴리스45파일 해시 일치·SQLite integrity ok/FK 위반0. 가상 시간/가짜 Worker 시험은 실물 시험과 구분한다.
남은 수용: 브라우저 실제 표시, 현재 패키지 기준 자리 사람 확인, 정상/L누락/R누락/양쪽누락의 사진·판정·DB·화면, 물리 USB 단절, 사람 준비 후 실제 카메라 Mock 사이클. 모두 대기이며 전체 완료로 표시하지 않는다. B04/재학습/ONNX·TensorRT/실 엔진/실 PLC·모터는 미실행. 실행 안내 apps/edge_service/INSPECTION_APP.md, 증거 docs/verification/INSPECTION-APP-V1-20260914.json 및 runs/inspection_app_v1/.

GitHub publication verification (2026-09-14):
사용자 요청에 따라 촬영 도구 보완/라벨 변환/그룹 분리/Baseline·오류 분석/Jetson BENCH 코드와 검증 기록을 기존 master에 동기화한다. 전체 자동 테스트185개 PASS(50.302초), 새 checkout 임시 폴더 준비 보완 후 관련11개 PASS. 원본 사진·가중치·ONNX/engine·임시 분석·무관한 미커밋 CAD 작업은 게시하지 않는다. ROI 폴더의 복사된 Baseline 보고서와 미검증 환경 설정 주장이 있는 과거 MODEL_SELECTION 문서는 로컬에 보존하며 배포 선택 근거로 게시하지 않는다. 현재 BENCH Baseline 선택은 최신 사용자 지시를 따른다. 실제 실물4상태 검증은 아래와 같이 대기 상태다.

Latest Runtime Checkpoint (2026-09-13 → 09-14, JETSON-BENCH-001):
전용키 자동 SSH 접속 성공. 실제 Jetson Orin Nano/aarch64/L4T36.4.7/Python3.10.12/torch2.8.0 CUDA12.6/Ultralytics8.4.118/OpenCV4.8.0 확인 및 CUDA 연산 성공. 기존 환경을 재설치하지 않고 PyTorch CUDA 단일 경로를 선택했다. TensorRT10.3 설치 존재는 확인했지만 사용하지 않았고 ONNX parity는 NOT_RUN_PT_PATH.
원래 Baseline best.pt를 전송해 SHA256 일치. B03 BASE CENTER 네 상태 원본4장을 Jetson cuda:0에서 실제 추론, 모두 기대 부품 목록 일치(총8객체). 실제 입력은 FP32[1,3,640,640]/rect=False/전체 프레임. 첫 호출5888ms, 다음 세 호출52~59ms는 smoke 관측이며 정식 성능 벤치마크가 아니다.
기존 Camera/Detector 계약 기반 PyTorch/GStreamer adapter와 apps/edge_service/bench.py+bench.html, config/earbud_bench.json 구현. Jetson Python3.10의 StrEnum 호환만 최소 보완. 단일 Worker 소유·요청 후 source PTS·3연속 관측·제품별 자리/가시성 확인·요청별 원본PNG/JSON·중복거부·저장오류/단절 표시. DB/PLC는 후속으로 유지.
실제 USB MJPG1280x720 수신/증가 PTS12프레임/HTTP READY와 이미지 수신 확인. 첫 USB 연결 대기0.5초 실패를 보존하고 초기 프레임만3초 대기로 수정한 뒤 실제 수신 성공. 브라우저 조작 도구 미연결로 사용자의 화면 확인 대기.
Windows/Jetson 계약19개씩, BENCH 집중11개씩 PASS. 모델/배포파일8개 해시 일치. Evidence: docs/verification/JETSON-BENCH-001-20260913.json 및 runs/jetson_bench_001/.
현재 Jetson 서비스 실행 중, 노트북 http://127.0.0.1:8767 (SSH tunnel, 대상은127.0.0.1에만 bind). 정상 기준 자리 사람 확인·실제 네 상태 판정/저장·물리 단절·실제 중복 HTTP 검사는 아직 대기이며 전체 완료가 아니다. 다음 행동은 사용자가 브라우저에서 현재 영상 확인. 실행/종료/위치는 apps/edge_service/JETSON_BENCH.md.

Latest Request / Checkpoint (2026-09-13, JETSON-BENCH-001):
현재 Task는 tasks/jetson-bench-001.md. 최신 사용자 요청이 CODEX_EDGE_VISION_NEXT_KO의 전체 시스템 순서보다 우선한다. 기존 Baseline으로 Jetson 저장 사진 GPU smoke → 실제 USB → 노트북 브라우저 정상/누락 검사 화면까지만 진행한다. 재학습/추가 ROI·768/B04/MES·DB복제·PLC는 이번 범위 밖이며 최종 DB·PLC 요구는 후속으로 유지한다.
원래 baseline_result와 best.pt SHA256 일치. best.onnx 구조/클래스 확인: FP32[1,3,640,640] → [1,7,8400], NMS 노드0. ONNX parity와 Jetson 실행은 미실행.
provenance의 B03 BASE CENTER 네 상태 원본을 각1장 준비하고 해시 대조했다. runs/jetson_bench_001/staging_v001/에 manifest/별도 평가정답/원본 사본4장 보존. 준비 코드 집중 테스트3개 PASS. 실제 GPU·카메라·웹 화면 PASS가 아니다.
현재 실행 중인 SSH 프로세스에서 접속 경로를 확인했으나 BatchMode 인증1회 거절(publickey,password). SSH config 없음. 사용자에게 scripts/connect_jetson_bench.py를 터미널에서 실행해 전용키 인증을 설정하도록 안내했다. 호스트키 검증/네트워크 설정을 변경하지 않았으며 키 생성·대상 설정·환경 probe는 아직 미실행. 접속 인증 뒤 단일 backend를 결정한다.

아래 Current Task/튜닝 미실행 표기는 이전 분석 시점 기록이다. 최신 요청은 위 JETSON-BENCH-001이며 Baseline/ROI 학습을 반복하지 않는다.

Completed:
V0-T01, PLAN-REVISION-001, PLAN-AUDIT-001, V0-T02, V0-T03, V0-T04
V0-T05: DONE / VERIFIED (B01/B02 120장 위치 라벨 사람 승인·YOLO 학습 후보 변환 범위)
V0-T06, V0-T07, PROXY-DATASET-TRAIN-001: DONE / VERIFIED (B03 승인60장·train120/val60·Windows 첫 baseline 완료)
HUMAN-CAPTURE-001-PREP: DONE / VERIFIED (촬영 준비 범위)
WINDOWS-CAPTURE-001: DONE / VERIFIED (소프트웨어 + 최초 실제 USB 촬영 흐름)
WINDOWS-CAPTURE-002: DONE / VERIFIED (제품별 안내 촬영 소프트웨어)
DATASET-WIZARD-001: DONE / VERIFIED (전체 계획 수집 길잡이 소프트웨어)

Current Task:
V0-T08 — 평가·오류 분석 및 실험안 완료 / VERIFIED. 실제 튜닝 실행은 사용자 요청에 따라 미실행.

Latest Checkpoint (2026-09-13, V0-T08 분석 완료):
기존 B03 예측60장/120객체를 조건·배치·상태·클래스별로 분석했다. OPPOSITE 평균confidence0.9433이 BASE0.9661/DIM0.9668보다 낮지만 평균IoU는 BASE0.9134가 가장 낮다. L/R IoU약0.878,case0.958. 최저IoU0002 R0.75872,최저confidence0046 R0.88213. FP0/FN0,IoU<0.75도0이며<0.85는13개다. 최저 두목록의18사진/19객체를 실제 원본·GT/pred·기존예측으로 보조 검토했다. 작은 이어폰 경계 차이와 반사/케이스 경계 불확실성은 원인 후보이며 라벨 수정은 하지 않았다.
ERROR_ANALYSIS.md/error_analysis_detailed.json/error_analysis_supplement.json/error_review_v001/을 기존 실험 폴더에 추가했다. 독립IoU120,분포/합계/순위/원본보존 및 새 집중테스트4개 PASS. Evidence: docs/verification/V0-T08-ERROR-ANALYSIS-20260913.json.
추천은 baseline 유지 대조 + 고정ROI만 변경(1순위) + imgsz768만 변경(2순위). 실제 학습/추론 재실행0,B04 접근0,Jetson0. T08의 과거 실제 튜닝 실행 계획은 후속 대기이며 이번 분석 완료와 구분한다.

Earlier Checkpoint (2026-09-13, Windows 첫 baseline 완료):
PROXY-DATASET-TRAIN-001 DONE / VERIFIED. B03 v003 전체60장 사용자 승인→새 승인본/사람 검토 기록→validation_candidate 변환60장120객체 완료, 보류0. B01/B02 기존 train120장과 B03 val60장, B04 test0 예약으로 T06 구성·누수 검사 PASS. 원본/기존 승인본/수집 기록을 포함한978개 보호 파일 해시 유지.
T07 단일100epoch 실제 학습 exit0 완료: yolov8n.pt, RTX5070 Laptop cuda:0, imgsz640/batch16/seed42/AdamW/FP32. 학습 호출 총313.42초(초기화·마지막 검증 포함), epoch loop300.78초. best/last 재로드 CUDA PASS. best B03 Precision0.9981466 / Recall1.0 / mAP50 0.995 / mAP50-95 0.8334961. B03 예측60장 저장, conf0.25·IoU0.5 class-aware matching TP120/FP0/FN0. IoU가 낮은0002 R(0.759),0055 L(0.774) 예측 이미지 보조 확인; 미검출 사례로 부르지 않는다.
결과: training/experiments/earbud_case_v0_20260913_v001/BASELINE_REPORT.md 및 docs/verification/PROXY-DATASET-TRAIN-001-BASELINE-20260913.json. 데이터: training/outputs/datasets/earbud_case_v0_B01_B03_20260913_v001/dataset.yaml. 새 집중 검사12개 PASS. B04 최종 시험·추가 튜닝·Jetson 배포는 이번에 미실행이며 다음 별도 단계로 남긴다. 전체 엔진 정상/불량 검사·DB 저장 완료를 뜻하지 않는다.

Earlier Checkpoint (2026-09-13, B03 전체 라벨 승인 후 학습 중):
사용자가 "모든사진 OK라는거야 일일이 확인 안받아도되"라고 B03 v00360장 전체의 라벨을 명시 승인했다. 새 project_reviewed_all60_v001.json/human_review_all60_v001.json 저장, 사각형 변경0·120객체·보류0. 기존 초안과 부분 검토 로그는 보존했다. via_to_yolo.py validation_candidate60장 변환 PASS.
T06 DONE: training/outputs/datasets/earbud_case_v0_B01_B03_20260913_v001/에 train120/val60/test0 예약·dataset.yaml/분리 목록/누수 검사 저장. 이미지 SHA 및 origin/session/episode/capture 중복0. 새 데이터 검사8개·오류 집계 검사4개 PASS.
T07 현재 실행 중: training/baseline_config.yaml, yolov8n.pt, CUDA RTX5070 Laptop, imgsz640/100epochs/batch16/seed42/AdamW/FP32. 출력 training/experiments/earbud_case_v0_20260913_v001/baseline, 로그 training/outputs/earbud_baseline_20260913_v001.log. 이미 시작한 동일 baseline을 중복 실행하지 않는다. 완료 여부는 baseline_result.json 또는 baseline_failure.json으로 확인한다. B04 예약 유지·Jetson 미실행.

Earlier Checkpoint (2026-09-13, B03 촬영 완료 후):
B01/B02 승인·YOLO 변환120장 유지. B03 실제60장 저장 및15묶음 사람 촬영 검토 완료, 촬영 검토 대기0. BASE/DIM/OPPOSITE 각20장, 네 상태 각15장이다. 전체 원본222장·49세션이며 과거 재촬영28장도 보존했다. B03는 사용자 촬영 중단·케이스/조명 재준비 확인 후 기존 GUI로 시작했고 origin_group OG697C8F89699D4572 / validation_candidate다. B01/B02의 OG1023298FB0FC4631과 그룹·실제 이미지 해시 중복0. 물리적 독립성은 사람 선언이며 자동 입증이 아니다.
기존 GUI 내보내기 EXPORT6F74307E8E314691와 prepare_via_project.py를 재사용해 별도 B03_20260913 작업 공간을 만들었다. 실제 B03 원본60장을 확대 확인하고120개(L30/R30/case60) pending 사각형을 작성했다. 최신 초안은 training/outputs/labeling/B03_20260913/project_draft_all60_v003.json, 검토 이미지는 같은 폴더의 review_all60_v003/이다. 사람 위치 라벨 승인0, B03 YOLO 변환0. B01/B02 승인본·출력과 원본을 포함한978개 보호 파일 해시 유지. 이전 B03 초안v001/v002도 보존한다.
B04 미시작·최종 시험 예약 유지. 앱의 현재 멈춤은 B04의 용도 전환 보호이며 B03 미완료가 아니다. dataset.yaml/분리 목록/실제 데이터 첫 학습은 아직 미실행이다. 과거 t02_smoke의 모델 파일은 이번 실데이터 학습 결과가 아니다.
근거: docs/verification/PROXY-DATASET-TRAIN-001-B03-CAPTURE-20260913.json 및 docs/verification/PROXY-DATASET-TRAIN-001-B03-LABEL-DRAFT-20260913.json.
현재 다음 작업: B03 최신 초안60장의 실제 부품 종류·사각형 범위만 사람 검토 → 승인 범위 YOLO 변환 → T06 그룹 분리 → Windows 첫 학습. B01/B02 재승인이나 B04 촬영은 요구하지 않는다.

Current Authorization (2026-09-13):
사용자가 오늘 데이터셋 제작과 첫 학습까지 진행하도록 범위를 확장했다. Jetson Orin Nano는 아직 연결하지 않았으며 지금 단계는 Windows에서 수행한다. 이전 촬영 전용 범위의 라벨링·학습 금지는 이번 명시 요청으로 대체되지만 원본 보존·사진별 준비·사람 검토·독립 그룹·시험 예약 정책은 유지한다.
프로젝트 .venv에서 torch2.11.0+cu128 / Ultralytics8.4.146, RTX5070 Laptop GPU의 실제 cuda:0 행렬 연산(유한 결과·합3920)을 앞서 확인했다. 현재 실제 위치 라벨120장은 승인·변환됐으나 baseline 학습은 아직 미실행이다. 이번 파일 작업에서는 GPU를 재실행하거나 환경을 재설치하지 않았다.

Earlier State (B03 완료 이전 기록, 최신 진행은 위 Latest Checkpoint 우선):
사용자 요청으로 브라우저 재연결 시도를 중단하고 허용된 로컬 PNG·VIA JSON 파일 작업을 유지한다. 브라우저의 미저장 내용은 읽지 않았다. 이어가기 위치는 tasks/v0-t05-labeling-validation.md의 Finalization Result와 tasks/v0-t06-grouped-split.md를 따른다.
V0-T05 DONE / VERIFIED — 사용자가 project_draft_all120_v001.json 전체120장의 부품 종류·사각형 범위를 학습용으로 명시 승인했다. 새 project_reviewed_all120_v001.json에120장 confirmed·240개(earbud_left60,earbud_right60,case120)를 기록했고 보류0장이다. human_review_all120_v001.json에 원래 초안/승인본 SHA256·전체 실제 이미지 ID·사용자 응답·기록 시각을 연결했다. 0001·0002·0057·0081을 포함한 경계 불확실성 메모는 사용자 현행 기준 승인으로 해결했으며 기존 메모와 pending 초안 자체는 보존했다. 사각형/클래스 변경0.
제품 schema를 읽는 공통 training/scripts/via_to_yolo.py로 training/outputs/yolo/B01_B02_reviewed_20260913_v001/에 실제 원본 사본120장·YOLO120파일/240객체·출처 목록을 저장했다. 집중 테스트16개 PASS(0.463초). 별도 실제 출력 검사 PASS: 원본/작업용/출력 해시, 클래스·객체 수·양의 유한 좌표·범위·그룹 연결, 픽셀 역변환 최대 오차4.8000061e-08 <= 허용1e-06, 보호368파일 보존. 기존 검토 이미지와 체크포인트는 학습 입력에서 제외했다. 근거는 docs/verification/V0-T05-YOLO.json 및 출력 폴더 independent_audit.json이다.
B02 DONE / VERIFIED — 현재 B01/B02 본수집120장 사람 확정(각60장), 검토 대기0. 원본162장(기준2·준비12·본수집120·과거 재촬영28), 34세션 검증과 599이벤트 체인 확인. B03/B04는 아직 시작하지 않았다.
B01/B02는 같은 origin_group OG1023298FB0FC4631 / train_candidate다. B03을 독립 회차 선언 없이 시작하면 기존 용도 충돌 보호 규칙으로 일시 정지된다. 코드의 '오늘은 멈추고' 문구는 날짜 제한 검사를 뜻하지 않는다. 실제 촬영 중단 후 시간/설치 재준비 사실을 확인해야 하며 선언만으로 물리적 독립성이 검증되는 것은 아니다.
기존 GUI의 라벨링용 자료 정리로 exports/EXPORTA48C70FCE9B94A62/ 생성 완료. 학습·라벨링 후보120장, 검증0·시험0·합성0, 제외42장(기준/준비14+과거 거절28). 그120장의 위치 라벨 승인·YOLO 변환이 완료됐다. B03는 현재 스탠드 계획상60장이나 실제 시작/촬영/라벨0이며 B04는 최종 시험 예약이다. dataset.yaml·그룹 분리 완료·학습 실행은 아직 없다. 기존 수집 기록과 창을 조작하지 않았고 물리적 재준비도 완료로 기록하지 않았다. 다음은 사용자의 실제 B03 설치 재준비 확인이다.

Earlier B01 Checkpoint (historical):
B01 DONE / VERIFIED — 2026-09-13 첫 본수집60장 저장·사람 확정 완료. 전체 계획은 진행 중이며 B02 준비 화면에서 대기한다.
실제 원본102장: 기준2장·준비12장 모두 확정, B01 원본88장 중 현재 유효60장 확정·과거 재촬영 원본28장 보존. 검토 대기0장, B02 촬영0장. 전체 본수집 목표240장 중60장 확정.
조명 정정 이후 사용자가 실제 GUI에서40장을 추가 촬영·묶음 검토했다. 현재 확정 B01은 BASE/DIM/OPPOSITE 각20장, NORMAL/MISSING_LEFT/MISSING_RIGHT/MISSING_BOTH 각15장이다. 같은 B01 origin_group을 유지하고 독립성은 선언하지 않았다.
19개 실제 세션의 PNG/manifest 재로드·크기·해시와 이벤트386개 검증 통과. 모든102장 source_kind=camera,1280×720. 현재 B02 회차 준비 두 체크는 미선택이고 round_started는 B01 하나뿐이다.
마지막 MISSING_BOTH의 SIMILAR_IMAGE는 과거 main_B01_BASE_LEFT/MISSING_BOTH와의 유사도 경고다. 픽셀 해시는 다르며 저장 실패가 아니다.
기존 GUI에서 경고 확인 후 사진을 묶음 검토까지 보존했으며, 이 동작으로 사람 검토 완료를 기록하지 않았다.
사용자가 혼자 진행한 뒤 조명 위치·밝기·거리를 전혀 바꾸지 않았다고 확인했다. 함께 진행할 때는 조명을 바꿨다는 후속 확인에 따라 기준/준비와 BASE 본수집20장은 유지했다.
DIM20장과 OPPOSITE8장을 실제 비교 GUI에서 조명 조건 불일치 사유로 재촬영 처리했다. 기존 batch_accepted14개는 모두 보존되고, 해당28장에 기존 attempt_rejected 이벤트만 추가됐다. 실제 물체 재배치 선언은 모두 false다.
촬영을 막은 확정 묶음 재검토 진입점 누락을 수집 현황→기존 비교 화면 연결로 보완했다. 사용자가 지적한 조명 안내 문제는 조건 전환/재개 시 별도 조명 준비 확인 창으로 보완했다. 조명 확인은 촬영하지 않고 실행 중 UI 상태로만 유지한다.
원본/manifest/계획 사본/이벤트 스키마/품질 임계값/사람 묶음 승인 정책은 변경하지 않았다. 내부 함수 우회로 실제 자료를 정정하지 않았다.
수정 관련21개 테스트, 전체132개 테스트(40.057초), 최종 현황창 라벨 위치 정리 후 관련1개 테스트 통과. 실제 앱 정상 종료 후 기존 실행 파일로 단일 창 재실행, 같은 수집 폴더 복원·검증·재촬영 처리 완료.
수집 폴더: data/proxy/raw/collections/C2709B20787804587/ — 새 계획을 만들지 않고 이 폴더로 이어한다.
스탠드 있음 계획 v1(BASE/DIM/OPPOSITE), 첫 본수집 B01 목표 60장. 화면 왼쪽=실물 L은 사용자 확인 완료.
재시작 후 Windows HCAM01L 존재 확인, DSHOW 후보2를 직접 연결해 실제 작업대 영상1280×720/MJPG 수신을 확인했다. 요청도1280×720이며 FPS·높이·조도는 미확인이다. 이후 사용자가 실제 설치 및 조명 준비 확인을 거쳐 같은 setup으로 B01을 완료했다.
HCAM01L은 Windows 장치 목록에서 확인했으며 앱의 device_name은 null이다. 후보 번호를 영구 장치 식별자로 취급하지 않는다.
실제 영상 읽기 실패로 촬영을 일시 정지했다. 3개 세션의 PNG 8장 재로드·크기·해시와 이벤트 32개를 검증한 뒤 같은 설정으로 재연결했다.
사용자가 실제 설치 유지 여부를 확인했고 앱은 같은 미촬영 단계로 재개했다. 이 복구 중 추가 촬영 0장, 끊김의 정확한 원인은 미확인이다.
미리보기의 미연결 안내문 잔류는 별도 표시 오류로 남아 있다. 실제 PNG에는 안내문/기준 테두리가 없으며 원본 픽셀 해시 대조도 통과했다.
최소 수정은 wizard_app.py/wizard_views.py와 관련 회귀 테스트·사용 안내에 한정했다. CAD·환경·Jetson·학습·라벨링은 변경하지 않았다. 준비 시험 확인은 데이터 충분성의 보장이 아니다.

Software Verification (DATASET-WIZARD-001, historical):
DONE / VERIFIED — 계획/setup/조명/배치/상태 자동 순서, 준비 후 한 장 저장·검증,
품질 보조, 묶음 사람 확인·재촬영·정확한 재개·그룹 용도 예약·라벨링 인계 목록 구현.
130/130 자동 테스트 (기존111 + 추가19), 실제 Tk 창의 합성 입력/비교/확대 확인.
이 소프트웨어 검증 당시 새 계획의 실제 USB 촬영은 사용자 실행 대기였고 본수집 확정 0이었다. 현재 실제 진행은 위 State를 따른다.
기존 WINDOWS-CAPTURE-001의 실제 네 장 및 WINDOWS-CAPTURE-002의 원래 Evidence는 보존한다.

Product Selection:
완료: earbud_case_v0 — 열린 케이스 안의 실제 L/R 이어폰

Capture Tool / Configuration:
JSON profile 선택, v1 호환 + v2 설정 사본/해시, 네 시나리오 지원 완료.
Windows 촬영 창: 제품/상태 선택, DSHOW/MSMF 후보 선택, 실시간 미리보기,
원본 PNG 한 장 저장, 묶음/배치 관리, 기존 기록 검증·수량 복원.
Windows 전체 92/92 테스트 성공 (기존 56개 보존 + 추가 36개).
후속 안내 기능: capture-guide.json, 조건별 새 묶음, 모든 상태의 단계 안내, 준비/원본 검토 게이트.
새 전체 테스트 111/111 (원래 92개 + 안내 기능 19개). 검토 기록은 버전 있는 별도 JSONL이며 기존 manifest는 유지한다.
실제 Tk 창의 합성 입력 검증 이후, HCAM01L / DSHOW 후보2 / 1280×720 / MJPG 영상 수신과 PNG 저장을 확인했다.
장치 보고 FPS는 미확인(null)이다. 후보 번호는 현재 열거 결과이며 영구 장치 identity가 아니다.
실행: scripts/start_capture_windows.cmd (기존 프로젝트 .venv, 추가 설치 없음).
현재 기본 화면: 「시작 / 이어하기」 수집 길잡이. 수동/한 조건 도우미는 고급 설정 또는 --manual로 유지.
기준 사진2장 → 준비 시험12장 → 본수집 초기240장(4회차×3조명×5배치×4상태).
스탠드가 없으면 준비 시험4장/본수집80장으로 조정하며 제외 이유를 보존한다. 충분한 학습량의 보장이 아니다.
수집 계획/이벤트는 별도 v1 파일이며 기존 manifest v1/v2와 GuidedRound의 사진별 검토 정책은 유지한다.

Confirmed Formal Captures:
4장 (2026-09-13): NORMAL 1 / MISSING_LEFT 1 / MISSING_RIGHT 1 / MISSING_BOTH 1.
Session: S20260912T171113_B362774D. 같은 묶음, 실제 배치별 E0001~E0004.
사용자가 실물 배치와 준비를 확인했고, 사용자 요청에 따라 Codex가 GUI에서 상태 선택·저장을 수행했다.
기존 verifier의 reload/크기/기록/해시 검증 성공. 사진은 로컬 Git 제외 경로에만 있다.
이 네 장은 최초 구도·저장 흐름 확인용이다. 새 수집 길잡이의 준비/본수집 수량에 소급 편입하지 않는다.
과거 81장 계획 및 90장 제안을 현재 확정 수량이나 실적으로 사용하지 않는다.

Human Placement / Photo Review:
4개 상태의 사용자 배치 완료 / Codex가 실제 원본 4장을 열어 확인.
열린 케이스와 각 이어폰 상태는 보이나 노이즈·부드러운 윤곽이 관찰되어 구도/저장 확인용으로 유지한다.
최종 촬영 품질과 확대 수집 조건의 사용자 승인은 아직 없다.

V0-T05 / Labeling:
IN PROGRESS — 본수집120장 전체에240개 pending 초안 저장. 기존 review_first4_v001/을 보존하며 누적 검토 자료는 training/outputs/labeling/B01_B02_20260913/review_all120_v001/에 있다. 검토 이미지는 학습 입력이 아니다. 사람 라벨 검토0, B03 미시작.

Historical Next Task (B03 완료 이전; 현재 다음 작업은 Latest Checkpoint 참조):
V0-T05 — 사용자가 현재 VIA 작업을 보존한 뒤 project_draft_all120_v001.json을 Project → Load로 불러와 라벨을 확인·수정한다. 우선0001·0002의 기존 경계와0057 L·0081 R의 어두운 줄기를 확인한다. 전체 사진의 의미 정확성 확인은 별도로 필요하며 실제 확인한 사진만 사람 검토 완료로 기록한다. 이후 B01/B02 라벨 검토→B03 실제 독립 촬영/라벨링→그룹 분리→Windows 첫 학습 목표를 유지한다. 이번 작업에서 브라우저 조작·새 촬영·학습은 실행하지 않았다.
기준 사진 2장과 준비 사진 12장은 모두 사람 확인 완료이며 중복 촬영하지 않는다.
B01 필수60장에 대한 저장과 사람 확정이 완료됐으며 기존 불일치28장은 이력으로 보존한다. B02를 시작할 때 조명 준비 확인→물체 배치→한 장 준비 확인을 분리한다. 촬영은 매번 사람 준비를 확인한다.
B03/B04의 실제 독립 회차 확인을 유지한다. 같은 날이라도 실제 촬영 중단·시간 간격·설치 재준비 사실을 확인해야 하며 같은 연속 촬영을 이름만 바꿔 독립 자료로 취급하지 않는다.
수집 후 기존 T05→T06→T07의 라벨 검증·그룹 분리·baseline 순서를 이어간다. 시험 예약 자료는 학습·튜닝에 쓰지 않으며 기존 프레임 안내 영역을 부품 위치 정답으로 변환하지 않는다.

Evidence / Boundaries:
- 수집 길잡이: tasks/dataset-wizard-001.md; docs/verification/DATASET-WIZARD-001.json; training/capture_windows/DATASET_WIZARD_KR.md.
- 130/130 PASS. 기존 실제 원본/기록을 포함한 보호 파일149개 해시 일치, 패키지42개 버전 유지. 이번 새 실제 촬영0장.
- 안내 촬영 계약: tasks/windows-capture-002.md; 검증: docs/verification/WINDOWS-CAPTURE-002.txt.
- 기존 실제 PNG 4장과 manifest/session-info 총6개 파일 SHA256 일치. 이 사진은 안내 완료 건수로 소급 집계하지 않는다.
- 현재 촬영 화면 계약: tasks/windows-capture-001.md; 사용 안내: training/capture_windows/README_KR.md.
- 현재 검증: docs/verification/WINDOWS-CAPTURE-001.txt. 92/92 PASS, 보호 tracked 파일 150개 해시 일치, 설치 패키지 42개 버전 유지.
- 후속 실기기 검증: docs/verification/WINDOWS-CAPTURE-001-HARDWARE.json. 실제4장과 state/episode/크기/SHA256 연결, 재연결/GUI 수량 복원 확인. 단순 장치 목록 인식과 실제 프레임 수신·저장을 구분한다.
- 선행 준비 계약: tasks/human-capture-001-prep.md.
- 준비 검증: docs/verification/HUMAN-CAPTURE-001-PREP.txt; 보호 파일 229개 해시 일치, 기존 v1 sample 3장 검증 성공.
- 검사 명세·촬영 순서: training/datasets/proxy/earbud_case_v0/README.md.
- 기존 V0-T02 GPU smoke, T03 공통 계약, T04 수집 도구·사용자 실행 하드웨어 검증은 완료 상태와 원래 Evidence를 유지한다.
- T04 CAMERA_SMOKE 3장은 USER-EXECUTED / VERIFIED인 과거 관측이며 정식 데이터에서 제외한다. 현재 카메라 모델·노드·지원 포맷은 미확인이다. 당시 노드/FPS를 현재 값으로 가정하지 않는다.
- 이번 Windows 후속 작업은 사용자 승인 후 지정 USB 카메라를 연결하고, 실제 배치 준비 확인마다 한 장씩 저장했다. 자동 burst 촬영, Jetson 접속, CAD 수정, 환경 설치, 라벨링/분할/학습/튜닝/평가/변환/PLC 제어 없음.
- 합성 sample 검증은 실제 촬영·검사 성공·모델 성능 검증으로 집계하지 않는다.
- Detector/Decision/DB/HMI 구현은 기존 후속 Task 범위다. 준비 완료는 V0 완료가 아니다.
