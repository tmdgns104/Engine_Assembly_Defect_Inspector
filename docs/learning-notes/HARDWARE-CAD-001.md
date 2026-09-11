# HARDWARE-CAD-001 학습 기록

## 무엇을 했는가

Windows에서 무료 OpenSCAD로 FE-L460용 조절식 카메라 거치대 프로토타입을 모델링하고 실제 STL 11개를 만들었다. 별도 CAD Python 환경에서 mesh와 치수·간섭을 검사했다. HCAM01L이 벨트를 아래로 보는 TOP-DOWN이 기본이며 V0 Task/Jetson/Training은 변경하지 않았다. 원본·출력·검증은 `hardware/camera_mount/FE_L460_HCAM01L_v2/`에 있다.

## 왜 했는가

학습용 사진마다 카메라 위치가 바뀌면 물체 변화와 촬영 조건 변화가 섞인다. 위치·높이·각도를 조절한 뒤 금속 볼트로 고정하고 다시 같은 조건을 찾을 수 있는 지지 구조가 필요하다.

## 무엇을 배웠는가

장착 가능한 모양을 그리는 것과 실제 조립 가능한 부품을 만드는 것은 다르다. 좌우 Clamp는 mounting wall 방향을 보존하도록 대칭 STL이 필요하다. 두 볼트가 같은 slot에 있어도 간격을 두면 한 볼트보다 회전을 제한하기 쉽다. M6 마찰 힌지의 washer/gap와 bolt 끝 보호도 출력품 밖의 설계 요소다.

Watertight mesh는 구멍 난 표면이 없이 닫혀 있다는 뜻이다. 양의 체적과 한 개의 연결된 solid까지 확인해도 프린터별 출력 성공·PETG 강도·카메라 실제 fit은 별도 검증이다. CSG로 특정 조절 자세의 교차 체적을 확인하고 Preview도 보지만, 측정하지 않은 stand와 cable은 합격했다고 할 수 없다.

실제로 개별 STL 검사는 통과했어도 낮춘 hinge lug가 Carriage에 겹치는 문제가 조립 검사에서 발견됐다. Pivot/Plate를 함께 앞으로 옮겨 해결했다. 또한 mirror 부품은 치수 변경 후 출력 바닥 위치까지 함께 계산해야 한다. 따라서 기본 치수만 보는 대신 lip 양 끝값을 바꾼 export도 확인한다.

## 확정 치수와 미확정 치수의 차이

87×37×33 mm body와 belt100 mm는 사용자 제공 확정값이다. 반면 frame두께12/lip26/stand gap12는 도구를 만들기 위한 임시 설계값이다. 하부 금속 insert 존재는 사용자가 전한 사진 특징이며 1/4-20 UNC라는 증거는 없다. 실제 thread·깊이·위치·frame profile을 재어야 한다.

## 3D Printer 공차가 왜 필요한가

설계 치수와 출력 치수는 재료·프린터·방향에 따라 다르다. 87 mm body를 정확히87 mm 틈에 넣으려 하면 끼지 않을 수 있어 이 프로토타입은 각 축 총1.2 mm, 중앙 배치 기준 편측0.6 mm 여유를 둔다. 보편적 정답이 아니라 fit 시험 후 보정하는 시작값이다. 헐거움은 압입 대신 pad/strap과 금속 체결로 다룬다.

## Parametric CAD가 왜 유리한가

치수를 코드 상단에 모으면 frame두께·lip·camera여유를 바꿔 재생성할 수 있다. Source와 STL의 hash, export 명령, mesh 결과를 함께 남겨 어떤 치수로 만든 파일인지 추적한다. 치수를 바꾸면 기존 PASS를 그대로 재사용하지 않고 다시 검증한다.

## Fit Coupon을 왜 먼저 출력하는가

작은 Clamp 단면과 Camera Mount Coupon으로 물림/bolt/stand/cable 간섭을 먼저 확인하면 큰 Upright·Crossbar를 버리는 비용이 줄어든다. Coupon 통과는 전체 clamp 강도 통과가 아니므로 전체 조립 뒤에도 수동 하중·흔들림 시험이 필요하다.

## Vision 검사에서 Camera 고정이 왜 중요한가

촬영 방향·초점·시야가 흔들리면 데이터와 검사 결과의 비교가 어려워진다. 기본0°는 수직 상부 촬영이지만 fixed focus의 최적 working distance는 실제 대상과 렌즈 위치로 찾아야 한다. 이번120~220 mm는 clamp datum에 대한 body 전면 reference 범위이며 검증된 초점 거리가 아니다.
