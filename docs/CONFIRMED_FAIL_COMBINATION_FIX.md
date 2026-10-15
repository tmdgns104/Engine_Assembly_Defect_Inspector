# 확정 불량 우선 통합 판정 수정

2026-10-15 사용자 확정: 기본 결품 또는 조립 검사 중 하나라도 FAIL이면 최종 FAIL이다. 다른 검사의 REVIEW/ERROR는 개별 사유로 보존한다.

## 원인과 변경

실제 배기 결품 시험은 기본 `FAIL / EXHAUST_TOP_MISSING`, 조립 `REVIEW`였지만, 종전 `ERROR > REVIEW > FAIL > PASS` 결합 순서가 최종 REVIEW를 만들었다. 화면은 저장된 결과를 올바르게 표시했고, 문제는 결합 정책이었다.

`jetson/src/vision/integrated_decision.py:combine_decisions()`를 `FAIL > ERROR > REVIEW > PASS`로 변경했다. 정책 식별자는 `ANY_CONFIRMED_FAIL_V2`이며 `standalone_service.py` 시작 정보도 같은 상수를 사용한다. 개별 판정과 원인은 그대로 유지한다. 기존 모델·임계값·정렬·촬영·PLC 설정·C 통신 코드 변경은 없다.

| 기본 검사 / 조립 검사 | PASS | FAIL | REVIEW | ERROR |
|---|---|---|---|---|
| PASS | PASS | FAIL | REVIEW | ERROR |
| FAIL | FAIL | FAIL | FAIL | FAIL |
| REVIEW | REVIEW | FAIL | REVIEW | ERROR |
| ERROR | ERROR | FAIL | ERROR | ERROR |

조립 검사 미완료의 내부 `FAIL_CANDIDATE`는 확정 FAIL로 읽지 않는다. 두 검사 모두 PASS일 때만 최종 PASS다. 통신 손실·STOP·저장 실패에 따른 취소 요청은 기존 Runtime 발행 경계에서 계속 차단한다. 완료된 검사 결과의 ERROR와 요청 취소를 혼동하지 않는다.

## 검증

- 새 회귀 6개: 전체 16조합, 실제 결품+정렬 REVIEW, 미완료 조립, 누락/알 수 없는 판정, 개별 ERROR 보존. 수정 전 실패를 확인하고 수정 후 통과.
- 노트북 28개, Jetson ARM64 28개 PASS. 결합·원본 품질·Journal 최종 저장·Runtime 발행 경계를 함께 점검했다. 실제 카메라/PLC 출력은 사용하지 않았다.
- 실제 검사 `5a0708cf246041d2a80a24c402c47f37`의 저장 판정을 새 함수에 입력하면 `FAIL / EXISTING_FAIL_ASSEMBLY_REVIEW`. 원본 자료 SHA는 동일하며 Journal을 수정하거나 결과를 재전송하지 않았다.
- 비공개 증거: `runs/basic_parts_missing_verification_001/policy_update/{LOCAL_TESTS.log,NATIVE_TESTS.json,SAVED_POLICY_REPLAY.json}`.

## 운영 적용 범위와 복원

변경 파일은 결합 함수와 서비스 정책 식별자 두 파일이다. 전체 `INTEGRATED_AI_OFFLINE` 패키지의 나머지 소스/모델/C/설정은 현 운영본과 해시가 일치해야 한다. 서비스 정지 후 current·설정·서비스 정의·SQLite backup API 백업을 노트북에서 해시/DB 무결성 확인한 다음 적용한다. 최신 Journal·사진·ABORTED·승인 이력을 이전 DB로 되돌리지 않는다.

적용 결과와 정확한 Release/SHA는 같은 비공개 경로의 `DEPLOYMENT.json` 및 `POST_DEPLOY_VERIFICATION.json`에 기록한다. 수정 후 신규 실제 검사 시험은 별도로 구분하며, 저장 결과 재결합만으로 현장 최종 FAIL 성공을 주장하지 않는다.

실제 적용 완료: source `887ea3f2eb1ffd141e9c3641e222da4e6438138b`, Release `engine-integrated-2719dff19eb79478`. 운영 185파일 해시 일치, 서비스/OpENer 각1개, 카메라 Worker 및 조립 Worker 유휴·준비 상태. PLC STOP, Request/Result/Done 0, 새 요청/발행 0. 이전 검사 원시 FAIL/저장 통합 REVIEW 보존 확인. 정지 백업 170파일 검증 및 SQLite 무결성 OK, archive SHA `07b34251d09950ed0ef51ee60a28f1894516f2646fdc570e0cc3ca1428574133`.

기존 실제 시험 완료 후 카메라 Worker 교체와 `CAMERA_OR_OBSERVATION_STREAM_UNAVAILABLE`가 별도로 관측됐다. 이 판정 정책 수정은 그 원인 해결이나 연속 운전 안정성 검증이 아니다.
