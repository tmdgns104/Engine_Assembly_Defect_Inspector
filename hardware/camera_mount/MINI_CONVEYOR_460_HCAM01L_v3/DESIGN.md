# HARDWARE-CAD-002 설계 계약

## 목적 / 범위
460 mm Mini Conveyor 위 HCAM01L을 작업대에 독립 고정하는 Portal. 기본 방향은 FIXED TOP-DOWN. Windows만 사용하고 V2, Vision 코드/Task, ML 환경, 사용자 사진 원본은 변경하지 않는다. 유료 도구·Jetson·Camera·Training은 사용하지 않는다.

## 요구사항과 구조
- 사용자 도면 전사값 460 / 85 / 118 / 22.7 / 55.5 mm를 사용한다. 110/100/300/60 표기 의미는 추정하지 않는다. 상품 페이지는 이번 도구에서 열리지 않아 직접 검증하지 못했다.
- 36×14 mm 기둥을 좌우 centre ±98에 배치해 안쪽 여유160 mm를 만든다. Base는 바깥으로 확장하여 같은160 mm 통로를 유지한다.
- 사용자 후속 확정: 분할 기둥 대신 **300 mm 일체형 두 개**. 작업대 Z=0, rail 시작 Z=10, rail 상단 Z=310이다. Height holes는 Z77.5..287.5, pitch15, D6.8, 기둥당15개다. Base 체결 구멍2개는 별도다. 초기 modular 검토를 대체하며 lap/joiner는 출력하지 않는다.
- Crossbar는 양쪽 두 볼트를 45 mm 간격으로 사용한다. 사용 lower index는2..12, upper=lower+3이다. Index1은 Base 위 작업 여유를 위해 사용하지 않는다. 지지면은 **작업대 기준150..300 mm, 15 mm step, 11단계**다. 최대300의 기준은 사용자가 확정한 **Deck의 카메라 지지면**이며 전체 제품 높이나 Belt-to-Lens가 아니다. Soft pad를 붙이면 카메라는 pad 두께만큼 높아진다.
- Crossbar 232×61×18 mm, 수평 slide ±30, Deck도 M6 두 개로 고정한다. Rail300×36 flat print는220급 정사각 bed에 들어가지 않으며 약250급 bed의 대각 배치를 검토한다. 실제 slicer/bed/brim 검증은 별도다.
- Deck은 고정 직각 shelf + 두 gusset이다. 88.2×38.2 pocket, contact plane 기준 깊이2.5, Ø30 lens window, 낮은 좌/우/뒤 stop, Velcro slot 두 개를 사용한다. 네 외곽 contact land 외의 pocket 바닥을1 mm 낮추고 선택한1 mm pad로 front face를 지지한다. Lens ring22/offset0은 PHOTO_ESTIMATE이고 돌출4 mm는 PROVISIONAL reference다. Optical FOV는 검증하지 않는다.
- Cable tie point와 위쪽 여유 loop를 둔다. Loop는 간섭 점검용 가정 경로이며 실제 케이블 출구/최소 굽힘 반경은 실측한다.

## 검증 계획
현재 SCAD에서 각 STL을 export하고 mesh topology, bounds, volume, build plane을 검사한다. 실제 mesh의 ray/구멍 원주 정점을 이용해 pitch·직경·slot/attachment·pocket·window·base hole spacing을 측정한다. Assembly에 쓸 mesh를 원래 좌표로 되돌려 portal 통로와 datum을 측정한다.

모든 허용 height index에서 실제 mating hole/bolt alignment를 검사한다. 실제 STL을 조립 좌표로 되돌려11개 높이×slide -30/0/+30의33구성에서 axis-aligned bounds 분리를 검사한다. 이는 conveyor/모터/케이블과 구조, rail/bar, deck/bar, camera와 나머지 구조의 비침투를 보수적으로 증명한다. 지정된 mating face의0 간격만 허용하고 다른 쌍은 양의 간격이 필요하다. Bounds가 겹치는 bolt/구멍은 저/중/고 위치의 CSG로 검사하며 Base/Rail, Body/Deck, Lens/Deck도 별도 CSG를 사용한다. 검사 범위를 줄여 실패를 숨기는 방식이 아니라, 공간 분리로 증명 가능한 쌍을 수치 검사하고 가까운 쌍에 CSG를 적용하는 방식이다.

전체 조립체를 먼저 Boolean union한 후 교차 검사하면 계산이 오래 걸렸다. 동일한 교차 범위를 부품별로 분배하고, 실제 STL bounds로 분리된 쌍을 먼저 확인하도록 바꿨다. 단위/치수/조립 검증 범위는 유지한다. 최종 JSON에 나열된 검사만 최종 완료 근거로 사용한다.

검증기의 기본 기대치는 이번 승인된 치수 profile이다. 새로운 사양으로 치수를 바꿀 때는 실제 요구값과 검사 기대치를 함께 검토한다. Camera lens offset의2/1 mm 변경은 별도 export로 실제 반영을 확인한다. Digital PASS는 실물 fit·강도·진동·creep·광학 PASS가 아니다.

## 확인한 수정과 한계
Side/rear stop의 둥근 끝이 한 선에서만 만나 non-manifold edge2개가 생겼다. Stop 사이에1.2 mm 위치 여유를 두고 source에서 수정하여, 실제 export의 watertight 검사를 다시 통과시켰다. 잘못된 hole 중심을 감지하는지 확인하기 위해 메모리에서 STL 구멍 하나를 X방향1 mm 옮겼을 때 치수 검사가 FAIL을 반환했다. 원본 STL은 바꾸지 않았다.

와셔/부품의 정확한 접촉면은 CSG에서 volume0의 비정상 surface로 출력될 수 있었다. Hardware 검사에서만 washer의 접촉면을0.02 mm 안쪽으로 두며 shaft 지름과 washer의 외경은 줄이지 않는다. Base/Rail도 의도된 벽·바닥 접촉에서 각각0.02 mm 이격한 gauge를 사용한다. 실제 출력 부품은 이동/축소하지 않는다. 이 epsilon은 FDM fit clearance가 아니며, 실제 hole 지름·위치와 접촉 datum은 원본 STL에서 별도로 확인한다. 0.02 mm 이하 접촉면 침투는 이 CSG 검사 단독으로 판별할 수 없다.

## 최종 검증 상태
2026-09-11: **PASS_WITH_WARNINGS / 디지털 Prototype 완료**. 현재 소스에서 8개 STL을 전부 새로 export한 전체 빌드는 405.78초, exit 0 / FINAL PASS였다. Mesh 8/8, 실제 STL 치수, 높이 11단계, 33개 배치의 AABB 분리 924건, 상세 CSG 6/6, lens offset 변경 export 및 LOW/MID/HIGH preview가 통과했다. Source·validator·STL SHA256을 실제 파일과 다시 대조했다.

최종 근거는 [stl_validation.json](validation/stl_validation.json), 검증기 오류 감지 확인은 [validator_selfcheck.json](validation/validator_selfcheck.json), 보호 범위 확인은 [scope_verification.json](validation/scope_verification.json)이다. V2 STL 11개와 보호 파일22개의 hash가 유지됐고 ML 패키지42개 목록도 보존됐다. V0-T05는 TODO이며 이번 CAD에서 시작하지 않았다.

실제 출력·slicing·카메라/나사 fit·강도·진동·PETG creep·focus/FOV는 **UNVERIFIED**다. 다음 단계는 Deck Fit Coupon과 Hole/Base Coupon의 실물 시험이다. 기존 카메라 사진 ZIP/폴더는 사용자 입력으로 보존하고 commit에서 제외한다.
