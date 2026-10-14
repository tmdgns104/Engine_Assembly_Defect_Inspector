# TASK-021 — PLC 자동 반복검사 배포 준비

기준 소스: `52ba2d4bac83949766af837067592488742ba501`. 2026-10-14 조사.
결론: **패키지·격리 검증 PASS / 실제 자동 반복 활성화 BLOCKED / 운영 미적용**.
새 승인 시스템·검사 알고리즘·PLC/EDS/모델/timeout 변경은 없다.

## 1. 배포 실패 원인과 수정

실패 run: https://github.com/tmdgns104/Engine_Assembly_Defect_Inspector/actions/runs/38550161553
깨끗한 52ba2d4 checkout에서도 `install.py --check-only`의 `collect_release()`가
`config/conveyor_references/raw_000.png`에서 실패하는 것을 재현했다.

Git 기본 `area_clearance.json`은 `DARK_SURFACE_SELF_OBSERVED`이고 references를
사용하지 않는다. 명시적 배포 목록에만 남은 raw_000~040(5 간격) PNG 9개를 제거했다.
현장 사진·가짜 이미지 업로드는 없다. 노트북의 기존 dirty 이미지 기반 설정과
Jetson의 실제 `CONVEYOR_FROZEN_EMPTY_ENVELOPE` 설정·9개 원본은 보존했다.
이 제거는 공개 기본 패키지의 불필요한 의존성 제거이며, 현장 설정 변경이 아니다.

추가로 누락된 기존 유지보수 HTML/JS 2개와 OpENer PROFILE을 포함했다.
정상 `/line`은 모니터링 화면이며 유지보수 화면 포함이 제품별 승인 재도입은 아니다.
배포 목록의 Python 로컬 import 대상 누락은 0개다.

필수 조립 검사에는 공개 checkout에 없는 동결 자산 28개가 필요했다. 기존 builder는
로컬 untracked manifest가 있으면 과거 run에서 이를 암묵적으로 가져왔고,
없으면 조립 자산을 조용히 생략했다. 다음처럼 명시화했다.

- `assembly_assets.lock.json`: 기존 28개 추론 코드/4분류기/매핑/정렬 자산 SHA 고정.
  운영 assets와 28개 모두 일치. 가중치와 알고리즘 바이트 변경 없음.
- `build_bundle.py`: `--assembly-assets <오프라인 자산 루트>`로만 가져온다.
  `--require-assembly`가 있으면 누락·SHA 불일치·경로 이탈을 거부한다.
- 기본 다운로드 패키지는 `CORE_MOCK_ONLY`/143파일로 명시한다.
  네 분류기가 포함된 현장용은 `INTEGRATED_AI_OFFLINE`/172파일이다.
  둘 다 현장 자격을 부여하지 않는다. 기본 MOCK 패키지를 운영 전체본으로 배포하면 안 된다.
- 이미지 기반 로컬 설정이 reference를 요구하면 allowlist 누락/해시 오류를 거부한다.
  사진을 빼고도 해당 설정이 유효하다고 잘못 통과시키지 않는다.

GitHub에 운영 DB·현장 사진·개인 설정·승인 원장을 추가하지 않았다.
동결 자산은 배포 패키지에만 명시적으로 들어가며 실행 시 다운로드하지 않는다.
기존 import 상대 경로를 유지하기 위해 자산 내부의 일부 `runs/` 이름은 유지한다.
전체 과거 프로젝트가 아니라 lock에 있는 파일만 포함한다.

## 2. 검증 및 산출물

| 검증 | 결과 |
|---|---|
| 깨끗한 Git export → install check | PASS |
| Linux ARM64 배포 회귀 | 31 PASS, skip 없음 |
| 기존 ARM64 Runtime 회귀 | 287 PASS / 91.730초 |
| C 초기/감독/자동 상태기계, ASan/UBSan, IPC clock/AF_UNIX | PASS |
| 기본·필수 조립 자산 포함 패키지 생성/내용 해시 | 모두 PASS |
| 실제 카메라/PLC/모터 시험 | NOT_RUN |
| GitHub Actions | [38553379628 SUCCESS](https://github.com/tmdgns104/Engine_Assembly_Defect_Inspector/actions/runs/38553379628), source `8e3386e60a03da461deb65040c7dd2fd411dd284` |

287개에는 실제 Worker 프로세스·Journal·AssemblyInspector·Runtime·C IPC 소유자를
사용한 승인 없는 3요청/3검사 ID와 3프레임, Result-only→다음 Done→reset이 포함된다.
카메라·모델·PLC 경계는 합성이다. 이것을 현장 제품 검사 성공으로 세지 않는다.
550ms commit 지연, 실제 보존 PNG 3장, STOP/저장 실패/IPC 손실/중복 차단 회귀를 유지했다.
이번 3제품 합성 경로의 원시 저장 commit은626.38~640.72ms, health 최대 간격은162.75ms였다.

노트북 증거 루트:
`runs/engine_standalone_plc_autostart_001/v001_20261007T052746Z/tag_data_link_008/deployment_readiness_021/`

| 산출물 | 값 |
|---|---|
| 현장용 코드·자산 Release | `engine-dev-267cd78f13b7bde8` |
| PC `INTEGRATED_FINAL.tar.gz` SHA256 | `f2c11f4f1e0e87d0a197522273a26ac6cacdc09d5bcdb2a3ec07ccb8d5b29ec0` |
| ARM64 결과 archive SHA256 | `06c978a3fcd400fef9f5315b86afed8be5ec31dcce273fd2d1cbcc02d79620c9` |
| 새 OpENer SHA256 | `127cedc473705479f6c135b513b6f9e8f86733b0eb89b50361a53f7ef1be98ac` |

PC와 ARM64 생성 패키지의 Release/내용 manifest는 같다. gzip 파일명·생성 시각 때문에
압축 archive 자체 SHA는 다르므로 바꿔 쓰지 않는다. source와 바이너리는 TASK020 검증본이다.

## 3. 실제 운영본과 자동 모드 차이

운영 Release는 여전히 **engine-integrated-4920568fe3750b64**,
source commit `45c36945928cdcbf04fa667d123a7b5342184adc`다.
service enabled/active, MainPID41150, NRestarts0. OpENer41167, 카메라 Worker41191,
필수 조립 검사 ready. 실제 검사/저장/Assembly 작업은 idle이다.
일부 Tracking active_cycle 객체와 실제 검사 중 상태를 혼동하지 않는다.

읽기 확인: Mc_Run=0, Request=0, Result=0, Done=0, EStop_OK=1, Stop_PB=1.
Stop_PB=1은 해제 상태 값이며 STOP을 물리적으로 누르고 있다는 뜻이 아니다.
새 물리 정지는 다음 현장 적용 직전에 다시 확인해야 한다.
이번 코드·C 교체, 서비스 재시작, 승인 발급, PLC 쓰기는 0회다.

| 설정 | 현재 운영 | 후속 변경안 / 증거 상태 |
|---|---|---|
| cycle_admission | FIRST_PRODUCT_ONLY | PLC_AUTOMATIC_REPEAT |
| initial_authorization | EXPLICIT_ONE_SHOT_V1 | 정상 자동 경로에서 제거 |
| OpENer SHA | 8506ffc2…842b82e | 127cedc4…1be98ac |
| supervised_web.enabled | false | false 유지; 제품별 코드/버튼 없음 |
| field_profile_verified | false | 증거 전 false 유지 |
| request_start_qualification | false | 실제 calibration SHA/근거 없으므로 미승인 유지 |
| automatic_operation_qualification | 없음 | 아래 항목 입증 전 생성·TRUE 금지 |
| PLC/EDS/4·8·10B 및 AI 판정 정책 | 기존 계약 | 변경 없음 |

**현재 값을 바꾸기만 해서 실제 자동 반복 모드로 진입할 수는 없다.** `_profile_ready()`는
온라인 PLC 동등성, 독립 timeout/STOP 복구, 출구 시야·방향과 calibration 근거를 요구한다.
이는 매 제품 권한이 아니라 현장 구성을 한 번 채택하기 위한 검증이다.
제품마다 approval ID/CLI/automatic_arm을 만드는 코드는 추가하지 않았다.

## 4. 실제 자동 검사 진입 차단

### 이전 Journal 제품 이탈

읽기 전용 DB `quick_check=ok`, 검사 116행. 새 소스와 동일한 SQL을 실행했다.
마지막 OPENER_CYCLIC + Track + integrated_decision 기록은
`9edd7bf904094733b9f92908bf566c17`이다. `AUTOMATIC_PRODUCT_SEPARATED`는 **0건**이다.
따라서 새 Runtime을 기동하면 `PREVIOUS_RUNTIME_PRODUCT_EXIT_UNPROVEN`이 실제로 설정된다.
98c04…의 기존 독립 ABORTED는 그대로 있으며 이 과거 제품 이탈 문제를 대신 해소하지 않는다.

현재 코드는 이 차단이 있는 새 유효 요청에서 제품을 새 엔진으로 묶지 못하고,
제한시간 ERROR/NO_ACTUAL_INSPECTION으로 끝날 수 있다. NG·Done 전달과 실제 검사 성공은 다르다.
**과거 제품을 새 연결의 Track과 연결해 이탈을 입증하거나, 감독하 예외 복구를 정식 기록하는
지원 경로가 현재 소스에 없다.** 기록 삭제/가짜 separation 삽입으로 해결하지 않았다.
이는 첫 실제 AI 반복 시험 전 해결해야 할 별도 명시적 차단 사항이다.

### PLC 로직·센서 래치·timeout

보존된 선택 프로젝트 SHA `9f491ee447dd5736858d07d2174a033a1654501b18f4c53fa641b4bf29b97806`에서
Move_pending 래치, TON T#2.7s, Inspecting 동안 Request 유지,
Done 후 Inspecting 해제, PhotoSensor OFF/Done OFF/Cycle_Done 조건의 Sensor_Ready 복귀를 확인한
기존 소스 분석을 재사용했다. Assembly150에는 포토센서 원신호가 없다.
과거 실제 NG 1회 소비·재가동 성공은 유효하나 현재 온라인 전체 로직 동등성 증거는 아니다.

선택 소스 23개 래더에는 독립 검사 응답 timeout TON이 확인되지 않았고,
Mc_Run OFF 때 Move_pending 정리도 미확인이다. 이송 중 STOP·응답 누락 후 복구는 NOT_VERIFIED.
온라인 동등성/timeout/STOP 복구를 TRUE로 둘 수 없으며 무인 자동운전은 허용 준비가 안 됐다.
PLC 수정 필요 여부는 온라인 대조 후 결정하고, 이번에는 PLC를 변경하지 않았다.

### ProductPassage와 실제 영상

현재 관측 FPS는 읽기 시점 약10.95다. 소스는 sequence 정확히 +1, 동일 epoch/generation,
프레임 간격 ≤0.5초, 나이 ≤1초, 출구 방향의 연속 bbox 이동/겹침/축소,
경계 통과 후 원래 폭20% 이하 tail, 이후 1.2초·6프레임 이상의 출구 관측을 요구한다.
전체 화면이 빈 상태일 필요는 없다. 잠깐 검출 소실/새 Request만으로 이탈을 인정하지 않는다.

기존 실제 위치 시험 373개 샘플(제품1개 관측219개)을 그대로 재생했다.
372개 인접 쌍 중334개에 sequence 간격이 있었고 좌/우 모두 continuity 거부로 proof가 없었다.
이는 HTTP 샘플 기록이므로 Runtime 자체가334번 누락했다는 뜻은 아니다.
Journal의 검사3프레임도 결과 이후 이탈 기록이 아니다. 따라서 현재 자료로 출구 방향,
연속 tail 관측, 제품 완전 이탈을 승인할 수 없다.

다음 현장 증거에는 **Runtime이 실제 소비한 연속 관측의 frame ID/sequence/epoch/시간/bbox**와
작업자의 제품 이탈 확인이 필요하다. 현 카메라 시야/FPS에서 이를 확보할 수 없다면
출구까지 보이는 카메라 배치 또는 별도의 배출 센서/PLC 관측 계약이 필요하다.
이번에 새 영상 알고리즘·허용 오차·프레임 조건 완화는 하지 않았다.

## 5. Class1 / IPC

운영의 구 C 실행 파일은 아직 TASK020 IPC 수신 시각 수정·추가 계측이 적용되지 않았다.
이번 읽기 기록에서도 connection19→24, 누적 timeout23이 확인됐다. Result/Done은0회다.
예: conn19 timeout의 마지막 RX age205.051ms/health age30.518ms,
conn20은 RX1.367231s/health1.380266s, conn23은 RX0.928ms/health0.042ms다.
마지막 수신 직후 timeout 콜백이 발생할 수 있는 기존 루프 순서 때문에
낮은 RX age만으로 패킷 손실을 배제할 수 없다. 첫 원인은 여전히 UNRESOLVED다.

일부 재접속은 같은 Jetson에서 격리 CPU 회귀를 돌린 시간과 겹친다.
부하와의 상관 가능성은 있지만 원인 확정은 아니다. Python heartbeat 지연,
호스트 스케줄링/파일 기록 지연, 실제 UDP 및 PLC 측 오류를 분리할 계측이 필요하다.
RPI50ms·timeout·lease를 늘리지 않았다. IPC 시각 회귀 PASS를 Class1 현장 해결로 보고하지 않는다.

## 6. 후속 배포·복원 계획

1. 새 현장 적용 확인 후 실제 STOP/작업영역, PLC LOW, 검사·저장·Assembly idle을 다시 확인한다.
2. 노트북에 current 전체/설정/unit/Release/SHA, SQLite backup API의 Journal·승인 DB를 회수한다.
   이번 읽기 백업 `CURRENT_492_READONLY_BACKUP.tar.gz`는144파일/링크1,
   SHA `a40be93205634b90006d274a092d619862af591c2bd7b8303be8ebfb3c852011`.
   모든 내용 해시와 SQLite integrity=ok를 노트북에서 확인했다.
   서비스 정상 종료 경계에서 다시 백업해야 하며 지금 백업을 미래 시점의 최신 DB로 간주하지 않는다.
3. `INTEGRATED_OFFLINE` 패키지를 기준으로 실제 설정/경로/새 C SHA를 묶은 최종 manifest를 만든다.
   실제 assets/config/data/envs를 보존한다. Git의 기본 area 설정으로 현장 설정을 덮지 않는다.
   새 코드만 확인하는 단계는 `cyclic_publication_enabled=false`로 대기시키고,
   자동 현장 자격은 false 유지한다. 실행 중 파일 부분 덮어쓰기는 하지 않는다.
4. 승인된 정상 service stop→자식 종료 확인→staging 전체 검증→단일 current 전환→start.
   Python/C manifest, 단일 카메라/OpENer, 유지보수와 무관한 모니터 UI, LOW/무출력 확인.
5. 실패하면 STOP 유지, 새 서비스 정상 종료 후 노트북의 직전 current/config/unit 복원.
   현재 Journal·ABORTED·승인 소비 기록은 이전 DB로 되돌리지 않는다.
   새 검사 결과를 만들거나 과거 결과를 재전송하지 않는다.
6. 성공 확인 후 검증한 임시 staging만 정리한다. 모델/증거/보호 파일은 삭제하지 않는다.

백업/복원 자료 검증은 PASS, 실제 전환 및 복원 실행은 NOT_RUN이다.

## 7. 후속 최대 3제품 시험

위 차단의 근거가 해결되기 전에는 START를 안내하지 않는다. 이후 별도 현장 적용·감독 확인을 받고
최대3제품을 순서대로 시험한다. 매 제품 소프트웨어 권한/웹 승인/CLI는 사용하지 않는다.

- 최초 정지 기준→현장 START→센서/2.7초 정지→새 Request와 고유 검사 ID를 연결한다.
- 각 제품 원본3프레임/SHA/원시 AI/필수 조립/통합 Journal, Result-only와 다음 cyclic Done,
  Request LOW 및 출력 reset, PLC 결과 반영, 실제 벨트 재가동을 같은 시간축으로 확인한다.
- 이전 제품 이탈 proof와 다음 제품 Track 구분을 확인한 뒤 다음 Request를 자동 접수한다.
- PASS는OK, FAIL/REVIEW/ERROR는NG·Done; 원 판정은 보존한다.
  저장·통신 실패/STOP 취소 후 늦은 결과는 보내지 않는다.
- 문제가 생기면 현장 STOP 후 로그/해당 검사 보존. 추가 START 반복 금지.

운전 완료 기준은3개의 서로 다른 실제 검사 ID에 대한 위 경로 전체이며,
합성 테스트나 ERROR/NO_ACTUAL_INSPECTION만으로 실제 연속검사 PASS를 선언하지 않는다.

최종 상태: **STOP_FOR_FIELD_DEPLOYMENT_APPROVAL**.
코드·패키지는 준비됐지만 현장 자동운전 자격과 과거 제품 식별 차단 해소는 미완료다.
운영 서비스 교체·PLC 쓰기·실제 START·Result/Done은 이번 작업에서 수행하지 않았다.

최종 보존 확인: current/config 해시·service PID41150/NRestarts0 불변, 카메라 Worker41191 정상,
Mc_Run/Request/Result/Done=0. connection은28로 증가하여 Class1 미해결 상태를 유지한다.
노트북 회수·해시 확인 후 이번 TASK021 소유의 Jetson 격리 디렉터리만 정리했다.

최종 패키지는 Git blob 기준 LF manifest로 확정했다. ARM64 회귀 당시 패키지와 다른 내용은
FROZEN_MANIFEST.json의 CRLF/LF뿐이며 JSON 의미·나머지171파일 SHA는 동일하다.
최종 archive172파일을 ARM64 메모리에서 다시 읽어 모든 SHA를 확인했다
(`FINAL_ARM64_PACKAGE_VERIFICATION.json`). 실행/모델 테스트를 중복 수행하지 않았다.
