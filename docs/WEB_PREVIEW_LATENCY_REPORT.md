# TASK-023 — 웹 미리보기 지연 수정 및 실제 한 제품 검증

2026-10-15. **운영 적용 및 승인된 한 제품 시험 완료.** 조립 전처리 복구와 구분한다.

## 변경과 적용

- 소스 commit: `52df5d22b13130493e3268de744724c9395b2723`.
- 실제 Release: `engine-integrated-8831b41d4448da2d`, 184개 파일 해시 일치.
- `jetson/apps/edge_service/inspection.py`: `preview_snapshot()`이 짧은 잠금에서 동일 세대의 JPEG·프레임 식별자·시각을 함께 읽는다. Journal 조회/전체 status 생성은 하지 않는다.
- `inspection_api.py`: preview API에 가벼운 snapshot 및 ETag/304 적용. 오래되거나 죽은 Worker는 503. 서버 프레임 나이는 Jetson의 monotonic만으로 계산한다.
- `line_hmi.html`: 기존 상태/이력 1Hz와 이미지 갱신을 분리했다. 이미지 fetch→decode→display 한 건만 진행하고 중복 frame ID를 표시 FPS로 세지 않는다. 최신 이미지 만료 표시·요청/디코드 종료·object URL 회수 유지.
- 카메라 capture/AI/preview 생성 순서, Worker, 모델, PLC, OpENer C, 안정 세 프레임, 조립 경로는 변경하지 않았다.

## 실제 대기 상태 측정

| 항목 | 변경 전 | 변경 후 |
|---|---:|---:|
| 약 30초간 서로 다른 표시 프레임 | 29 | 163 |
| 실제 새 프레임 표시 FPS | 0.966 | 5.432 |
| 브라우저 이미지 HTTP 평균 / p95 | 17.07 / 20.7ms | 9.55 / 14.0ms |
| 같은 1Hz 서버 측 표본의 이미지 나이 평균 | 254.97ms | 251.37ms |
| Worker sequence / source-time 기준 처리 속도 | 10.838Hz | 10.866Hz |
| health 갱신 평균 간격 | 110.969ms | 110.897ms |

HTTP 전후와 프레임 ID 전후는 각각 별도의 명시된 30초 창이다. 변경 전 두 번째 HTTP 창의 frame ID 로그는 누락돼 FPS에 사용하지 않았다. 센서 exposure-to-display 지연은 미측정이며, Jetson과 브라우저 clock을 직접 빼지 않았다. 대기 표본의 정확한 health 최대 간격은 미측정으로 남긴다. 전체 상태 API 호출 빈도는 1Hz를 유지했다.

## 승인된 실제 한 제품 시험

- 검사 ID `769713b76bd7406fa8cceb1fc443ff3f`. 실제 새 PNG 3장 → 원시 부품 존재 검사 PASS → Journal 저장 → 필수 Assembly 실행 → 전처리 거부로 Assembly REVIEW → 통합 REVIEW.
- 기존 정책대로 NG Result 1회, 다음 cyclic 패킷 Done 1회. sequence `5570 → 5571`, 요청 LOW 복귀 관측. 현장 담당자가 정지 후 재가동과 검사 중 영상 갱신을 확인했다.
- 76.724초 관측에 서로 다른 표시 프레임 421개, **5.487FPS**, 가장 긴 표시 간격 329.2ms. 실제 camera Worker BUSY 응답 동안도 서로 다른 7프레임이 표시됐다. 이 전체 창 FPS를 BUSY 전용 FPS로 해석하지 않는다.
- 시험 중 기록된 ready=false 없음. 이 서비스 실행 전체의 health 최대 간격은 208.45ms로 시험 구간의 상한도 된다. Class1 open 1회, timeout 0회. 장기 연결 안정성이나 연속운전 일반 보장은 아니다.
- 현장 최종 STOP 확인 후 `Mc_Run/Request/Result/Done=LOW`, 저장·Worker·Assembly 미완료 작업 없음. 단일 서비스/카메라/C 유지. 새로운 요청이나 출력은 추가하지 않았다.
- 기존 cyclic 계약에는 독립적인 PLC 소비 ACK가 없다. `Result/Done 송신 + Request 해제 + 현장 재가동 확인`을 근거로 하며 별도 ACK 수신으로 보고하지 않는다.

## 검증·백업·한계

- 로컬 집중 Python: 26 PASS, 원본 fixture 비공개 1 SKIP. 별도 안정 프레임 회귀 9 PASS. JavaScript 미리보기 루프 3 PASS. ARM64 preview snapshot 3 PASS.
- 원래 current/config/unit/Release 및 SQLite backup API 자료를 노트북에서 읽고 169개 파일 SHA와 DB integrity를 확인했다. 백업 SHA `62b74d55aea53da1e92f5d62bb1c68a853c95609f97a486d4a7845ee7191bf80`.
- 전체 배포 archive SHA `e8f08a1eade172777e8d79189a7d6053d0482eab60f5cbf11c4ca668c57e1afb`.
- 실제 파일과 Git은 Python 1개/HTML 1개의 기존 CRLF 정규화 차이가 있다. LF 정규화 내용은 일치하며, raw byte SHA가 같다고 주장하지 않는다. 실제 Release manifest는 배포 바이트를 기준으로 검증했다.
- 코드 복원 시에도 새로운 Journal·사진·문맥·승인 소비 기록은 되돌리지 않는다. 이번 복원은 시행하지 않았다.
- 이 시험은 미리보기와 기존 검사/통신 경로를 검증했다. **Assembly 정렬 및 분류 성공을 뜻하지 않는다.** 해당 문제는 TASK-022 후속으로 이어간다.

개인 현장 증거(공개 Git 제외): `runs/web_preview_023/IDLE_COMPARISON.json`, `TRIAL_VERIFICATION.json`, `TRIAL_BROWSER.json`, `TRIAL_STATUS.jsonl`, `TRIAL_C_events.jsonl`, `TRIAL_COLLECTION.json`, `COMMIT_SOURCE_EQUIVALENCE.json`, 노트북 백업·배포 영수증.
