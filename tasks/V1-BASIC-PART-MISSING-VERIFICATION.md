# V1 — 기본 부품 누락 검사 실제 자료 검증

2026-10-15. 사용자 요청으로 정렬 실험을 종료·보존하고 기본 결품 검증만 수행.

## 최신 완료 상태

- 추가 승인된 최소 중단 복구 적용: source a005df5, 운영 a542b0df44800e81. 원본 보존·독립 ABORTED로 정확한 미송신 이전 검사만 정리, 차단 1→0. 관련 PC/ARM64 76개 회귀 통과.
- 사용자 배기만 분리·한 번 START: 새 검사 5a0708cf246041d2a80a24c402c47f37의 실제 3프레임 기본 FAIL/EXHAUST_TOP_MISSING. 조립 REVIEW·종전 통합 REVIEW. NG Result5285→Done5286·Request 해제와 실제 벨트 재가동/STOP 확인.
- 사용자 확정 정책 수정: 한 검사라도 FAIL이면 최종 FAIL, 둘 다 PASS여야 PASS. source 887ea3f2 / 운영 engine-integrated-2719dff19eb79478 적용, 185파일 해시·STOP·새 출력0 확인. PC/ARM64 각28회귀와 실제 저장 결과 재결합 FAIL. 과거 저장 REVIEW는 보존.
- 노트북 백업170파일·SQLite 검증. 새로운 현장 시험은 하지 않았다. 실제 시험 완료 후 별도 카메라 관측 중단이 있었으므로 연속운전 안정성은 미검증이다.
- 최신 보고: docs/BASIC_PART_MISSING_VERIFICATION_REPORT.md, docs/CONFIRMED_FAIL_COMBINATION_FIX.md. 아래는 이전 단계의 시간순 기록이다.

## 완료한 검증

- 현재 Jetson source/model/config로 보관 원본 정상3장/배기결품3장/정상복원3장 재생.
- EngineInspector/EnginePoseEstimator/inspect_frame/aggregate_three 실제 운영 경로 사용.
- 정상 PASS, 결품 EXHAUST_TOP_MISSING/FAIL, 정상복원 PASS. 9장 pose/품질/할당 신뢰도 유효.
- 9PNG·픽셀 SHA/metadata、운영185파일 SHA、수집 결과10파일 SHA、aggregate 재계산 확인.
- 검출그림 및 보고서: `docs/BASIC_PART_MISSING_VERIFICATION_REPORT.md`; private `runs/basic_parts_missing_verification_001/`.
- 운영 Python/C/config/모델/PLC/서비스/Journal 변경 없음. 오조립 제외 정책 미적용.

## 추가 현장 요청과 현재 차단

사용자가 배기 결품 실제1회 시험을 요청하고 현재 정지·방호·감독 조건을 확인했다. 이 승인만으로 START를 안내하지 않았으며 현재 새 시험 미실행.

이전 검사60aa99de9b8a409fac7682572a06b5f6은 저장 중 취소돼 rawPASS/COMPLETE, Assembly/통합 final 없음. 미완료1. 같은C요청의 접수/취소 이벤트 누적Result/Done2->2로 미송신 확인. 단순Reset으로 지울 수 없고 기존 abort 검증은 첫 요청 누적0/새boot 가정이라 현재 상태와 불일치. 근거가 없는 count 변조/final 생성/DB 초기화 금지.

사용자가 비치명적 판정으로 반복검사를 계속하고 제품별 소프트웨어 권한을 두지 말라는 요구 재확인. 정상 완료 FAIL/REVIEW/ERROR는 기존 NG·Done; 이미 취소된 요청에는 늦은 결과 금지. 중단 복구 최소 보완·적용 허용 여부를 질문한 상태이며 서비스 변경 금지 범위를 임의 확대하지 않는다.

## 다음 행동 경계

- 복구 범위 승인 시 이 차단을 해결하는 최소 기존 경로 보완/집중회귀/백업/적용 후 승인된 배기결품1회로 이어간다. 새 알고리즘/모델/PLC 변경/제품별 권한 추가 금지.
- 승인 전 운영 변경·START·Result/Done 금지. 원본 비교 결과는 이미 완료했으므로 재추론 반복하지 않는다.
- V1 전체완료/다른3부품 결품/현재위치 일반화/무인운전은 미검증. 다음 TASK 자동시작 금지.
