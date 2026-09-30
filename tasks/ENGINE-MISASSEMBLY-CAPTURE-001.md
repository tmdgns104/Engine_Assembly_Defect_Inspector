# ENGINE-MISASSEMBLY-CAPTURE-001

## 2026-09-30 사용성 회귀 수정 — Windows EXE 및 전달 ZIP 검증 완료

Status: WINDOWS_FROZEN_UI_AND_HCAM_PREVIEW_VERIFIED / TEAMMATE_PC_NOT_RUN

사용자 요구: 이전 촬영기의 큰 영상·카메라 설정·배치 박스·360° 회전 안내를 유지하고 매 사진에는 촬영 한 번만 요구한다.

확인 원인: 새 UI는 미리보기를 690×300으로 제한하고 기존 overlay/회전 정렬을 연결하지 않았다. 해상도 선택이 없고 촬영자 입력이 카메라 미리보기 연결을 막았다. 이전 합성 저장 검증은 실제 화면 사용성 검증을 대신하지 못한다.

수정 순서:
- [x] 기존 Canvas/overlay/engine_alignment 재사용, 최초 구도 드래그, 중심·회전 박스·목표각 표시.
- [x] 카메라 설정을 별도 최초 설정 패널로 정리, 해상도 선택/명시적 재연결 복원, 실제 영상 상태 표시.
- [x] 촬영 시 step/operator/setup을 고정하고 저장 후에만 자동 이동; 입력 반복·실패·재개 검증.
- [x] 사용자 후속 요구대로 10° 간격 0~350°. 오조립 7종 × 두 위치 × 36방향 = 504장. 기존 정상/결품 6종의 부족한 24방향씩 = 144장. 정상 장치 대조군 6장. 총 654장. 기존 수집은 원래 계획으로 재개하며 원장을 변경하지 않는다.
- [x] 960×650/1240×820 실제 렌더링, 최종 추출 EXE의 GUI/저장/재촬영/재개 및 실제 카메라 검증, 전달 ZIP 생성.

변경 범위: capture_windows 및 해당 집중 테스트/작업 증거. 기존 정상 원본·승인·E04·다른 Runtime은 변경하지 않는다.

### 최종 전달본과 확인 범위

- ZIP: `dist/engine_misassembly_capture/20260930_102438/Engine_Misassembly_Capture.zip` — 81,552,250 bytes, SHA-256 `a90ac39174d00f19be0c18d7c9182138c54eb97a741803be84fa104a4dce13bf`.
- 압축 해제 후 `Engine_Misassembly_Capture/EngineMisassemblyCapture.exe` 더블클릭. `_internal`/assets 포함 폴더 전체를 유지한다. EXE SHA-256 `b8f9fcad454e108fe2e312c449c74f23e29372552d3dcc4af14a9ec9d8354bee`.
- 저장: 최초 지정한 폴더의 `collections/<collection_id>/sessions`. 기본값은 EXE 옆 `data/collections`이다. 촬영 종료 / 전달 폴더로 생성한 해당 수집의 `전달_*` 폴더 전체를 팀원이 되돌려 준다. 원본·manifest·계획·완료/미완료 요약 포함.
- 집중 source 검사 46건(camera/storage 29, 시작 deadline 3, portable 5, 안내 4, setup/결품/지연/중지/오류 처리 5) PASS. source writer sample 8항목 PASS.
- 최종 ZIP에서 추출한 EXE의 GUI 7항목 PASS. 한 입력→새 프레임→원본 저장→자동 이동, 중복 입력, 각도/상태 이동, 저장 실패/재촬영, 카메라 끊김/오래된 프레임, 원래 계획 재개를 확인했다. 합성 사진은 sample이며 실제 새 학습 원본이 아니다.
- 같은 추출 EXE의 실제 DSHOW 후보 1(HCAM01L로 열거됨), 1280×720/MJPG, 고유 fresh sequence 40개 수신 PASS. 이 실행의 첫 프레임 10.412초/worker 준비 5.408초. 모델명/FPS를 OpenCV가 보고하지 않아 camera 메타데이터에는 null을 유지했다. 실물 사진 저장 0.
- 최종 ZIP CRC·상대경로/파일 목록·1100개 파일·41개 빌드 입력 해시·실행 EXE 동일성 PASS. 빈 data/logs, 안내 및 라이선스, BUILD_INFO/VERIFICATION 동봉. 증거: `runs/engine_misassembly_capture_001/final-package-verification.json`, `frozen_release_03_invocation.json`, `frozen_release_03_ui/result.json`, `frozen_release_03_camera/result.json`.
- 제한: 다른 팀원 PC, 실물 엔진의 654장 전체 촬영, 실제 부품 상태/각도·라벨 검토는 NOT_RUN. 현재 후보 1을 다른 PC의 HCAM 번호로 고정하지 않는다. 새 수집은 NOT_REVIEWED 학습 후보이며 학습/품질 보장이 아니다. 기존 수집은 원래 계획을 보존해 재개한다.

### 추가 요구와 수정 과정 (중간 실패 기록 보존)

- `make_coverage.py`는 source_index의 accepted TRAIN E01/E02 144개 ID만 허용하고, 해당 attempt_saved/attempt_intent와 원본 SHA-256을 대조했다. NORMAL 및 기존 결품 5종 모두 0/30/.../330 목표각이 있었다. 정확히 같은 상태/목표각만 기존 자료로 계산한다. 두 기존 조명 조건은 각도 존재 여부에서 합산하며 새 장치/물리 독립성이나 실제 각도 일치를 보장하지 않는다. validation/test/E04 원본은 열람하지 않았다.
- 새 기본 정렬 ROI는 임의 [.4,.28,.2,.44]에서 D001의 실제 setup `SETUPDD7C08CED9464C7E` 값 [.3816568047337278,.07631578947368421,.2736686390532544,.8263157894736842]로 복원했다. 출처는 `assets/reference-framing.json`. 정답 bbox가 아니다.
- 사용자가 정상 이미지의 꼬리만 밖에 나온다고 확인했다. 본체 크기/기존 회전 중심은 유지하고, 하단 중심축 부분만 기준 영상에서 40px 확장한 윤곽을 사용한다. 각도별 polygon과 회전 공간을 계산하며 원본 픽셀에는 그리지 않는다.
- 원본 보기: `runs/engine_misassembly_capture_001/tail-framing-1240x820.png`, `tail-framing-960x650.png`. 카메라 입력은 이 화면 검증에 한해 기존 NORMAL sample이며 새 학습 촬영이 아니다.
- source `test_windows_capture.py` 29 PASS, `test_misassembly_guidance.py` 4 PASS, `test_misassembly_setup.py` 2 PASS. 소스 Tk 7개 경로 PASS. source 실제 DSHOW 후보 1에서 1280×720/MJPG fresh sequence 40개 수신 PASS, 사진 저장 없음, 모델명/FPS는 미확인으로 유지.
- 첫 frozen UI 시험의 6초 대기 한도는 앱의 8초 안정 대기보다 짧았다. 실패 증거를 보존하고 GUI 시험의 전체 비동기 대기를 15초로 수정했다(앱의 안정 대기/저장 검증을 완화하지 않음). 20260930_091921 frozen UI 7개 경로 PASS. 최종 꼬리 수정본은 별도 검증한다.
- 단일 EXE는 이 PC에서 시작 시 90초 이상 무창 상태가 관측되어 onedir 배포로 변경했다. `_internal`과 assets를 포함한 폴더 전체가 실행 단위다. 팀원 PC의 시작 시간은 미측정이다.
- `20260930_092829` 꼬리 수정본의 frozen UI 7항목과 ZIP CRC/추출/소스 입력 해시는 통과했다. 그러나 추출 EXE의 실제 DSHOW 후보 1 연결은 cold/warm 두 실행 모두 15초 연결 시간 초과, 수신 0이었다. source의 같은 후보/해상도 성공과 구분하며, 실패 근거 `frozen_tail_camera_01`, `frozen_tail_camera_warm_02`를 보존했다. 이 ZIP은 실제 카메라 검증 완료본으로 취급하지 않는다. EXE 자식 프로세스의 대기 위치를 기록하는 opt-in 진단을 추가해 원인을 확인 중이다.
- `20260930_094604`의 시간 기반 stack dump 진단 실행은 access violation(exit -1073741819)으로 종료됐다. 이 진단 방식은 제거했고 결과를 카메라 성공 근거로 사용하지 않는다. 실패 로그 `frozen_camera_trace_01-worker-logs`는 보존했다.
- `20260930_095521`의 단계 시각 기록으로 원인을 확인했다. 작업 시작 준비 8.153초 + 장치 열기 5.004초 + 해상도 설정 3.252초로 첫 read 직전 준비 단계에 도달한 시점이 연결 요청 16.409초 뒤였다. 선택한 장치는 열렸지만 기존 단일 15초 제한이 먼저 경과했다. 근거: `runs/engine_misassembly_capture_001/camera-startup-diagnosis.json`와 해시가 기록된 두 process 로그. 이 실행은 ZIP 작성과 겹쳤으며 시작 지연의 OS 내부 원인까지 규명한 것은 아니다.
- camera worker의 ready 이벤트로 실행 준비(최대 30초)와 실제 첫 프레임 대기(ready 이후 15초)를 분리했다. 카메라 자동 대체·무한 대기·강제 저장은 없다. UI에서도 준비/첫 영상 대기/연결 해제를 구분한다. 새 timeout 회귀 3건은 수정 전 2 FAIL을 재현하고 수정 후 모두 PASS; 기존 camera/storage 29건과 portable 5건 PASS. 새 EXE의 실제 프레임 수신을 별도로 검증한다.
- 읽기 전용 DirectShow moniker 열거에서 현재 PC의 후보 1은 HCAM01L이었다(`dshow-device-enumeration.json`; 장치를 열지 않는 `enumerate_dshow.ps1`). OpenCV의 reported device_name/FPS는 null로 유지한다. PC·연결 순서가 다른 환경에서 번호를 HCAM 이름으로 고정하지 않는다.
- `20260930_100716` 추출 EXE에서 DSHOW 후보 1, 1280×720/MJPG, fresh sequence 40개 수신 PASS. 첫 프레임 11.615초/worker 준비 6.683초라는 단일 관측이며 성능 보장은 아니다. 원본 저장 0. 근거 `frozen_camera_deadline_01/result.json`.
- 같은 빌드의 frozen UI 시험에서는 저장 실패 후 재개 시 파일 준비/품질 계산 동안 프레임이 1초 freshness 한도를 넘는 경로가 드러났다(`frozen_release_02_ui/failure.txt`). 개발자 self-test 예외가 EXE 오류창으로 이어진 것도 확인했다. 해당 창은 시험 실행의 종료와 함께 닫았고 실패 자료를 보존했다.
- 파일/세션 준비를 별도 worker 단계로 먼저 끝낸 뒤 새 프레임 안정 대기를 시작한다. 준비/대기/저장 중에는 같은 step을 유지하고 한 클릭만 받는다. 보조 품질 계산은 원본 writer의 freshness 검사 뒤에 수행한다. 기존 1초 frame freshness·원본 검증을 완화하지 않았다. 느린 세션 준비(1.2초 추가)와 준비 중 일시정지/동일 버튼 재시도 회귀 PASS. 개발자 시험 오류는 로그+종료코드로 남기며 팝업을 띄우지 않는다. 소스 GUI 7항목, setup/결품/지연/중지/진단 5건, sample로 명시한 별도 writer 8항목 PASS. 최종 EXE/ZIP은 새 해시로 재검증한다.

### 실제 수정 파일 (2026-09-30)

- `notebook/training/capture_windows/misassembly_app.py`: 큰 Canvas, 최초 설정 패널, 명시적 재연결/해상도, 최초 정렬, 단계 고정, 진행/최근 사진/회전 안내.
- `misassembly_guidance.py`: 기존 정렬 기하/overlay 재사용, 위치 이동, 꼬리 윤곽, 원본 보존.
- `misassembly.py`: 결품별 기존 원본 저장 profile의 실제 개수/제거 slot, guide setup/명시적 sample 출처, 새 프레임 선택 전 저장 준비.
- `misassembly_entry.py`, `misassembly_ui_selftest.py`: Windows GUI 및 선택한 실제 카메라의 로컬 검증 경로.
- `misassembly_selftest.py`: 진단 원본을 실제 카메라 자료와 구분하는 sample 출처.
- `camera.py`, `portable.py`: worker ready와 드라이버 첫 영상 deadline 분리, opt-in 로컬 시작 단계 기록. 일반 촬영에는 진단 기록을 켜지 않는다.
- `build_misassembly.py`: onedir ZIP, 계획 기반 장수, Python/Tcl/Tk 라이선스 동봉.
- `assets/make_plan.py`, `misassembly-plan.json`, `make_coverage.py`, `existing-angle-coverage.json`, `reference-framing.json`: 10° 계획, 부족 각도 근거, 기준 구도 출처.
- `notebook/tests/test_misassembly_guidance.py`, `test_misassembly_setup.py`: 안내 기하/원본 불변/출처/각도 보충/첫 설정/결품 저장 검증.
- `notebook/tests/test_camera_startup.py`: 준비 시간과 장치 timeout, 즉시 실패 처리 검증.

이하 2026-09-29 기록은 이전 전달본의 증거이며 최신 수정본과 구분한다.

Status: PACKAGE_BUILT_AND_WINDOWS_SYNTHETIC_VERIFIED / PHYSICAL_CAMERA_NOT_RUN — 2026-09-29

## Scope and basis

- Reuse `notebook/training/capture_windows` camera, verified PNG/session writer, event log, quality gate and Windows PyInstaller pattern. Keep the reviewed Wizard policy and old collections untouched.
- At task start, `notebook/training/training.zip` had 54 entries; its Python files matched the current `notebook/training` source by SHA-256. The local ZIP later disappeared during unrelated workspace activity; no original was overwritten.
- `D:/머신러닝_학습자료/engine_parts_CFA8507_v001/source_audit.json` reports E01/E02 accepted acquisition, and `source_index.json` identifies D001 as accepted `train` NORMAL. Its bytes from `CFA8507BBBF384292.zip` match source SHA-256 `6dc94539570259d7747d8cc2b4d5fb0ed3d782b6b5a881408f427cd80c39f561`. D001 is guidance only; bbox candidates remain unreviewed.
- `D:/OnDevice과정/팀프로젝트/엔진모형/잘못끼워진` supplied mixed-state photos. Seven part-only crops retain parent SHA-256 and crop coordinates in `example-provenance.json`. No explanatory crop is a new training original.

## Implemented contract

- `operator-declared-one-click-v1` has an explicit click declaration event, followed by a post-click stable frame, verified old writer save, separate `simple_saved` event, and automatic next step. Retake supersedes metadata while preserving the prior PNG and count. Unreviewed rows remain `NOT_REVIEWED`.
- Pilot plan: 54 steps, consisting of six NORMAL device comparisons; six each for left/right pipe up/out and exhaust reverse/side; twelve for symbol upside down. One physical assembly state is grouped across its position and engine-angle targets. These counts are collection targets, not proof of model sufficiency. Planned engine angles are distinct from unmeasured mounting angle.
- Part states, target position/engine angle, session/assembly/group/setup IDs, camera properties, verified PNG path/bytes/hash, advisory quality and review status are exported. No automatic split, bbox, YOLO annotation, model, PLC or Jetson update.
- Handoff creates a new verified folder containing original session files, `capture-manifest.jsonl`, plan and partial/complete progress summary. Each raw copy is checked against recorded size and SHA-256.

## Verification

- Source synthetic save/metadata/duplicate/supersede/resume/export/disk-failure/no-progress/reopen retry: PASS.
- Source Tk startup and capture button visibility at 960×650: PASS. Plan 54 IDs, referenced assets and source/crop hashes: PASS.
- Existing focused regression: `test_dataset_wizard.py` 13/13, `test_windows_capture.py` 29/29, `test_engine_portable.py` 5/5 PASS.
- Final ZIP `dist/engine_misassembly_capture/20260929_173939/Engine_Misassembly_Capture.zip` (80,640,977 bytes; SHA-256 `eec59e897500f3f51aee665817c5c93ca20d737cd68c91aaa34e271ee5e91b2a`). EXE SHA-256 `6e0bebf9b16e368edc8819169baeba97bcc7572a9c2a9595b3577be58ab33a9a`.
- ZIP 41 entries/CRC PASS; extracted EXE byte-identical to release, seven crop files, normal image, plan, empty data/log folders present; all 37 recorded build inputs still match SHA-256.
- Extracted Windows EXE `--self-test`: exit 0, eight checks PASS (save, metadata, duplicate, supersede, resume, export, disk-failure/no-progress, retry after reopen). The copied handoff raws match row SHA-256 under Windows extended paths. Ordinary frozen no-camera startup stayed running without a startup error log; owned smoke process was stopped after observation. UI interaction and physical camera were not exercised in frozen mode.
- Physical USB camera and teammate PC: NOT_RUN. No image was captured from hardware in this task.

## Limitations for receiver

- Existing `source_audit` is an acquisition and origin check; old candidate boxes have no human label approval. New operator declarations require later dataset review before training adoption.
- Crop photographs come from mixed configurations; the screen confines each to the target part and directs the other parts to the accepted NORMAL reference. Actual installation angle is not measured.
