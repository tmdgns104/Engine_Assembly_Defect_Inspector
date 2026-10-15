# V1 판정·복구·실물 검사

2026-10-15 진행 중. 새 정책의 현장 정상/결품/복원 검증은 아직 완료되지 않았다.

## 변경 전 실물 확인

기존 `ANY_CONFIRMED_FAIL_V2`, Release `engine-integrated-2719dff19eb79478`에서 새 배기 결품 검사 `0fd4458adf01458f8350283527e6e865`를 수행했다. 실제 원본3장의 PNG·픽셀 SHA를 확인했고 기본 `FAIL/EXHAUST_TOP_MISSING`, 조립 `REVIEW`, 최종 `FAIL`이었다. NG는 cyclic31667, Done은 다음31668, 요청 해제와 출력0 및 transaction settled를 확인했다. 요청부터 Result10.019초. 현장 사용자가 불량 LED·재가동·마지막 STOP을 확인했다. Worker7590/연결1 유지, 해당 시험 timeout0.

## 최소 수정

- `integrated_decision.py`: `BASIC_WITH_CONFIRMED_ASSEMBLY_FAIL_V1`. 유효한 기본 PASS는 조립 정렬/분석 불확실성만으로 NG가 되지 않는다. 기본 FAIL과 근거가 확인된 조립 FAIL은 우선한다. 조립 후보 문자열만으로 확정하지 않고 각 원본3장의 식별·무결성, 몸체 자세, crop 저장, argmax와 세 프레임 합의를 확인한다. 모델·정렬·점수 임계값은 그대로다.
- `standalone.py`: 원본/저장 증거가 없거나 취소된 요청은 선택적 분석으로 우회하여 발행하지 않는다. 실제 cyclic STOP 입력으로 카메라 복구를 판단하며 새 Worker 준비 중에는 이전 프레임의 시계로 오류를 만들지 않는다. 새 epoch는 이전 제품 이탈 근거가 아니므로 제품/미완료 Journal 계약을 보존한다.
- `standalone_web.py`, `line_hmi.html`, `line_details.js`: 기본 부품 검사와 오조립 참고 분석을 구분하고 개별 원인과 확정 여부를 표시한다. 이전 저장 결과는 수정하지 않는다.

## 최초 카메라 오류 근거

이전 시험 기록에서 monotonic6249.863에 `FRAME_INTEGRITY_REJECTED/BROAD_HORIZONTAL_CORRUPTION`이 최초 원인이었다. Worker6099→6626, generation 변경6250.124, 새 유효 영상6251.835. 기존 Runtime은6251.462에 옛 프레임의 시각으로 `CAMERA_OR_OBSERVATION_STREAM_UNAVAILABLE`을 남겼다. 줄무늬 검출은 유지한다. 이 기록만으로 하드웨어 고장 또는 줄무늬 검출의 오탐을 확정하지 않는다.

정상 분석 불확실성은 결과 처리로 끝나지만 실제 카메라/저장/통신 장애는 현재 요청을 취소한다. 카메라 복구는 정지·무출력·유휴 상태에서 하며 미완료 기록을 가짜 final/ABORTED로 변경하지 않는다. 기존 독립 ABORTED 복구와 Journal 차단을 재사용한다.

## 검증·배포 상태

노트북 집중 회귀147개 PASS(환경별2skip), UI 검사 PASS. ARM64 집중 회귀도147개 PASS(플랫폼 조건1skip). 노트북 일관된 백업·해시 검증·실제 적용과 새 정책3회 현장 시험은 진행 중이다. 검증용 도구의 첫 ARM64 실행은 spawn 진입 가드 및 fixture 누락으로 실패하여 도구를 수정했다. 운영 실패나 현장 성공으로 혼동하지 않는다.

비공개 원본/Journal/실행 증거: `runs/v1_line_completion_001/`. GitHub에는 코드·합성 회귀·보고서만 보관한다. PLC·EDS·카메라·조명·모델·C 바이너리·현장 설정은 변경 대상이 아니다. 신규 제품별 권한 없음.

복원은 서비스 정상 종료 후 검증된 노트북 직전 백업의 current/config/unit만 사용한다. 최신 Journal·PNG·ABORTED·승인 소비 원장은 되돌리지 않는다. 직전 코드는 V2이므로 V1 현장 성공으로 표시하지 않는다.
