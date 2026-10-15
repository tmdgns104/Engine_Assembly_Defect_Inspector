# TASK-022 — 실제 영상의 AI·조립 전처리 진단 및 수정 보고

## 2026-10-15 형상 매칭·LoFTR 및 같은 검사 상대 LK 비교

**비교 실행 완료 / 운영 정렬 미해결 / B·C·LK 미배포.** 출발 HEAD `28e24455906b05601de890e5e495b1bfe5618a76`, 실제 운영 소스 `e20ebbdcd825a19b28922bb1fef2bac53d46e57c`, Release `engine-integrated-a8d842b879cd14ea`다. 사용자가 설명한 수동 설치의 거리·높이·각도 차이는 현장 조건으로 유지했다. 카메라 재설치, 모델·판정 임계값, PLC 변경을 해결 전제로 삼지 않았다. 기존 미커밋 변경은 보존했다.

### 입력·구현·좌표 계약

동일 원본 **40장**은 현장 9개 촬영 묶음의 27장과 허용 TRAIN 정상·결품·오조립 13장이다. 기존 정상/조명/실제 배기 결품/복원/이전 PLC와 추가 정상·SIDEWAYS·복원, 최근 PLC 세 장을 포함한다. raw/pixel SHA·frame ID·epoch·reference/profile SHA를 연결했다. 촬영 묶음으로 개발/평가를 구분했지만 모두 이미 본 자료이며 독립 holdout이 아니다. E04는 열람하지 않았다.

- A: 실제 동결 `StaticShadowModels` 경로. 보존된 A 기록을 재사용하고 미기록 정지 대조 9장만 같은 모델로 추가 재생했다.
- B: 공개 OpenCV 연산으로 한정된 방향성 chamfer를 구현했다. 마스크 이전 Canny, 고정 물리 영역별 동일 가중치, 6방향 에지, 1/4 해상도·10도 간격·scale 0.7–1.2 탐색 후 상위 16개 제한 보정이다. 범용 산업 matcher나 OpenCV Guil 자체를 구현했다고 주장하지 않는다. [OpenCV 형상 검출 문서](https://docs.opencv.org/4.13.0/da/ddc/tutorial_generalized_hough_ballard_guil.html)를 참고했다.
- C: [공식 LoFTR 저장소](https://github.com/zju3dv/LoFTR)가 안내하는 Kornia **0.8.2**, `kornia-rs 0.1.9`, `indoor_new` dual-softmax/ScanNet 가중치를 실제 실행했다. [가중치 출처](https://cmp.felk.cvut.cz/~mishkdmy/models/loftr_indoor_ds_new.ckpt), SHA `be9ff88b323ec27889114719f668ae41aff7034b56a4c4acbd46b8b180b87ed3`, 46,355,053B. Apache-2.0 코드, FP32/CUDA, `temp_bug_fix=True`, 나머지 모델 설정 유지. 노트북 별도 환경만 준비했고 Jetson 패키지는 변경하지 않았다.
- C 입력: grayscale/255, 0.5 축소·8배수 padding, 사전 고정한 전체 영상 0/90/180/270도 후보. 정확한 회전 역변환·축척 복원 후 원본 픽셀로 평가한다. 기준/현재 각각 8px cell별 중복을 줄이고 몸체 지지·잔차로 선택한다. 분류 점수는 선택에 사용하지 않는다. 기준 몸체 밖을 평탄화한 ablation은 별도로 보존했으며 좋은 결과만 혼합하지 않았다.

고정 몸체판·베이스·마운트 림·사용자가 고정이라고 확인한 양옆 금색 캡을 진단 마스크로 표시했다. 중앙 회전축·피스톤·검사 부품·구멍 안 배경은 제외했다. 금색 캡을 운영 특징점에 추가한 것은 아니다. LoFTR 대응의 끝점이 몸체 안에 있어도 수용 영역의 부품/배경 영향이 제거됐다고 주장하지 않는다.

### A/B/C 결과 — 후보 수와 정확도를 구분

| 경로 | 현장 27장 내부 상태 | TRAIN 13장 | 최근 PLC 1508/1509/1510의 독립 고정부 최대 오차 |
| --- | --- | --- | --- |
| A 기존 운영 | 기존 VALID 2, 거부 25 | 기존 VALID 12, 거부 1 | 1·2번 거부. 기존 VALID 3번도 새 보류점 최대 **20.46px** |
| B 방향성 형상 | 후보 17, 모호 10 | 후보 13; 각각 새 crop 분류의 전체 상태가 해당 TRAIN 정답과 일치 | **115.44 / 115.06 / 259.20px**, 세 장 모호 |
| C LoFTR / T0001 | 후보 22, 지지 부족 5 | 후보 13; 각각 새 crop 분류의 전체 상태가 해당 TRAIN 정답과 일치 | **20.57 / 22.97 / 23.84px** |
| C / 기준 몸체만 입력 | 현장 후보 0, 지지 부족 27 | 후보 4, 지지 부족 9 | 최근 세 장 지지 부족 |

**`BODY_GEOMETRY_CANDIDATE`는 VALID가 아니다.** 최근 PLC의 여덟 수동 보류점은 fit에 사용하지 않았으며 주석 불확실성은 약 ±3px다. 진단의 최대 5px 비교선은 운영 차단 조건으로 추가하지 않았다. 나머지 현장 24장은 전체 기하를 정밀 인증하지 않았으므로 정상 정렬 수로 계산하지 않는다. 이번에 운영 적용 대상으로 자격을 확인한 현장 정렬은 0이며, 이것을 27장 모두 같은 원인으로 실패했다는 뜻으로 해석하지 않는다.

자기 자신/이동/25도/90도/-90도+축소/160도+축소의 알려진 변환에서 B crop 모서리 최대 오차는 0–0.60px, C는 0.28–8.44px였다. 정확한 quarter-turn 픽셀/역행렬 단위 검증과 별개로 matcher의 잔차가 남는다. 좌우 반전은 **B와 C 모두 내부 후보를 잘못 생성**했다. 기존 방향 anchor NCC를 별도 대조하면 B 반전은 0.184로 거부되지만 C는 0.400으로 기존 0.35 조건도 넘었다. 따라서 C를 운영 validator 없이 채택할 수 없다. 빈 영상은 거부했다. 정상도 전부 거부하는 몸체 제한 ablation을 개선으로 세지 않는다.

C는 기존보다 대응을 만들었지만 최근 세 장의 RANSAC 지지가 V8 몸체판·옆면에 집중됐다. 같은 대응의 similarity, affine, homography 및 영역 균등 fit을 분리 확인해도 독립점 최대 오차 약 19–24px가 남았다. 고정부 밖을 바꾼 합성 입력도 결과에 영향을 주므로 배경/부품 독립성이 입증되지 않았다. **촬영 높이·각도에 따른 비평면 투영 차이는 가능한 원인이지만, 오대응과의 기여도를 정밀 분리하지 못했다.** 더 많은 특징점이나 자유도만으로 해결됐다고 결론내리지 않는다.

### 현재 시야 기준과 상대 LK — 별도 통제 실험

같은 LoFTR 설정에서 reference만 최근 3번 프레임의 기존 A 자세로 만든 현재 시야 사진으로 바꿨다. 독립 고정부 오차가 **3.41/3.77/5.44px**로 작아졌다. 그러나 기준 생성과 비교가 같은 촬영 묶음이며, A 자세를 통해 학습 crop을 가져온 관계는 독립 인증되지 않았다. 반전 오수락도 남았다. 입력 해상도만 원본으로 올린 추가 제한 비교는 **6.83/6.04/6.78px**, warm 약 1.19초로 개선되지 않아 더 조정하지 않았다. 기준 효과와 matcher 효과를 섞어 성공으로 세지 않는다.

사용자 요청에 따라 B/C 다음에 **같은 검사·epoch의 3번→1·2번 상대 LK**만 평가했다. 실제 고정 표면 수동 주석을 기준으로 LK window 전체가 들어가도록 erosion하고, 물리 영역별 ROI에서 9×9/no-pyramid 정·역방향 추적을 실행했다. 절반의 점만 fit, 나머지는 보류했다. 한 제품의 작은 움직임을 보는 진단이며 매 프레임 수동 정답을 운영에 제공하는 방식이 아니다.

- 1번 보류 오차 median 0.201 / p95 0.655 / max **2.37px**; 2번 median 0.298 / p95 1.352 / max **8.00px**. 두 프레임 모두 진단의 최대 1px 상대 검사선을 만족하지 못했다. 이 기준 역시 운영 정책으로 배포하지 않았다.
- 각 원본에서 별도로 전체 정렬→기존 네 crop→동결 분류를 실행한 **12개 crop의 argmax는 모두 CORRECT**다. 원본·crop SHA 및 각 점수는 개별 기록했고 3번 결과를 복사하지 않았다. 미자격 자세에서의 조건부 분류 진단이며 통합 PASS나 결과 송신으로 사용하지 않았다.
- A3의 기존 지지 `[38,1,0,3,0]`에서 두 번째 강한 영역은 기존 profile의 중앙 하단 회전축 범위 `[642,530,698,678]`다. 따라서 과거 `VALID/CORRECT`만으로 새 고정 몸체 기준의 절대 정렬을 인증할 수 없다. 상대 LK는 이 절대 기준 오차를 고치지 못한다.

결론: **LoFTR 단독으로 세 장을 해결했다고 할 수 없다. 상대 정렬이 반드시 필요하다고도 확정하지 않았다.** LK는 비용이 낮은 가능성이지만 절대 기준 자격 및 보류 대응 문제를 먼저 해결해야 한다. LoFTR+LK를 자동 결합하지 않았고 새 matcher를 더 추가하지 않았다. 현재 시야 기준과 학습 crop 관계를 이미 확보한 정상·결품·SIDEWAYS·복원 묶음에서 독립적으로 확인하는 것이 남은 최소 문제다. 카메라를 학습 때와 완전히 같게 달라는 요구로 대체하지 않는다.

### 시간·운영 경로·재부팅 복구

노트북 Python3.13.5/Torch2.11.0+cu128/OpenCV5.0.0/RTX5070 Laptop 8GB에서 B 매칭 중앙값 **1,337ms**(1,206–2,358ms), C 4방향 매칭 **289ms**(271–733ms, 첫 실행 포함)다. C 모델 로딩 **709ms**, PyTorch 최고 할당 **905,812,992B**이며 전체 RSS/장치 메모리 값은 아니다. 저장된 행렬의 전체 warp+기존 네 crop 별도 측정 p50 **4.63ms**, p95 **6.05ms**다. 파일 decode·분류·Journal·PLC를 포함한 요청 시간으로 표시하지 않는다.

Jetson 기존 Python3.10.12/OpenCV5.0.0, CPU 1스레드·낮은 우선순위로 같은 저장 3장 상대 LK만 6묶음 측정했다. 첫 묶음 **122.27ms**, warm 5묶음 **118.24–125.35ms**, 프로세스 peak RSS **79,696KiB**다. 운영 카메라와 Assembly는 대기 상태였다. 측정 전후 동일 연결1, 접수/Result/Done 증가0, READY 유지; 부팅 이후 health 최대245.86ms가 증가하지 않았다. 이 최대값은 해당 2초 구간만의 최대값이 아니다. 임시 파일은 결과 SHA 회수·검증 후 정리했다.

기존 실제 요청→Result **13.745초** 중 Assembly는 **11.644초**였다. 위 LK 0.12초에는 절대 기준 정렬·분류·저장 등이 없으므로 이를 13.7초에서 단순 차감할 수 없다. **새 경로의 전체 Jetson 검사 시간 및 단축량은 UNMEASURED**다. B/C가 기하 자격을 얻지 못해 Jetson 의존성 설치·실제 Assembly 통합·새 PLC 시험을 수행하지 않았다.

사용자 보고의 우발적 전원 분리 후에는 별도 재기동 문제를 처리했다. 사용자가 전원 복구·실제 STOP을 확인했고 `STALE_OR_COMPETING_IPC_SOCKET_REQUIRES_REVIEW`를 읽었다. 기존 절차로 서비스 정상 정지→독점 owner lock→커널/fuser/포트에서 소유자 없음·socket inode/UID 검증 후 해당 잔여 socket 하나만 제거→동일 서비스 기동했다. current·모델·설정·Journal을 교체/초기화하지 않았다. 이후 Release 동일, **185 SHA 일치**, MainPID3667/active/NRestarts0, 카메라·Assembly ready/유휴, PLC fresh/SYNC_LOW, Request/Mc_Run LOW, Result/Done0, 새 접수0을 확인했다. 기동 중 재부팅 소켓 자동 복구 기능을 새로 개발한 것은 아니다.

### 복구 후 사용자가 직접 진행한 별도 시험

위 Result/Done0은 복구 직후 관측이다. 최종 확인에서 같은 C 연결의 누적 Result/Done이 각각2로 증가했고, 사용자는 재부팅 후 직접 START로 시험했으며 현재 실제 STOP을 유지한다고 확인했다. Codex가 새 권한·START·결과 명령을 보낸 시험이 아니며, B/C/LK는 운영에 적용되지 않았다.

- 첫 사이클: 촬영0장, `PREVIOUS_RUNTIME_PRODUCT_EXIT_UNPROVEN`, `NO_ACTUAL_INSPECTION`의 ERROR. 약30.01초 후 기존 정책의 NG·Done 경로가 기록됐다. 실제 AI 검사로 세지 않는다.
- 두 번째 사이클: 새로운 원본3장과 Journal COMPLETE, 기존 부품 검사 **PASS**. 조립 세 프레임은 모두 `SEED_INSUFFICIENT_SPATIAL_BODY_SUPPORT`이며, 지지점이 한 영역에 집중되어 네 부품 분류는 실행하지 않았다. 필수 조립 **REVIEW**, 통합 **REVIEW**, PLC에는 기존 정책대로 NG·Done. 전체 최종판정12.897초, 조립10.819초이며 변경 전 운영 경로의 별도 관측이다.
- 두 건 모두 `PLC_CYCLIC_COMPLETION_OBSERVED`와 요청 해제가 기록됐지만, `plc_consumption_confirmed=false`이므로 PLC 내부 판정 소비나 각 사이클의 실제 벨트 동작까지 새로 입증하지 않는다. 최종 Request/Mc_Run/Result/Done LOW, 카메라 신선, 검사 유휴, Journal quick_check=ok. 원본·이력은 읽기만 했다.

비공개 증거: `matcher_comparison/OPERATOR_POST_RECOVERY_TRIALS.json`, `OPERATOR_POST_RECOVERY_SUMMARY.json`, `FINAL_STATE.json`. 최근 기본 검사 PASS를 전체 조립 PASS로 표시하지 않는다. 이전 비교 묶음의 1·2번 실패/3번 VALID와 이번 새 세 프레임 모두 실패를 구분한다.

### 산출물·검증·남은 범위

코드는 `notebook/diagnostics/body_matching/`의 `geometry`, `shape_matcher`, `loftr_matcher`, `relative_lk`, `compare`와 README다. `notebook/tests/test_body_match_geometry.py`의 5개 검증이 통과했다(quarter-turn 픽셀 동일성/역행렬, 구멍 배경 제외, projective 분모, 두 고정부 상대 이동, 무정보 영상 거부). 실제 B/C 실행과 각 실험의 입력·profile·source SHA를 별도 보존했다. 최초 B의 scipy 누락과 A 보충 실행의 문법 오류는 수정 후 실행 결과와 분리했고 최종 알고리즘 실패로 집계하지 않았다. 전체 Runtime 회귀는 운영 코드가 변경되지 않아 반복하지 않았다.

비공개 원본·대조 그림·40장 표·분류·시간 기록은 노트북 `runs/assembly_ai_022/matcher_comparison/`에 있다. 대표 UI는 `BODY_MATCH_COMPARISON.html`, 한 원본의 mask→실제 대응→전체 정렬→네 crop을 A/B/C/기준 변경별로 나란히 제공한다. `PLC_15010` 파일 별칭의 실제 frame ID는 `…-1510`이며 새로운 프레임이 아니다. 원본은 Git에 포함하지 않는다. 브라우저 도구의 file URL 정책으로 실제 브라우저 상호작용 검증은 차단됐고, 저장 PNG 확인과 HTML/스크립트 정적 검증으로 범위를 한정했다.

이번 작업의 운영 정렬 완료 조건은 **미달**이다. 새 경로의 실제 PASS/FAIL·연속 세 번·처리시간 개선을 주장하지 않는다. 실험 결과를 먼저 보고하며, 다음 알고리즘·모델 재학습·무인운전 작업을 자동 시작하지 않는다.

2026-10-15 후속 기준. **Worker 안정화와 웹 미리보기는 운영 적용됐다. 마지막 실제 촬영 검사는 원시 PASS → Assembly 전처리 거부 → 통합 REVIEW → NG·Done으로 종료됐다. 이후 추가 요청 한 건은 촬영 없이 ERROR로 종료됐다. 기존 자세 재사용 B는 기하 검증에 실패하여 미배포다. 필수 조립 정렬·분류 복구는 미완료다.** 아래 과거 시험·진단은 현재 상태와 구분한다.

## 현재 후속 결과 — D001 자세 재사용 가설

### 실제 기준과 변경 범위

소스 `52df5d22b13130493e3268de744724c9395b2723`, 실제 운영 Release `engine-integrated-8831b41d4448da2d`. Jetson의 동결 조립 자산 28개 SHA를 새로 읽어 manifest와 일치함을 확인했다. 새로운 조립 후보, 모델, 설정, PLC, 서비스는 변경하지 않았다. Git의 기존 미커밋 작업은 보존했다. 이번 후속에서 Codex가 START·새 검사 권한·PLC Result/Done 명령을 실행한 횟수는 0회다. 기존 운영 서비스가 처리한 추가 요청은 아래에 별도로 기록한다.

직전 미리보기 시험의 실제 검사 `769713b76bd7406fa8cceb1fc443ff3f`는 새 PNG 3장과 원시 PASS를 저장했으나 Assembly 전처리가 3/3 거부됐다. 기존 정책에 따른 통합 REVIEW의 NG Result seq5570 → 다음 패킷 Done seq5571, Request 해제와 작업자의 벨트 재가동 확인이 있다. 이것은 새 정렬 후보의 현장 성공이 아니다. 미리보기 결과는 `WEB_PREVIEW_LATENCY_REPORT.md`에 별도로 기록했다.

현재 읽기 전용 상태는 Mc_Run/Request LOW, Result/Done `00000000`, `SYNC_LOW`, 활성 검사·저장·Assembly 대기 작업 0이다. 이미 종료한 과거 문맥을 다시 복구하지 않았다. 마지막 제품의 정상 진입/이탈 관측 상태도 임의로 CLEAR 처리하지 않았다.

최종 읽기 확인 중 누적 Result/Done이 1/1에서 2/2로 증가한 것을 발견했다. 추가 요청 ID 2, 검사 `f2b009674c6c49fa9f92f81091d56e8b`는 `PREVIOUS_PRODUCT_IDENTITY_OR_EXIT_UNPROVEN`이며 observation 0장이다. 요청 접수 후 약 30.13초에 durable ERROR가 생성되고 Result seq25264 → Done seq25265 → Request 해제·출력 초기화가 기록됐다. **실제 AI/조립 검사 미실행**이며 정렬 후보의 평가 28장에 포함하지 않는다. 사용자는 작업 중 직접 START를 눌렀고 현재 STOP으로 실제 정지 중이라고 확인했다. 이 건의 물리적 재가동은 별도 미확인이다. 서비스 재시작 0, 현재 STOP·작업 유휴 상태이며 추가 명령을 보내지 않았다. 근거: `pose_reuse_followup/ADDITIONAL_RUNTIME_EVENT.json`, `FINAL_READONLY_STATE.json` 및 현재 사용자 확인.

### 실제 로딩 경로와 실패 지점

`EngineInspector.detect()` → `EnginePoseEstimator.estimate()` → `rectify_image()`가 부품 존재 검사 입력을 만든다. `part_input_transform`은 **D001 기준 픽셀 → 현재 원본 픽셀**의 2×3 similarity다. `rectify_image()`는 그 역행렬로 원본을 D001 크기 1280×720에 정렬한다. 최신 Journal의 세 observation에 이 행렬·frame ID·epoch·픽셀 SHA가 실제 저장되어 있다.

`AssemblyInspector`의 durable row → `ShadowObserver.process_one()` → `load_assembly_frames()`의 원본/식별/품질 검증 → `load_frozen_models()` → `/home/jetson/oned_device_bench/assets/misassembly_runtime/jetson/shadow_misassembly/static_models.py`의 `StaticShadowModels` 순으로 호출된다. 클래스는 `TemporalShadowModels` → `ShadowModels`, 전처리는 `TemporalShadowPreprocessor(RobustShadowPreprocessor)`이며 guard를 `StaticPoseGuard`로 바꾼다. 이 경로는 observation의 D001 자세를 사용하지 않고 T0001 고정 몸체 대응과 sequence seed를 다시 계산한다. `load_frozen_models()`가 검증하는 실제 자산 manifest를 기준으로 비교했고, 이름만 같은 노트북 진단 파일을 운영본이라고 하지 않았다.

최신 세 장의 첫 T0001 대응은 각각 7/9/10개로 최소 12개보다 적다. bank/reciprocal 후에도 최종 seed는 `POSE_QUALITY_REJECTED`다. 첫 장의 reciprocal 55개 중 inlier 8개, 몸체별 지지 `[7,0,1,0,0]`; 둘째 `[10,0,0,0,0]`; 셋째 `[7,0,0,1,0]`로 여러 몸체 영역이 지지되지 않는다. 최종 crop/classifier 호출 이전의 거부다. 반면 같은 원본의 D001 자세는 유효하고 inlier 27/32/27개다. **존재 검사 pose의 유효성이 조립 crop 정확도를 보장하지 않는다.**

### 두 기준 좌표와 한 가지 B 비교

두 사진은 모두 1280×720이지만 바이트·제품 픽셀 위치가 다르다. D001 SHA `6dc94539570259d7747d8cc2b4d5fb0ed3d782b6b5a881408f427cd80c39f561`, T0001 SHA `bf45d6a7a191809907863cfe0b7ed24bdac437b441d26645690a98d1a5a82c32`.

개발용 주석은 고정 몸체판 네 모서리와 사용자가 고정 구조라고 확인한 마운트 림 두 중심이다. 피스톤·금색 축·네 검사 대상 부품은 제외했다. T0001의 1·3·5를 D001의 동일 지점에 similarity로 맞추고 2·4·6은 계산에서 제외했다. 보류점 오차는 **9.53 / 13.65 / 19.44px**다. 여섯 점 모두로 최소제곱을 해도 잔차 4.89~13.20px가 남는다. ±3px 주석 민감도 1,000회에서 최대 보류 오차의 최솟값은 10.74px였으며 이는 통계적 신뢰구간이나 정밀 실측은 아니다. 3px와의 비교는 기존 수치 예산을 참고한 진단이며 새 운영 승인 게이트를 추가한 것이 아니다.

이 결과는 단순 행렬 복사나 한 개의 이동·회전·균일 크기 변환으로 좌표 연결을 검증할 수 없다는 근거다. 깊이·촬영 투영 차이가 원인일 가능성은 있으나, 이 주석만으로 비평면 왜곡의 정확한 원인을 확정하지 않았다. 일반 affine/homography를 추가 채택하지 않았다.

B는 `T0001→D001 연결 제안`을 `같은 프레임 D001→원본 자세`에 합성한 뒤 기존 영역별 level0 LK의 몸체 similarity 보정만 사용했다. 정상/조명/최신 PLC 원본은 저장된 자세, 결품/복원/TRAIN은 같은 원본과 기록된 envelope로 기존 estimator를 재생했다. 후자는 당시 저장 pose라고 표시하지 않았다. 식별자·SHA를 묶었으며 다른 프레임 pose를 재사용하지 않았다.

| 자료 | 장수 | A 기존 조립 전처리 VALID | B 몸체 보정 통과 | B 운영 적합 |
|---|---:|---:|---:|---:|
| 현장 정지 정상 | 3 | 0 | 0 | 0 |
| 조명 추가 정상 | 3 | 0 | 0 | 0 |
| 실제 배기 결품 | 3 | 0 | 0 | 0 |
| 정상 복원 | 3 | 0 | 0 | 0 |
| 최신 실제 PLC 검사 | 3 | 0 | 0 | 0 |
| 기존 TRAIN 정상/결품/오조립 대조 | 13 | 12 | 0 | 0 |

A는 해시가 일치하는 보존된 실제 운영/동결 재생 결과를 재사용했다. B는 새 로컬 CPU 기하 실험이다. 참조 연결의 미검증 여부와 별개로 B의 몸체 보정 자체도 0/28이므로 숨겨진 새 게이트 하나 때문에 실패한 결과가 아니다. 세 장은 각각 같은 촬영의 인접 영상이며 독립 물리 실험 3회로 세지 않는다. 정상 복원과 결품 장면은 몸체 위치도 달라 단일 부품 변화만의 인과 실험은 아니다.

### crop·반전·분류의 분리

T0001 crop은 pipe_left `[426,96,625,345]`, pipe_right `[709,96,922,345]`, exhaust `[569,373,764,524]`, symbol `[599,282,735,392]`다. 기존 입력은 BGR uint8 → 색40 정사각 패딩 → 224×224 bilinear → 기존 FixedPredictor RGB/255이며 class mapping/가중치는 유지한다.

비교 그림은 원본에 합성한 전체 역변환을 한 번만 적용한 **미승인 진단 crop**도 보여 준다. 몸체 탐색 마스크로 분류 이미지를 지우거나 부품을 각각 정상 방향으로 돌리지 않았다. 최신 원본에서는 특히 배기 crop이 실제 부품 위치를 벗어난다. B가 기하를 통과하지 못했으므로 네 분류기 점수는 전부 NOT_RUN이며 임의 점수를 채우지 않았다. A에서 실제 분류가 수행된 TRAIN 기록은 기존 전체 class 점수를 보여 준다.

과거 V8-template 후보의 반전 실패는 저장된 제안 행렬·동일 원본·동일 reference와 gate로 다시 재현했다. **반전 영상도 수용**, 방향 상관 0.368614로 기존 0.35를 통과하고 행렬 determinant도 양수였다. 대칭 구조의 잘못된 대응이 두 영역 지지·상관 기준을 통과할 수 있어 determinant 부호만으로 영상의 물리 방향을 입증할 수 없다. 이 후보는 여전히 미채택이다. B의 mirror/blank/몸체판 가림/잘못된 translation 네 합성 대조는 거부했으나, 정상도 모두 실패하므로 이를 유용한 보호기능 개선 성공으로 세지 않는다.

별도로 보존된 고정 행렬 정상 exhaust 결과 CORRECT/SIDEWAYS/SIDEWAYS와 전체 점수는 여전히 유효한 미해결 증거다. 동일 행렬이 동일 crop/tensor를 뜻하지 않는다. 기존 입력 parity 자료를 근거 없이 재실행하지 않았고, 올바른 현장 crop 자체가 아직 입증되지 않아 **분류기 자체의 실패로 확정하지 않는다**. 새 현장 오조립 상태의 실물 자료는 없다. TRAIN 대조와 합성 반전을 그 자료 대신 PASS 처리하지 않는다.

### 결과·산출물·다음 판단

- **가설 기각 범위:** 현재 D001 자세 + 한 개의 검증되지 않은 similarity 기준 연결 + 기존 국소 몸체 보정으로는 조립 crop 복구가 입증되지 않았다. 모든 소프트웨어 보정이 불가능하다는 결론은 아니다.
- 재현 가능한 좌표 계산/합성/역변환 3개 자체 검사, 원본 28개 해시 불변, 반전 실패 재현, 그림 272개 디코드 및 HTML JavaScript syntax를 확인했다. 초기 진단식의 계수 배치 오류는 좌표/그림 검사에서 발견해 수정 후 전체 결과를 재생했다. 해당 잘못된 수치는 결과에서 제외했다.
- 로컬 HTML의 실제 브라우저 렌더링은 브라우저 정책이 `file:` URL을 차단해 미검증이다. 우회하지 않았고 별도 PNG 비교 그림을 실제 열어 확인했다.
- 노트북 전용 증거: `runs/assembly_ai_022/pose_reuse_followup/REFERENCE_BRIDGE.json`, `POSE_REUSE_COMPARISON.json`, `VERIFICATION.json`, `POSE_REUSE_COMPARISON.html`, `POSE_REUSE_SUMMARY.png`. 실행 스크립트는 같은 폴더의 `compare_pose_reuse.py`, `verify_pose_reuse.py`, `render_comparison.py`. 사진/DB는 Git 제외.
- **이번 조립 수정 배포 없음 / 운영 Release 유지 / 복원 불필요 / 새 PLC 시험 없음.** 실패 후보를 서비스에 넣거나 전처리 거부를 제거하지 않았다. 미리보기의 실제 기존 시험 결과와 구분한다.
- 다음에 필요한 것은 정상 모형 투입 횟수 증가가 아니라, 여러 높이·몸체 영역을 함께 설명하는 기준 좌표 관계의 근거다. 현재 단일 similarity의 잔차를 먼저 설명한 뒤 변환 모델을 바꿀지 판단해야 한다. 부품별 정답 방향 보정·재학습·임계값 변경으로 대신하지 않는다. 그 관계가 검증되면 실제 반복 투입으로 재현성을 확인하고, 현재 시점의 실제 오조립 대조도 확보해야 한다.

## 과거 확인 — 복원 장면과 사용자 PLC v4 적용

사용자는 PLC v4의 이송 5초와 운전 출력 OFF 후 요청 지연 2초를 모두 의도했으며, 실제 PLC 적용 후 직접 START했다고 확인했다. Codex는 PLC를 수정하거나 START하지 않았다. 저장본의 SHA는 `c1fd080562bce55c728b8f0b9d8375a3d5095abcaa6b302df78bbb212f170d3c`다. 온라인 전체 프로그램 동등성은 아직 별도 검증되지 않았다. 이전 2.7초 이송의 검사 위치를 현재 위치로 간주하지 않는다.

이 직접 시험의 ID는 `bb3c18819efc404aba57a09f3bc5320a`다. `PREVIOUS_RUNTIME_PRODUCT_EXIT_UNPROVEN`으로 약 30초 동안 실제 Worker 접수에 도달하지 못했다. 원본 3프레임과 조립 검사는 없으며, 원시/통합 기록은 `ERROR / NO_ACTUAL_INSPECTION`이다. 기존 정책에 따른 NG Result(seq1724) → 다음 cyclic 패킷 Done(seq1725), 이후 Request 해제와 출력 초기화는 C 기록으로 확인했다. 물리적 재가동과 PLC 내부 결과 소비는 이 시험에 대해 작업자가 확인하지 않았으므로 성공으로 표시하지 않는다. 2초 지연의 흔들림 개선 효과도 아직 평가할 수 없다.

정상 복원 장면의 별도 5초 유지보수 수집은 PNG 53장의 파일·픽셀 SHA를 검증했다. 상태는 `SAVED_WITH_DROPS`이며 전체 카메라 무누락을 뜻하지 않는다. 원본을 대조하면 배기 제거 장면과 복원 장면의 몸체 위치·각도도 달라져, 부품 제거만의 인과 비교가 아니다. 기존 운영 및 field20 경로에서는 선택한 복원 3장 모두 정렬이 거부됐다.

| 새 비활성 진단 경로 | 확인한 결과 | 채택 여부 |
| --- | --- | --- |
| 전체 영상 초기 제안 후 새 몸체 국소 대응·기존 시간 순서 검증 | 정상 3장/배기 제거 3장 정렬, 복원 첫 seed 확보 실패. 24개 crop이 기존 T0001 좌표 추출과 픽셀 일치 | 미채택 |
| 위 crop에 동결 분류기 적용 | 정상 배기 CORRECT/SIDEWAYS/SIDEWAYS, 배기 제거는 MISSING 3장. 제거 장면 왼쪽 파이프는 OUTWARD_SPLAYED이나 실제 파이프 불량 근거 없음 | 원시 분류 기록만 확보; 최종 검사 성공 아님 |
| V8 고정 표기의 한정된 템플릿 초기 탐색 후 새 몸체 대응 | 복원 첫 장은 V8 30점만 유효, 두 고정부 대응 0점. 후속 두 장의 cold search는 반복하지 않아 시퀀스 미성립. **좌우 반전 음성 대조가 잘못 통과** | 실패 후보, 운영 적용 제외 |

현재 수치로 입증된 것은 고정 몸체 대응의 부족·모호성이다. 복원 영상에서 다른 영역의 독립 대응이 없으므로 원근 때문에 similarity 자체가 불가능하다고 결론내리지 않는다. 기존 수치 기준을 낮추거나 더 유연한 행렬로 통과시키지 않았다. 다음 분석은 저장 원본의 실제 고정부 대응과 모델 입력 변화를 분리하는 데 한정한다. 부품별 정렬·모델·임계값 변경은 없다.

과거 제품 문맥 종료 대상은 마지막 실제 Track 검사 `2a80c3ed85df476c832aae8ac5ac82a9`다. **사용자의 현재 STOP·모형 벨트 밖 보관·손 뗌 확인 후 기존 유지보수 API로 한 건의 종료를 완료했다.** Journal과 승인 원장은 SQLite backup API로 노트북에 회수해 파일 해시·DB integrity·보호 행 해시를 검증했다. 백업 manifest SHA는 `a7730c0be3aa594b165a567d3278cc7a51bc91789659ac1ee6a48f73b75a1059`다. 검사 130건·frame asset 492건·승인 2건 등 기존 행은 불변이며 유지보수 event/outbox/service_state 각 1개만 추가됐다. 새 NO_ACTUAL_INSPECTION 기록이나 원본 결과는 바꾸지 않았다. 가짜 자동 이탈·AI CLEAR·새 검사 권한·결과 재전송·서비스 재시작은 없다. 실행 영수증 SHA는 `5d650208e6ee671e15fa52557d3921af36962e1583eb0fa0bda5d3d3178522d2`다.

종료 후 실제 장치에서 `SYNC_LOW`, Request/Mc_Run/Result/Done LOW, 카메라·Assembly ready/IDLE, 미완료 0, 기존 Result/Done 누적 1/1 유지, 184개 운영 파일 해시 일치를 확인했다. 과거 제품 차단은 해제됐고 `WAIT_NEW_PHYSICAL_START`다. 자동운전 검증값을 TRUE로 바꾸거나 새로운 START를 지시하지 않았다.

### 원인 분리 후속 결과

- 정상 light 3장의 정렬값 차이는 crop 모서리 기준 최대 0.04858px다. 같은 첫 장의 몸체 변환을 세 장 모두에 고정한 정확히 3회 exhaust 분류에서도 CORRECT 0.684557 / SIDEWAYS 0.738916 / SIDEWAYS 0.675168로 기존 class conflict가 유지됐다. 픽셀·RGB/255 tensor·동결 가중치를 검증했으며, 미세 정렬 흔들림 제거만으로 해결되지 않는다. 이 고정 행렬은 원인 분리용이며 운영 fallback이 아니다.
- 현재 배기 crop의 중앙은 학습 기준보다 명암 정보가 적다. 이는 저장 픽셀의 관측이며 조명만의 원인, 센서 포화, 소프트웨어 복구 불가능을 입증한 것은 아니다. 카메라·조명·모델·임계값은 그대로다.
- V8 몸체판 네 모서리와 작업자가 고정이라고 확인한 두 마운트 중심의 수동 대응점을 독립 비교했다. 좌표에는 약 ±2~4px 오차가 있고 부위 간 동일 평면/높이가 입증되지 않았다. 작은 V8 영역의 정렬을 전체 몸체로 외삽한 오차가 커질 수 있어, 기존 field20 기준 변환을 정답 calibration으로 승인하지 않았다. 수동 대응점은 운영 설정으로 사용하지 않았다.
- field20 대신 원래 T0001 사진만 바꾼 한정된 비교에서도 정상·결품·복원 첫 장 모두 공간 지지/대응 수 부족으로 거부됐다. blank·mirror·V8-only도 거부했으나 실제 영상 성공이 없어 해결 후보가 아니다. 모델 호출·PLC 쓰기·Runtime 변경은 0이며, 새 기준 선택이나 문턱 완화는 하지 않았다.

따라서 과거 문맥 복구는 완료됐지만 **조립 정렬과 현재 시점 분류 문제는 미해결**이다. 다음 검증에는 검사 부품·구멍 속 배경을 사용하지 않은 고정부의 독립 대응과, 그 변환이 학습 crop 좌표에 실제로 맞는다는 근거가 필요하다. 현재 정상/배기 결품만으로 다른 현장 오조립까지 성공했다고 할 수 없다. 실패 후보를 배포하거나 실제 PLC 재시험으로 성공을 대신하지 않는다.

실제 운영 Release는 여전히 `engine-integrated-eac535432b143ac5`이며 정렬 후보는 미배포다. 근거는 비공개 `runs/assembly_ai_022/plc_v4_readonly/`, `restored_exhaust_control/`, `whole_frame_local_sequence_diagnostic/`, `anchor_template_sequence_diagnostic/`, `historical_context_recovery/`와 `assembly_flow_viewer/WHOLE_FRAME_LOCAL_SEQUENCE_SIX_STAGE.png`에 보존했다. 아래 시간별 단락은 당시 관측이며 위 최신 사실과 구분한다.

## 현재 진행 업데이트 — 2026-10-15 11:16 KST

**IN_PROGRESS / 조립 정렬 보완 NOT_DEPLOYED.** 앞서 배포한 Worker 안정화 수정은 유지한다. 아래는 저장 원본의 로컬 재생과 비활성 소스 검증이며 새 PLC 검사·Result/Done 송신·현장 조립 검사 성공을 뜻하지 않는다. 이후 단락의 초기 진단 결과는 이력을 보존한 것이다.

- **동결 운영 경로 기준선:** 허용된 기존 TRAIN 대조군 13장과 현장 정지 원본 6장을 실제 `StaticShadowModels`의 독립 cold-start 경로로 재생했다. TRAIN은 12장 정렬·분류 실행(정상 1장 PASS_CANDIDATE, 결품/오조립 11장 FAIL_CANDIDATE), 1장은 공간 지지 부족으로 REVIEW였다. 분류한 48개 부품은 기존 라벨과 일치했지만, 현장 6장은 모두 정렬 거부였다. TRAIN 대조군은 현재 현장의 다른 오조립 상태를 검증한 증거가 아니다.
- **정확한 시간 순서 경로:** 고정된 field20 진단 프로파일을 `TemporalShadowPreprocessor` + `StaticPoseGuard`에 연결해 정상 `light_20/23/26`을 한 시퀀스로 재생했다. 최초 ABSOLUTE_SEED 이후 두 장은 CURRENT_BODY_REESTIMATE이며 매 프레임 독립 cold-start가 아니다. 실제 CUDA 검출기와 동결 네 분류기를 실행했고, 12개 crop은 별도 시간 순서 재생의 픽셀과 모두 일치했다. 배기구는 CORRECT 0.684557 → SIDEWAYS 0.750054 → SIDEWAYS 0.674379, 다른 세 부품은 CORRECT여서 기존 3프레임 정책의 결과는 **REVIEW / FRAME_STATE_CONFLICT**다. 이전 독립 정렬 진단의 점수와 혼합하거나 더 좋은 경로를 선택하지 않았다.
- **새 실물 배기구 누락 대조군:** 작업자가 배기구만 제거하고 촬영 중 본체·카메라·조명을 유지했다고 확인했다. 52개 PNG의 파일·픽셀 SHA를 검증했으나 수집 상태는 SAVED_WITH_DROPS이며 전체 카메라 프레임 보존을 주장하지 않는다. 미리 고정한 ordinal 20/23/26을 처리한 결과 기존 운영 프로파일은 모두 POSE_QUALITY_REJECTED, field20 시간 순서 경로는 매칭 6/4/3개로 모두 POSE_TOO_FEW_MATCHES였다. 유효 crop과 MISSING 분류는 생성되지 않았다. **이 누락 촬영 직전 정상 영상은 아직 없으며, 비교에 사용한 과거 light 영상과는 본체 위치·각도가 다르다.** 따라서 매칭 감소를 배기구 제거 하나의 영향으로 단정하지 않는다. 선택 메타데이터의 tracking pose는 NOT_EVALUATED_DURING_TRACKING이어서 이동·회전량을 검증된 pose 수치로 표시하지 않는다.
- **픽셀 격리 보완의 범위:** 노트북의 비활성 `isolated_body_registration.py` 모듈과 `test_isolated_body_registration.py` 집중 회귀(공개 운영 소스에 포함하지 않은 진단 구현)는 11개 테스트 PASS다. 선언한 고정 영역 바깥의 픽셀이 ORB 피라미드·descriptor에 섞이지 않도록 분리하고, 현재 영상의 대응점으로 엔진 전체 similarity 하나를 다시 추정한다. 잘못된 제안·반사·단일 영역·지원 부족을 거부하며 분류 crop, 모델, 임계값을 바꾸지 않는다. 정상 운영 경로에는 연결하지 않았다. 사용자가 검은 고정부의 기계적 고정을 확인했지만 구멍 안 배경 픽셀까지 고정 본체라고 인증한 것은 아니다. 피스톤·로드·축 움직임은 고정 기준에서 제외한다. 허용 마스크와 현재 영상에서 충분한 독립 지지를 얻는지는 별도로 검증해야 한다.

비공개 노트북 근거는 `production_controls/PRODUCTION_CONTROL_REPLAY.json`, `production_controls/VERIFICATION.json`, `field_body_calibration_diagnostic/FIELD_PROFILE_TEMPORAL_REPLAY.json`, `missing_exhaust_control/NOTEBOOK_VERIFICATION.json`, `missing_exhaust_control/MISSING_EXHAUST_ASSEMBLY_REPLAY.json`, `missing_exhaust_control/ASSEMBLY_REPLAY_VERIFICATION.json`이다. 마지막 재생 SHA는 `f41fc94b8e63dd91123520290e0b4099fb229729246b3c7b46836a0ee7d6a938`, 검증 SHA는 `0ebd57978ee252fdf5b2f1c1d1a4f7bea19b246b6c3f3b300f403adb354b58ac`이며 15개 생성 이미지와 실제 CUDA 검출·분류를 대조했다. 원본 사진·DB·개인 설정은 공개 소스에 포함하지 않는다.

다음 판단에는 누락 촬영과 같은 위치의 정상 복원 대조군이 필요하다. 이는 현재 교란 요인을 분리하기 위한 비교이며 카메라 변경을 전제하지 않는다. 아직 운영 조립 경로 배포, 현장 결품 판정, PLC 결과 전달 성공으로 승격하지 않는다.

## 1. 기준과 현재 상태

| 항목 | 확인 결과 |
| --- | --- |
| 작업 시작 소스 | `3babaa8250f8c8dab671e4246703ce222d535478` |
| 변경 전 실제 Release | `engine-integrated-c04fa92419200551` |
| Worker 수정 Commit | `0dc3f77e6688e10573a98f85524816ed15f2a16d` — 공식 저장소 Push 완료 |
| 변경 후 실제 Release | `engine-integrated-eac535432b143ac5` |
| 운영본 해시 | 배포 구성 184개 대조, 불일치 0개 |
| 수정 후 현장 재시험 | 사용자 직접 START 1건은 과거 문맥 차단으로 **실제 검사 미실행**. Codex가 진행한 새 AI 재시험은 NOT_RUN |
| 필수 Assembly | **미해결** — 동일 정지 영상에서도 pose/공간 지지 검증에서 거부 |

개발 원본은 공식 저장소 `jetson/`이다. Codex는 모델 가중치, 임계값, PLC 래더, EDS, RPI, 4/8/10B 계약과 Result→Done 순서를 변경하지 않았다. 사용자의 PLC v4 변경은 위 최신 기준에 기록했다. 실제 운영 자산·설정과 이전 배포 묶음의 차이는 운영본 기준으로 보존했다. Journal과 승인 이력을 이전 값으로 되돌리지 않았다.

## 2. 실제 저장 영상으로 확인한 원인

직전 연속 3회 검사의 원본 9장을 보존한 복사본에서 분석했다. 각 프레임의 기존 부품 존재 검사와 3프레임 집계 결과가 달랐다. 개별 검사는 PASS였지만 집계는 모두 `REVIEW / ENGINE_OR_HAND_MOTION`이었다. 영상에서도 제품의 실제 이동이 관측돼, 단순한 표시 오류나 임계값 문제가 아니었다.

세 검사의 첫 영상은 요청 후 약 6.27ms, 10.46ms, 27.82ms에 선택됐다. 이 수치는 `GSTREAMER_PTS_MONOTONIC_ESTIMATE`에 따른 source 시각이며, 센서 노출 시각을 직접 측정한 값은 아니다. 요청이 들어왔다고 기계의 관성 이동까지 즉시 끝난 것으로 간주할 수 없었다.

정지 상태의 승인된 5초 원본 기록에서는 53장의 PNG를 확보했다. 이 중 동일한 세 장의 저장 픽셀을 Jetson에서 오프라인 재생했을 때 기존 부품 존재 검사는 각 프레임 PASS, 3프레임 집계도 `PASS / ALL_REQUIRED_PARTS_PRESENT_3_FRAMES`였다. 이 결과는 네 부품의 오조립 분류를 포함한 통합 최종 PASS가 아니다.

초기 재생의 calibration 확인용 임시 값을 그대로 근거로 채택하지 않았다. 실제 저장 calibration을 운영 `InspectionService` 로딩 경로로 검증한 뒤, 저장된 네이티브 observation의 집계만 다시 확인했다. 결과는 PASS로 유지됐으며, 기존 observation·원본 Journal·최초 재생 결과는 변경하지 않았다. 현재 카메라의 물리 calibration을 새로 현장 인증한 것은 아니다.

## 3. 채택·배포한 최소 수정

수정 파일은 `jetson/src/vision/inspection_worker.py`의 `worker_main()` 검사 프레임 수집 경로와 회귀 테스트 `notebook/tests/test_stationary_inspection_capture.py`다.

- 적용 대상은 OpENer의 전체 화면·정지 검사 정책에 연결된 실제 검사 요청이다.
- 요청을 접수한 뒤 기존 deadline 안에서 요청 이후의 새로운 영상 중 **연속으로 안정한 세 프레임**을 확보한다. 두 장이 안정해도 다음 영상이 움직이면 세 프레임 창을 다시 시작한다.
- 안정 여부는 기존 `engine_dynamic.stable`을 그대로 사용한다. 움직임 임계값이나 3프레임 최종 판정 규칙을 낮추지 않았다. 부품 판정이 PASS인 영상만 선택하지 않는다.
- frame ID, source time, camera epoch, Worker generation, 취소 및 timeout 검증을 유지한다. 다른 정책의 작업은 기존 수집 방식을 유지한다.
- `POST_REQUEST_STABLE_THREE_FRAMES` 메타데이터에 후보 수·제외 수와 최대 32개의 최근 제외 근거를 남긴다. 안정화 기한을 넘기면 실제 최근 원본과 실패 근거를 보존하며 성공 판정을 만들지 않는다.

따라서 이번 수정은 이동이 끝나기 전 검사를 시작하던 수집 시점 문제를 다룬다. 기계 정지를 전기 입력만으로 인증하거나 실제 PLC 시험을 대신하지 않는다.

## 4. 미해결 Assembly와 진단용 crop

같은 정지 영상 세 장을 변경하지 않은 필수 Assembly 경로로 재생하면 `POSE_QUALITY_REJECTED`, `SEED_INSUFFICIENT_SPATIAL_BODY_SUPPORT`, `POSE_QUALITY_REJECTED`가 발생한다. 이 경로에서는 전처리 검증을 통과하지 못해 네 분류기를 정상 실행하는 단계에 도달하지 못했다.

Reference LK 진단은 저장 영상에서 기존 기하 검증을 만족하는 대응을 찾았고, 평탄 배경·좌우 반전·180px 잘못된 이동·본체 일부만 남긴 네 음성 대조군을 모두 거부했다. 그러나 본체 마스크에 움직이는 피스톤·축이 포함되고, 정렬 후 crop의 외형도 달라지는 문제가 있어 **운영 전처리로 채택하지 않았다**. 기하 검증 통과만으로 분류 입력의 타당성이 확인된 것은 아니다.

미채택 진단 crop으로 네이티브 분류기를 실행한 결과 왼쪽·오른쪽 파이프와 심볼은 CORRECT였지만 exhaust는 세 장 모두 SIDEWAYS(약 0.992–0.995)였다. 사용자는 해당 실물의 네 부품이 모두 정상 조립이라고 확인했다. 따라서 이는 **진단 crop에서 나타난 정상 제품 오분류**이며 실제 운영 검사 FAIL로 기록하거나 PLC에 전송하지 않았다.

추가 입력 대조에서는 동결 classifier SHA·class mapping을 확인했고 `FixedPredictor`와 학습 입력 변환의 tensor가 비트 단위로 일치했다. T0001 학습 reference와 정확한 기존 학습 crop은 CORRECT 약 0.99999988이었다. 사용자는 T0001 exhaust 사진과 현재 실물이 같은 정상 방향이라고 추가 확인했다. 현재 세 진단 crop의 SIDEWAYS는 노트북 RTX 5070에서도 재현됐고 Jetson 점수와의 최대 차이는 0.000022 미만이었다. 현재 근거로는 단순 채널 순서나 class index 오류가 확인되지 않았다. 촬영 조건 차이와 정렬·crop 문제의 기여도는 아직 분리하지 못했다. 모델 교체·재학습·판정 덮어쓰기는 하지 않았다.

### 추가 조명 A/B 관측

작업자는 카메라·모형은 유지하고 조명만 추가했다고 보고했다. STOP과 손을 뗀 상태에서 별도 5초 원본 기록으로 PNG 53장을 확보했다. 기록 대상으로 접수된 53장의 PNG 저장과 frame ID 중복 0건·카메라 소유자 1개·PLC 쓰기 0회를 확인했다. raw 저장 drop 계수는 0이지만 최종 기록 상태는 `SAVED_WITH_DROPS`이므로 전체 카메라 프레임이 누락 없이 기록됐다는 의미가 아니다. 연속 CLEAR 증거로 사용하지 않는다. 저장 종료 사유는 `TIME_LIMIT`이다. 수집 묶음 SHA-256은 `41c88ac544e6bc2ee259ffe596f7c328eeb1fd1fe1d1178c9907c136b78462d5`다.

| 조명 추가 후 동일 세 프레임의 경로 | 관측 결과 |
| --- | --- |
| 기존 부품 존재 검사 네이티브 재생 | 3프레임 집계 PASS, `ALL_REQUIRED_PARTS_PRESENT_3_FRAMES` |
| 변경하지 않은 운영 Assembly 전처리 | **0/3 통과** — 모두 `POSE_QUALITY_REJECTED` |
| 미채택 진단 기하 경로 | **2/3 통과** — `light_20`, `light_26`만 crop 생성; `light_23`은 거부 |
| 위 두 진단 crop의 동결 분류기 | 네 부품 모두 최상위 class CORRECT; exhaust 점수 0.607389 / 0.503357, 왼쪽 파이프 0.526043 / 0.546257 |

`light_23`은 분류 결과가 없으며 3장 성공으로 계산하지 않는다. CORRECT는 분류기의 **argmax(가장 큰 점수인 class)**이며, 특히 exhaust·왼쪽 파이프의 점수가 약 0.50~0.61인 이 관측을 통합 PASS나 운영 Assembly 성공으로 해석하지 않는다. 모델·class mapping·입력 변환·임계값은 동일하다.

조명 추가 전후 진단 정렬의 scale도 약 2% 달라졌다. 이전 정렬을 그대로 다음 영상에 적용하는 별도 temporal 진단은 세 장 모두 `CURRENT_BODY_REGIONS_DISAGREE`로 거부했다. 따라서 **조명만이 오분류의 유일한 원인이라고 확정할 수 없다**. 조명·기하·crop 변화가 섞여 있으며, 이전 pose를 재사용하거나 실패한 프레임임에도 정상으로 간주하지 않았다. 이후 사용자 지시에 따라 카메라 조정 비교는 보류하고, 현재 촬영 조건을 유지한 소프트웨어 정렬 수정을 우선 조사한다. 카메라 조정을 해결의 필수 전제조건으로 삼지 않는다.

## 5. 검증 범위

### 현재 촬영 조건을 유지한 소프트웨어 조사

사용자는 카메라를 움직이는 대신 소프트웨어 해결을 우선 요청했다. 기존 `EnginePoseEstimator`는 이미 회전·이동·축척 보정을 수행하며, 기준→현재 행렬을 역변환하는 방향도 올바르다. 조립 입력은 별도 T0001 좌표를 일관되게 사용한다. 실제 배포 백업과 로컬의 전처리·정렬 관련 6개 소스 SHA도 일치했다. 따라서 현재 근거로 카메라 회전이 필수라거나 단순 90도 보정이 빠졌다고 결론 내릴 수 없다.

기존 고정 몸체 마스크·분류 대상 제외·통과 기준을 유지한 SIFT 진단을 정지 원본 6장에 한정해 실시했다. 조명 전 세 장의 reciprocal 대응은 6/4/6개(고유 좌표 6/4/4개), 조명 후는 2/3/4개로 모두 기존 12개 최소 조건을 만족하지 못했다. 동일 기준 영상의 합성 회전 대조군은 통과했고 빈 배경은 거부했다. 파라미터 탐색이나 운영 검출기 교체는 하지 않았다. 근거는 `frozen_sift_diagnostic/FROZEN_SIFT_DIAGNOSTIC.json`이다.

`fixed_body_feature_regions_xyxy`의 B1/B2에는 피스톤·로드, B3에는 축 영상이 포함된다. 현재 대응점만으로 고정 하우징에만 독립적인 지지가 있다는 사실은 입증되지 않았다. 기준 영역을 다시 검토할 근거는 있지만, 새 마스크가 실제 모든 조립 상태에서 불변이라는 검증은 아직 없다. V8 글자 하나를 여러 영역으로 나눠 공간 지지 조건을 통과시키거나 검사 부품을 각각 정상 방향으로 돌리는 해결책은 채택하지 않는다.

기존 부품 존재 검사의 D001 pose는 여섯 프레임에 저장돼 있으나 제품 전체 특징을 사용하고 숫자 기준도 조립 검사와 다르다. 검증된 T0001→D001 교정 행렬도 확보되지 않았다. 그러므로 D001 행렬을 조립 승인이나 T0001 crop에 직접 대입하지 않는다. 필요한 소프트웨어 수정은 고정 몸체 기준·대응점 분포·동일 canonical crop을 함께 검증해야 하며, 이번 진단만으로 수정 완료 또는 운영 Assembly 성공을 주장하지 않는다.

| 확인 항목 | 결과와 한계 |
| --- | --- |
| 로컬 집중 회귀 | 61 PASS |
| Jetson 네이티브 Worker 회귀 | 9 PASS; 실제 Worker·판정·PNG 경로, 합성 카메라·모델, PLC 미사용 |
| 안정화·취소·오류 경로 | 이동 후 안정화, 중간 재이동, 결품 FAIL 보존, 기한 만료, bounded 메타데이터, 취소, epoch 변경, 품질 실패, 다른 정책 회귀 확인 |
| 정지 원본 재생 | 기존 부품 존재 검사 3장 PASS 및 실제 calibration 검증 후 집계 PASS |
| 필수 Assembly 재생 | FAIL — 전처리 미해결; 통합 AI 성공으로 표시하지 않음 |
| 진단 crop 분류 | 최초 조명에서는 exhaust 정상 실물과 불일치. 추가 조명에서는 기하 통과 2장만 네 부품 CORRECT 최상위 class; 운영 미채택 |
| 추가 조명 네이티브 재생 | 기존 부품 존재 집계 PASS, 운영 Assembly 전처리 0/3. 조명 단독 인과와 3프레임 통합 성공은 미입증 |
| 배포 구성 | 184개 해시 일치, C 실행 파일·설정·운영 데이터 변경 없음 |
| 새로운 실제 제품 사이클 | NOT_RUN |

원본·개인 설정·DB·현장 이미지와 상세 진단 결과는 노트북의 비공개 `runs/assembly_ai_022/`에 보존한다. 주요 근거는 `NATIVE_TESTS.json`, `STATIONARY_NATIVE_REPLAY.json`, `STATIONARY_REPLAY_CALIBRATION_CORRECTION.json`, `reference_lk_diagnostic/REFERENCE_LK_DIAGNOSTIC.json`, `PROPOSED_CROPS_NATIVE.json`, `EXHAUST_INPUT_PARITY_DIAGNOSTIC.json`이다. 사진이나 DB를 이 보고서와 함께 공개 저장소에 추가하지 않는다.

추가 조명 근거는 `lighting_comparison/CAPTURE_RECEIPT.json`, `LIGHTING_NATIVE_REPLAY.json`, `LIGHTING_GEOMETRY_COMPARISON.json`, `LIGHTING_CLASSIFIER_INPUT_DIAGNOSTIC.json`, `LIGHTING_TEMPORAL_GEOMETRY_DIAGNOSTIC.json` 및 상위의 `POST_LIGHTING_STATE.json`이다.

## 6. 실제 배포 및 복원 근거

| 산출물 | SHA-256 |
| --- | --- |
| 변경 Worker | `c149fa8aa34e26d32229a1b99f138452b05c524cfb9acb5f73d17dfa5e62e9b9` |
| 노트북 직전 운영본 백업 `PRECHANGE_BACKUP.tar.gz` | `29995aaa57be40c4620e4caf2c47997bedacd861bb6b2f645e8907afddb75296` |
| 전체 배포 패키지 | `09101f7a40ebc1b6d2a0786f783f0fdb98717da11073bcc7f004da9963570dea` |
| 보존된 OpENer 실행 파일 | `63ca4b16db530eecc9f95155a40cf758b291a590d85894dc8e9faf7aa0b2f4a4` |

백업은 169개 파일 해시 검증과 SQLite integrity `ok`를 확인했다. 배포 영수증 `WORKER_DEPLOYMENT.json`의 `service_started=false`는 파일 전환 직후의 단계별 기록이다. 이후 `POST_DEPLOY_VERIFICATION.json`에서 실제 기동한 새 Release와 해시를 확인했다.

배포 후 관측 시점에 카메라 Worker와 Assembly Worker는 ready였고 미완료 작업은 없었다. PLC 연결은 fresh, 상태는 `SYNC_LOW`, Request·Mc_Run은 LOW, Result/Done 바이트는 `00000000`이었다. 이 확인 과정에서 새 검사나 PLC 결과를 발행하지 않았다. 재시작 전 제품 문맥에 대한 `PREVIOUS_RUNTIME_PRODUCT_EXIT_UNPROVEN` 사유가 남아 있으므로 **다음 현장 시험 준비 완료나 자동 재무장 완료로 해석하지 않는다**.

추가 조명 기록 후 `POST_LIGHTING_STATE.json`에서도 같은 Release, Request/Mc_Run LOW, Result/Done `00000000`, 접수된 요청 0건, 활성 검사 없음, 저장·최종 commit 대기 없음과 카메라·Assembly ready를 확인했다. `PREVIOUS_RUNTIME_PRODUCT_EXIT_UNPROVEN`은 그대로 남아 있다. 원본 수집·오프라인 재생을 신규 PLC 제품 검사로 세지 않는다.

복원 시 현장 정지와 서비스 정상 종료 후 검증된 노트북 백업에서 직전 current·설정·서비스 정의 및 기록된 링크를 복구하고, 파일 SHA와 실제 상태를 다시 확인한다. 배포 이후 생성된 Journal·증거·승인 이력을 과거 DB로 덮어쓰지 않는다. 현재 모델·assets·환경 의존성을 보존한다.

## 7. 남은 작업과 완료 판단

1. 현재 정상 실물에서 Assembly 전처리 실패와 진단 exhaust 오분류의 원인을 분리한다. 추가 조명 관측은 완료했으나 조명 단독 원인은 미입증이다. 사용자의 소프트웨어 우선 지시에 따라 카메라 비교는 보류하고 현재 원본으로 대응점·좌표 변환·crop 경로를 조사한다. 정상으로 표시되게 결과를 바꾸지 않는다.
2. 미채택 정렬 제안을 운영에 반영하려면 동일 원본·기하 음성 대조군·실제 부품 상태를 함께 검증해야 한다.
3. 기존 제품 문맥과 실제 이탈 상태를 확인한 뒤, 별도 승인 범위에서 수정 후 실제 제품 한 사이클을 검증해야 한다.

현재 완료 범위는 **Worker 안정화 수집 수정의 코드·회귀·배포 확인**이다. TASK-022 전체 AI 품질 문제, Assembly 정상 실행, 수정 후 현장 PASS/FAIL 검증은 완료되지 않았다.


### 고정 금색 원통 추가 검토 — 미채택

사용자가 양옆 금색 원통은 독립 고정부라고 확인했다. 중앙 회전축은 제외했다. 같은 저장 원본으로 기존 bridge에 마스크만 추가한 경우와 대응점을 추가한 경우 모두 현장 15장·TRAIN 대조 13장의 기하 수용은 0이었다. 보류 대응점 최대 오차는 19.44px에서 25.24px로 커졌다. 사용자 지시에 따라 운영 특징점에는 추가하지 않는다. 이 비교는 실제 운영 정렬 성공이나 모델 분류 성공을 의미하지 않는다. 비공개 근거: `runs/assembly_ai_022/pose_reuse_followup/fixed_gold_caps/FIXED_GOLD_COMPARISON.json`.
