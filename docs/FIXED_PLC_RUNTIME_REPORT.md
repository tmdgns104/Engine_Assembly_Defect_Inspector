# 기존 PLC 고정 — 반복검사 Runtime 수정

상태: 실제 1제품의 촬영·조립 처리·통합 REVIEW·NG/Done·재가동 확인. 다음 자동 반복의 제품 구분 보완 및 감독형 재시험 진행 중.
PLC/EDS/4·8·10B/RPI/모델/판정 임계값은 변경하지 않았다.

## 수정 근거와 범위

- 정상 운전 준비와 무인 장애 복구 자격을 분리했다. `_profile_ready()`는 현재 calibration 일치, 명시적 좌/우 출구, 기존 passage 정책을 확인한다. 온라인 PLC 동등성·독립 timeout·현장 이탈·Class1 장기 안정성은 미검증 제한으로 따로 표시한다. 미검증 값을 TRUE로 만들지 않는다.
- 기존 PLC 주도 상태기계를 유지한다. 새로운 Request는 C의 boot/connection/request 토큰으로 구분한다. 제품별 웹·CLI 승인, 파일 생성 또는 automatic_arm 호출은 추가하지 않았다.
- `product_context_recovery.py`는 과거 마지막 제품 문맥에만 독립적인 `MAINTENANCE_PRODUCT_CONTEXT_CLOSED` 영수증을 추가한다. 정지 신호·유휴 소유자·DB 무결성·원본/최종판정 해시·현장 제품 처리 확인을 검증하고 commit 직전 PLC 문맥을 다시 비교한다. 정상 제품마다 쓰는 경로가 아니다. 원래 검사·ABORTED·승인 기록은 보존한다.
- 유지보수 호출은 기본 비활성인 단일 인증 POST이며 정상 `/line` 운전과 분리된다. 웹 승인 UI가 필요하지 않다. 다른 POST 보호는 유지한다.
- `consumed_frames.py`는 Runtime이 실제로 소비한 프레임 1,024개 이하의 ID/sequence/시간/epoch/generation/bbox를 기록한다. HTTP 표본의 누락을 Runtime 누락으로 해석하지 않는다. 이미지·tensor 복사나 별도 카메라 실행은 없다.
- OpENer의 JSON 파일 I/O를 단일 writer thread로 옮겼다. cyclic 소유자는 고정 크기 event queue와 status snapshot에 복사만 한다. event 순서, 상한, 저장 실패 차단은 유지한다. 중간 status snapshot만 병합할 수 있다. 출력·Run/Idle·Result→다음 패킷 Done·lease는 그대로다.

## 재현 및 검증

실제 application callback을 컴파일한 무 NIC fixture에서 파일 fclose에 250ms 지연을 넣었다. 기존 callback 두 번은 0.501630s, 수정 후 0.000058s였다. 비동기 파일 저장 실패는 `EVIDENCE_WRITE_FAILURE` 및 무출력으로 차단됐다. 이는 callback blocking 재현·수정의 근거이며 현장 Class1 timeout 전체 원인 확정은 아니다.

- ARM64 Runtime 회귀: 297개 PASS, 93.806s.
- ARM64 배포 회귀: 31개 PASS, 6.786s.
- C 초기/감독/자동 상태기계, ASan/UBSan, AF_UNIX IPC clock 및 Result/Done 순서 검사 PASS.
- 실제 Worker/저장/Assembly/IPC 소유자를 쓰는 격리 fixture의 네 판정·지연 저장·3제품 서로 다른 ID 검사 PASS. 카메라/PLC 입력은 fixture이며 현장 성공이 아니다.
- calibration 불일치, 실제 미완료 Journal, 낮은 디스크, 조작된 복구 영수증, commit 중 PLC 문맥 변경, 인증 없는 유지보수, STOP/lease/중복 출력 차단 유지.
- `INTEGRATED_AI_OFFLINE` 설치 확인: 174파일, 네 조립 classifier 및 기존 TensorRT/Pose 포함. `CORE_MOCK_ONLY`는 운영에 사용하지 않는다.
- 검증 중 운영 current/config/unit/PID/검사 목록/승인 원장 불변 확인.

새 ARM64 C SHA-256: `63ca4b16db530eecc9f95155a40cf758b291a590d85894dc8e9faf7aa0b2f4a4`.

## 현장 적용 원칙

사용자가 현장 정지·작업 영역·방호·STOP/E-STOP·감독과 서비스 전환 후 최대 3제품 시험을 승인했다. 카메라 화면의 실제 이동 방향은 오른쪽→왼쪽으로 확인했다. 실제 START는 현장 사용자가 누른다.

기존 current가 Git `45c36945928cdcbf04fa667d123a7b5342184adc`와 일치함을 확인했다. 서비스 정상 종료 후 current/설정/unit/SHA와 SQLite backup API의 Journal·승인 원장을 노트북에서 읽어 검증한 뒤 전환한다. 복원은 코드·설정만 대상으로 하며 검사/사진/ABORTED/소비 이력을 되돌리지 않는다.

독립 PLC 응답 timeout과 온라인 전체 로직 동등성은 미검증이다. 저장/통신 장애에서는 늦은 결과를 차단하며 현장 STOP·진단이 필요하다. 이것을 정상 제품마다 소프트웨어 권한을 발급하는 조건으로 사용하지 않는다. 실제 ProductPassage·3제품 자동 반복·Class1 장기 안정성은 현장 증거가 확보되기 전 PASS로 표시하지 않는다.

원본 증거는 노트북 `runs/.../tag_data_link_008/deployment_readiness_021/fixed_plc_followup/`에 보존한다. 운영 DB·사진·개인 설정·인증정보는 이 저장소에 포함하지 않는다.

## 첫 현장 실패와 조립 프로세스 분리

실제 원시 3프레임 저장은 383.552ms에 완료됐다. 조립 검사 중 Runtime health 갱신이 484.036ms 지연돼 기존 400ms lease가 만료됐다. C는 PYTHON_NOT_READY로 결과 발행을 취소했다. 이후 나타난 JOURNAL_UNFINISHED_INSPECTION은 취소의 결과이므로 미완료 차단을 제거하지 않았다. 이 요청에는 Class1 timeout이 없었다. 조립 결과는 뒤늦게 REVIEW로 저장됐으며 통합 최종판정과 Result/Done은 생성되지 않았다.

카메라를 하나만 소유하는 실제 Runtime과 보존된 3프레임 조립 검사를 함께 실행한 격리 재현에서 frozen feature matching의 knnMatch 동안 interpreter 전체 지연을 관측했다. `assembly_process.py`는 같은 동결 조립 코드를 별도 spawn 프로세스에서 실행한다. 부모는 완료 ID와 fsync 이후 DURABLE 응답을 확인한 뒤 결과를 읽는다. 자식은 카메라와 PLC를 열지 않으며 종료·실패·ID 불일치 시 readiness를 내린다. 모델, 임계값, 판정 정책, 400ms lease는 유지한다.

실제 카메라/저장 원본을 사용한 동일 조건 재처리의 health 최대 간격은 변경 전 306.927ms, 변경 후 134.582ms였다. 단일 재현 측정이며 전체 Class1 안정성이나 현장 성공의 증거는 아니다. ARM64 집중 회귀 84개가 통과했고 비공개 PNG fixture 1개는 해당 테스트 경로에서 제외됐다. 실제 저장 원본은 별도의 재처리에 사용했다. 별도 프로세스의 native GIL을 프레임마다 550ms 점유시킨 3제품 C/IPC 종단 테스트도 요청/결과/Done 각 3회, 승인 0회로 통과했다.

`aborted_recovery.py`는 PLC_AUTOMATIC_REPEAT의 실제 요청·취소 이벤트, 무출력, 다른 adapter boot, 현재 STOP·유휴 소유자를 검증하는 경로를 추가한다. 존재하지 않는 승인 기록을 만들지 않는다. 원래 inspection/사진/조립 결과와 승인 원장은 그대로 보존한다. 복구는 독립 ABORTED 영수증만 추가하며 결과 재전송이나 새 검사 권한을 생성하지 않는다.

서비스 종료 상태의 직전 current/설정/unit/원장/실패 증거 158파일을 노트북에서 해시·SQLite 무결성으로 검증했다. 백업 SHA-256: `b6f8bf95a9e58988679d3751dcb51949eed985fbb6a925d4f7cb40dea7f4f10d`. 복원 시 코드·설정만 복원하고 현재 Journal/사진/복구 이력은 되돌리지 않는다. 수정본의 실제 PLC 재시험은 진행 전이며 결과는 별도로 기록한다.

## 두 번째 현장 시도: 요청 접수 전 health 지연

조립 프로세스 분리본 `engine-integrated-82d677f3208eaa27`을 실제 적용했다. 기존 실패 검사에는 실제 무출력·취소·정지 근거에 따라 독립 ABORTED만 추가했다. 원래 결과/PNG/승인 이력은 보존했고 미완료 차단은 1건에서 0건이 됐다.

다음 실제 START에서는 제품이 처음 보인 뒤 health 간격이 669.586ms로 늘어났다. IPC는 410.085ms 시점에 HEALTH_LEASE_EXPIRED를 기록했다. 이후 PLC Request가 들어왔지만 C는 이미 DISARMED였다. 새 검사 ID/AI 검사/Result/Done은 모두 0건이며 현장 성공이 아니다. 사용자는 STOP과 실제 정지를 확인했고 서비스는 정상 종료했다.

VISION_PASSAGE_STARTED와 PRODUCTION_TRACK_STATE 기록 사이에 403.985ms가 있다. 정지 카메라 재현에서는 전체 670ms가 재현되지 않았다(최대 239.599ms). 복사 SQLite의 실제 commit 측정에서는 WAL 자동 checkpoint 시 166.566ms, 이후 readiness 재검사 100.195ms가 측정됐다. 따라서 동기 추적 로그와 반복 기록 검사가 주기 갱신을 방해할 수 있다는 근거는 있으나, 현장 670ms 전체를 하나의 확정 원인으로 단정하지 않는다.

최소 수정은 PLC_AUTOMATIC_REPEAT의 세 관측용 이벤트(VISION_PASSAGE_STARTED, PRODUCTION_TRACK_STATE, PRODUCTION_DEPARTURE_EDGE_ASSESSED)를 기존 크기 제한 메모리 trace로 옮긴 것이다. 각 frame의 검사 ID/요청 결합, 실제 요청/검사/최종판정/제품 이탈 확정/중단의 durable 기록은 유지한다. 특히 AUTOMATIC_PRODUCT_SEPARATED는 여전히 Journal에 저장한다. 과거 기록은 지우지 않으며 모델/판정/STOP/통신 lease와 C 바이너리는 바꾸지 않는다. 추적 진단이 SQLite를 변경하지 않으므로 정상 관측마다 과거 원장을 재검사하는 연쇄 비용도 사라진다.

개발 재현 스크립트와 회귀 테스트는 운영 current에 배포하지 않는다. 노트북 및 장치의 임시 verify 폴더에서만 실행하며, 모의 입력은 실제 PLC/AI 성공으로 세지 않는다. 500ms 저장 지연을 넣은 테스트는 수정 전 1.619s로 실패했고 수정 후 통과했다. 요청/최종판정/이탈 확정/중단 이벤트의 durable 저장과 메모리 상한도 검증한다. 실제 현장 재시험은 아직 필요하다.

이번 정상 종료 후 백업 159파일은 노트북에서 모두 해시 및 SQLite 무결성을 확인했다. SHA-256: `ceba32b37fe0e28266088c0f35db83aff7b36b836342b37513f830be155b2a48`. 복원 대상은 코드·설정·서비스이며 최신 검사/사진/ABORTED/소비 이력은 되돌리지 않는다.

최종 집중 ARM64 회귀: 64개 실행, 실패 0, 비공개 PNG fixture 1개 skip. C/IPC 합성 3제품은 request/result/done/completed 각각 3, 별도 승인 0을 확인했다. install --check-only --require-assembly 및 INTEGRATED_AI_OFFLINE 패키지 생성도 통과했다. 패키지 175파일, SHA `1a962d3582de4a030d99b13f4a293fa7ab2e37f09690e8f51c18bcdb207c95d3`. 실제 카메라 단일 소유자·PLC 미연결 정지 진단에서 추적 처리 최대 2.639ms, 상태 갱신 최대 206.802ms였다. 이는 실제 PLC 재시험 성공 근거가 아니다. 배포 변경은 standalone.py 한 파일과 release 메타데이터이며 C/현장 설정은 그대로 유지한다.

## 세 번째 현장 시도: 통신 완료, 실제 AI 시작 미완료

`engine-integrated-b90026f57a3d8b3c` / Git `dc73af8e4a75c253cf5e0bfb9c2302bb4df5ca52`에서 새 요청 `756c08e340299d0f:1:1`을 수신했다. Runtime health 최대 간격은 248.288ms로 유지됐고 Class1 연결 ID는 1로 유지됐다. 그러나 START 이전 미리보기에서 모형을 옮긴 뒤 MISSED_OBSERVATION_LIMIT / WAIT_AREA_CLEAR가 남았다. 이 상태는 실제 START보다 약 88초 전부터 있었고, 아직 요청 토큰이 없었다.

30초 뒤 검사 `1ef61078d8ce4edeb12fde1e1ffe99e3`는 NO_VALID_CURRENT_PRODUCT_AT_PLC_REQUEST / ERROR로 저장됐다. 원본 촬영·기존 AI·필수 조립 검사는 실행되지 않았고 `source=NO_ACTUAL_INSPECTION`, `existing_decision=NOT_RUN`, `assembly_decision=NOT_RUN`으로 구분된다. 사용자가 정한 ERROR→NG 정책에 따라 Result 1회(sequence 6441), 다음 패킷 Done 1회(6442), PLC Request 해제와 출력 초기화를 확인했다. 작업자는 약 30초 뒤 실제 재가동과 이후 STOP을 확인했다. 통신 반환 성공을 실제 AI 검사 성공으로 세지 않는다.

추적 수정은 유효한 PLC 기준 상태에서, 아직 요청/검사에 연결되지 않은 미리보기의 관측 손실만 폐기하고 이후 새 프레임으로 다시 추적한다. PLC 요청 접수 후의 Track, 저장/조립 진행 상태, 과거 제품 이탈 미확인 상태와 ProductPassage는 그대로 유지한다. 이를 CLEAR나 제품 이탈 증거로 기록하지 않는다. 현장과 같은 정지 미리보기→관측 손실→새 요청 재현은 수정 전 실패, 수정 후 정상 제출됨을 확인했다. 노트북 관련 41개 회귀 PASS.

직전 운영본과 이번 완료 ERROR/원장을 포함한 151파일 백업은 노트북에서 모든 해시·SQLite 무결성을 검증했다. SHA `8f28ce0ffc8fa096adc4c6e6b5b8a2bffe1713ca0a8fd9dadc25d35be593322b`. 복원은 코드·설정·서비스만 대상으로 하고 새 검사/승인/ABORTED 기록을 되돌리지 않는다. 추가 현장 START는 아직 진행하지 않았다.

ARM64 집중 회귀 69개: 실패 0, 비공개 PNG fixture 1개 skip. 합성 C/IPC 3제품은 requests/results/done/completed 각각 3, 승인 0; 결과 sequence 367 다음 Done 368. 전체 INTEGRATED_AI_OFFLINE 175파일 패키지 SHA `c6994e4209ed2034c275b914b0d522f4d439ccdc42fc6668cbb6e5abd2c3751e`. 현재 변경은 Runtime 한 파일이며 C/PLC/모델/현장 설정과 기존 400ms lease는 불변이다.

## 실제 촬영·조립 처리와 PLC 반환 확인

Git `8d951f09f5483bc5941aa423bca0c362b914db82`, 운영 Release `engine-integrated-d44c2e926a6553c7`의 추가 1회 시험에서 실제 1280×720 PNG 세 장과 원시 REVIEW를 저장했다. 원시 이유는 ENGINE_OR_HAND_MOTION이다. 필수 조립 프로세스도 실행됐지만 세 프레임의 전처리는 SEED_INSUFFICIENT_SPATIAL_BODY_SUPPORT로 실패했고, 부품 classifier는 판정하지 않았다. 통합 최종판정은 원시 REVIEW와 조립 REVIEW를 보존한 EXISTING_REVIEW_ASSEMBLY_REVIEW다. 조립 모델이 부품을 정상 분류했다고 보고하지 않는다.

저장 397.358ms, 조립 처리 8025.672ms, 요청→발행 10117.764ms였다. health 최대 간격은 292.833ms였으며 기존 400ms lease를 유지했다. C에서 Result sequence 3738 → 다음 cyclic Done sequence 3739 → Request OFF → Done reset을 확인했다. 실제 작업자는 벨트 재가동과 이후 STOP을 확인했다. 전용 PLC 소비 ACK 태그는 없으므로 소프트웨어 증거 범위는 CYCLIC_SEND_AND_REQUEST_RESET_ONLY이며 작업자 재가동 관찰과 구분한다. 시험 중 Class1 timeout 및 IPC 단절은 관측되지 않았으나 장기 안정성을 증명한 것은 아니다.

비공개 원장·PNG·조립 결과·C 이벤트·실제 Runtime 소비 프레임을 포함한 20파일을 SQLite backup API로 수집하고 노트북에서 모두 검증했다. 증거 압축 SHA: `451e1c1d45b6e6cf0c072e07a5073429e417e844e6ea895b083841f4b9f2a8fe`. 원본과 DB는 Git에 포함하지 않는다.

## 다음 제품 구분의 실제 관측 정합성

기존 ProductPassage는 정지한 제품 bbox의 약 0.2픽셀 역방향 흔들림도 영구적인 TRAJECTORY_DISCONTINUITY로 처리했다. 실제 Runtime 소비 기록의 sequence 2002→2003으로 재현했다. 2006→2008의 실제 소비 간격도 관측했다. HTTP 표본 간격만으로 누락을 추정한 것이 아니다. 왼쪽으로 이동하는 제품의 검출은 원래 폭의 약 36%에서 끝났으므로 기존 20% 꼬리 관측 조건은 성립하지 않았다. 미검출이나 사용자의 이탈 설명을 자동 CLEAR로 기록하지 않는다.

`product_passage.py`는 기존 Tracker의 공간 hysteresis·중심 이동 한계를 재사용한다. 작은 흔들림과 짧은 소비 간격을 허용하되 누락 구간은 연속 관측 시간을 초기화한다. 기존의 꼬리·출구 영역 관측 경로는 보존한다. 꼬리 관측이 부족하면 이전 제품의 실제 출구 경계 통과와 충분한 외향 이동, 반대쪽 경계에서 시작한 새 제품의 분리된 연속 진입, 최소 1.2초의 누락 없는 출구 영역 관측을 함께 요구한다. 이 경우 증거는 OUTBOUND_PRODUCT_AND_NEW_UPSTREAM_ENTRY이며 `product_exit_claimed=false`다. 완전한 물리 이탈이나 AI Area CLEAR를 주장하지 않는다. Request OFF, 순간 미검출, 중앙에 갑자기 나타난 물체만으로는 재무장하지 않는다.

실제 소비 96프레임을 재생하면 잘못된 영구 차단은 사라지지만 새 제품 진입 증거가 없어서 proof는 여전히 null이다. 실제 연속검사 PASS가 아니다. ARM64 관련 67개 회귀 및 마지막 진입 추적 보완 후 16개 집중 회귀가 통과했다. 합성 C/IPC 네 판정은 승인 0회, request/result/done/completed 각각 4회와 Result 다음 패킷 Done을 확인했다. `test_product_passage_field.py`의 후속 제품은 합성임을 명시한다. 실제 다음 제품과의 구분은 감독형 현장 반복 시험으로 검증한다.

이번 적용은 Python 두 파일과 Release 메타데이터만 대상으로 한다. C 실행 파일, 현장 설정, PLC, 모델, 무인운전 검증값은 변경하지 않는다. 서비스 정상 종료 후 current/설정/unit/일관된 원장을 노트북에서 검증하고 적용한다. 과거 제품 문맥은 실제 STOP·모형의 벨트 밖 보관·유휴 작업을 확인한 기존 유지보수 경로로 한 번 종료한다. 정상 제품마다 복구나 권한 발급을 요구하지 않는다.

## 연속 시험 첫 제품과 추가 폭 정합성 보완

`engine-integrated-79dbf3c5989a9c55` / Git `bdc289751370903200b28c8ca50a595524775b9c` 적용 후 새 실제 검사도 원시 REVIEW→조립 처리 REVIEW→통합 REVIEW→NG·Done→Request 해제까지 진행했고 작업자는 재가동 및 STOP을 확인했다. 요청→발행10139.898ms, health 최대264.392ms였다. 두 번째 제품은 투입하지 않았다. 제품 이동 중 bbox 폭을 초기 값+고정 여백과 비교하는 제한이 sequence2719에서 정상적인 연속 이동을 차단했다(실제 폭0.59226, 초기 기준 상한0.58828). 첫 수정만으로 연속 운전을 해결했다고 보고하지 않는다.

인접 프레임의 폭 변화와 기존 이동/겹침 한계를 비교하도록 한 줄을 보완했다. 갑작스러운 폭 증가, 역방향 이동, 미검출만으로 다음 제품을 인정하지 않는 테스트를 유지한다. 해당 실제16프레임 회귀는 수정 전 실패했고 수정 후 통과했다. 두 번째 실제 기록116프레임도 재생했으며 새로운 진입이 없으므로 proof=null을 유지한다. 노트북 관련91개와 ARM64 집중19개 회귀 PASS. C/IPC 합성 네 결과는 승인0회, Result sequence19 다음 Done20이었다. 현장 자동 반복 성공은 아직 미검증이다.

직전 184파일 운영본의 정상 종료 백업159파일은 노트북에서 해시·SQLite 무결성을 검증했다. SHA `e0cd3ddbc86f1c6b4d5f997f9f219e52dff83b851af9534af73731ed3628c47b`. 배포와 과거 문맥 정리는 검사 권한을 발급하지 않았고 과거 원시/최종 기록을 보존했다.

재시험 전 같은 현장 기록의 실제 상류 진입7프레임을 합성 후속 순서로 재생했다. 첫 bbox의 오른쪽 끝은0.99710이므로 정확히1픽셀 이내의 경계만 허용하던 조건도 불필요하게 차단했다. 기존 Tracker 공간 hysteresis를 상류 경계 관측에 동일하게 적용했다. 수정 전 회귀 실패와 수정 후 정상 관측을 확인했으며, 이는 새로운 물리 반복검사의 증거가 아니다. 중앙 출현·역행·급격한 크기 변화·epoch 변경·관측 누락만으로의 이탈 인정 금지는 유지한다.

## 같은 서비스에서 두 실제 요청 자동 처리와 완료 시점 관측 인계

Git `84723d18ce80a9c84d97c27b80f13d3962450c6a`, 운영 Release `engine-integrated-79ef7df28bf3c61d`에서 같은 C boot/connection으로 두 요청을 처리했다. 제품 회수·재배치를 위한 현장 STOP/START는 있었지만 서비스 재시작, 권한 발급, 제품 문맥 초기화는 사이에 없었다.

| 항목 | 첫 요청 | 두 번째 요청 |
|---|---|---|
| 검사 ID | `2e401aa60d6c4146a5ddac8eeb0731ea` | `8d388776297142c6acf69e49f39c0e34` |
| 요청 토큰 | `53e783693f07cae3:1:1` | `53e783693f07cae3:1:2` |
| 원시/조립 처리/통합 판정 | REVIEW / REVIEW / REVIEW | REVIEW / REVIEW / REVIEW |
| 실제 촬영 원본 | 새 PNG 3장 | 새 PNG 3장 |
| Result 패킷 → Done 패킷 | 3590 → 3591 | 5380 → 5381 |
| 요청 → 결과 제출 | 10,374.756ms | 9,225.630ms |
| Request 해제·출력 초기화 | 관측 | 관측 |
| 작업자 실제 재가동 확인 | 확인 | 확인 |

두 번째 요청은 첫 제품의 관측된 외향 경로와 별도의 상류 진입 4프레임(2780~2783)으로 자동 구분했다. 당시 연속 관측 구간은 11.752초였고, 전체 화면 비움·Area CLEAR·원시 포토센서·소프트웨어 승인은 사용하지 않았다. `product_exit_claimed=false`로 기록하여 완전한 물리 이탈과 새 검사 사이클 구분을 구별한다. PLC에는 별도 소비 ACK가 없어 `plc_consumption_confirmed=false`를 보존하며, Request 해제와 작업자 재가동 확인을 별도 근거로 둔다.

두 건 모두 필수 조립 전처리가 `SEED_INSUFFICIENT_SPATIAL_BODY_SUPPORT`로 끝나 부품 classifier는 실행되지 않았다. 실제 조립 처리 경로 실행 및 REVIEW 저장을 부품 정상 판정 성공으로 보고하지 않는다. 해당 세션은 connection 1, Class1 timeout 0, health 최대 300.582ms였다. 장기 연결 안정성은 미검증이다.

두 번째 결과 반환 후에는 `PRODUCT_PASSAGE_FRAME_CONTINUITY_INVALID`가 발생했다. 원인은 실제 프레임 누락이 아니라 완료 순간의 최신 프레임2878이 NO_FOREGROUND인 상태에서 ProductPassage를 생성하여 origin이 없어진 것이다. 마지막 실제 bbox는2871, 같은 위치 재관측은2881이며 프레임/epoch/generation은 연속이었다. 세 번째 요청은 수행하지 않았다. 사용자 STOP 확인 후 두 검사·원장·원본·C 이벤트29파일을 노트북에서 검증했다. 백업 SHA `6808ce256dc6f2ca29438892a0bc2305c6704fb1f403da0b0e2b721f01977095`.

최소 보완은 동일 request/Tracking session/Track의 검증된 최근 관측을 기존 Track 누락 한도+2개로 제한해 유지하고, 완료 후 마지막 실제 bbox에서 관측을 이어가는 것이다. 짧은 미검출은 기존 12프레임/3초 Track 한도 안에서만 기다리며, 재관측은 기존 이동·겹침·역행 조건을 만족해야 한다. 누락은 이탈이나 CLEAR가 아니며 출구 관측/새 상류 진입 근거는 그대로 필요하다. 다른 요청/epoch/Worker/모델, 모호한 제품, 유효한 기준 bbox 부재, 실제 프레임 시간 불연속은 차단한다. PLC·C·모델·lease·판정 정책은 변경하지 않는다.

실제 소비467프레임 재생은 수정 전 첫 후속 프레임2879에서 차단되던 문제를 해소했고, 후속 제품이 없으므로 proof=null을 유지했다. 노트북 관련80개 회귀와 실제 Runtime→Journal 결과 완료 시 미검출 인계·다음 요청 시험이 통과했다. ARM64 검증 및 실제 보완본 적용은 진행 중이며, 이 재생을 세 제품 현장 연속 성공으로 표시하지 않는다.

적용 전 검토에서 기록을 Tracker 연결 판정 전에 보관하던 문제와 검사 시작 프레임이 빠지는 문제를 추가 재현했다. 기록 시점을 기존 Tracker 처리 후로 옮기고, 실제 검사에 바인딩된 프레임을 첫 기록으로 보존했다. 다른 bbox로 연결이 불확실해진 LOST/WAIT_AREA_CLEAR 상태는 다음 제품 이탈 증거로 인계하지 않는다. 해당 검사의 REVIEW/ERROR→NG·Done 반환은 유지한다. 두 회귀는 수정 전 실패, 수정 후 통과했다. 최종 노트북 집중 회귀70개 통과(4.231초). 초기 Windows 샌드박스의 임시 SQLite/로컬 HTTP 제한은 테스트 실패와 구분하고, 허용된 노트북 환경에서 다시 검증했다.

실제 두 번째 검사에서 시작~완료94개 소비 프레임(2785~2878)은 누락 없이 연속이었다. 완료 시 Tracker는 INSPECTED, missed_frames=7, reason_code=null이었다. 동일 기록의 Tracker 재생도 이상 없이 끝났고 최대 미검출11프레임/0.976초로 기존 한도 안이었다. 따라서 해당 실물 실패는 연결이 불확실한 다른 물체 사례가 아니라 완료 시점 기록 인계 결함이다. 실제94프레임 Tracker 재생과467프레임 ProductPassage 재생은 새 현장 시험을 대신하지 않는다.

사용자는 현재 정지·방호·감독 상태와 모형1개를 배출 후 안전하게 회수·재투입할 수 있음을 확인했다. 새 시험 범위는 START 한 번, 수동 STOP/서비스 초기화 없이 세 검사 사이클이다. 기존 PLC의 검사 위치 자동 정지/재가동은 유지한다. 관리자 인증과 최신 정지 백업 검증 후 적용하며, 아직 이 범위의 START는 수행하지 않았다.

정상 종료 후 최신 운영본·설정·서비스·SQLite 백업159파일을 노트북에서 전부 읽고 SHA/DB 무결성을 검증했다. 백업 SHA `1d3daba0723512ab3dbf511f910946206a56f4c8a50671137f007c7f219c182b`. 서비스가 정지된 Jetson에서 집중 ARM64 회귀71개 통과(13.930초). C/IPC fixture는 합성 요청4/결과4/Done4/완료4/권한0, Result19→Done20을 확인했다. 실제 PLC 소켓은 이 회귀에서 열지 않았다. 사용자 모형 벨트 밖 보관 확인. 이번 변경은 Python 두 파일이며 C·설정·모델·DB는 유지한다.
