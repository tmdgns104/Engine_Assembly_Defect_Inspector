# V0-T08 — B03 첫 Baseline 평가·오류 분석

분석·실험안 완료. 기존 best.pt와 저장된 예측만 재사용했으며 학습/추론 재실행0,라벨 변경0,B04 이미지 접근0,Jetson 작업0이다.

## 핵심 결과

- **confidence는 OPPOSITE에서 낮다.** 평균 0.9433으로 BASE 0.9661, DIM 0.9668보다 낮다. 동일 배치·상태·클래스 40쌍을 비교하면 BASE 대비 36쌍, DIM 대비 36쌍에서 낮다. DIM의 일관된 저하는 없다.
- **위치 정확도는 양쪽 이어폰이 비슷하게 약하다.** 평균 IoU는 L 0.87765, R 0.87798, case 0.95799다. L/R 차이는 0.00033에 불과하므로 한쪽을 확실히 열등하다고 부르기 어렵다. 최저 단일 사례는 R이다.
- 조명별 평균 IoU는 BASE 0.9134가 최저, OPPOSITE 0.9216이 최고다. confidence와 IoU의 약점은 다르다.
- 배치는 RIGHT 평균 IoU 0.9135, CENTER 0.9142, CCW 0.9146이 가깝고 LEFT 0.9272가 높다. 회전만의 일관된 악화는 없다. 상태별 평균은 케이스와 이어폰의 구성 비율이 달라 단순한 원인 순위로 해석하면 안 된다.
- **최저 IoU: 0002 R 0.75872**, BASE/CENTER/MISSING_LEFT. 기존 0055 L 0.77350도 재확인했다. **최저 confidence: 0046 R 0.88213**, OPPOSITE/LEFT/MISSING_LEFT. 이 객체의 IoU는 0.8930으로 검출 실패가 아니다.
- TP 120 / FP 0 / FN 0이다. IoU < 0.5와 < 0.75는 모두 0개지만, < 0.85는 13개, < 0.9는 39개다. 높은 mAP50이 엄격한 경계 일치를 뜻하지 않는다.

## 계산 범위와 한계

이미지 60장, 정답 120개, 저장 예측 120개, 동일 클래스의 일대일 매칭 120개를 분석했다. confidence는 conf ≥ 0.25와 NMS IoU 0.7을 거친 저장값이다. 제거된 낮은 점수 후보의 분포나 confidence의 확률 보정 상태는 이번 자료로 알 수 없다.

IoU는 원본 1280×720 좌표의 연속 xyxy 면적에서 재계산했다. 저장된 120개 값과 차이가 1e-12 미만이다. 평균은 객체 수로 가중하며, IoU는 매칭 객체만 집계하고 FN은 별도로 센다. 클래스별 이미지 수는 해당 정답 또는 예측이 있는 사진 수다.

Framework 전체 지표 P 0.9981466 / R 1.0 / mAP50 0.995 / mAP50-95 0.8334961은 기존 best 검증 결과다. 아래 고정 confidence 매칭과 IoU 기준별 생존 수는 그룹 AP가 아니다. 저장 예측으로 framework mAP를 다시 계산하지 않았다. IoU ≥ 0.5 / 0.75 / 0.8 / 0.85 / 0.9 / 0.95의 생존 수는 120 / 120 / 116 / 107 / 81 / 44다. 엄격한 IoU 기준에서 일치 수가 감소하는 것이 위치 정확도의 한계다.

B03는 하나의 origin이며 조명·배치·상태 조합당 사진이 한 장이다. 조명별 클래스 객체 수는 이어폰 각각 10개, 케이스 20개다. 같은 사진의 객체와 촬영 묶음은 독립 반복이 아니다. 통계적 유의성이나 조명의 인과 효과를 주장하지 않는다. train도 하나의 origin이므로 새로운 제품·날짜·설치에 대한 일반화는 미검증이다.

## 조건별 집계

### condition

|그룹|사진|GT객체|평균conf|최소conf|평균IoU|최소IoU|IoU<.5|IoU<.75|FP|FN|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|BASE|20|40|0.9661|0.9468|0.9134|0.7587|0|0|0|0|
|DIM|20|40|0.9668|0.9263|0.9187|0.7961|0|0|0|0|
|OPPOSITE|20|40|0.9433|0.8821|0.9216|0.7735|0|0|0|0|

### placement

|그룹|사진|GT객체|평균conf|최소conf|평균IoU|최소IoU|IoU<.5|IoU<.75|FP|FN|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|CCW|12|24|0.9668|0.9289|0.9146|0.7961|0|0|0|0|
|CENTER|12|24|0.9550|0.9007|0.9142|0.7587|0|0|0|0|
|CW|12|24|0.9573|0.8991|0.9200|0.7735|0|0|0|0|
|LEFT|12|24|0.9588|0.8821|0.9272|0.8626|0|0|0|0|
|RIGHT|12|24|0.9558|0.8951|0.9135|0.7658|0|0|0|0|

### scenario

|그룹|사진|GT객체|평균conf|최소conf|평균IoU|최소IoU|IoU<.5|IoU<.75|FP|FN|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|MISSING_BOTH|15|15|0.9632|0.9357|0.9542|0.9272|0|0|0|0|
|MISSING_LEFT|15|30|0.9564|0.8821|0.9188|0.7587|0|0|0|0|
|MISSING_RIGHT|15|30|0.9558|0.8951|0.9128|0.7735|0|0|0|0|
|NORMAL|15|45|0.9608|0.9260|0.9085|0.8080|0|0|0|0|

### class

|그룹|사진|GT객체|평균conf|최소conf|평균IoU|최소IoU|IoU<.5|IoU<.75|FP|FN|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|earbud_left|30|30|0.9545|0.8951|0.8777|0.7735|0|0|0|0|
|earbud_right|30|30|0.9584|0.8821|0.8780|0.7587|0|0|0|0|
|case|60|60|0.9610|0.9357|0.9580|0.9155|0|0|0|0|

### 클래스×조명 분포

p10/median/p90은객체값의선형분위수다. 전체최소/최대와모든분포는JSON에보존했다.

|클래스/조명|n|평균conf|conf p10/median/p90|평균IoU|IoU p10/median/p90|
|---|---:|---:|---|---:|---|
|earbud_left/BASE|10|0.9645|0.9553/0.9622/0.9765|0.8793|0.8142/0.8805/0.9448|
|earbud_right/BASE|10|0.9672|0.9552/0.9703/0.9769|0.8603|0.7651/0.8835/0.9119|
|case/BASE|20|0.9664|0.9594/0.9682/0.9745|0.9569|0.9448/0.9560/0.9722|
|earbud_left/DIM|10|0.9622|0.9448/0.9627/0.9788|0.8852|0.8505/0.8780/0.9341|
|earbud_right/DIM|10|0.9706|0.9637/0.9683/0.9812|0.8847|0.8486/0.8753/0.9255|
|case/DIM|20|0.9672|0.9574/0.9675/0.9749|0.9524|0.9381/0.9521/0.9642|
|earbud_left/OPPOSITE|10|0.9369|0.9132/0.9380/0.9575|0.8684|0.8238/0.8694/0.9239|
|earbud_right/OPPOSITE|10|0.9375|0.8974/0.9458/0.9672|0.8889|0.8572/0.8916/0.9289|
|case/OPPOSITE|20|0.9495|0.9411/0.9481/0.9592|0.9646|0.9346/0.9692/0.9804|

![조건별 분포](error_review_v001/condition_class_distribution.png)

## IoU 최저10개

좌표는원본px xyxy. 동일한19객체/18사진을7페이지에서원본·GT/pred중첩·기존예측순으로확인했다. 비교카드는보고서전용이며모델입력이아니다.

1. **[0002.png earbud_right](error_review_v001/0002_earbud_right.png)** — BASE / CENTER / MISSING_LEFT; conf 0.971311, IoU 0.758722
   capture_id: `S20260913T105513_310760CD_E0002_20260913T105601091459Z_7cd22c7c723b`. GT `[567.0, 327.0, 680.0, 455.0]` →pred `[567.0, 347.3, 681.68, 467.16]`.

2. **[0010.png earbud_right](error_review_v001/0010_earbud_right.png)** — BASE / RIGHT / MISSING_LEFT; conf 0.969995, IoU 0.765794
   capture_id: `S20260913T105745_CF4D21B9_E0002_20260913T105755153518Z_21325ac1a71b`. GT `[655.0, 327.0, 766.0, 454.0]` →pred `[650.29, 342.99, 766.48, 466.2]`.

3. **[0055.png earbud_left](error_review_v001/0055_earbud_left.png)** — OPPOSITE / CW / MISSING_RIGHT; conf 0.950006, IoU 0.773502
   capture_id: `S20260913T110759_54DCC4CC_E0003_20260913T110819973830Z_6200c4d60a69`. GT `[455.0, 349.0, 549.0, 466.0]` →pred `[455.6, 334.56, 551.55, 453.77]`.

4. **[0039.png earbud_left](error_review_v001/0039_earbud_left.png)** — DIM / CCW / MISSING_RIGHT; conf 0.976941, IoU 0.796139
   capture_id: `S20260913T110359_D06CD21B_E0003_20260913T110418843640Z_bcd375903efc`. GT `[459.0, 389.0, 564.0, 478.0]` →pred `[456.36, 386.32, 564.75, 494.61]`.

5. **[0011.png earbud_left](error_review_v001/0011_earbud_left.png)** — BASE / RIGHT / MISSING_RIGHT; conf 0.956189, IoU 0.803119
   capture_id: `S20260913T105745_CF4D21B9_E0003_20260913T105805730031Z_724004eeec70`. GT `[535.0, 346.0, 625.0, 457.0]` →pred `[533.42, 335.78, 631.89, 452.15]`.

6. **[0053.png earbud_right](error_review_v001/0053_earbud_right.png)** — OPPOSITE / CW / NORMAL; conf 0.936253, IoU 0.807983
   capture_id: `S20260913T110759_54DCC4CC_E0001_20260913T110759701988Z_74adb68529a6`. GT `[565.0, 359.0, 678.0, 459.0]` →pred `[565.63, 361.5, 680.89, 476.17]`.

7. **[0001.png earbud_right](error_review_v001/0001_earbud_right.png)** — BASE / CENTER / NORMAL; conf 0.976823, IoU 0.811104
   capture_id: `S20260913T105513_310760CD_E0001_20260913T105513044578Z_959de408cf35`. GT `[567.0, 310.0, 679.0, 439.0]` →pred `[566.1, 325.18, 678.5, 448.76]`.

8. **[0017.png earbud_left](error_review_v001/0017_earbud_left.png)** — BASE / CCW / NORMAL; conf 0.961955, IoU 0.815449
   capture_id: `S20260913T105922_CC274337_E0001_20260913T105922656046Z_fac263edb201`. GT `[456.0, 366.0, 562.0, 457.0]` →pred `[457.62, 370.95, 564.85, 467.48]`.

9. **[0019.png earbud_left](error_review_v001/0019_earbud_left.png)** — BASE / CCW / MISSING_RIGHT; conf 0.976144, IoU 0.827581
   capture_id: `S20260913T105922_CC274337_E0003_20260913T105942512722Z_f44cce94fcc3`. GT `[455.0, 370.0, 558.0, 467.0]` →pred `[456.38, 372.41, 564.48, 476.35]`.

10. **[0053.png earbud_left](error_review_v001/0053_earbud_left.png)** — OPPOSITE / CW / NORMAL; conf 0.925984, IoU 0.829403
   capture_id: `S20260913T110759_54DCC4CC_E0001_20260913T110759701988Z_74adb68529a6`. GT `[457.0, 337.0, 549.0, 460.0]` →pred `[456.51, 329.9, 551.84, 448.46]`.

## confidence 최저10개

좌표는원본px xyxy. 동일한19객체/18사진을7페이지에서원본·GT/pred중첩·기존예측순으로확인했다. 비교카드는보고서전용이며모델입력이아니다.

1. **[0046.png earbud_right](error_review_v001/0046_earbud_right.png)** — OPPOSITE / LEFT / MISSING_LEFT; conf 0.882130, IoU 0.893015
   capture_id: `S20260913T110615_368E15E3_E0002_20260913T110625304949Z_7acc860dbb30`. GT `[498.0, 353.0, 608.0, 455.0]` →pred `[495.17, 349.48, 610.04, 458.86]`.

2. **[0051.png earbud_left](error_review_v001/0051_earbud_left.png)** — OPPOSITE / RIGHT / MISSING_RIGHT; conf 0.895069, IoU 0.834608
   capture_id: `S20260913T110705_ADC07BB2_E0003_20260913T110724920000Z_683b89297210`. GT `[528.0, 347.0, 623.0, 463.0]` →pred `[524.98, 339.66, 625.14, 455.17]`.

3. **[0054.png earbud_right](error_review_v001/0054_earbud_right.png)** — OPPOSITE / CW / MISSING_LEFT; conf 0.899071, IoU 0.867897
   capture_id: `S20260913T110759_54DCC4CC_E0002_20260913T110809399292Z_0c4c1f57fe7a`. GT `[571.0, 363.0, 684.0, 463.0]` →pred `[571.54, 360.24, 686.47, 472.51]`.

4. **[0042.png earbud_right](error_review_v001/0042_earbud_right.png)** — OPPOSITE / CENTER / MISSING_LEFT; conf 0.900687, IoU 0.899524
   capture_id: `S20260913T110528_2DFA03CF_E0002_20260913T110539721106Z_52b25582f448`. GT `[577.0, 360.0, 690.0, 466.0]` →pred `[572.94, 363.1, 687.52, 468.15]`.

5. **[0043.png earbud_left](error_review_v001/0043_earbud_left.png)** — OPPOSITE / CENTER / MISSING_RIGHT; conf 0.915179, IoU 0.869325
   capture_id: `S20260913T110528_2DFA03CF_E0003_20260913T110549914354Z_5e6815eab2d3`. GT `[453.0, 368.0, 549.0, 473.0]` →pred `[454.04, 362.69, 553.41, 477.01]`.

6. **[0053.png earbud_left](error_review_v001/0053_earbud_left.png)** — OPPOSITE / CW / NORMAL; conf 0.925984, IoU 0.829403
   capture_id: `S20260913T110759_54DCC4CC_E0001_20260913T110759701988Z_74adb68529a6`. GT `[457.0, 337.0, 549.0, 460.0]` →pred `[456.51, 329.9, 551.84, 448.46]`.

7. **[0021.png earbud_left](error_review_v001/0021_earbud_left.png)** — DIM / CENTER / NORMAL; conf 0.926305, IoU 0.856515
   capture_id: `S20260913T110042_D7D56BA3_E0001_20260913T110042335059Z_b35cb8ecc494`. GT `[460.0, 340.0, 551.0, 451.0]` →pred `[458.43, 346.74, 555.48, 454.57]`.

8. **[0047.png earbud_left](error_review_v001/0047_earbud_left.png)** — OPPOSITE / LEFT / MISSING_RIGHT; conf 0.926770, IoU 0.862765
   capture_id: `S20260913T110615_368E15E3_E0003_20260913T110634906044Z_2c4361e644a6`. GT `[383.0, 352.0, 476.0, 456.0]` →pred `[383.74, 345.03, 480.37, 459.33]`.

9. **[0059.png earbud_left](error_review_v001/0059_earbud_left.png)** — OPPOSITE / CCW / MISSING_RIGHT; conf 0.928902, IoU 0.869424
   capture_id: `S20260913T110848_12321588_E0003_20260913T110908486102Z_9a07a4d14dca`. GT `[451.0, 362.0, 546.0, 478.0]` →pred `[450.0, 359.43, 555.49, 476.31]`.

10. **[0044.png case](error_review_v001/0044_case.png)** — OPPOSITE / CENTER / MISSING_BOTH; conf 0.935662, IoU 0.966416
   capture_id: `S20260913T110528_2DFA03CF_E0004_20260913T110559048539Z_5e26efbd8ed0`. GT `[418.0, 253.0, 725.0, 555.0]` →pred `[410.18, 251.3, 724.18, 555.23]`.

## 실제 이미지 관찰과 원인 분류

A 라벨 / B 다양성 / C 크기·해상도 / D 조명·반사 / E 모델 용량 / F 현재 검출 목표에서 문제없음. 아래 분류는 원인 후보이며 확정 진단이 아니다.

- **0002.png earbud_right (A/C/D)**: 예측 상단이 GT보다20.30px 아래,하단도12.16px 아래다. 원본의 R 뒤쪽 검은 영역과 케이스 경계가 약하고 반사된 줄기는 식별된다. GT 상단의 실물 귀속과 하단 여백을 다시 판단할 여지는 있으나 라벨 오류 확정은 아님.
- **0010.png earbud_right (A/C/D)**: 0002와 같은 BASE/MISSING_LEFT에서 위·아래 방향 이동이 반복된다(상단+15.99,하단+12.20px). 오른쪽 배치에서도 검은 경계와 밝은 줄기가 공존한다. 조명만의 원인으로 보기 어렵다. 작은 물체의 경계 정의/모델 localization이 함께 후보.
- **0055.png earbud_left (A/C/D)**: CW 회전한 케이스 안 L 예측이 GT보다 위로 이동했다(상단-14.44,하단-12.23px). 줄기는 보이지만 검은 몸체 하단과 케이스가 겹쳐 보인다. 회전과 경계 차이의 연관 후보이며 회전의 인과 효과는 미입증.
- **0039.png earbud_left (A/C/D)**: DIM/CCW의 밝게 반사된 L 표면이 보인다. 예측 하단이 GT보다16.61px 내려가 케이스 쪽 여백이 커진다. confidence는0.9769로 높다. DIM 자체의 검출 약화로 해석하지 않는다. 아래쪽 보이는 외곽 기준 확인 후보.
- **0011.png earbud_left (A/C)**: BASE/RIGHT L의 밝은 표면과 검은 하단이 대비된다. 예측 상단-10.22px,오른쪽+6.89px로 범위가 바뀐다. 몸체/케이스 경계의 불확실성과 작은 입력 크기 후보.
- **0053.png earbud_right (A/C/D)**: OPPOSITE/CW/NORMAL의 R은 강한 표면 반사와 검은 하단이 보인다. 예측 하단이17.17px 아래로 확장된다. 반사·회전은 관찰됐으나 모델 용량 부족 증거는 없음.
- **0001.png earbud_right (A/C)**: BASE/CENTER/NORMAL R의 예측 상단+15.18px,하단+9.76px. 같은 위치0002처럼 세로 이동이 보이며 양쪽 이어폰은 구별된다. 빈자리 오탐/클래스 혼동은 관찰되지 않았다.
- **0017.png earbud_left (A/C)**: BASE/CCW/NORMAL L의 예측 하단이10.48px 아래다. 두 이어폰이 케이스 안에 있고 L의 표면 반사와 검은 하단이 보인다. 겹침과 줄기/몸체의 작은 경계 후보.
- **0019.png earbud_left (A/C)**: BASE/CCW에서 L만 있어도 예측 오른쪽+6.48px,하단+9.35px 차이가 남는다. 다른 이어폰 존재만으로 설명되는 오류는 아니다.
- **0053.png earbud_left (A/C/D)**: OPPOSITE/CW/NORMAL의 L은 R보다 표면이 어둡게 보인다. 예측 상단-7.10,하단-11.54px,confidence0.9260. 반사 분포/검은 경계와 confidence 저하가 함께 있으나 causal 분리는 안 됨.
- **0046.png earbud_right (D/F)**: OPPOSITE/LEFT R에 밝은 반사가 있고 몸체와 케이스는 검게 보인다. 최저confidence0.8821이나 IoU0.8930으로 위치는 맞는다. confidence 약화 후보,현재 기준의 실질 검출 실패는 아님.
- **0051.png earbud_left (A/C/D)**: OPPOSITE/RIGHT L 표면은 비교적 어둡고 케이스 경계가 약하다. confidence0.8951,IoU0.8346; 위/아래 box 차이가 남는다. 저조도 일반화가 아닌 해당 반사 방향/모양의 후보.
- **0054.png earbud_right (D/F)**: OPPOSITE/CW R의 밝은 반사와 검은 하단이 공존한다. confidence0.8991이나 IoU0.8679이며 줄기는 검출 box 안에 있다. 밝기 단순 증가가 해결한다는 근거는 없음.
- **0042.png earbud_right (D/F)**: OPPOSITE/CENTER R confidence0.9007,IoU0.8995. 밝은 표면 반사와 어두운 하단이 보이지만 GT/예측은 대체로 겹친다. confidence와 localization을 분리해 해석.
- **0043.png earbud_left (C/D/F)**: OPPOSITE/CENTER의 L은 검은 몸체 경계가 약하게 보이나 위치/클래스를 찾았다(conf0.9152,IoU0.8693). 추가 전처리 필요를 입증한 실패는 아님.
- **0021.png earbud_left (D/F)**: DIM/CENTER/NORMAL L에 밝은 반사와 어두운 몸체가 함께 있다. 낮은confidence 목록에서 유일한 DIM 사례지만0.9263으로 검출된다. DIM 전체 악화 주장을 지지하지 않음.
- **0047.png earbud_left (A/C/D)**: OPPOSITE/LEFT L confidence0.9268,IoU0.8628. 어두운 하단과 케이스가 맞닿고 GT/예측 가장자리에 작은 차이가 있다. 형상/광학 조건의 후보; 라벨 수정 결정은 보류.
- **0059.png earbud_left (C/D/F)**: OPPOSITE/CCW L confidence0.9289,IoU0.8694. 오른쪽 box 경계 차이가 보이나 부품 전체 검출은 유지된다. 회전만의 성능 저하로 일반화할 수 없음.
- **0044.png case (D/F)**: OPPOSITE/CENTER/MISSING_BOTH 케이스의 confidence0.9357이지만 IoU0.9664로 열린 뚜껑/몸체 외곽은 잘 일치한다. 명확한 box 문제나 빈자리 이어폰 오탐은 없음.

A: 검은이어폰몸체와케이스가맞닿는상·하단은정답경계자체의불확실성이있다. 승인본을유지하며틀린라벨로자동지정하지않는다. B: 다양성한계는있으나특정오차원인이라고확정하지않는다. C:640입력에서L너비44~53px,R51.5~58px,case148~168px. 작은부품에원본10~20px의세로차이가상대적으로큰영향을준다. D: 원본의밝은반사/어두운겹침은보이나반사포화·센서노이즈·blur정도는별도측정하지않았다. E: 모델용량비교없음. F: 현재존재검출조건에는FP/FN0이지만경계정밀도합격기준은아직없다.

## 전처리 판단

| 후보 | 현재 필요 근거 | 기대 효과 | 부작용 | 향후 Runtime 일치 |
|---|---|---|---|---|
| ROI Crop | 첫 실험 가치가 높음. 필수라고 입증된 것은 아님 | 같은 640 입력에서 작은 부품을 더 크게 표현 | 범위 밖 부품 잘림, 카메라 이동 민감도, 문맥 손실 | 동일 고정 ROI·resize·padding 및 좌표 역변환 필요 |
| imgsz 768 | 두 번째 후보. 640 입력에서 이어폰 너비가 약 44~58px | 전체 프레임 유지, 선형 크기 1.2배 | 입력 픽셀 1.44배, 시간·VRAM 증가 | 채택한 입력 shape와 letterbox 정책 일치, export와 Jetson 비용 재검증 |
| CLAHE | 현재 우선순위 낮음. DIM 일관 악화와 FP/FN 없음 | 국소 명암 대비 개선 가능 | 노이즈·반사·질감 변형, 매개변수 의존 | 동일 색공간·clipLimit·tileGridSize·처리 순서 |
| Gamma | 현재 필요 근거 부족. OPPOSITE가 단순히 전체적으로 어두운 문제인지 미확정 | 어두운 중간톤의 밝기 조절 | 광도 분포 변경, 가려진 외곽 복원 불가 | 동일 gamma/LUT·색공간·순서 |
| sharpening | 현재 필요 근거 부족 | 경계 강조 가능 | halo와 노이즈·반사 강조, 없는 디테일 복원 불가 | 동일 kernel·강도·border 정책 |
| denoise | 노이즈가 오차 원인이라는 분리 근거 없음 | 확인된 노이즈가 있을 때 변동 완화 | 작은 줄기·경계 소실, 추가 처리 시간 | 동일 알고리즘·강도·순서 |

[OpenCV CLAHE 설명](https://docs.opencv.org/4.13.0/d5/daf/tutorial_py_histogram_equalization.html)은 국소 대비와 노이즈 증폭 제한을 설명한다. [Gamma 설명](https://docs.opencv.org/4.13.0/d3/dc1/tutorial_basic_linear_transform.html)은 비선형 광도 변환을 설명한다. 이러한 기능 설명이 현재 데이터의 성능 향상을 입증하지는 않는다. sharpening과 denoise의 효과도 이번 측정 결과가 아닌 예상이다.

## 다음 후보 — 신규 실험은 최대 2개, 아직 미실행

### A. Baseline 유지

- 변경 변수: 없음. 기존 결과만 비교 기준으로 사용한다.
- 유지: 모든 기존 데이터, 라벨, 모델, 학습 설정.
- 지표: 기존 전체·조건·클래스 IoU/confidence, AP, FP/FN.
- 추가 GPU 비용: 학습 0회.
- 결정: 현재 기준 모델을 보존하며 재실행하지 않는다.

### B. 고정 ROI Crop만 변경 — 추천 1순위

- 변경 변수 하나: 공간 전처리. train 라벨의 전체 외곽에 원본 48px 여유를 더한 고정 ROI **[287,168,863,628]**, 크기 **576×460**을 적용한다.
- 유지: imgsz 640, 동일 COCO pretrained YOLOv8n, 100 epochs, batch 16, seed 42, AdamW, FP32, 증강 수치, train 120장/val 60장과 원래 촬영 그룹. 사각형의 의미는 유지하고 crop에 따른 좌표만 기하적으로 변환한다.
- 비교 지표: 동일 B03 60장/120객체에서 원본 좌표 IoU 평균·p10·최저 10개, mAP50-95/AP75, FP/FN, 조건별 confidence. 전처리를 포함한 latency와 VRAM도 측정한다.
- 예상 GPU 비용: 훈련의 640×640 입력은 유지되므로 모델 연산량은 대체로 기준 수준이다. 실제 시간은 미측정이다. 직사각 추론은 약 512×640으로 기존 384×640 대비 입력 픽셀이 약 1.33배가 될 수 있다.
- 지켜야 할 조건: B03 정답별로 crop하지 않는다. 잘린 객체를 제외해 분모를 줄이지 않는다. ROI와 광도 전처리 또는 imgsz 변경을 합치지 않는다.

ROI는 train 라벨만으로 먼저 정했다. 이후 B03의 범위 포함 여부만 감사했으며 120개 객체가 모두 안에 있었다. B03 오류에 맞춰 ROI를 조정하지 않았다. 좌표는 실수 라벨의 floor/ceil 때문에 약 1px 보수적일 수 있다. 같은 640 입력에서 선형 크기가 약 2.22배가 될 수 있지만 원본에 없는 디테일을 복원하는 것은 아니다.

고정 카메라·검사 영역을 쓰는 엔진 구조에서도 제품별 ROI 설정과 좌표 역변환 절차의 재사용 가치가 높다. **엔진의 실제 ROI 좌표는 엔진 촬영 범위로 별도 결정해야 한다.** 이번 이어폰 좌표를 그대로 가져가면 안 된다.

### C. 전체 프레임 imgsz 768만 변경

- 변경 변수 하나: imgsz 640 → 768.
- 유지: 전체 프레임, ROI와 광도 전처리 없음. 동일 초기 checkpoint·모델·100 epochs·batch 16·seed 42·optimizer·FP32·증강·train 120장/val 60장.
- 비교 지표: B와 같은 원본 좌표 지표, 조건별 표, latency, VRAM.
- 예상 GPU 비용: 훈련 입력 픽셀은 1.44배다. 시간과 VRAM 증가는 예상되지만 실측 전이다. 메모리가 부족하면 batch를 자동으로 바꾸지 않고 별도 실험 변경으로 기록한다.
- 결정: 두 번째 후보로만 남긴다. B와 합치지 않으며 B의 학습 결과에서 이어 학습하지 않는다.

채택 기준 제안: FP/FN 0 유지, 이어폰 IoU 평균·하위 10%와 mAP50-95 개선, 특정 조명에서 뚜렷한 악화 없음, 실측 latency/VRAM 예산 충족. 개선이 없거나 잘림·속도 손해가 크면 REJECT하고 baseline을 유지한다. 작은 차이는 한 seed·한 origin의 관측으로만 기록한다. 위치 정밀도와 Runtime 비용의 정식 합격 기준은 아직 확정하지 않았다.

[Ultralytics Predict 문서](https://docs.ultralytics.com/modes/predict/)의 직사각 padding 정책 때문에 imgsz 640이 항상 실제 추론 텐서 640×640을 뜻하지는 않는다. baseline 실행 로그에서는 384×640이었다. 비교할 때 실제 shape와 전처리 시간을 함께 기록해야 한다. 위 GPU 비용은 픽셀 비율에 따른 예상이며 벤치마크 결과가 아니다.

## 파일과 검증

- [전체 계산 JSON](error_analysis_detailed.json): 120개 객체, 그룹 통계, 최저 10개 목록, 원인 후보, 실험안, 입력 해시.
- [보조 계산](error_analysis_supplement.json): 조건 쌍 confidence, 입력 크기, train만으로 정한 ROI.
- [대표 원본 사본](error_review_v001/originals/) · [기존 예측 사본](error_review_v001/predictions/) · [검토 이미지](error_review_v001/).
- 실행: `python -B -X utf8 -m training.scripts.analyze_saved_validation --experiment training/experiments/earbud_case_v0_20260913_v001 --split training/outputs/datasets/earbud_case_v0_B01_B03_20260913_v001/split_manifest.json`.
- 원본·기존 예측·모델·이전 결과 해시를 보존했다. IoU 120개 재계산, 그룹 수·가중 평균 대조 및 새 집중 테스트 4개를 통과했다. 최종 검증: `docs/verification/V0-T08-ERROR-ANALYSIS-20260913.json`.
- 이번 분석 완료는 과거 T08 문서의 실제 튜닝 실행 완료를 뜻하지 않는다. 실측 KEEP/REJECT 결정은 대기 중이다. B04와 Jetson은 다루지 않았다. Codex 모델/reasoning/Fast 적용 상태는 확인하지 못했다.
