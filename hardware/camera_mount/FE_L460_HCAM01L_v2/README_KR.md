# FE-L460 · HCAM01L 카메라 마운트 v2

HARDWARE-CAD-001: Vision Dataset과 AI Inspection의 촬영 위치를 반복 설정하기 위한 **상부 촬영 조절식 프로토타입**. 실제 STL과 파라메트릭 source를 제공한다. 완성품 FE-L460 전용 fit/강도 인증은 아니다. Jetson/카메라 접근·Training·V0 Task 상태 변경 없이 Windows에서 만든다.

HCAM01L body는 **87×37×33 mm(stand 제외)**, fixed focus, USB2.0/200 cm cable, 표기1280×720/30 FPS/1MP다. FE-L460의 확정 치수는 belt100 mm다. frame단면·lip·insert thread·접힌 stand 간섭은 [DIMENSIONS](DIMENSIONS.md)에 미확정으로 남겼다.

**2026-09-11 결과: PASS_WITH_WARNINGS.** OpenSCAD 실제 STL 11/11, watertight 및 단일 solid 11/11, 치수/gauge와 조립 자세 CSG 13/13, lip 변경 export 2/2가 통과했다. [검증 JSON](validation/stl_validation.json)에 source/STL hash와 실측 수치를 남겼다. 실제 출력·slicing·FE-L460 fit·stand 간섭·강도는 미검증이다. V0-T05는 TODO 그대로다.

## 실제 출력 파일

STL 단위는 **mm**, 100% scale. 모두 권장 bed orientation으로 export되어 Z=0이다. 기존 전체 assembly를 한 번에 출력하는 STL은 제공하지 않는다.

| STL (stl/ 아래) | 수량 | 출력 방향 / 역할 |
|---|---:|---|
| upright.stl | 2 | 넓은 면을 bed에, 긴 축 평면 배치. 수직으로 세워 출력하지 않음 |
| clamp_body.stl | 1 | 오른쪽, 옆면 bed, gusset 포함 |
| clamp_body_left.stl | 1 | 왼쪽 대칭 형상, 이미 mirror되어 있으므로 slicer에서 다시 뒤집지 않음 |
| clamp_jaw.stl | 2 | 넓은 평면 bed, metal 접촉면은 위 |
| crossbar.stl | 1 | 180×48 넓은 면 bed, 두께18 |
| camera_carriage.stl | 1 | 뒤 평면 bed; fork/가로 bore에는 local support 검토 |
| camera_mount_plate.stl | 1 | camera쪽 평면 bed; hinge lug 아래만 support 검토 |
| camera_cradle_HCAM01L.stl | 1 선택/fit | 바닥 bed, 앞·위 개방. body-only fit 시험 및 fallback |
| clamp_fit_coupon.stl | 1 시험 | 상부 section coupon, 평면 bed |
| clamp_fit_coupon_jaw.stl | 1 시험 | 반드시 upper coupon과 함께 출력 |
| camera_mount_fit_coupon.stl | 1 시험 | Plate 접촉면 bed, insert/stand/cable 간섭 시험 |

**좌우 clamp:** mounting wall 방향과 바깥 bolt 위치를 유지하도록 좌우 대칭 STL 한 쌍을 제공한다. 같은 부품을 단순180° 회전해 대신하지 않는다. Jaw는 Y 대칭이라 동일 STL을 Z축180° 회전 배치할 수 있다.

## 먼저 시험할 순서

1. **clamp_fit_coupon.stl + clamp_fit_coupon_jaw.stl**만 싸게 출력. 실제 frame에 상/하가 들어가고 X16 bolt가 frame 바깥으로 지나가며 pad 접촉·jaw 물림이 되는지 확인한다. 안 맞으면 frame parameters를 수정한다.
2. **camera_cradle_HCAM01L.stl**로 body 여유를 확인한다. 동시에 작은 **camera_mount_fit_coupon.stl**로 원래 stand를 접은 상태의 insert/Plate/케이블 간섭과 bolt 규격을 확인한다. 억지 끼움·webcam 분해 금지.
3. 두 fit 계열 시험이 성공한 뒤 나머지를 출력한다. 카메라 무게를 측정하고 수동 저하중·흔들림 시험을 거친다. 미확정 값 때문에 전체를 먼저 출력하는 것은 권장하지 않는다.

Camera Mount Coupon은 실제 slot/strap 위치와 전체56 mm 접촉 영역을 보존하고 hinge만 생략한다. Slot은 hinge축보다24 mm 위에 있어 bolt head 접근 공간을 둔다. Coupon 통과만으로 전체 bracket의 움직임·강성을 보장하지 않는다.

## PETG 초기 설정

- 0.4 mm nozzle, 0.20 mm layer, walls4~5, top/bottom5 이상, infill35~45%.
- Clamp/Upright는 5 walls·45~55%부터 검토. Slicer의 실제 wall/bridge/support를 확인한다. 이 값이 강도 보증은 아니다.
- PLA는 Coupon/fit용 허용, 최종 PETG 우선. 온도·bed·fan은 해당 filament/프린터 profile을 사용한다.
- 작은 horizontal M6 bore와 hinge lug만 local support 필요 여부를 본다. mating land/슬롯 안 support 잔류를 제거한다. 최대 flat part230 mm이므로 실제 bed 여유를 확인한다.

## 조립·조정

1. 전원 차단된 정지 conveyor에서 frame/roller/guard 간섭을 먼저 확인한다. 1 mm pad를 clamp 위아래 평면에 붙이고 M6 두 개로 넓게 물린다. frame을 찌그러뜨리지 않는다.
2. Upright 아래 두 hole(12/36)에 Clamp mounting wall을 붙여 M6 2개씩 잠근다. gusset은 bar/camera쪽을 지지한다.
3. Crossbar 끝의 두 hole(간격24)을 각 Upright slot에 체결한다. 양쪽 lower bolt centre를 같은 눈금에 맞추고 네 bolt를 고정한다. body front reference 높이는 clamp deck 기준120~220 mm; 실제 lens working distance가 아니다.
4. Carriage의 두 M6 socket-head bolt를 Crossbar 수평 slot에 넣고 X ±50 범위에서 lens/belt 중심을 실물로 맞춘 뒤 두 bolt를 잠근다. 앞쪽 washer는 OD12 mm를 사용해 fork 사이 간격14.4 mm를 침범하지 않도록 한다.
5. Plate lug를 fork 사이에 넣고 양옆 1 mm washer를 배치한다. M6 hinge bolt로 -15~+30° 조절 후 잠근다. **0°는 전면이 아래인 TOP-DOWN**. 측면 참조선과 수직 기준을 사용하며 fixed focus의 최적 높이는 실제 대상에서 찾는다.
6. 검증된 금속 camera bolt/washer로 접힌 stand의 인서트를 Plate slot에 연결한다. bolt bottom-out 금지. stand hinge가 잠기지 않거나 흔들리면 보조 strap 또는 cradle를 시험한다. 접힌 stand 간섭과 실제 mic위치는 아직 미검증이다.
7. Cable은 출구에서 바로 꺾지 말고 여유 loop를 두어 Carriage tie slots로 무게를 받친다. 초기 radius25 mm 공간을 목표로 하되 실제 cable의 자연 굽힘을 따른다. 전면/mic/움직이는 belt에 strap/cable이 들어가지 않게 한다.
8. 모든 bolt 끝을 cap으로 덮고, 부드럽게 손으로 흔들어 미끄러짐·PETG 눌림·각도 이동이 없는지 확인한다. 사람이 실제로 조립/프린트한 결과는 아직 없다.

## 후처리

Brim/support 제거부와 burr를 확인한다. 손 접촉부는 deburring tool 또는 **400~600 grit 사포**로 가볍게 마감한다. M6 hole은 필요할 때 reamer/drill로 조금씩 정리한다. 얇게 깎거나 crack이 난 부품은 쓰지 않는다. 손으로 edge를 만져 sharp spot이 없는지 확인한다.

## 재생성·검증

무료 OpenSCAD 2021.01, 독립 `tools/cad/.venv`의 numpy/trimesh만 사용한다. Project `.venv`는 변경하지 않는다. repository root에서:

```powershell
tools/cad/.venv/Scripts/python.exe hardware/camera_mount/FE_L460_HCAM01L_v2/build_validate.py
```

새 PC의 경우 무료 안정 OpenSCAD를 설치하고 `python -m venv tools/cad/.venv` 후 해당 환경의 pip로 이 폴더 `requirements-cad.txt`를 설치한다. `--openscad`로 CLI 경로를 지정할 수 있다. 기본 STL 11개가 모두 필요한 것은 아니며 표의 기본/시험/선택 수량을 따른다.

주요 parameter는 [SCAD source](src/FE_L460_HCAM01L_v2.scad) 상단. 출력 결과는 [stl/](stl/), [검증 JSON](validation/stl_validation.json), [조립 Preview](preview/assembly_preview.png), [Cradle 상세](preview/cradle_preview.png)를 확인한다. 변경 뒤 mesh와 clearance/pose CSG 검사를 모두 다시 실행한다.

Preview: 파랑=출력 frame/지지부, 주황=Plate, 검정=87×37×33 body reference, 반투명 노랑=**미측정 stand gap 예시**, 초록=100 mm belt reference, 빨강=아래 방향. 광학 FOV/실제 lens centre를 모델링한 그림이 아니다.

[뒤쪽 조립 Preview](preview/assembly_rear_preview.png)에서는 Plate slot과 Tilt fork의 연결을 볼 수 있다.

[설계/한계](DESIGN.md) · [확정/미확정 치수](DIMENSIONS.md) · [BOM](BOM.md). Mesh PASS는 watertight 형상 검증이지 프린터별 slicing·실물 fit·강성 PASS가 아니다.
