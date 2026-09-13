# 이어폰 첫 baseline — 2026-09-13

**완료:** B03 전체 라벨 승인 기록 →YOLO 변환 →train120/val60 구성 →Windows GPU100epoch 한 번 학습 →모델 재로드·B03 예측 저장.

| 항목 | 실제 결과 |
|---|---|
| 학습 데이터 | B01/B02 120장,240객체 |
| 검증 데이터 | B03 60장,120객체 |
| 승인/변환 보류 | 0장 |
| B04 | 최종 Test 예약,이번 입력0장 |
| 모델 | 원본 yolov8n.pt COCO pretrained →earbud_left/earbud_right/case |
| GPU/framework | RTX5070 Laptop cuda:0 / torch2.11.0+cu128 / Ultralytics8.4.146 |
| 설정 | imgsz640,epochs100,batch16,seed42,AdamW lr0.001,FP32,workers0 |
| 증강 | HSV0.015/0.2/0.2,회전±5°,이동0.05,크기0.1; flip/mosaic/mixup/cutmix/copy_paste0 |
| 학습 호출 시간 | 313.42초(초기화·마지막 검증 포함),epoch loop300.78초 |
| 프로세스/모델 | exit0,100epoch 완료,best/last cuda:0 재로드 PASS |
| B03 Precision | 0.9981466083 |
| B03 Recall | 1.0 |
| B03 mAP50 | 0.995 |
| B03 mAP50-95 | 0.8334960747 |

실제 원본·라벨·승인 입력 해시/클래스/좌표/개수를 검증했다. train/val의 이미지 SHA 및 origin/session/episode/capture 교집합0. 기존978개 보호 파일은 그대로다. 카메라 calibration ID는 유지됐으며 B03 재준비는 기존 사람 선언을 근거로 한다. 이를 물리적 독립성 자동 입증으로 부르지 않는다.

best 모델의 B03 전체60장 예측을 저장했다. confidence0.25, class-aware IoU≥0.5에서TP120/FP0/FN0이므로 대표 오탐/미탐은 이 기준에서 없다. 상대적으로 경계가 덜 맞는0002 R(IoU0.759),0055 L(IoU0.774) 예측 이미지를 확인했다. 높은 검출률이 사각형의 완벽한 일치를 뜻하지 않는다. 위 P/R은 framework 검증 operating point, AP는 confidence 곡선 집계다.

## 보존 파일

- [best.pt](baseline/weights/best.pt), [last.pt](baseline/weights/last.pt)
- [실제 전체 설정](baseline/args.yaml), [epoch별 결과](baseline/results.csv), [학습 곡선](baseline/results.png)
- [학습 결과/입력 해시/GPU 기록](baseline_result.json)
- [B03 예측60장](b03_predictions/), [사진별 정답·예측·매칭](validation_error_analysis.json)
- [실행 로그](../../outputs/earbud_baseline_20260913_v001.log)
- [dataset.yaml](../../outputs/datasets/earbud_case_v0_B01_B03_20260913_v001/dataset.yaml)
- [전체 검증 근거](../../../docs/verification/PROXY-DATASET-TRAIN-001-BASELINE-20260913.json)

B03 검증은 B04 최종 시험 성능이 아니다. 추가 튜닝,엔진 데이터 성능,Jetson 배포,정상/불량 판단·DB 저장까지 완료한 결과가 아니다. 환경 재설치·추가 모델 실험은 하지 않았다. Codex 모델/reasoning/Fast 적용 상태는 독립 확인하지 않았다.
