# HARDWARE-CAD-003 — Optical Clearance 작업 계약

## 범위와 기준
Baseline `daf1a8a`. 기존 Base, 300 mm 일체형 기둥 두 개, 15 mm pitch, 11단계 Deck 지지면150~300 mm, Crossbar 양쪽 두 bolt, ±30 mm slide, 고정 TOP-DOWN과88.2×38.2 pocket을 유지한다. V2/Runtime/V0 Task/ML 환경은 수정하지 않는다. 이전 검토 파일·ZIP·사용자 사진은 보존한다.

## 설계 보완
HFOV90°/VFOV70°는 **PROVISIONAL_DESIGN_ENVELOPE**다. 실제 HCAM01L보다 넓다는 보장은 없으며 실측 FOV/입사동공 위치/왜곡으로 보정해야 한다. 초기 동공 기준은 지지면+3 mm, XY 불확실성은 편측2 mm다. 시야 옆면에서 법선 방향5 mm의 추가 여유를 둔다. 동공 뒤쪽은 촬영 공간이 아니므로 뒤로 무한 확장하지 않는다.

기존 Portal은 렌즈 기준 Y62 mm에서 시야를 침범했다. 이전 결과의243.74 mm는 필요한 **Y 좌표**이며 추가 이동량이 아니다. 추가 이동량은 약181.74 mm이고 여유5 mm를 아직 더하지 않은 값이다. Camera Y255 mm로 연장하고 Conveyor 중앙을 그 아래에 배치한다. Base/기둥/Crossbar 치수와 높이 체결 위치를 보존하며 Deck에 길어진 두 gusset을 사용한다. 이 이동은 기구 보완 범위이며 실제 하중·진동·PETG creep은 여전히 별도 시험이다.

렌즈 창은 상부 기준 원뿔 Ø30 mm에서 하부 Ø49.53 mm로 넓어진다. 상단에는 pocket이 겹치므로 실제 Deck 상면 개구는88.2×38.2 mm이며 Ø30 mm의 원통 목이 남는 것은 아니다. HFOV/VFOV의 모서리 광선까지 고려한 원뿔 기울기를 사용한다. 외곽 contact lands와 pocket은 그대로 유지한다. Velcro의 Deck 아래 경로는 렌즈 뒤쪽 band로 옮기고, Cable은 Camera 위/뒤→Crossbar 뒤→기둥 뒤로 고정한다.

## 검증 계획
현재 source에서 모든 출력 STL을 재export한다. 기존 mesh/치수/높이/기계 간섭 검사를 유지한다. 실제 STL을 조립 좌표로 변환하여 모든11개 height×3개 slide에서 광학 envelope와 교차하는 triangle을 검사한다. 닫힌 solid 내부에 envelope가 통째로 들어가는 경우도 검사한다. 구조물 정점이 발견되지 않는다는 이유만으로 PASS하지 않는다.

Lens plane / Deck top / contact plane / Deck bottom / Belt reference plane의 시야 단면을 기록한다. 실제 STL 단면에서 상/하 개구 치수와 flare를 대조한다. Conveyor와85×120 mm inspection rectangle은 검출 대상 reference이므로 구조물 침범 검사에서 제외하고 포함 여부를 별도로 확인한다.

## 상태
**PASS_WITH_WARNINGS — Digital envelope PASS / Physical FOV UNVERIFIED.**

2026-09-11 Windows CAD 전용 Python에서 `build_validate.py` 전체 실행을 완료했다. 최종 소스에서 8개 STL을 새로 export했고 전체 실행은555.15초, exit0이다. OpenSCAD2021.01 / Python3.13.5 / numpy2.5.3 / trimesh5.1.0을 사용했다. 근거와 SHA256은 [stl_validation.json](validation/stl_validation.json)에 있다.

- 8개 STL 모두 nonempty, positive volume, watertight, winding consistent, one connected solid, bed Z=0 PASS.
- 실제 STL 치수·hole·높이11단계·기계적 간섭 검증 PASS. 상세 CSG7개도 빈 교차를 확인했다.
- 모든11개 height × slide -30/0/+30 mm =33개 자세, 429개 부품·자세 조합에서 확대 FOV와 교차 NONE. LOW/MID/HIGH 및 LEFT/CENTER/RIGHT 모두 포함한다. 연속 slide 전 구간의 수학적 증명은 아니다.
- Deck/Stop/Retainer/Tie Guide, Crossbar, 양쪽 Upright/Base, Cable, Velcro, 체결 하드웨어 reference를 검사했다. 통합 feature는 실제 Deck STL 전체 검사에 포함한다.
- 광학 교차 알고리즘의 경계·면 관통·완전 포함·빈 내부 공간·margin 검증7개 PASS. 수치 epsilon은1e-7 mm이며 물리 여유5 mm와 구분한다.
- 창 실제 단면: local Z60.02에서49.484 mm, Z63에서42.208 mm, Z67.98에서 pocket88.2×38.2 mm. Lens→Deck→Belt 단면과 독립 광학 계산을 대조했다.
- 85×120 mm Inspection Zone은33개 자세의 **잠정 nominal FOV**에 포함된다. 넓은 시야 가정은 구조물 침범 검사에는 보수적이지만 촬영 범위 보장에는 낙관적이므로 실제 촬영 가능성을 확정하지 않는다.

LOW/MID/HIGH와 LOW 좌우 preview를 새로 생성하고 LOW/HIGH 및 coupon을 눈으로 확인했다. FOV reference는 출력 STL에 포함하지 않는다. 길어진 Deck의 출력 크기는267×69.5×112 mm이며 옆면 출력과 support가 필요하다. 실제 장착·강성·진동·PETG creep·렌즈 중심/동공 위치·FOV/왜곡/영상 crop은 미검증이다. Jetson/Camera/ML 실행 없이 기존 V2와 V0-T05 TODO를 보존했다.
