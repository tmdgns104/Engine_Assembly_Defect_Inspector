# HARDWARE-CAD-001 설계 계약

독립 Hardware CAD 작업. V0 Task/Runtime/Training 상태·코드를 변경하지 않는다. Windows만 사용하며 Jetson·카메라에 접근하지 않는다. Baseline 8a800d1. 도구는 무료 OpenSCAD + 별도 Python numpy/trimesh 환경이다.

## 목적과 설계 선택

Dataset 촬영과 Inspection View의 위치·높이·기울기를 반복 설정하기 위한 **조절 후 볼트로 고정하는 프로토타입**이다. X=벨트 폭, Y=진행 방향, Z=위. 기본 0°는 광학 방향이 아래인 TOP-DOWN이며 실제 렌즈 중심 좌표는 가정하지 않는다.

- 230 mm Upright 두 개와 폭 180 × 높이 48 × 두께 18 mm Crossbar. 두 볼트로 각각 높이와 좌우 위치를 잡아 단일 볼트 회전을 줄인다.
- 높이 슬롯 lower centre 84~184 mm, 상부 볼트는 +24 mm. 카메라 body front reference는 상부 clamp deck 기준 약 120~220 mm. 실제 belt/object 기준 광학 working distance는 frame 높이·lens 위치 실측 전 미확정이다.
- Carriage는 두 수평 슬롯에서 X ±50 mm 이동한다. Tilt는 X축 M6 마찰 힌지, -15~+30°, 0° 수직 참조선. 기계적 클릭 detent나 무한 회전 구조가 아니다.
- 기본 Camera Plate에 56 × 8 mm 긴 슬롯과 양옆 strap 슬롯. 하부 금속 인서트는 **사용자가 제공한 사진 특징 설명**을 근거로 반영했으며 실제 사진 파일/나사 규격/중심/깊이를 직접 측정하지 않았다. 기존 stand를 접고 인서트로 고정하는 A 방식을 우선 시험한다. 1/4-20 UNC로 확정하지 않고 금속 볼트 규격 확인 후 선택한다. 모형의 12 mm stand gap은 시각화용 가정이다.
- 인서트로 체결할 수 없다면 body-only Open Cradle과 strap을 시험한다. Cradle의 2개 M6 구멍(±24, depth17.1)은 Plate 슬롯에 체결할 수 있다. Nut는 fork 바깥으로 놓이도록 ±24를 선택했다. Slot은 hinge 위24 mm로 두어 bolt head/washer가 hinge lug 뒤에 갇히지 않게 했다. 본체와 insert centre 정렬은 미확정 reference이며 실측 후 바꾼다. 접힌 stand 간섭은 미검증이며 억지로 끼우거나 분해하지 않는다.
- Cradle 내부 envelope 88.2 × 38.2 × 34.2 mm: body의 각 치수보다 총 1.2 mm 여유(중앙 배치 시 편측 0.6). PETG 일반 FDM의 시작값이며 특정 프린터의 공차 보증이 아니다. 완전 개방된 전면·상부, 낮은 뒤 지지대와 strap으로 보강한다. 불명확한 렌즈/마이크 위치에 작은 구멍을 만들지 않는다.
- Clamp는 프레임을 위아래로 잡는 두 M6 볼트 방식. 12 mm frame/26 mm lip은 PROVISIONAL. 평평한 접촉면과 1 mm pad 2개를 가정한다. 체결 볼트는 local X=16, 접촉 금속은 X=-22..4를 가정하여 나사를 frame 바깥으로 배치한다. 실제 profile이 이 공간을 침범하면 Coupon 이후 치수를 수정한다.
- Coupon은 full clamp의 X-Z 단면과 X=16 bolt station을 보존하고 Y 길이만 64→20 mm로 줄인 상·하 두 부품이다. 두 볼트 간격이나 전체 frame 고정 강성을 시험하는 부품은 아니다.
- Carriage에 두 넓은 tie slot. camera cable은 실제 출구 방향에 맞춰 여유 loop를 두고 고정부에 묶는다. 굽힘 반경은 미확정: 25 mm 이상 반경 공간을 초기 배치 목표로 두되 실제 cable 사양·유연성을 확인한다.

## 출력과 안전 경계

외부 평면 corner는 R4, Camera Plate R3, 작은 부분 R2.5를 기본으로 하며 좁은 cradle wall은 R2 끝단 + 0.4 mm chamfer다. 일반 외부 edge에는 0.7 mm chamfer, 접촉·mating 면에는 평평한 land를 남긴다. M6 bore 6.8 mm는 PROVISIONAL. 나사산은 출력하지 않는다. 하중 고정은 금속 bolt/washer/nyloc이고 노출 나사 끝에는 상용 cap을 사용한다.

카메라 무게·진동·체결 토크·장기 PETG creep는 측정되지 않았다. Mesh PASS는 강도 인증이나 실물 fit 보증이 아니다. Coupon→Camera fit→수동 저하중 시험을 거쳐야 전체 장착을 진행한다. 이동 벨트/롤러/가드와의 간섭도 실측한다.

## 완료 검증

1. OpenSCAD CLI로 각 실제 STL export, 누락/오류 확인.
2. numpy/trimesh: vertex/face/volume/bounds, positive volume, watertight, winding, 단일 solid, Z=0.
3. Cradle STL의 triangle에 numpy ray를 쏴 내부 폭·바닥·뒤벽을 읽고 mesh bounds로 열린 깊이/벽 높이를 대조한다. 88.2×38.2×34.2 envelope CSG gauge는 겹친 평면의 0두께 export를 피하기 위해 각 경계에서0.02 mm만 안쪽으로 둔다. 이 수치는 fit 여유가 아니라 수치 검사 epsilon이며 실제 내부 치수는 별도로 측정한다.
4. Tilt/slide/height 경계 12개 자세에서 움직이는 Plate/body와 가장 가까운 Carriage를 CSG로 검사한다. 멀리 있는 bar/post는 Y축 분리, clamp는 Z축 분리를 사용한다. 회전된 사각 envelope 꼭짓점의 삼각함수 극값을 -15~+30° 연속 구간에서 구해 보수적 간격을 계산한다. Fallback M6 nut/washer와 fork의 간격도 별도 계산한다. 이 계산을 모두 통과해야 전체 PASS다. 미측정 stand/cable/실제 camera screw는 보증 범위 밖.
5. assembly PNG 시각 검토. reference belt/body/unknown stand envelope는 출력 부품이 아니다.
6. Lip parameter 양 끝값 22/40 mm에서도 왼쪽 Clamp를 실제 export하여 mesh, 폭, bed Z=0을 확인한다. 이는 두 끝값의 회귀 검사이며 모든 parameter 조합의 보증은 아니다.

진행 중 Cradle R2/4 mm wall 조합에서 작은 mesh 연결 결함이 검출되어 wall을5 mm로 변경하고 재export했다. Mesh를 자동 수선해서 결과를 통과시키지 않았다. 동일 평면 gauge 접촉도 처음에는 invalid empty-surface export가 발생해, 위의 명시적 검사 epsilon과 독립 치수 측정을 사용했다.

Camera screw 접근을 확보하려고 hinge를 내렸을 때 lug 뒤쪽과 Carriage backplate가 겹쳤다. Pivot과 Plate를 Y 방향으로 6 mm 함께 이동해 기본 lug/backplate 사이에 2 mm를 확보하고 자세 검사를 재실행했다. 개별 STL이 watertight여도 조립 간섭은 별도로 확인해야 한다. 왼쪽 Clamp의 출력 Z 이동량도 lip parameter에 연동하여 치수 변경 후 bed 아래로 내려가지 않도록 했다.

## 참고 자료

- [OpenSCAD CLI](https://files.openscad.org/documentation/manual/Using_OpenSCAD_in_a_command_line_environment.html): -o/-D로 export/part 선택.
- [Prusa 모델링 안내](https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135): 맞춤 부품에는 실제 프린터/재료를 고려한 여유가 필요하다. 여기의 0.6 mm는 본 프로토타입 선택값이다.
- [Prusa PETG 안내](https://help.prusa3d.com/article/petg_2059): 재료 특성 참고. 실제 profile은 filament/프린터 제조사 설정을 우선한다.
