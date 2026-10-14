# TASK-019 — 저장 중 health 유지와 중단 복구

상태: ISOLATED_VERIFIED / STOP_FOR_DEPLOY_APPROVAL. 기준 db3628dc8bd1d666da9c67239d0deca689efbc5a.

실제 운영 engine-integrated-d247e1e9579ab6e7, 실패 검사
98c04ad398a7422daba705e206b9bae6. 사용자가 STOP 유지 확인했고 읽기 전용
재확인에서 Request/Result/Done/Mc_Run LOW, Worker/Assembly idle, 승인 REVOKED.
원시 COMPLETE/REVIEW와 원본은 보존한다.

## 구현 계약

- 서비스 잠금 아래서 결과의 ID/generation/trigger를 검증하고 단일 저장 작업자에게
  소유권을 넘긴다. 파일 저장은 서비스/Journal 잠금 밖, DB commit은 Journal 잠금 안.
  완료 통지는 같은 active 객체와 generation에만 적용한다. BUSY 동안 다음 요청은 금지한다.
- Runtime은 DB commit 대기 중 동기 DB 조회를 하지 않고 현재 Worker/카메라와
  동일 토큰의 저장 진행을 확인하여 기존 health lease를 갱신한다. STOP/통신/실제 오류는
  C에서 계속 차단한다. timeout/lease/판정/모델/PLC 계약은 바꾸지 않는다.
- 저장 단계·락 대기·health 원인/나이와 C 분기를 제한된 진단 기록으로 남긴다.
- 취소된 Bridge는 ABORTED로 표시한다. 원시 판정과 통합/발행 상태를 별개로 보여준다.
- 감독하 복구는 별도 durable ABORTED 증거를 추가한다. 원본 검사/승인 소비 상태를
  변경하거나 최종판정을 만들어 넣지 않는다. 불충분한 증거는 차단한다.

## 검증 및 종료

실제 3 PNG 크기/원본을 이용한 300–500ms 이상 저장 지연, Worker/카메라/DB/IPC 장애,
취소/중복/세션 경계, 실제 Worker→Journal→Assembly→final→C Result/다음 패킷 Done을
격리 검증한다. 기존 회귀 및 ARM64 네이티브 검증 후 선택한 소스/테스트/문서만 push.
운영 파일 교체·서비스 재시작·ABORTED 운영 적용·새 승인·실제 PLC 발행은 별도 승인 전 금지.

최종 ARM64 Python 283 PASS(78.510초), C 초기승인22/감독형/자동 sanitizer 시험 및
OpENer 빌드 PASS. 네 판정 모두 원시 저장 1047–1057ms/최종 commit567–570ms와 UI
조회 중 Result→다음패킷 Done 1회 확인. 최대 health 간격196.9ms; lease 변경 없음.
실제 실패 DB 복사본116행/승인 불변, ABORTED 독립 추가만으로 blocker1→0;
원본 미완료는 운영에서 그대로 차단. 현재 서비스/파일/DB 전후 불변.
보고서: docs/PYTHON_NOT_READY_FIX_REPORT.md. exact current 백업과 차분/복원 manifest는
기존 run/health_storage_019에 보관. 실제 배포/현장 재시험/운영 복구 NOT_RUN.
