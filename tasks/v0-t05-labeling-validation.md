Task ID: V0-T05
Title: Labeling + Dataset Validation
Status: DONE / VERIFIED — B01/B02 train120장·240객체 및 B03 val60장·120객체 승인/변환 완료
Depends On: V0-T04

## Latest result (2026-09-13, B03 approval)

사용자가 "모든사진 OK라는거야 일일이 확인 안받아도되"로 B03 v003 전체60장의 부품 종류·사각형 범위를 승인했다. 초안 SHA256 `1ec9e399e7810dadfd4e1ba45ead74f8b0e127e0d80c57e07524c32668cf42aa`와60개 실제 사진 ID를 새 `human_review_all60_v001.json`에 연결했다. `project_reviewed_all60_v001.json`은 상태만 confirmed로 변경했으며 사각형/메모/과거 초안/부분 검토 로그는 보존했다. `training/outputs/yolo/B03_reviewed_20260913_v001/`에 기존 변환기로60장/120객체, 보류0을 생성했다. 기존 B01/B02 승인·YOLO 결과는 재사용했다. 후속 T06/T07까지 완료됐으며 최신 종합 근거는 `docs/verification/PROXY-DATASET-TRAIN-001-BASELINE-20260913.json`이다. 아래 과거 B03 미진행 기록은 당시 이력이다.

## Purpose
Finish pilot labeling and validate dataset quality before splitting.

## Allowed Changes
- Build a simple label taxonomy for proxy objects.
- Run label consistency and completeness checks.

## Forbidden Changes
- Do not split before labeling validation.
- Do not tune model while labels are incomplete.

## Implementation
- Create labeling rubric for V0 placeholder classes.
- Produce `label_audit.md` and resolve obvious mistakes.

## Verification
- No required object annotations are missing in the pilot set.
- Label quality checks pass the project threshold.

## PASS Criteria
- Labeling complete.
- Labeling report approved.

## Current Finalization Contract (2026-09-13)

- 사용자가 `project_draft_all120_v001.json` 전체120장의 부품 종류와 사각형 범위를 학습용으로 명시 승인했다. 추가 확인 없이 정확한 파일 SHA256·실제 이미지 ID·응답 근거·기록 시각을 새 reviewed 프로젝트와 별도 승인 기록에 연결한다. 기존 pending 초안과 경계 불확실성 메모는 보존한다.
- 기존 변환기가 없어 공통 `training/scripts/via_to_yolo.py`와 집중 테스트를 추가한다. 클래스는 제품 schema에서 읽고, 파일 전체가 승인된 경우만 원본 사본·YOLO 라벨·출처 목록으로 변환한다. 일부 미확정/무라벨/잘못된 라벨은 사진 전체를 보류하고 이유를 남긴다.
- 입력/원본 해시, ID·클래스·좌표, 실제 출력의 역변환 오차, 파일명 충돌, 촬영 회차·origin_group 보존을 검증한다. B03가 없으면 dataset.yaml·학습 완료를 만들지 않는다. B04는 시험 예약으로 유지한다.

## Artifacts
- `label_audit.md`
- `label_schema.json`

## Finalization Result (2026-09-13)

- 최신 사용자 저장본 검색에서 후속 JSON이 발견되지 않아 명시 승인한 `project_draft_all120_v001.json` SHA256 `c3ae6b5c0a9cbacad59aee1a6ce54d2fdea1e160b2fb17aff4e72033404bfd14`를 기준으로 삼았다. 사용자 응답은120장 전체의 부품 종류와 사각형 경계를 학습용으로 승인한다는 명시 진술이다. VIA 표시 성공만으로 승인한 것이 아니다.
- `training/outputs/labeling/B01_B02_20260913/project_reviewed_all120_v001.json`: confirmed120장·240객체(클래스0/1/2=60/60/120), 보류0. `human_review_all120_v001.json`에 초안/승인본 SHA·사진별 실제 ID/원본 해시·응답·기록 시각을 연결했다. 실제 검토 시각은 별도로 알려지지 않아 null이며 기록 시각과 구분한다.
- 변경은120개 이미지의 review_status뿐이다. 사각형·클래스·초기/기존 초안·provenance·원본·이전 메모는 보존했다. needs_review의 우선0001·0002·0057·0081 및 나머지 경계 메모는 전체 승인 범위에 포함된다. 수정/보류 요청0이며 흐림·반사가 물리적으로 개선됐다는 뜻은 아니다.
- 승인 검사/보고: 같은 작업 폴더의 `review_approved_all120_v001/approval_verification.json`, `label_audit.md`.
- 공통 변환기 `training/scripts/via_to_yolo.py`는 제품 schema 및 해시로 연결한 사람 승인 기록을 입력으로 사용한다. 일부 미확정·무라벨·잘못된 객체는 사진 전체를 보류하며 좌표 자르기나 객체 삭제로 통과시키지 않는다. collection_id+capture_id로 Windows 파일명 충돌을 차단하고 전체 원본 provenance를 보존한다.
- 변환 결과: `training/outputs/yolo/B01_B02_reviewed_20260913_v001/`의 images120·labels120/240객체, candidate_manifest.json, withheld_images.json(0), conversion_validation.json, independent_audit.json, dataset_readiness.json. 실제 이미지1280×720이며 검토용 표시 PNG는 입력에 없다.
- 집중 테스트16개 PASS(0.463초): 공통 클래스 정상 변환·실제 텍스트 역변환, 범위 밖/비유한/0크기·잘못된 클래스·pending 파일/객체·보류/무라벨·변경된 승인 해시·원본 해시·충돌/덮어쓰기·시험 예약 거부, validation 그룹 보존. 최초 unittest 모듈 경로 호출은 tests가 패키지가 아니어서 import 실패했고 discovery 명령으로 실제16개를 실행해 통과했다. 전체 프로젝트/GPU/카메라 테스트는 반복하지 않았다.
- 실제 출력 별도 검사 PASS:120쌍·240객체·출력 파일 재로드·SHA·클래스·좌표·회차/그룹 연결, 코너 역변환 최대 오차4.8000061e-08픽셀(허용1e-06), 보호368파일 및 원본162장 보존,599이벤트 체인. 요약 근거: `docs/verification/V0-T05-YOLO.json`.
- 다음 V0-T06 준비: B03 현재 미시작/0장, 유효 스탠드 계획60장. B01/B02는 같은 OG1023298FB0FC4631 학습 후보로 유지한다. B03 실제 재준비·촬영·위치 라벨 검토·변환과 그룹 분리 확인 전 dataset.yaml/학습 준비 완료로 표시하지 않는다. B04는 시험 예약이며 첫 학습에 사용하지 않는다. 물리적 독립성이나 재준비는 이번 파일 작업으로 확정하지 않았다.

## Earlier Evidence (2026-09-13; superseded by Finalization Result)
- 기존 B01/B02 작업 공간120장·초기 영역0·라벨 confirmed0. 현재 초기 프로젝트 및 provenance/원본/사본120개 연결과 SHA256 일치 확인.
- 준비 스크립트 관련7개 회귀 테스트 통과(0.127초): 원본 보존·pending 사본·그룹 연결, 덮어쓰기/원본 폴더 출력 거부, 해시/인계 불일치·합성/다른 제품·시험 예약 입력 거부.
- 검증 로그: `docs/verification/V0-T05-VIA-PREP.txt`. 준비 코드를 재실행해 실제 작업 공간을 덮어쓰지 않았다.
- 후속 사용자 요청에 따라 브라우저를 조작하지 않고 실제 PNG4장과 기록된 실물 L/R 관계를 확인해 초안을 작성했다. 0001 NORMAL=3개,0002 MISSING_LEFT=2개,0003 MISSING_RIGHT=2개,0004 MISSING_BOTH=1개. 모두 pending·사람 검토0이며 흐린 경계는 needs_review 메모로 남겼다.
- 새 저장본: `training/outputs/labeling/B01_B02_20260913/project_draft_first4_v001.json`. SHA256 `7fbf7a8bd7a8a6b8b140082a35e959d9968400effb5714cf8640ec72c8261ef4`.
- 검토 이미지4장·모아보기·작성 근거·보호 해시·검사 결과: 같은 작업 폴더의 `review_first4_v001/` (`annotation_worklog.json`, `verification.json`). 실제 원본 위 사각형과 네 장 비교 이미지를 Codex가 확인했다. 검토 이미지는 학습 입력이 아니다.
- 별도 디스크 검증 PASS: 클래스·양의 정수 좌표·원본1280×720 범위, 이미지 ID/provenance/원본·사본120쌍, 보호365파일 해시 보존, 초기 JSON/설정/나머지116장 불변, 새 JSON 재로드 일치. 실행 중 앱의 `.wizard-writer.lock`은 읽거나 변경하지 않고 해시 대상에서 제외했다.
- 기하 검사 통과는 의미 정확성 승인과 다르다. 실제 VIA 로드 후 표시 복원과 사람 검토는 아직 미확인이다.

## Local File Draft History (superseded by Finalization Result)

- 최신 요청은 첫4장 제한을 대체하여 나머지116장의 pending 초안을 허용했다. 사용자의 첫4장 VIA 표시 확인은 라벨 정확성 승인이 아니다. 작업 시작/종료 전 작업 공간과 Downloads의 JSON 후보에서 후속 사용자 저장본을 발견하지 못했으며 기존 project_draft_first4_v001.json을 기반으로 삼았다. 브라우저 미저장 내용은 읽지 않았다.
- 0005~0120의 실제 PNG 확대 영역을 각각 열람하고 원본 픽셀 좌표로116장232개 초안을 작성했다. 초기4장8개 라벨·메모·검토 상태를 보존했다. 12장씩9묶음+마지막8장, 총10개 누적 체크포인트 및 원본 위 확대 비교29개를 실제 열람했다. 별도 시각 확인 기록은 visual_review_ledger.json에 있다. 제품 클래스는 기존 schema에서 읽었으며 영상처리의 어두운 성분 탐색은 열람 영역만 골랐고 라벨을 생성하지 않았다.
- 최종 JSON: `training/outputs/labeling/B01_B02_20260913/project_draft_all120_v001.json`, SHA256 `c3ae6b5c0a9cbacad59aee1a6ce54d2fdea1e160b2fb17aff4e72033404bfd14`.
- 최종 범위 검사 PASS: 전체120장·기존4장 보존·신규116장·총240개(0=60,1=60,2=120), pending120·사람 confirmed0. 부분 작성0·판단 불가 미작성0·미작성0. 원본/사본120쌍 및 보호367파일 SHA, 이미지 ID/파일명/크기 연결, schema 클래스, 유한 좌표·양의 크기·원본 범위, 기존 설정/라벨 불변, 체크포인트 해시·수량·미처리 목록 일치. 의미 정확성은 미확정이다.
- 검토 자료: 같은 작업 폴더 `review_all120_v001/`의 사진별 PNG120개·확대 비교30개·`REVIEW_KR.md`·`needs_review.json`·`processing_status.json`·`annotation_worklog.json`·`verification.json`. 기존4장 표시도 같은 폴더에 복사 렌더링했으며 좌표는 바꾸지 않았다. 모든 사진의 흐린 외곽 또는 반사 사유를 유지했다. 우선0001·0002,0057 L,0081 R부터 검토한다. 검토 이미지는 학습 입력이 아니다.
- 사용자가 현재 VIA 작업을 보존한 뒤 최종 누적 JSON을 Project → Load로 불러온다. 최종 파일의 실제 VIA 표시 복원은 아직 미확인이다. 실제 확인한 사진만 사람 검토 완료로 기록한다. 기존 준비 코드 테스트는 반복하지 않았다.
- 브라우저 연결 복구·다른 화면 도구 우회는 재시도하지 않는다. 초기 JSON·실제 원본·provenance·그룹 관계를 보존한다.

## Desktop Resume (historical; superseded by local-file request)

- 사용자가 현재 Codex CLI로 실행 중임을 확인했다. 이 세션의 공식 브라우저 목록은0이며 iab는 unavailable이다. Windows Computer Use는 Chrome URL 확인에서 중단됐고 우회하지 않았다.
- 이 PC에는 OpenAI.Codex26.903.8094.0 및 OpenAI.ChatGPT-Desktop1.2026.190.0 패키지가 설치되어 있다. 데스크톱 앱의 공식 Browser/Chrome 연결로 같은 프로젝트를 이어갈 수 있는지 다음에 확인한다. 연결 성공을 아직 주장하지 않는다.
- 작업 폴더: `training/outputs/labeling/B01_B02_20260913/`. 기존 초기 JSON과 원본·사본·provenance를 보존한다. 저장된 후속 프로젝트는 현재 작업 폴더에 없으며 실제 브라우저의 미저장 상태는 확인하지 못했다.
- 주소: `http://127.0.0.1:8766/via.html`. 서버와 후속 저장본을 먼저 확인하고, 실제 페이지의 주소 확인을 거친 뒤 첫 정상 사진의 pending 초안을 작성한다.
- 첫 대표 사진은 provenance에서 확인한0001 NORMAL,0002 MISSING_LEFT,0003 MISSING_RIGHT,0004 MISSING_BOTH다. 실제 이미지도 다시 대조한다. 클래스0=L,1=R,2=case. 사람 확인 전 confirmed로 변경하지 않는다.
- 준비 코드7개 회귀 테스트는 이미 통과했다. 변경·실패가 없으면 반복하지 않는다. B03/B04·새 촬영·학습·Jetson은 아직 미실행이다.
