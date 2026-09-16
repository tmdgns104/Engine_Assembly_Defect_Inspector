# JETSON-P0-002R3 — NvMap Exact-Stage Isolation

2026-09-16. **NVMAP_NOT_REPRODUCED_IN_BOUNDED_STAIRCASE / ROOT_CAUSE_UNCONFIRMED. P0-003 = BLOCKED.**

A~H 각1회와 H 추가5회, 총13개 새 process에서 stderr가 모두 비어 있었다. Camera/모델/3회 detect/Recipe/encode/Journal/close/최종 process exit까지 관측했지만 최초 NvMap Case나 stage interval은 **관측되지 않았다**. P0-002R2 오류가 사라졌거나 해결됐다고 결론내리지 않는다. 추가 실행이나 복구는 수행하지 않았다.

## 수집 방식과 해석 경계

Jetson의 parent가 `Popen`의 stdout/stderr pipe를 `selectors`와 `os.read`로 함께 읽었다. stderr newline-complete line마다 수신 즉시 `time.monotonic()`을 붙이며, 원시 byte log와 `pipe_events.jsonl`을 즉시 flush했다. chunk 경계에서 나뉜 line은 합쳐 저장한다. 여러 line이 같은 read에 포함되면 수신 timestamp를 공유할 수 있다. Child는 stage 진입 monotonic, `/proc/meminfo`, 초기화된 CUDA의 free/total/allocated/reserved/peak, memory snapshot 완료 시각을 별도 `stages.jsonl`과 flush stdout에 기록했다.

Parent/child는 같은 host clock을 사용한다. stderr 수신 시각 앞뒤의 child stage marker로 `BETWEEN_<LEFT>_AND_<RIGHT>`를 분류하며, 마지막 BEFORE_PROCESS_EXIT 이후에는 `POST_APPLICATION_TEARDOWN_INTERVAL`이다. **pipe 수신 시각은 native emission 시각이 아니다.** buffering·스케줄링·snapshot 자체 비용으로 인접 구간이 달라질 수 있다. 이 계측만으로 CUDA destructor나 camera를 원인으로 지정할 수 없다. 이번에는 분류할 실제 오류 line이 없었다.

Parent는 BEFORE_PROCESS_EXIT 이후에도 양쪽 pipe EOF를 확인하고 process exit까지 기다렸다. 모델과 frame 객체를 diagnostic global에 유지해 임의 `del`, GC, empty_cache 없이 정상 interpreter teardown으로 넘겼다. 종료 직전 marker 뒤에는 진단 결과 JSON 기록과 정상 Python 종료도 포함된다. 각 Case에 종료 전 loaded libraries와 process list를 남겼고, 오류가 있을 경우에는 첫 stderr 수신 즉시 살아 있는 child의 maps/status/process list/meminfo도 읽도록 했다. 실제 오류가 없어 해당 first-error snapshot은 생성되지 않았다.

합성 collector test는 framework/GPU/camera 없이, 분할된 synthetic marker line과 atexit marker를 출력했다. active-stage interval과 post-application teardown interval 분류가 모두 통과했다. synthetic marker는 실제 NvMap 문자열이 아니며 실제 Case 결과에 포함하지 않는다.

## Staircase 결과

| Case | 추가한 실행 범위 | warmup detect | fresh detect | stderr / exit |
|---|---|---:|---:|---|
| A | Camera open → 5 frames → close; torch import/CUDA 초기화 없음 | 0 | 0 | empty / 0 |
| B | Camera + 기존 Detector construct/CPU load/CUDA ready | 0 | 0 | empty / 0 |
| C | B + 승인 저장 이미지 warmup | 1 | 0 | empty / 0 |
| D | C + LOCAL_TEST fresh frame1 | 1 | 1 | empty / 0 |
| E | C + LOCAL_TEST fresh frame3 | 1 | 3 | empty / 0 |
| F | E + 기존 Recipe assess | 1 | 3 | empty / 0 |
| G | F + 기존 encode_evidence; image 파일 저장 없음 | 1 | 3 | empty / 0 |
| H | G + 새 Journal admit/finish/local publication | 1 | 3 | empty / 0 |
| H_repeat_1~5 | H와 같은 진단 코드·설정, 각 새 process/data root | 각1 | 각3 | 모두 empty / 0 |

총 warmup11회 + fresh detect28회 = **detect API 호출39회**. 내부 Ultralytics warmup과 forward 횟수로 환산하지 않는다. 실험 process13개가 순차로 실행됐으며 동시 GPU 진단은 없었다. H 조건은 최초1회+추가5회=6회다. Model-only Case는 이번에 실행하지 않았다. 이전 P0-002R raw-model PASS는 배경 근거이며 현재 조건의 동시 대조군으로 취급하지 않는다.

각 Case의 단계와 기능은 추가되는 범위만 실행했다. H에서는 기존 R2 순서를 유지해 warmup 후 Journal 초기화, trigger 생성 직후 admit, 그 다음 frame/detect3개, Recipe/encode/finish/publication을 수행했다. admit를 encode 뒤로 옮기지 않았다. H당47개, 전체456개 stage event가 있다. A는 CUDA를 일부러 초기화하지 않으므로 CUDA_INIT stage가 없다.

H의 주요 marker는 IMPORT/CUDA_INIT/CAMERA_OPEN/PREVIEW_CAPTURE의 START·END, MODEL_CONSTRUCT_START → MODEL_CPU_LOAD_OBSERVED → MODEL_CUDA_READY → MODEL_CONSTRUCT_END, PRETRIGGER_WARMUP_START·END, TRIGGER_CREATED, 각 FRAME_n_CAPTURE_START → FRAME_n_SELECTED → DETECT_n_START·END, RECIPE/EVIDENCE_ENCODE/JOURNAL_ADMIT/JOURNAL_FINISH/LOCAL_PUBLISH/CAMERA_CLOSE/JOURNAL_CLOSE의 START·END, BEFORE_PROCESS_EXIT다. Journal open과 trigger 직전 preview도 별도로 표시했다.

실제 오류가 없으므로 **최초 발생 직전 MemAvailable/CmaFree/CUDA allocated/reserved는 N/A**다. 전체 관측 범위는 다음과 같다.

| 항목 | 최소–최대 |
|---|---:|
| MemAvailable | 1,786,848–3,034,204 kB |
| CmaFree | 0–43,980 kB |
| SwapFree | 3,342,776–3,494,584 kB |

CUDA 개별/peak/free/total 값은 각 stage와 verification JSON에 저장했다. CmaFree0에서도 이번 실행은 통과했다. 메모리 범위만으로 OOM·CMA 부족·단편화·driver 문제를 확정하거나 배제하지 않는다. Python exception0, NVML_SUCCESS assertion0, CUDACachingAllocator 문자열0, NvMap 문자열0이다. 타임스탬프 계측과 memory query는 원래 process의 타이밍을 바꿀 수 있다. 13회 clean은 production 신뢰도 기준이나 이전 장애의 복구 증거가 아니다.

## 원본과 진단 범위

기존 R2 candidate `/home/jetson/oned_device_bench/candidates/app_v008_dev_p0_002_reaccept/runtime`를 읽기만 했다. NumPy1.26.4 overlay는 기존 경로를 process-local로 사용했다. torch2.8.0/CUDA12.6/OpenCV5.0.0 및 HCAM0 MJPG1280×720@30 설정을 유지했다. OpenCV5 metadata의 numpy>=2 충돌은 여전히 존재한다.

Jetson의 모든 새 파일은 `/home/jetson/oned_device_bench/diagnostics/p0_002r3_nvmap/` 아래에 생성했다. 각 H의 Journal/assets와 local publication도 자기 subfolder 안에만 있다. Ultralytics/Matplotlib/torch/CUDA disk cache/temp 위치를 이 경로로 격리했으며 allocator 환경변수는 바꾸지 않았다. Camera 설정·기존 Fresh Frame source·global 환경·current symlink 변경0, 패키지 설치/재부팅/시스템 설정/PLC/MQTT/모델변환/학습/commit/push0이다.

H는 기존 Recipe의3관측·spacing0.15초·window3000ms를 유지했다. 물리 view와 calibration을 미승인으로 두어 Recipe 결과는 REVIEW다. raw3/overlay1은 진단 Journal용이며 Dataset이 아니다. Journal.finish 반환 후 local file publication을 기록했고 PLC/network publish는 없었다. H 반복은 각각 새 Journal을 사용했다. 실제 conveyor acceptance와 P0-003 성능 분석은 수행하지 않았다.

app_v007/app_v1/overlay/P0-002·R2 candidates/제품·best.pt/기존 DB·assets/R2 candidate DB·assets/이전 diagnostics/사용자 패키지·settings 및 알려진 cache의 전후 SHA가 동일하다. Jetson 보호33그룹+overlay inventory+current symlink를 비교했다. Windows Fresh Frame source, PC mirror, 이전 raw evidence도 동일하다. OS 전체의 background write를 감사했다는 의미가 아니라 열거한 보호 경로의 content hash 검증이다. 다른 팀원 작업은 되돌리지 않았다.

## 산출물과 다음 결정

- 기계 판정: [JETSON-P0-002R3.json](../verification/JETSON-P0-002R3.json).
- Windows raw: `runs/jetson_p0_002r3/{A..H,H_repeat_1..5}.json`에 parent timeline/stderr/application evidence. `before.json`, `after.json`, `windows_before.json`, `inventory.json`에 보존 근거.
- Jetson Case별 `stdout.log`, `stderr.log`, `pipe_events.jsonl`, `stages.jsonl`, `child_result.json`, `process.json` 보존. 실제 stderr.log는 모두0bytes.
- collector 합성 시험과 결과/구간/보존/compile/git diff 검사는 `runs/jetson_p0_002r3/final_checks.json`에 기록한다. 기존102 tests는 runtime source 변경이 없어 재실행하지 않았다.

진단은 정해진 횟수까지 완료했다. **ROOT_CAUSE_UNCONFIRMED / P0-003 BLOCKED**를 유지한다. 발생 구간을 특정하지 못했으므로 패키지 교체나 allocator 우회를 다음 복구 방식으로 결정하지 않는다. 추가 재현·복구·재수용 Task는 별도로 정해야 한다.
