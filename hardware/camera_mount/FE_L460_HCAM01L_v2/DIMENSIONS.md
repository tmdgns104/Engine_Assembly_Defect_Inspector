# 치수와 확정 수준

단위 mm. source 상단 파라미터가 기본 geometry의 기준이다. 제품 치수와 설계 선택값을 혼용하지 않는다.

| 항목 | 값 | 상태 / 출처 |
|---|---|---|
| HCAM01L body W×H×D | 87×37×33, stand 제외 | CONFIRMED — 사용자 제공 제품 표기 |
| FE-L460 belt width | 100 | CONFIRMED — 사용자 제공 기준 |
| 카메라 접이식 stand, 하부 금속 insert 존재 | 있음 | 사용자 제공 사진 특징 설명; 직접 사진 측정 아님 |
| 해상도 / FPS / 연결 / cable / focus | 1280×720 / 30 FPS / USB2.0 / 200 cm / fixed focus | 사용자 제공 제품 사양, 광학 성능 재검증 아님 |
| Camera body 소재/화소 | ABS 외 / 1 Megapixel | 사용자 제공 표기 |
| Cradle 내부 W×H×D | 88.2×38.2×34.2 | PROVISIONAL, 총 1.2/편측 0.6 clearance |
| Cradle 외형 / wall | 98.2×39.2×48.2 (출력 X×Y×Z), wall5 | PROVISIONAL, body envelope와 별도 |
| Crossbar | 180×48×18 | PROVISIONAL, X×Z×Y |
| Upright | 높이 230, root 폭40, stem 폭32, 두께14 | PROVISIONAL |
| Post centre spacing | 148 | PROVISIONAL, belt width가 frame 폭을 뜻하지 않음 |
| Height slot centre range | 84..208 | PROVISIONAL, 두 볼트 간격24 |
| Lower height bolt range | 84..184 | PROVISIONAL, 기계적 travel100 |
| Top-down body front plane 높이 | clamp upper deck 기준120..220 | PROVISIONAL, belt/object/lens 실제 높이 아님 |
| Horizontal slot | centre -54..54, width6.8, 2개 | PROVISIONAL, 사용 slide ±50 |
| Tilt | -15..+30°, 기본0=TOP-DOWN | PROVISIONAL operating range, 참조선만 있고 click detent 없음 |
| Hinge lug / fork gap | 12 / 14.4 | PROVISIONAL, 안쪽1 mm washer 2개 +0.4 gap |
| M6 through hole | 6.8 | PROVISIONAL FDM 보정 시작값 |
| Camera Plate | leaf 폭104×높이56×두께8; lug 포함 높이58 | PROVISIONAL; 바닥 insert 규격 미확정 |
| Camera mounting slot | 전체56×8, 중심 이동48 | PROVISIONAL; 금속 bolt용 clearance, printed thread 없음 |
| Folded stand gap | 12 | PROVISIONAL 시각화만; 실제 envelope/bolt length 아님 |
| Clamp plate | 48×64×10; 아래 jaw도 동일 | PROVISIONAL |
| Clamp through bolts | local X16, Y±22 | PROVISIONAL; opposing faces pad 공간1씩 |
| FRAME_THICKNESS / FRAME_LIP_DEPTH | 12 / 26 | PROVISIONAL 기본 가정, 실제 FE-L460 치수 아님 |
| Frame adjustment modelling interval | thickness6..20, lip22..40 | PROVISIONAL parameter 범위; lip 변경 시 jaw 폭도 변경. 형상/bolt length 재검증 필요 |
| Clamp coupon | 48×20×10 상판+하판 각각 | PROVISIONAL, 같은 X-Z section 및 bolt X16 |
| Camera mount coupon | 폭104×높이56×두께8 | PROVISIONAL, 같은 full contact face/56×8 slot, hinge만 생략 |
| Camera slot / body reference | hinge 위24, body reference centre 위24 | PROVISIONAL alignment; actual insert offset 별도 실측 |

## REQUIRES_MEASUREMENT — 출력/조립 전

1. **HCAM01L 하부 thread 직경·pitch·유효 깊이**. 1/4-20 UNC로 추정해 억지 체결하지 않는다. 맞는 금속 bolt로 규격을 확인하고 bottom-out을 피한다.
2. **Insert centre**의 body/접힌 stand 기준 X·높이·앞뒤 위치. Plate slot 이동48 mm가 충분한지 확인한다.
3. **FE-L460 side frame** 실제 두께·단면·폭·높이, 좌우 clamping face 간격. Belt100은 이 값을 주지 않는다.
4. **Clamp lip** 안쪽 물림 깊이, 아래 jaw 삽입 공간, bolt station 바깥 여유, 기존 hole/guard/roller/motor와 간섭.
5. 접힌 stand 전체 envelope와 회전 관절 상태, microphone opening, cable 출구·직경·자연 굽힘 반경.
6. Lens centre, body 전면에서 optical centre까지 offset, belt/object 높이, 카메라 실제 질량과 요구 촬영 높이.
7. 프린터 build volume와 보정값. 최대 평면 부품은 230×40 mm, 180×48 mm. **최소 240×190 mm 유효 bed**를 권장(회전 배치·brim 여유 포함); 실제 slicer에서 확인한다.

실측이 parameter 범위를 벗어나면 SCAD를 수정하고 전체 export/검증을 다시 실행한다. 초기 STL을 FE-L460 확정 전용 치수로 사용하지 않는다.
