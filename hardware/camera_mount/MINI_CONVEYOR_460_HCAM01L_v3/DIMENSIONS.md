# 치수와 근거

단위 mm. **최신 사용자 수정은 초기 modular 요구보다 우선한다:** 기둥300 mm 일체형2개, 최대 높이는 작업대→Deck 지지면300 mm. 실제 광학 거리와 전체 높이는 별개다.

| 상태 | 항목 | 값 / 의미 |
|---|---|---|
| CONFIRMED_USER_DRAWING | Conveyor length / belt / outer width | 460 / 85 / 118, 사용자 도면 전사값 |
| CONFIRMED_USER_DRAWING | Side height / motor max height | 22.7 / 55.5, table-to-belt 값은 아님 |
| CONFIRMED_USER_SPEC | HCAM01L 본체 | 87×37×33, stand 제외 |
| CONFIRMED_USER_SPEC | Camera 표기 | 1280×720, 30 FPS, 1MP, USB2.0, cable200 cm, fixed focus, ABS 외 |
| CONFIRMED_USER_REQUIREMENT | 기둥 / 최대 지지면 높이 | 300 mm 부품2개 / 작업대 기준300 mm |
| PHOTO_ESTIMATE | Lens ring 외경 | 약20~22, reference22 |
| PHOTO_ESTIMATE | Lens centre | body centre 근처; 초기 offset X0/Y0, source 상단에서 변경 |
| PHOTO_OBSERVATION | 사진에서 확인 | 돌출 렌즈·금속색 ring·foldable stand·하부 금속 insert; thread 규격은 미확인 |
| PROVISIONAL_DESIGN | Rail W×L×T | 36×300×14, 좌우 동일 STL |
| PROVISIONAL_DESIGN | Height holes | D6.8 / pitch15 / 기둥당15개, table Z77.5..287.5 |
| PROVISIONAL_DESIGN | Hole index | 아래부터1..15; 사용 lower2..12 / upper=lower+3 |
| PROVISIONAL_DESIGN | Crossbar 체결 | 한쪽2개, 수직 간격45, 양쪽 동일 index |
| PROVISIONAL_DESIGN | Rail bottom / top | table Z10 / Z310; Base 두께10 포함 |
| PROVISIONAL_DESIGN | Base rail 체결 holes | table Z30,60; height15개에 포함하지 않음 |
| PROVISIONAL_DESIGN | Deck 지지면 | table150..300, step15, 11단계; pad 제외 |
| PROVISIONAL_DESIGN | Crossbar bottom | table84.5..234.5; 선택 lower bolt보다8 낮음 |
| PROVISIONAL_DESIGN | Deck outer top / stop top | 지지면+2.5 / 지지면+4; 최대302.5 / 304 |
| PROVISIONAL_DESIGN | Camera body 전면 | 지지면+pad1; 최대301, body rear 최대334; stand는 별도 |
| PROVISIONAL_DESIGN | Crossbar | X232×Z61×Y18 |
| PROVISIONAL_DESIGN | Portal inside / post centres | 160 / X±98; body118과 편측21 여유 |
| PROVISIONAL_DESIGN | Base footprint | 80×70×10, outboard 배치; tower 포함높이72 |
| PROVISIONAL_DESIGN | Table screw holes | 4개 per Base, D6.5, X/Y 간격50/48, 입구 chamfer; 나사 규격 미확정 |
| PROVISIONAL_DESIGN | Camera Deck pocket | 88.2×38.2; 지지 land 기준 깊이2.5; 주변 relief1 |
| PROVISIONAL_DESIGN | Camera 접촉 land | 10×6 네 곳, centre X±35/Y±12; optional pad1 |
| PROVISIONAL_DESIGN | Lens window | Deck top 생성 기준D30 → bottom 약49.53; top 실제 개구는 pocket88.2×38.2 |
| PROVISIONAL_DESIGN_ENVELOPE | Camera HFOV / VFOV | 90° / 70°, 공식 사양 아님; 실제 시야보다 넓다는 보장 없음 |
| PROVISIONAL_DESIGN_ENVELOPE | Optical pupil / XY 불확실성 | Deck 지지면+3 / 편측2 |
| PROVISIONAL_DESIGN_ENVELOPE | Optical clearance | FOV 측면 법선 방향5; 뒤쪽 동공 평면 너머에는 적용하지 않음 |
| PROVISIONAL_DESIGN_ENVELOPE | Optical target plane | table Z0; belt reference Z22.7을 포함 |
| PROVISIONAL_DESIGN | Portal→Camera / Conveyor 중심 | Y255, 이전Y62에서193 이동; Camera가 Conveyor 중앙 위에 위치 |
| PROVISIONAL_DESIGN | Extended Deck 출력 크기 | 267×69.5×112; 옆면 바닥, 지지대 필요 |
| PROVISIONAL_DESIGN | Inspection zone | Belt 위85×120; 엔진 크기 가정 아님 |
| PROVISIONAL_DESIGN | Velcro | 폭10 reference, 하부는 lens 뒤쪽25 mm band로 통과 |
| PROVISIONAL_DESIGN | Lens protrusion reference | 4, 실제 돌출 길이 아님 |
| PROVISIONAL_DESIGN | Slide / Tilt | ±30, M6 두 개 잠금 / fixed0° TOP-DOWN |
| PROVISIONAL_DESIGN | Conveyor reference datum | bottom table Z0을 그림에만 사용; 실제 belt 높이 미확정 |
| PROVISIONAL_DESIGN | Motor reference 길이 | 70의 임시 상자; 도면의 의미 불명확한60을 사용한 것이 아님 |

## REQUIRES_MEASUREMENT
1. Conveyor belt top의 table 기준 높이, 실제 outer width, 받침/발 구조.
2. Motor의 실제 길이·폭·높이와 전선/guard/조절부를 포함한 간섭 영역.
3. Lens ring 실제 외경, 돌출 길이, body 기준 중심 X/Y, optical centre.
4. 전면 contact land가 닿는 실제 flat area, mic 위치, 접힌 stand와 strap의 간섭.
5. 작업대 재질·두께·나사 규격·유효 체결 깊이·washer/head 크기.
6. 검사할 물체 최대 높이, 요구 focus/FOV/pixel coverage, camera 실제 무게.
7. Printer bed 유효 범위, brim/support, hole 보정, PETG 재료/설정.
8. 실제 HCAM01L HFOV/VFOV/왜곡, optical pupil 위치, 사용 해상도와 crop 설정. 큰 가설 FOV로 나온 coverage가 실제 coverage를 보장하지 않는다.

`Belt-to-Lens = table-to-contact + pad - optical offset - table-to-belt`이며 실제 값은 **DERIVED AFTER PHYSICAL MEASUREMENT**다. CAD의 ring 끝은 optical centre가 아니다. 도면의110/100/300/60은 의미를 부여하지 않았다.

상품 출처: https://smartstore.naver.com/trendpickcom/products/13492307077 (도구 열기 실패; 숫자는 사용자 제공 기준). 로컬 `카메라규격` 사진을 확인했지만 원근·손·자 위치 때문에 정밀 metrology로 사용하지 않았다. 원본 ZIP/사진은 기존 untracked 상태를 유지하고 이 commit에 포함하지 않는다.
