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
