# TASK-021 후속 — 기존 PLC 고정 조건의 반복검사 준비

상태: IN_PROGRESS. 기준 Git 41e1c9a0343a69173fe5e0cd6b1a65a2888c1385.

사용자 최신 지시가 이전 TASK-021의 PLC timeout 필수 계획을 대체한다.
PLC 래더·태그·타이머·I/O·EDS·Assembly·RPI는 변경하지 않으며 센서를 추가하지 않는다.
정상 검사 준비와 무인 장애 복구 검증을 분리한다. 정상 경로에는 권한 파일/승인 ID를 추가하지 않는다.

구현 범위:
1. 실제 운영 소스·정지 신호·Journal·Class1/IPC를 읽기 전용 조사한다. 통신 원인 측정과 ARM64 부하 검증은 시간적으로 분리한다.
2. 정상 readiness에서 독립 PLC timeout을 요구하지 않되 실제 STOP/통신/저장 보호는 보존한다. 미검증 무인 복구는 별도로 표시한다.
3. 과거 제품 문맥만 종료하는 append-only 유지보수 복구를 구현한다. 원본/ABORTED/승인 기록을 변경하거나 AI 이탈 증거를 합성하지 않는다.
4. 실제 Runtime 소비 프레임을 제한된 ring buffer에 기록한다. HTTP sampling gap을 Runtime loss로 단정하지 않는다.
5. 콜백 파일 I/O 지연을 격리 재현하고 입증된 경로만 수정한다. lease/timeout/RPI는 유지한다.
6. 회귀·ARM64·패키지 검증 후 공식 소스 Commit/Push와 INTEGRATED_AI_OFFLINE 배포 계획을 준비한다.

현장 정지·작업 영역·방호·STOP/E-STOP·감독과 적용 후 최대 3제품 시험을 사용자에게 확인받았다. 승인된 범위에서 서비스 전환·복구·시운전을 진행하며 실제 START는 사용자가 누른다. 정상 제품마다 별도 승인을 만들지 않는다.
최종 현장 증거는 최대 세 제품의 고유 ID·실제 AI/조립·Journal·Result→다음 패킷 Done·PLC 소비·다음 자동 요청이다.
격리 성공을 현장 성공으로 기록하지 않는다. 제품별 소프트웨어 승인은 재도입하지 않는다.

증거 위치: 기존 tag_data_link_008/deployment_readiness_021/fixed_plc_followup/.

기존 검증: ARM64 297개 Runtime + 31개 배포 회귀 PASS; C/IPC 및 지연 파일 callback 검사 PASS.

현장 1회차는 실제 3프레임·원시 REVIEW 저장까지 완료했지만 조립 검사 중 health 간격 484ms로 400ms lease를 넘겨 결과 발행이 취소됐다. 이후 조립 REVIEW는 저장됐으나 통합 최종판정/Result/Done은 없다. 사용자가 STOP을 확인했고 서비스 정상 종료 및 노트북 일관 백업을 완료했다.

최소 보완: 필수 조립 검사만 독립 Python 프로세스로 실행한다. 카메라/PLC 소유자는 늘리지 않고 모델·정책·lease는 그대로다. PLC 주도 요청의 중단 복구는 존재하지 않는 과거 승인 ID 대신 실제 요청·취소 이벤트·새 adapter boot를 검증한다.
ARM64 집중 84개 회귀 PASS(비공개 PNG fixture 1개 skip), 별도 프로세스 3제품 C/IPC 종단 검사 PASS(각 frame에 550ms native GIL 점유, 승인 0회). 실제 카메라와 저장 영상 재처리에서 health 최대 간격 135ms. 실제 PLC 재시험은 아직 수행하지 않았다. 상세: docs/FIXED_PLC_RUNTIME_REPORT.md.

후속 실제 2회차: 요청 접수 전 health 669.586ms 지연으로 DISARMED. 새 검사/Result/Done 없음. 사용자 STOP 확인 후 서비스 정상 종료, 최신 코드/설정/Journal/승인 원장 159파일 노트북 백업 검증. 운영 시험용 재현/회귀 코드는 current에 추가하지 않는다. 세 관측용 추적 이벤트만 동기 SQLite 기록에서 기존 bounded memory trace로 옮기는 최소 수정 중이다. 실제 요청/최종판정/이탈 확정/중단 기록과 보호 조건은 유지한다. 670ms 전체 원인은 아직 단일 원인으로 확정하지 않는다. 수정 검증 후 남은 승인 범위의 실제 재시험을 진행한다.

추적 진단 I/O 분리 수정의 ARM64 64개 집중 검사 및 전체 통합 패키지 검증 완료(실패 0, fixture 1 skip). 실제 정지 카메라 진단 health 최대 207ms. 검증된 한 파일 수정 적용 후 남은 실제 시험을 수행한다. 회귀/재현 코드는 current에 배포하지 않는다.

실제 3회차: health 최대 248.288ms, ERROR→Result(6441)→Done(6442)→PLC Request 해제 및 작업자 재가동/STOP 확인. 실제 AI는 미실행: START 전 미리보기의 WAIT_AREA_CLEAR 잔류가 원인. 미접수 미리보기만 재획득하는 최소 수정과 노트북 41개 회귀 완료. 접수 후 동일성/이탈 보호 유지. 추가 START 미실행.

추가 1회 실제 시험: d44c2e926a6553c7에서 새 카메라 3프레임·원시 REVIEW·조립 처리 REVIEW·통합 REVIEW 저장, NG Result3738→Done3739→Request 해제 및 현장 재가동/STOP 확인. 조립 전처리 실패로 부품 classifier는 미실행이었다. 저장397ms 동안 health 최대293ms 유지. 실제 촬영 및 PLC 반환 완료와 AI 판정 품질은 구분한다.

사용자가 연속 시험을 요청했다. 다음 제품은 bbox 미세 흔들림을 불연속으로 처리하는 ProductPassage 때문에 차단됐다. 실제 소비96프레임 재생과 ARM6467개/최종16개 회귀로 최소 보완을 검증했다. 이전 외향 궤적과 분리된 새 상류 진입을 함께 확인하며 미검출만으로 이탈을 만들지 않는다. 현재 운영본은 아직 d44c2e926a6553c7; Python 두 파일 적용·기존 문맥 한 번 정리·감독형 최대3제품 시험이 남았다. 사용자는 벨트 정지 및 모형을 벨트 밖에 보관했음을 확인했다. PLC/모델/lease/무인 검증 플래그는 유지한다.

79dbf3c5989a9c55 적용 후 연속 시험의 첫 제품은 실제 촬영/조립 처리/통합 REVIEW/NG·Done/재가동 완료. 다만 bbox 폭의 초기 기준 상한 때문에 이동 도중 다음 제품 문맥이 차단됐다. 사용자 STOP 확인, 추가 제품 미투입. 인접 bbox 폭 변화 기준으로 최소 보완했으며 실제 실패116프레임 재생과 노트북91/ARM64집중19 회귀 통과. 기존 시험 증거·원장을 보존한 뒤 한 파일 보완 적용 및 남은 시험을 이어간다. 연속 자동 처리 완료가 아니다.
