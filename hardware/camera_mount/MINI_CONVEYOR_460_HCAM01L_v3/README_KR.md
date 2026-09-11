# 460 mm Mini Conveyor용 HCAM01L Portal V3

독립 작업대 나사 고정식, **FIXED TOP-DOWN** 카메라 거치대다. 기존 V2 Clamp 방식과 CAD-002 커밋은 보존했다. 현재는 HARDWARE-CAD-003 Optical Clearance 보완이며 V0-T05/Runtime/Training을 변경하지 않는다.

사용자 최종 선택: **300 mm 일체형 기둥 두 개**, **작업대→카메라를 받치는 Deck 지지면 최대300 mm**. 높이는150~300 mm, 15 mm 간격11단계다. 전체 장치 높이가300 mm라는 뜻은 아니다. Base를 포함한 기둥 상단은310 mm이며 Camera body/stand는 별도로 올라온다.

현재 상태는 [광학 검증 기록](OPTICAL_VALIDATION.md)과 [전체 검증 JSON](validation/stl_validation.json)을 따른다. **현재 FOV 검증은 공식 HCAM01L FOV가 아니라 보수적인 PROVISIONAL Design Envelope**다. 실제 HFOV/VFOV와 동공 위치를 측정하기 전에는 이 envelope가 실제 영상을 모두 포함한다고 보장할 수 없다. 실물 출력·fit·강도·영상 검증은 별도다.

## 먼저 볼 파일
- [LOW + CENTER](preview/fov_low.png), [MID](preview/fov_mid.png), [HIGH](preview/fov_high.png)
- [LOW + LEFT](preview/fov_low_left.png), [LOW + RIGHT](preview/fov_low_right.png)
- [Deck Fit Coupon 상세](preview/fov_deck_fit.png): flared window, 네 contact land, 낮은 stop과 뒤쪽 strap slot
- [OpenSCAD source](src/MINI_CONVEYOR_460_HCAM01L_v3.scad): OpenSCAD에서 열고 F5, 마우스로 회전/확대.
- [실제 STL](stl/), [검증 결과](validation/stl_validation.json), [치수표](DIMENSIONS.md), [BOM](BOM.md), [설계 근거](DESIGN.md)

미리보기에서 파랑은 Base/기둥, 주황은 Crossbar/Deck, 검정은 카메라 본체, 초록은 Belt다. Cyan 투명체는5 mm 측면 여유를 포함한 Optical Keep-Out, 분홍 사각형은85×120 inspection zone이다. 빨간 화살표는 하향 촬영 방향이며 보라색은 Cable reference다. 기존 `preview_*.png`와 `optical_*.png`는 이전 설계/검토 이력이며 현재 형상이 아니다.

## 출력 파일과 방향
STL 단위mm, scale100%. STL은 아래 방향으로 이미 Z=0에 놓았다.

| STL | 수량 | 출력 방향 / 용도 |
|---|---:|---|
| base_left.stl | 1 | 작업대 접촉면 bed, 바깥쪽 확장 foot |
| base_right.stl | 1 | 작업대 접촉면 bed, 반대쪽 foot |
| upright_300.stl | **2** | 300×36 넓은 면을 bed에 눕힘; 수직 출력하지 않음 |
| crossbar.stl | 1 | 232×61 넓은 면 bed |
| camera_deck.stl | 1 | 길게 연장된 Deck의 옆면 bed; backplate/gusset 아래 support 필요 |
| camera_deck_fit_coupon.stl | 1 시험 | 바닥 bed; 실제 pocket/land/window/stop/strap 보존 |
| upright_hole_coupon.stl | 1 시험 | 넓은 면 bed; D6.8 hole4개, pitch15 |
| base_mount_coupon.stl | 1 시험 | 바닥 bed; D6.5와 입구 chamfer |

Stop과 cable tie point는 Deck에 통합되어 별도 retainer/guide STL이 필요 없다. Camera Deck Coupon은 전체 접촉 구조를 보존하지만 backplate/gusset/cable tie 부분은 생략하므로 전체 강성을 시험하지 않는다.

**Bed 주의:** 300×36 mm rail은220×220 mm bed에 평평하게 들어가지 않는다. 45° 배치의 사각 외곽은 약237.6×237.6 mm이다. Deck의267×69.5 mm 바닥도 대각 배치 사각형 약237.9 mm, 출력 높이112 mm다. **250×250 mm급 bed의 대각 배치**가 후보지만 실제 유효 영역·brim·support·clip·slicer를 확인해야 한다. 300 mm 기둥은 사용자 선택에 따라 일체형을 유지한다.

## 시험 출력 순서
1. `camera_deck_fit_coupon.stl`: camera를 앞면이 아래로 가게 올린다. Body fit, ring과 아래로 넓어지는 window 간섭, stand/strap/mic를 확인한다. Ø30은 Deck top 기준의 생성 원 지름이고 실제 top에는88.2×38.2 pocket이 열린다. 아래 개구는 약Ø49.53이다. Lens 중심이 다르면 **LENS_OFFSET_X/Y**를 측정값으로 바꾸고 재출력하며 시야 검사를 다시 실행한다.
2. `upright_hole_coupon.stl`: 실제 M6 bolt fit, 15 mm 간격, 벽/층 접합 품질 확인.
3. `base_mount_coupon.stl`: 실제 작업대 screw와 washer/head 확인.
4. 기둥 하나와 Base 한 쌍을 먼저 조립해 footprint·직각·흔들림을 확인한 뒤 전체 Portal을 출력/조립한다.

## 조립 / 높이 설정
1. Portal을 Conveyor 중앙 검사 영역보다 길이 방향으로255 mm 뒤에 둔다. 연장 Deck 위 카메라가 Conveyor 중앙을 향한다. 좌우 기둥 안쪽 간격160 mm, 중심 간격196 mm를 맞춘다. Base는 **넓은 foot가 바깥쪽**을 향하게 하고 작업대에 맞는 나사4개씩 고정한다. 실제 Motor/받침/배선 위치도 대조한다.
2. 각 기둥 하단의 별도2개 구멍(table Z30/60)을 Base에 M6 두 개로 고정한다. 기둥 아래면은 Base 위 Z10에 앉는다.
3. 높이 구멍을 아래부터1~15로 센다. 작은 긴 tick은1/6/11을 표시한다. 양쪽 동일한 **lower index2~12와 upper index=lower+3**을 선택하고 M6 두 개씩 Crossbar를 체결한다.
4. LOW는2/5 → 지지면150 mm, MID는7/10 →225 mm, HIGH는12/15 →300 mm. 한 단계가15 mm다. 바꾸기 전에 camera를 내려놓고 bar를 손으로 받친 상태에서 볼트를 제거·재체결한다.
5. Deck의 두 M6를 bar의 수평 slot에 넣고 ±30 mm 범위에서 belt/lens 중심을 맞춘 뒤 두 개 모두 잠근다. 각도 조절 힌지는 없으며0° TOP-DOWN이다.
6. 네 contact land에 선택한1 mm pad를 붙인다. Camera 전면을 아래로 놓고 ring 접촉을 확인한다. 폭10 mm Velcro를 뒤쪽 slot에 통과시키며 **Deck 아래에서는 lens 뒤25 mm band**를 지나게 한다. 렌즈 아래를 가로질러 감지 않는다. Cable은 Camera 위/뒤→Deck tie point→Crossbar 뒤→기둥 뒤 순서로4곳에 고정한다. 자유 loop가 렌즈 앞으로 떨어지면 사용하지 않는다.
7. 실제 belt top·물체 높이를 측정한 뒤 이후 장비 검증에서 preview로 focus/FOV/pixel coverage가 좋은 높이를 선택한다. 이번 작업은 카메라를 실행하지 않았다.

Pad를 붙이면 camera는 그 두께만큼 올라온다. Lens ring reference는22, 돌출4지만 모두 실측값이 아니며, CAD의 belt reference Z22.7을 실제 belt 높이로 사용하지 않는다.

## 출력 설정 / 후처리
PETG, nozzle0.4 mm, layer0.20 mm, walls4~5, top/bottom5 이상, infill35~45%부터 검토한다. Base/rail은 walls5와 infill45~55%를 시작값으로 고려한다. PLA는 coupon fit 시험용으로 사용할 수 있다. 강도 보증 profile은 아니다.

Base R6, rail/bar/Deck R4, 작은 stop R2와 일반 edge chamfer를 적용했다. Brim/support 제거부와 burr를 정리하고 손 접촉 edge를400~600 grit 사포로 가볍게 마감한다. M6 hole은 필요 시 가볍게 reamer/drill로 정리하되 균열·층 박리가 생기면 사용하지 않는다. 긴 나사 끝은 cap으로 덮는다.

## 재생성
무료 OpenSCAD2021.01과 기존 CAD 환경만 사용한다. Repository root에서:

```powershell
tools/cad/.venv/Scripts/python.exe hardware/camera_mount/MINI_CONVEYOR_460_HCAM01L_v3/build_validate.py
```

기본 명령은 현재 source로 모든 STL을 처음부터 export한다. `--mesh-only`는 중간 진단이며 최종 PASS가 아니다. 검증은 실제 STL의 section/ray 측정과 CSG를 사용하고 자동 repair로 결함을 숨기지 않는다. Source/STL SHA256과 tool version은 JSON에 기록한다.

Digital PASS는 **실제 fit·slicing·강도·진동·PETG creep·광학 focus/FOV PASS가 아니다.** 미측정 조건과 실제 screw/stand/케이블 간섭은 Coupon과 실물에서 확인한다.

## 실제 영상 검증 — 다음 장비 작업
이번 CAD 작업에서는 Jetson과 Camera에 접속하지 않았다. `camera_preview.py`는 현재 Repository에서 찾지 못했으므로 Jetson에 실제 준비된 파일의 경로·CLI·현재 영상 장치 노드를 먼저 확인한 뒤 실행한다. 존재하지 않는 명령 옵션을 추정하지 않는다.

1. HCAM01L을 Deck에 장착하고 실제 렌즈 중심·pad·stand 상태를 확인한다.
2. 승인된 다음 장비 작업에서 `camera_preview.py`를 실제 확인된 CLI로 실행한다. 해상도·crop·초점/FOV 측정 조건을 기록한다.
3. LOW150 mm, MID225 mm, HIGH300 mm를 각각 검사한다. 각 높이에서 LEFT/CENTER/RIGHT도 확인한다.
4. 화면 상·하·좌·우와 네 corner에 Deck, Crossbar, 기둥, Base, Stop, Bolt, Velcro가 보이지 않아야 한다.
5. Cable을 실제 routing한 뒤 반복한다. Inspection zone 전체가 보이며 필요한 초점과 pixel coverage가 나오는지도 따로 확인한다.
6. 한 자세라도 거치대가 보이면 Physical FAIL이다. 실측 HFOV/VFOV/동공/왜곡에 맞춰 parameter를 보정하고 CAD 재검증 후 수정 부품을 출력한다.

넓은 가설 FOV는 구조물 침범 검사에 보수적인 방향이지만 coverage에는 낙관적인 방향이다. 따라서 CAD의 inspection zone 포함 결과는 실제 카메라의 Belt 전체 촬영 보장이 아니다. 긴 Deck의 처짐·진동·체결 풀림·장기 변형도 실제 설치 상태에서 검사한다.
