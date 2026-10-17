# 실제 운영 중단 조건 감사 — 2026-10-17

상태: **수정본 적용·실제 재부팅 자동 기동 확인 / 노트북 분리 후 실물 30회 시험 진행 안내 / 결과 검증 대기**.
현재 운영본은 `engine-integrated-f03d3f570a172c5f`다. 사용자 START 이후 실제 `Mc_Run=true`, Request LOW, IDLE, 오류 없음과 새 시험 카운터 0을 확인했다. 노트북 LAN 분리 사용자 확인과 SSH 접속 단절을 기록한 뒤 정상 모형 30회 연속 투입을 안내했다. 노트북이 분리된 동안의 실제 완료 수는 재연결 후 Jetson 원기록으로 검증한다.
Git 공개 대상만 내보낸 별도 작업 폴더에서도 관련 회귀 349개 중 344PASS·5skip(비공개 사진 1, Linux 전용 4)을 확인했다. 기존 UI 2건은 해당 회귀 범위에서 미검증으로 남는다. 실제 배포한 8파일과 공개 소스는 줄바꿈을 정규화하면 동일하며, Git의 LF 변환으로 달라진 바이트 해시는 런타임 해시와 구분해 `PUBLICATION_EXPORT_TEST.json`에 보존했다. 모델·원본·SQLite·현장 증거 파일은 Git에 포함하지 않는다.
공개 묶음에 새 런타임 모듈 4개가 빠지지 않도록 기존 allowlist와 관련 계약 시험도 함께 포함한다. 별도 Git 내보내기의 배포 계약 시험 7개가 통과했다(`PUBLICATION_MANIFEST_TEST_v003.json`). 앞선 검사 도구의 notebook import 경로 오류와 Windows 임시 폴더 권한 오류는 로그를 보존했으며, 제품 소스 변경 없이 명시적인 내보내기 경로와 작업 폴더 내 임시 경로로 해결했다. 이 검증은 새 장치의 전체 모델 설치·실물 수용 완료를 뜻하지 않는다.
사용자 최신 TASK(2026-10-17)가 기존 촬영/처리기한 설계 승인 대기를 대체한다.
현재 Task는 `tasks/CONTINUOUS-30-FIELD-001.md`이며 이전 실패/원본은 보존한다.

## 수정 전 실제 실행본과 비교

근거: `runs/runtime_audit_20261017/RUNTIME_BEFORE.json`, `SOURCE_COMPARISON.json`.
운영 `engine-integrated-a807de46a264aa3e`, boot `d1c9285e-c935-44b3-9dad-5dfce734a7aa`.
systemd enabled/active, Main5395, 시작 2026-10-17 12:34:22 KST.
ExecStart는 `envs/app_v1/bin/python -B -X utf8 current/standalone_service.py --config config/standalone.json`.
실제 cwd `current`, 인터프리터 실제 파일 `/usr/bin/python3.10`; 가상환경 명령행 유지.
자식 OpENer5412, Assembly5416, Inspection5447. multiprocessing 보조 프로세스 포함 명령행은 원증거에 보존.
촬영/모델 재시작·PLC 조작 없이 조회했다. PLC STOP/Request LOW, Result/Done0.
카메라/Worker/조립 준비 확인. 이전 c7f15…는 raw COMPLETE/PASS이나 integrated INCOMPLETE/PLC BLOCKED로 유지.

GitHub HEAD와 로컬 HEAD는 `5fe3669318b166ee945d04cc0bd7cafe865f9e23`로 동일하다.
비교 가능한 운영 파일131개 중 로컬 working tree와 바이트 동일127, HEAD와 동일109.
차이4개는 release.json, supervised_panel.html/js, journal/sqlite.py.
sqlite.py는 줄바꿈을 정규화한 본문 차이 없음. 나머지는 배포 범위 결정 전 별도 대조 대상.
메모리 코드를 직접 덤프한 검증은 아니다. 실행시각·Release 응답·과거189파일 배포 증거와 디스크 해시를 연결했으며,
파일 해시만으로 메모리 코드 일치를 단정하지 않는다. 루트 RELEASE_MANIFEST는 과거값이므로 현재 운영 근거로 쓰지 않는다.

운영 SHA256:

| 대상 | SHA256 |
|---|---|
| current/standalone_service.py | fdac0226b17add99f035a87eb8486a5743d112ba7d7081af839b3ac6fb30ff44 |
| current/opener/OpENer | 63ca4b16db530eecc9f95155a40cf758b291a590d85894dc8e9faf7aa0b2f4a4 |
| config/standalone.json | f128f7999c9bdec4a973a22eade5e1042c15436e3b9e6a91f6ebd834bf240a91 |
| config/station.json | 23fab6d7dd0b50c86cfdb1b51d6215e59c25d0bab0a3763f62cbf8e4999773bb |
| config/line_profile.json | 4568dab0cd26311819fc273f3f9b43a6a2578abdd4283dcbbe2c1daf65d0159f |

## 실제 경로와 기존 상태

standalone_service.main → OpenerProcess + OpenerGateway + StandaloneRuntime,
실제 선택: EXISTING_PLC_INSPECTION / OPENER_CYCLIC / PLC_AUTOMATIC_REPEAT /
PLC_REQUEST_TRACKED_FULL_FRAME / STATIONARY. 최종 판정은 BASIC_PRESENCE_ASSEMBLY_REFERENCE_V2.
카메라와 모델은 기존 Inspection Worker만 소유하며 조립은 별도 ProcessAssemblyInspector.

| 동작 | 기존 상태·담당 | 완료 근거 |
|---|---|---|
| 대기 | C IDLE / Handshake ARMED / Service IDLE | 실제 LOW 및 건강·직전 거래 정리 |
| 요청 수락 | C REQUEST_RECEIVED → REQUEST_LATCHED → Service ADMITTING | C boot/connection/request + Writer의 영속 admission |
| 촬영·처리 | Handshake INSPECTING / Service BUSY | 원 trigger와 durable admission 이후의 새 프레임 |
| 원본 저장 | BUSY + storage_pending | Journal.finish 완료와 같은 context의 Writer receipt |
| 조립·통합 저장 | INSPECTION_DURABLE → ASSEMBLY_INSPECTING / final_pending | 조립 evidence + commit_integrated |
| 결과 송신 | IPC_QUEUED → C TEST_RESULT_READY → RESULT_SENT | queued는 송신 완료가 아님; 실제 C 수락/전송 기록 |
| 종료 | DONE_SENT → WAIT_REQUEST_OFF → CLEARING_DONE → READY_NEXT | Result와 다른 후속 패킷 Done, LOW, clear 전송 |
| 다음 대기 | retire_automatic → IDLE | 정리된 거래/기록; 물리적으로 다른 모형이라는 주장은 하지 않음 |

## 차단 조건 표

A 실제 활성, B 다른 모드 비활성, C 수정되어 운영 반영, D 후보만 반영, E 증거 부족.
행 번호는 감사 시작 당시 소스 기준이며 수정 후 diff와 함께 읽는다.

| 분류·조건 | 파일·함수·행 | 설정·시계 | 전→후 / 영향 | 회복·증거 | 조치 |
|---|---|---|---|---|---|
| A 촬영3초가 active deadline까지 대체 | production_admission.py activate:164–176 | station fresh_frame=3000ms, trigger부터; 기존15초 덮음 | BUSY/저장→health false→C취소 | attempt08 c7f… 실제 재현; 늦은 저장은 원PASS 보존, 재전송 금지 | **최초 원인 수정** |
| A 추론/인코딩 뒤 촬영기한 재검사 | inspection_worker.py worker_main:405,463 | selector.check_active, 마지막 선택 이후에도3초 | 유효 원본→ERROR | 경계 fixture로 전후 비교 | **같은 원인 수정** |
| A 늦은/중복/이전epoch 프레임 | fresh_frame.py consider:112 이후 | 요청+epsilon/영속수락 floor, age350ms, 간격150ms, 촬영3초 | 선택 거부/현재 ERROR | 기존 floor/epoch/cancel 회귀 | 유지 |
| A 저장기한·context·Writer 생존 | inspection.py health:203–215 / _storage_completions:163 | 현재 active deadline, generation/epoch/identity | BUSY→RECOVERY/현재 차단 | 원본/SQL 성공과 PLC 완료 구분; 경계 경합 추가 시험 | 기한 범위 수정·보호 유지 |
| A Worker/camera/disk | inspection.py health:187–235 | heartbeat5초, preview2초, 실제disk 여유 | health false→C disarm | 실제 사망/단절은 자동 heartbeat로 은폐 안 함 | 유지 |
| C 요청 시작 동기SQL 지연 | request_start.py tick/_submit; production_admission.prepare/activate | 단일 기존 Writer, durable-before-dispatch | ADMITTING 중 실제제어 검사 지속 | 이전 Windows/ARM64각318실행, native6; 운영 반영 | 재설계 없이 지연 회귀 |
| C 원본/최종/완료감사SQL | result_storage.py _run:40; standalone.py _run:1700 / _storage_wait_health:1658 | bounded writer, Journal try-lock; queue1 | 정상pending은 대기, 실제실패는 차단 | 기존550ms 지연 health최대110.766ms(합성) | 조합 회귀 |
| A Python Ready lease | opener_cyclic.py _connected_loop:171 | 실제 health_update부터400ms | Ready→false; C취소 | 이전418ms 사례, attempt08 최대192.385ms로 이번 원인 아님 | 유지 |
| A C Python heartbeat | engine_commissioning.c CommTick:277 | 마지막IPC heartbeat부터500ms | active→DISARMED | 명령수신 주기; Ready lease와 별개 | 유지 |
| A PLC freshness | engine_callbacks.c.inc EngineInit:105 / CommControlsValid | 마지막 cyclic 입력부터200ms | 입력/출력허가차단 | 실제 C config값; heartbeat와 별개 | 유지 |
| A IPC freshness | opener_cyclic.py decode_snapshot:21/read_snapshot:87 | 생성시각500ms, timeout poll100ms | snapshot없음→HOLD | 기존 poll vs lease 분리 | 유지 |
| A 전체 PLC 거래 상한 | engine_callbacks.c.inc:113 / CommTick:285 | C request_at부터120초, Result/Done/LOW까지 | active→REQUEST_HANDSHAKE_TIMEOUT | 소스 설정 확인; 운영 binary build 대응 추가확인 필요 | 유지 |
| A 요청전 관찰·조립 대기 | standalone.py _trigger_cyclic:1154/_poll_result:1558 | line_profile arrival30초(C accepted_at), assembly30초(조립submit) | 촬영미실행 ERROR 또는 조립시스템실패 | 총상한120초가별도존재;15초를 단계마다 재부여 안 함 | 유지·전체시간계측 |
| A HIGH 잔류2초 | standalone.py _automatic_health:559–568 | disarmed/sync/idle/ready_next에서HIGH 관측부터2초 | 다음요청차단/물리STOP필요 | attempt08은 **수락 후 저장기한→취소의 후속오류**, 처음부터 미수락 아님 | 2초삭제/가짜Done 금지 |
| C 이전 배출 추적 오류 | standalone.py _automatic_health/_start_automatic_observation_window; product_passage.py | 새C cycle+정리된거래+새관측; 과거passage진단 | 과거오류가다음cycle영구차단하지않음 | cycle_scoped_tracking 배포증거; 새 물리제품 증명 아님 | 회귀 |
| B 과거 제품 배출 필수 gate | standalone.py supervised/기존tracking 분기 | 현재 automatic정책과다름 | 다른모드전용 | import/call조건 기준 구분 | 작업 제외 |
| C 완료 후 preview 미검출 | standalone.py _validate_cyclic_final:1357, _completed_observation; completed_evidence.py | automatic/fullframe, 현재검사3원본durable | 과거preview guard대신현재원본검증 | 이전 완료6건; 카메라실제장애/epoch/STOP/세션검사는유지 | 회귀 |
| A 현재cycle/session/STOP 취소 | standalone.py _poll_cyclic/_validate_cyclic_final; CyclicHandshake.poll | 실제controls/token/generation/epoch | INSPECTING→HOLD/BLOCKED | 현재제어유효성필수 | 유지 |
| A IPC 결과 queued→무송신 | opener_cyclic.py _connected_loop:200–211; standalone.py _publish_committed:1479 | queue400ms+healthy+동일key+REQUEST_RECEIVED | 조건실패시pending제거; published_ids는이미추가 | 실제발동 미확인, C120초가유한차단; 명시적실패진단시험필요 | 최초원인수정후 별도검증 |
| A 미완료Journal 복구 | aborted_recovery.py / request_start.py settlement:108 | 동일원거래final/취소/전송증거 | 다음수락보류 | 현재c7f…실제복원; 원PASS를완료거래로위조하지않음 | STOP 기반 append-only 복구 유지 |
| A 조립 참고분석과시스템실패 | integrated_decision.py combine_decisions; standalone.py:1563 | 참고 오조립FAIL은최종영향없음, 실행/저장실패는별개 | 정상참고FAIL은다음cycle가능; 시스템실패BLOCK | V2정책유지 | 임의생략/먼저PASS금지 |
| A C evidence 실패/한도 | engine_evidence.c Writer:29,52 / callbacks | queue128, events12000/16MiB, 별도Writer | 기록실패→출력차단 | 장시간한도실측미확인; 첫30회와장기보장구분 | 보호유지·누적계측 |
| A 기동 잔여IPC 소켓 | opener_process.py __init__:33–36 | 배타owner lock후에도존재하면거부 | 부팅service5회실패 | 10/17 실제, 수동무소유확인/보존이동복구 | 자동기동수용의남은문제 |
| E Windows 수집기 nonPASS 중단 | 기존continuous observer 조건 추적 중 | REVIEW/FAIL시collector종료와서비스차단구분 | 수집기만종료가능 | Jetson영속기록으로30집계하도록점검 | 완료전확인 |
| C 노트북 의존 | standalone_service/main, local Journal/OpENer/Worker | 직접Jetson192.168.50.2↔PLC192.168.50.3 | UI/export ACK를기동조건으로쓰지않음 | 코드상독립; 노트북없는실물은미검증 | 실제 단독30 필요 |

## 최초 수정 단위

원 capture trigger부터 **촬영3초**, **원검사 처리/PNG·Journal 저장15초**를 분리한다.
prepare→Writer admission→dispatch 사이에서15초를 다시 시작하지 않는다.
마지막 선택시각은 원본 metadata의 selected_at_monotonic이며 추론 종료시각과 구분한다.
선택3초 이후 원본은 계속 거부한다. 이미 선택된 사진의 추론/인코딩은 기존15초까지만 허용한다.
후속 조립30초 및 C 거래 전체120초는 기존 계약대로이며,15초가 전체PLC거래 SLA라는 주장은 하지 않는다.
STOP·취소·원본 무결성·Worker 사망·queue/SQL실패·세션소유권·중복전송 보호는 유지한다.

수정 전 `attempt08/DEADLINE_REPRODUCTION.json`을 재사용하고, 새 fixture는 추가로 마지막 추론/인코딩 경계를 검증한다.
합성 회귀는 실물 횟수로 세지 않는다. 이후 같은운영본·한START의30개 완료거래에서 원본3장/판정/Result→Done/LOW/다음수락을 감사한다.
정상제품의 REVIEW/FAIL 분포는 AI성능 항목에 별도로 남긴다. 사진없는ERROR는 실물AI검사완료로 세지 않는다.

## 2026-10-17 검증 후보와 배포 준비

**최신 적용 결과:** `f03d3f570a172c5f` 실제적용및재부팅자동기동 확인. 백업174파일/SQLite 무결성·노트북SHA=`590779f37fa69ad8d98a6b60d2be23bf0669c68254e138bae35313722df7e48d`. 새boot `c050e0e3-9cd9-4b69-80de-76932fd6616d`, systemd enabled/active Main1078 NRestarts0, 단일카메라Worker2758, 운영189파일SHA·모델·PLC ready·WAIT_START. 이후31.36초동안7개서로다른프레임과같은Worker/STOP대기확인. 재부팅후수동복구없음. 이전검사원본·행·final보존,미전송건은기존ABORTED추가,새grant/재전송없음. 실물연속30회와장시간안정성은아직미검증이다. 아래는적용직전준비기록이다.

후보 `engine-integrated-f03d3f570a172c5f`, 운영 `a807de46a264aa3e`에서 정확히8파일만 변경한다. 아직 적용·재부팅·새 실물 시험 전이다. 현재 사용자STOP·모형전부제거 확인과 실제PLC STOP/RequestLOW/출력0을 대조했다. 이전 실패 c7f…는 원본4자산/원판정PASS/통합미완료/미전송을 그대로 보존하며 기존 append-only abort 절차의 읽기 전용 사전검증을 통과했다. 새grant/사진/PLC출력은 생성하지 않았다.

| 확인 | 실제 결과 | 한계 |
|---|---|---|
| 촬영/처리·저장 경계 수정 전 재현 | 유효 마지막사진 추론/인코딩과저장이 촬영창을 넘을 때 실패 재현 | 기존attempt08와 연결, 새로운 실물 아님 |
| 관련회귀 | Windows와ARM64 각각338실행:337PASS+기존자료1skip | 기존 UI2 및 전체패키징자산2 차단은 PASS로 세지 않음 |
| 실제 C/Python 격리 IPC |7PASS, 한START12회 요청/원본/최종저장에350/450/600/1000ms지연 | 합성 PLC·AI, 실제PLC네트워크 미사용 |
| 12회 health 갱신 간격 | 최대114.614ms, p95=102.749ms,p99=110.606ms,488구간 | 400ms 기준 유지; 현장 지연보장은 아님 |
| 기동 잔여소켓 |Windows35PASS+Linux전용4skip / ARM64 39PASS | 실제재부팅 자동기동은 적용 후확인 |
| 송신대기 경계 |추가5PASS: stale/healthfalse/다른session·request/phase불일치 무송신; ambiguoussend 재생금지 | 소켓send도 C수락·PLC완료가아님; C120초의 유한거래상한은유지 |

IPC 감사 보충: `OpenerGateway._connected_loop`의 조건불일치 시 pending 제거가 실제로 존재한다. Python의 published표시만으로 검사완료를 집계하지 않는다. 같은C 거래는120초 상한/health·controls 실패로취소되므로 이 경로 자체를 무한대기라고 단정할 수없다. 현재현장 최초원인으로 입증되지 않아 통신동작을 추가변경하지 않았다. 자동재전송도 추가하지 않았다.

수집기 보충: `notebook/diagnostics/collect_field100.py:167–173`은 ERROR·필수사진부족·시스템fault에서 종료한다. REVIEW/FAIL만으로는 종료하지 않는다. `runs/continuous_30_20261016/observe.py`도 판정을 출력할 뿐 서비스제어를하지않는다. 과거 각회차STOP은 당시정상PASS 시험의 사람개입 절차였다. 새승인기준은 Jetson Journal과실제C Result/Done/LOW의30회 완료이며 수집기 실행유무가 검사허가가아니다.

증거 정정(원본 유지): `IPC_RESULT.json`의 12회항목 `injected_storage_delay_ms=550`은 이전3회fixture의 요약필드가 남은 값이다. 실제12회 지연은 같은항목의 `stage_delays`12개(각단계350/450/600/1000ms)와 동결시험소스를 따른다. 측정치나원본JSON을 고쳐 성공을만들지않았다. PC회귀 완료 뒤 보고용 CANDIDATE누락 오류는 원로그/입력해시를 대조해 별도receipt로복구했다. 추가IPC단위시험 최초Windows실패는fixture의AF_UNIX상수누락이었고, 시스템호출mock을보완한v002에서5PASS했다. 제품코드수정은없었다.

배포사전근거: `runs/runtime_audit_20261017/FINAL_CANDIDATE.json`, `DEPLOYMENT_VALIDATION.json`, `RAW_ABORT_CHECK.json`. 백업은정지후SQLite backup API와전체운영파일SHA를노트북에서검증한뒤에만적용한다. 권한상 원격sudo는비밀번호를요구하여사용자터미널의시작명령을기다린다.

## 2026-10-17 단독 실물 attempt09 결과와 수락 대기 수정

노트북 LAN을 분리한 상태에서 한 START로 **17개 요청 중 16개 PLC 거래가 완료**됐다. 17번째 요청에서 운전이 중단되어 사용자가 STOP 후 LAN을 다시 연결했다. 부품 검사 결과는 **PASS 14건, 촬영 ERROR 2건, 촬영 전 취소 ERROR 1건**이다. 최대 연속 유효 PASS는 13회이며 **30회 안정성 목표는 미달성**이다. 16건 완료를 16건 정상 검사로 바꾸어 집계하지 않는다.

실제 SQLite와 C trace에서 첫 16건 모두 원본 3장·표시 이미지 1장, 통합 결과, Result → 이후 sequence의 Done → Request LOW → Done 해제 → 다음 요청 대기를 확인했다. 64개 자산 SHA 및 SQLite quick_check를 확인했다. C 요청부터 거래 완료까지 최소 9.555초, 중앙값 10.031초, 최대 16.304초다. 첫 요청부터 16번째 완료까지 290.250초였다. 이 짧은 시험을 장시간 안정성으로 표시하지 않는다. 수집기는 첫 ERROR에서 종료됐지만 운영 서비스는 계속 실행됐으며, 이후 건수는 Jetson 원장과 C trace에서 직접 복원했다. 원증거: `runs/runtime_audit_20261017/ATTEMPT09_AUDIT.json`, `FIELD30_NATIVE.json`.

| 사례 | 실제 증거 | 해석과 남은 한계 |
|---|---|---|
| 1번째 `258e0266…` | `DEADLINE_EXCEEDED`, 후보 11장 중 거부 8장. 마지막 진단 사진의 motion_fraction 0.030486, stable=false | 원래 3초 안에 안정된 연속 3장을 확보하지 못함. 저장된 3장 각각의 부품 판정은 PASS여도 촬영 요건 통과가 아님 |
| 15번째 `e64adb5b…` | 같은 촬영 오류, 후보 12장 중 거부 9장. 저장된 진단 사진 3장 모두 stable=false | 작은 순간 변화량만으로 0.6초 연속 안정 시간을 충족했다고 할 수 없음. 원본을 실제 열어 확인했으나 진동·밝기 변화 중 어느 것이 주원인인지 미확정 |
| 17번째 `55766bc5…` | 수락 저장 253.908ms 정상 완료. 같은 camera/worker/track 1. frame 8646→8647에서 eligible true→false 뒤 `ADMISSION_CURRENT_TRACK_OR_REQUEST_CHANGED` | 정확한 8647 provider packet은 보존되지 않아 순간 미검출을 현장 직접 원인으로 확정할 수 없음. 촬영·통합 final·C Result/Done 모두 없음. health lease 만료가 아니라 Python의 명시적 Ready 해제 |

운영 코드에서는 수락 저장 직후의 일시적 영상 부적격과 실제 요청/추적 소유권 변경을 같은 오류로 처리했다. 동일 조건의 격리 재현은 수정 전 실패했다. 후보는 **`src/runtime/request_start.py` 한 파일**만 변경한다. 같은 영속 수락 receipt를 유지하면서 원래 기한 안에서 새 유효 프레임을 기다리고, 재저장·중복 촬영 요청 없이 한 번만 시작한다. 요청·track 변경, STOP/EStop, 카메라/Worker/통신/저장 실패와 기존 기한은 계속 차단한다. 촬영3초·처리15초·Ready400ms·모델·검출/안정화 임계값은 변경하지 않았다. 위 촬영 ERROR 두 건까지 해결됐다고 주장하지 않는다.

검증: Windows 73/73, ARM64 73/73 PASS. 실제 C AF_UNIX 격리 경로는 서로 다른 시험 8개를 검증했다. 새 시험은 같은 수락 receipt에서 미검출 3tick 후 새 프레임으로 3거래를 완료했고 갱신 간격 최대 111.567ms였다. 12거래의 요청/원본/최종 저장 350/450/600/1000ms 지연 회귀도 통과했다. 이는 합성 PLC·사진 시험이며 실물 횟수에 더하지 않는다. 최초 새 C 시험은 시험 변수 초기화 순서의 NameError로 실패했으며, 원로그를 보존하고 해당 모듈 5개를 다시 실행해 통과했다. 운영 PLC 카운터·카메라 소유자는 시험 전후 동일했다.

**적용 상태:** 후보 `engine-integrated-a8afabe667e881ed`는 검증·임시 배치만 완료했다. 현재 운영본은 `f03d3f570a172c5f`이며 실제 적용/재부팅/새 30회는 아직 대기다. 사용자가 현재 STOP·모형 전부 제거를 확인했다. 원격 sudo 인증이 없어 기존 정지 백업 절차의 시작 명령을 요청했다. 기존 17건 전체와 취소 증거를 보존하며, 취소 건은 새 adapter의 실제 STOP 증거가 확인된 뒤 기존 append-only 복구 절차로만 정리한다. 새 결과·가짜 Done·재전송을 만들지 않는다. 상세 검증·배포 준비는 `runs/admission_frame_wait_20261017/FINAL_CANDIDATE.json`에 있다.

## 2026-10-17 수락 대기 수정 적용·실제 재부팅·attempt10 시작

위 임시 배치 상태 이후 사용자 STOP·빈 벨트와 sudo 실행을 받아 **a8afabe667e881ed를 실제 적용**했다. 정지 백업 174파일·SQLite의 SHA256 `f54556de1bc9ba19512c38226563ba47a7d5b1ba6b765cd936a0a34edb5a6d96`를 노트북에서 검증하고, 적용된 운영 파일 189개의 해시를 대조했다. 원래 17건의 검사행·원본·판정은 보존했다. 미전송 17번은 기존 append-only 취소 복구만 기록했으며 가짜 결과·Done·재전송·승인 grant를 만들지 않았다.

유지보수 도구의 실패도 남겼다. C trace 파생 파일의 CRLF/LF 해시 불일치는 원본을 보존하고 기존 예상 해시와 정확히 일치하는 별도 LF 사본으로 수정했다. 취소 기록기의 기본 outbox 10,000 제한은 이미 운영 코드가 사용하던 PC 수집 비필수 정책(`outbox_limit=None`)과 불일치하여 같은 정책으로 맞췄다. 저장 내구성·디스크·STOP 검사는 유지했다. 제품 종료 확인의 두 조회 사이 프레임 만료는 새 유효 프레임을 제한 시간 동안 읽기 전용으로 확인한 뒤 기존 종료 API를 한 번 호출했다. `TRACE_ARTIFACT_CORRECTION.json`, `MAINTENANCE_POLICY_CORRECTION.json`, 실패 로그와 성공 receipt를 함께 보존했다. 배포를 처음부터 반복하거나 실패 기록을 삭제하지 않았다.

**실제 재부팅 확인:** boot `081d4e63-96af-4ec0-b49c-174640b3960b`, systemd enabled/active, MainPID 1079, NRestarts 0. 단일 카메라 Worker 2725, 모델·PLC·준비 상태가 자동으로 복귀했고, 31.054초 동안 같은 Worker의 새 프레임 7개를 추가 확인했다. Jetson 수동 재시작이나 전원·USB 조작은 없었다. 노트북 SSH 터널은 별도로 다시 연결했다. 브라우저 도구가 URL 접근을 정책상 거절하여 실제 렌더링은 미검증이며, 서버 API의 WAIT_START 상태와 영상 갱신은 확인했다. 근거는 `runs/admission_frame_wait_20261017/DEPLOYMENT.json`, `AFTER_REBOOT_PROOF.json`, `POSTBOOT_SUMMARY.log`다.

**새 실물 attempt10:** Jetson 내부 GET-only 기록기 PID 4696, `data/engine_dynamic_pose_002/acceptance/continuous30_20261017_attempt10`. 준비 도구가 BASELINE 작성 중 읽은 초기 오류는 같은 프로세스가 파일 작성을 마친 뒤 확인했으며 중복 실행하지 않았다. 실제 START 후 운전·IDLE·요청/결과/Done/완료 0·카메라 준비를 확인했다. 사용자가 노트북 LAN만 분리했고 SSH timeout을 관측한 뒤 정상 모형 30회 연속 투입을 안내했다. 실물 결과는 아직 원장/C trace 회수 전으로 **30회 성공 미확인**이다. 기존 시험의 성공 수는 합산하지 않는다. 정상 기대 상태는 시험 기록에만 사용한다.

## 2026-10-17 단독 attempt10 — 오류 뒤 후속 검사 계속됨

한 START와 노트북 LAN 분리 상태에서 실제 **5요청/5 PLC 거래**를 확인했다. 순서는 **PASS → PASS → ERROR → PASS → PASS**다. 사용자는 오류 후 검사가 한 번 더 진행됐다고 관측했으며, 원장에는 별개 요청 두 건이 뒤따랐다. 오류를 지우거나 같은 요청을 재검사한 것은 아니다. 각 ID의 원본3장+표시1장 총20자산 SHA, SQLite quick_check, Result → 이후 Done → Request LOW → 거래 종료를 확인했다. 요청→C완료 최소9.498초/중앙10.795초/최대13.345초, 첫요청부터5완료까지84.194초. 정상유효검사4건/촬영오류1건이며 최대연속PASS2, **30회 목표 미달성**이다. 같은boot/Main1079/Worker2725이고 서비스 재시작은 없었다. 수락 취소·Ready 만료·통신 차단은 이번5건에서 없었다.

3번째 `e14586d0800243d98bb4a35c768041ff`의 원인은 `DEADLINE_EXCEEDED`다. 원래 촬영3초 동안 후보11개 중10개가 안정조건을 충족하지 못했고, 한 장만 안정으로 확보했다가 다음 프레임에서 연속성이 깨져 폐기됐다. 마지막 진단 원본3장은 실제 열어 확인했으며 모두 엔진과 네 부품이 보이고 각 프레임의 부품판정은PASS다. 그러나 진단사진을 유효한 연속안정3장으로 대체해서는 안 된다. C는 기존계약의 `AI_ERROR_AS_PLC_NG`로 해당거래를 종료했고 다음 요청2건은PASS로 처리했다. 사용자 STOP 후 RequestLOW/출력0/저장유휴를 확인했으며 복구·재시작·새START를 실행하지 않았다.

변화량을 **운영 Jetson OpenCV5.0.0**에서 원본으로 재계산했을 때 마지막두구간의 motion_fraction=0.0153298611/0.0197743056이 원기록과 정확히 일치했다. 기준0.008 초과 변화픽셀은883/1139개이며, 인접사진의 검출제품상자 합집합 밖이808/950개(91.5%/83.4%)였다. 이는 전체영상 차분 방식(`engine_inspector.py:motion`)이 주변 변화에 크게 영향을 받았다는 증거다. 엔진자체정지·조명·반사·진동의인과는 이 세 장만으로 확정하지 않는다. 이전8후보는메타데이터만있어 전체3초의화면을재구성할수없다. Windows 재계산은 첫구간에서1픽셀 차이로 엄격대조에실패했고, 원실행환경의Jetson에서정확대조했다. 원본·실패스크립트·결과를보존했다. 모델/검출기준/안정임계값/촬영기한은변경하지않았다.

**수집기 준비 결함:** Jetson 내부 GET-only수집기는 첫결과 검증 때 `replay_envelope_thresholds`가 `replay_basic_part_presence`를 지연import하며 모듈누락으로 종료했다. 시작프로세스·BASELINE 확인만으로 준비완료를 보고한 것은 불충분했다. 필수운영원장과원본은독립저장되어5건모두회수했다. 빠진진단의존성만전송하고 다음준비도구는첫결과검증에필요한import를시작전에검사하도록수정했다. 이번실패를새수집기실행으로덮지않았다. 이개발도구보완은운영서비스나카메라변경이아니다.

근거: `runs/admission_frame_wait_20261017/ATTEMPT10_AUDIT.json`, `FIELD30_NATIVE.json`, `FIELD30_AFTER_STOP.json`, `SAVED_MOTION_ANALYSIS.json`, `field_error_originals/`. 실물30회/장시간안정성은계속미달성이고, 임계값완화로PASS를만들지않는다.
