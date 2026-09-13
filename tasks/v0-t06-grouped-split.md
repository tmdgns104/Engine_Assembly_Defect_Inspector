Task ID: V0-T06
Title: Grouped Train / Validation / Test Split
Status: DONE / VERIFIED — train120 / val60 / test0 reserved
Depends On: V0-T05

## Purpose
Create leakage-safe split based on capture acquisition boundaries.

## Core Rule
- TRAIN: updates model weights.
- VALIDATION: used during development, thresholding, hyper-parameter comparison.
- TEST: sealed final evaluation used once after final model selection.
- Never use TEST for repeated tuning decisions.

## Allowed Changes
- Split by session / setup / arrangement episode / sequence grouping.
- Keep near-duplicate frames in same split.
- Create split manifests and seeds.

## Forbidden Changes
- No random per-frame split for primary dataset.

## Verification
- Leakage check confirms no group appears in multiple splits.

## PASS Criteria
- Train/val/test manifests are published and auditable.

## Artifacts
- `split_manifest.json`
- `leakage_check_report.md`

## Final split result (2026-09-13)

B03 v003 전체60장 사용자 명시 승인 후 공통 변환기로 validation_candidate60장/120객체, 보류0을 생성했다. 기존 B01/B02 train120장/240객체와 같은 제품 schema로 구성했다.
`training/outputs/datasets/earbud_case_v0_B01_B03_20260913_v001/`에 dataset.yaml, train.txt, val.txt, split_manifest.json, leakage_check_report.json/.md, dataset_integrity.json을 저장했다.
실제 원본/후보 PNG·라벨·승인 입력 해시, 클래스·좌표·개수 검사 PASS. train/val 이미지 SHA와 origin/session/episode/capture 교집합0. camera setup은 같은 calibration ID를 유지하고 실제 재준비는 기존 사람 선언에 근거한다. 외형 유사성이나 환경 일반화를 독립 입증한 것은 아니다.
B04 test manifest는 빈 배열+예약 이름만 기록했다. B04 이미지 접근/학습 사용0. 새 분리/입력 집중 검사8개 PASS.

## Earlier Ready-to-resume Evidence (historical, 2026-09-13)

최신 추가: B03 실제 촬영60장·15묶음 검토 완료. origin_group OG697C8F89699D4572는 B01/B02와 다르며 실제 이미지 해시 중복0. 별도 B03_20260913/project_draft_all60_v003.json에60장/120개 pending 위치 라벨을 작성했지만 사람 라벨 승인0·B03 YOLO 변환0이므로 T06은 아직 TODO다. B01/B02 기존120장 승인은 유지한다. 다음은 B03 위치 라벨 검토와 validation_candidate 변환이며, 그 뒤 실제 승인된 양쪽 후보로 split_manifest/dataset.yaml을 만든다. B04 미촬영은 첫 학습 차단 사유가 아니다. 아래 B03 미시작 내용은 이 체크포인트 이전 근거다.

- V0-T05의 B01/B02 위치 라벨120장·240객체 승인/YOLO 후보 변환 완료. `training/outputs/yolo/B01_B02_reviewed_20260913_v001/dataset_readiness.json`을 기준으로 이어간다.
- B01/B02 각60장, 같은 origin_group `OG1023298FB0FC4631`, 모두 train_candidate다. 두 회차를 임의로 train/val로 나누지 않는다.
- 기존 수집 `C2709B20787804587`의599이벤트 체인 및 유효 계획 확인: B03 validation_candidate60장 계획, 실제 시작/촬영/라벨0. 다음 기존 블록은 main_B03_BASE_CENTER다. 재준비 사실은 아직 사람 확인 전이다.
- B03 원본·검토된 위치 라벨·별도 실제 그룹이 준비돼야 train/val 경로와 누수 검사를 만든다. dataset.yaml과 split_manifest는 아직 생성하지 않았다. B04는 test_reserved로 유지하며 최종 시험 자료를 학습/튜닝에 사용하지 않는다. B04 미촬영만으로 B03까지 준비된 첫 학습을 차단하지 않는다.
