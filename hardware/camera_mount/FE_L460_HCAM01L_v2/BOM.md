# BOM — CAD 체결 위치 기준

기본 Plate 방식. 다음 길이는 표준 washer/nyloc의 실제 두께와 frame 실측에 따라 다시 고른다. 나사산을 PETG에 직접 출력하지 않는다.

| 용도 | 금속 부품 | 수량 | 설계 stack / 선정 근거 |
|---|---|---:|---|
| Clamp 상·하 jaw | M6×50 bolt, frame 두께12 기준 | 4 | 한 clamp당2. print10+gap14+print10=34; washer/nut 추가. frame6..20 변경 시 대략45..60 길이를 실제 선정 |
| Upright→Clamp body | M6×40 bolt | 4 | 2 per side, 14+10=24 stack |
| Crossbar→Upright | M6×45 bolt | 4 | 2 per side, 18+14=32 stack |
| Carriage→Crossbar | M6×40 socket-head bolt | 2 | 10+18=28 stack; fork 사이 head는 지름10 이하, 육각렌치로 접근 |
| Tilt hinge | M6×45 bolt | 1 | cheeks16+lug12+inner washers2≈30 stack |
| 위 15 bolt용 | M6 nyloc nut | 15 | 반복 조절 시 마모 확인 |
| 위 15 bolt 양면 | M6 flat washer | 30 | 대략 OD12~18, 실제 mating 여유 확인 |
| Hinge lug 양옆 | M6 flat washer, 두께1 mm | 2 | gap14.4-lug12=2.4 공간; 남는0.4만 가볍게 조임 |
| 나사 끝 보호 | M6용 상용 protective cap | 15 | 선택 bolt의 돌출 길이까지 덮는 제품; 부딪히는 날카로운 끝 방치 금지 |
| Camera bottom insert | **실측 규격 금속 bolt + 넓은 washer** | 1 set | thread/pitch/길이 모두 미확정. Slot8, washer OD18 이상 시작 검토. 인서트 바닥에 닿지 않는 유효 길이 |
| 보조 camera retention | 폭10~15 mm Velcro strap 또는 cable tie | 2 | 전면/lens/mic 피해 실제 routing 확인 |
| Cable strain relief | 폭2.5 mm 내외 cable tie | 2 | Carriage 3.2 mm slot에 통과, cable을 누르지 않음 |
| Frame 보호 pad | 1 mm rubber, 약24×56 mm | 4 | clamp당 upper/lower1개씩. 실제 접촉면에 맞춰 절단 |

**기본 M6 bolt 합계15, nut15, washer32.** 선택한 bolt 끝이 길면 더 짧은 규격/추가 metal spacer/충분한 cap으로 보호한다. 정해진 조임 토크나 허용 하중은 시험하지 않았다. PETG를 찌그러뜨리는 과도한 조임 대신 넓은 washer와 실제 하중 점검을 사용한다.

Carriage 앞쪽 두 washer는 **OD12 mm**를 사용한다. 특히 위쪽은 fork 안쪽 간격14.4 mm 안에 들어가야 하므로 OD18을 쓰지 않는다. 이 washer도 위 합계30개에 포함된다. 실제 렌치와 선택한 hardware가 들어가는지 조립 전에 확인한다.

## 시험/선택 부품

- Clamp Coupon 상·하: M6 bolt/nut/washer 한 세트를 위 부품에서 임시 사용한다. Full clamp의 Y방향 두 bolt 간격/비틀림 강성은 coupon으로 검증되지 않는다.
- Camera Mount Coupon: 실제 camera thread를 확인한 한 세트를 임시 사용한다. 원래 stand를 분해하지 않는다.
- Cradle fallback을 Plate에 붙일 때: M6×25 button-head bolt **2개**, nyloc2, 외부washer2 추가. Hole X=±24, diameter12/depth4 recess에 head가 완전히 들어가는지 확인한다. 뒤쪽 nut 외접반경6 이하, washer두께1.6 이하/OD18 이하를 기준으로 fork와 간격을 검토했다. Camera body가 금속 head 위에 직접 눌리지 않도록 한다.
- 낙하 방지를 위한 별도 느슨한 safety tether 1개 권장. 설치 전 배치·움직이는 conveyor 간섭을 확인한다.

설계 재료: PETG. pad/strap/metal fastener는 출력 STL에 포함되지 않는다. 미측정 thread를 재현한 adapter나 금속 나사 mesh는 없다.
