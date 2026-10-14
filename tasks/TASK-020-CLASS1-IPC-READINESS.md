# TASK-020 — PLC 주도 자동 반복과 Class1/IPC 진단

상태: ISOLATED_VERIFIED / STOP_FOR_FIELD_DEPLOYMENT_APPROVAL. 사용자 최신 수정 지시를 적용한다. 기준 45c36945928cdcbf04fa667d123a7b5342184adc.
운영 engine-integrated-4920568fe3750b64는 변경하지 않는다.

정상 PLC_AUTOMATIC_REPEAT 경로에서 제품별 권한 파일·challenge·admission ID·arm 명령을 제거한다.
C는 현재 연결의 실제 정지 기준 상태, RUN 중 Request LOW→HIGH, 결과/Done/reset 순서를 관리한다.
Python은 현재 검사/제품 식별·Journal·저장소·Worker 건강 상태를 관리한다.
이전 제품 이탈 미입증은 자동 CLEAR로 만들거나 이전 AI를 재사용하지 않는다.
사용자 재확인: 유효한 요청의 제한시간 ERROR도 원인·미검사 사실을 저장하고 NG·Done으로 보낸다.
STOP/통신 손실/저장 실패에는 늦은 결과를 보내지 않는다.

유지: PLC 4/8/10B, Result→다음 패킷 Done, PASS→OK 및 실제 FAIL/REVIEW/ERROR→NG,
저장 완료·요청 식별·STOP/통신 장애 차단. 과거 승인/ABORTED/Journal 불변.
이전 시운전 정책은 유지보수 호환 경로이며 정상 자동 경로에서 인스턴스화하지 않는다.
Class1 및 IPC 원인은 분리하며 timeout/RPI/lease를 변경하지 않는다.

검증: 승인 없는 초기 요청·3제품 실제 소프트웨어 경로, 제품 이탈/불확실성,
중복·재접속 잔류·STOP/EStop·저장 실패·지연 저장 health, 기존 ARM64/C 회귀.
실제 카메라/모델/PLC 경계의 합성과 현장 검증을 구분한다.
검증 후 공식 jetson/ 변경만 commit/push. 운영 교체·PLC 쓰기·START는 새 승인 전 금지.

증거: runs/engine_standalone_plc_autostart_001/v001_20261007T052746Z/tag_data_link_008/class1_ipc_020/

결과: ARM64 Python287 PASS(92.418s), C sanitizer/state/IPC/build PASS. 정상 automatic_arm/ID/원장 경로 제거, REVIEW/ERROR→NG·Done 유지. Class1 현장 최초 원인 미확정. 보고서: docs/CLASS1_IPC_AND_REPEAT_READINESS_REPORT.md. 운영 적용/실제3제품 NOT_RUN.
