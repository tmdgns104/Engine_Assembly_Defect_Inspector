# 비출력 부품

금속 나사와 washer로 고정한다. 출력 나사산은 없다. 아래 bolt 길이는 prototype stack 기준이며 실제 washer/nut 두께와 돌출량을 확인한다.

| 용도 | 규격 후보 | 수량 | 근거 |
|---|---|---:|---|
| Base ↔ Upright | M6×40 bolt | 4 | 한쪽2개, printed stack14+10=24 |
| Upright ↔ Crossbar | M6×45 bolt | 4 | 한쪽2개, stack14+18=32 |
| Crossbar ↔ Deck | M6×40 socket-head bolt | 2 | stack18+10=28, 두 개 동시 잠금 |
| 위 bolts | M6 nyloc nut | 10 | 육각 외접 지름12 이하 시작 검토 |
| 위 bolts 양쪽 | M6 washer OD12, 두께1.6 이하 | 20 | 큰 OD18 washer를 임의 대체하지 않음 |
| Bolt 끝 보호 | M6 protective cap | 10 | 실제 돌출 길이 전체를 덮는 상용 cap |
| Base ↔ 작업대 | **실측 후 선정할 screw/bolt** | 8 | Base당4개, 통과 구멍6.5; M6 표준 확정 아님 |
| 작업대 screw | 적합한 washer/head | 8 set | 조립 접근 기준 OD12 이하부터 검토; table 재질에 맞게 선택 |
| Camera retention | 폭10 mm Velcro strap | 1 | 뒤로 이동한 두 slot을 사용; 하부는 lens 뒤25 mm band로 통과 |
| Cable strain relief | 폭2.5 정도 cable tie | 4 | Deck slot2개와 Crossbar/기둥 뒤쪽 routing 고정2곳; 실제 둘레에 맞는 길이 |
| Camera support | 10×6×1 soft rubber/felt pad | 4 | 전면 외곽 land, 실제 접촉 영역 확인 |

기본 M6 bolt10 / nut10 / washer20. 별도 작업대 고정8개는 포함하지 않는다. 기둥은 일체형이라 modular joiner/bolt가 없다. 하부 camera thread도 사용하지 않는다.

나사 끝이 길면 더 짧은 규격이나 적합한 spacer/cap을 사용한다. Bolt/nut를 장착한 채 손에 날카로운 끝이 닿지 않아야 한다. 허용 하중이나 torque는 아직 실험값이 없다. PETG를 압궤시키지 말고 실제 출력품에서 풀림·미끄러짐을 점검한다.

CAD-003에서 Deck이 길어져 무게중심과 굽힘 모멘트가 증가했다. 볼트 수는 같지만 기존 짧은 Deck의 체감 강성을 그대로 기대하지 않는다. 실제 카메라·케이블을 장착해 처짐·풀림·진동·장기 변형을 별도로 확인한다.
