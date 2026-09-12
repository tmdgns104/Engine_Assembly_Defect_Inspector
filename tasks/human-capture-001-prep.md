Task ID: HUMAN-CAPTURE-001-PREP
Title: 검사 기준 설정 / 이어폰 첫 네 장 촬영 준비
Status: DONE / VERIFIED (촬영 준비 범위)
Depends On: V0-T04 (DONE / VERIFIED 유지)

## 문제와 요구

열린 케이스 안의 실제 L/R 이어폰을 첫 Proxy 제품으로 선택한다. 기존 수집
도구의 OBJ_A/B/C 고정을 제품 설정으로 확장하고, 네 상태를 한 장씩 촬영할
준비를 한다. 사용자 요청이 이번 작업의 승인된 범위다.

## 구조와 구현 범위

- 기존 Training/Runtime 분리, Camera/Detector 및 결과 계약을 유지한다.
- 수집 전용 JSON profile을 선택한다. 미선택 시 기존 schema_version=1 동작을
  유지하고, 선택 시 v2 manifest에 설정 사본과 정규 JSON SHA256을 보존한다.
- profile은 부품·촬영 상태 정답만 정의한다. Runtime 판정 입력이나 bbox가 아니다.
- 같은 세션은 같은 설정을 유지한다. 설정 변경은 새 세션, 물체 재배치는 새 episode다.
- 검사 기준과 실제 촬영 순서는 제품 README 한 곳에 정리한다. 실제 판정 구현은
  V0-T11~T14 후속 Task에 남긴다. 승인된 Architecture 변경은 필요 없다.
- 원본 사진, CAD/FOV 미커밋 파일, ML 환경, 완료 Task와 Evidence는 보존한다.
- 카메라/Jetson 접속, 설치, 라벨링, 학습, 평가, 변환, 배포, PLC 제어는 제외한다.

## 수용 기준과 검증

- 정상/왼쪽 누락/오른쪽 누락/양쪽 누락 정답 기록이 정확하고 case는 유지된다.
- 잘못된 설정·정의 밖 객체/시나리오, 설정 해시 불일치를 거부한다.
- v1과 CAMERA_SMOKE, 파일명/덮어쓰기 방지/잠금/재로드/크기/해시 검증을 유지한다.
- 원본 설정 변경·삭제 후에도 기존 기록을 독립 검증한다.
- 이름과 부품 수가 다른 가상 설정으로 공통 처리 경로를 검증한다.
- 기존 테스트는 변경하지 않고 전체 unittest와 추가 회귀 테스트를 실행한다.
- 첫 네 장 준비와 실제 수집/검사 성공을 구분한다. 전체 수집량은 사진 검토 후 결정한다.

## 시작 근거

- Windows `D:\OneDevice_Team_project`, HEAD `d41bdd5e33b8ef3911dc0413924c0754e8b12835`.
- 기존 전체 테스트 40/40 성공. CAD/FOV 변경은 hardware/ 아래이며 이번 범위와 겹치지 않는다.
- 로컬 data/proxy/raw의 PNG/manifest는 0개. 과거 CAMERA_SMOKE 3장은 별도 역사적 근거다.
- 다음 Human Action: Jetson에서 현재 카메라 조회 → 열린 케이스 정상 배치 → 첫 사진 촬영·검토.

## 결과와 근거

- 준비 수용 기준 PASS: 기존 40개 무수정 + 추가 16개 = 전체 56/56 성공.
  [실행 근거](../docs/verification/HUMAN-CAPTURE-001-PREP.txt)에 명령·출력·검증 범위를 기록했다.
- 두 수집/검증 스크립트를 확장하고 제품 profile/설명, schema, 세션 양식, 회귀 테스트를 추가·갱신했다.
  이름과 부품 수가 다른 가상 제품도 같은 경로로 저장·검증했다.
- 기존 v1 schema 의미, 로컬 sample 3장, 보호 파일 229개를 대조했다. CAD/FOV와 사용자 사진,
  기존 테스트·T04 Task/Evidence·Runtime 계약을 보존했다. 추가 패키지는 설치하지 않았다.
- 실제 촬영 0장, 사진 검토·라벨링·학습·배포 미실행. 현재 카메라와 검사 판정 실행은 UNVERIFIED다.
  JSON Schema 외부 엔진 검증은 미실행이며 실행 검증기/필드 계약 검사는 성공했다.
- 학습 메모: [설정과 과거 기록의 경계](../docs/learning-notes/HUMAN-CAPTURE-001-PREP.md).
- 다음 작업은 HUMAN-CAPTURE-001의 사람 장치 확인·정상 사진 촬영이다. V0-T05는 시작하지 않는다.
