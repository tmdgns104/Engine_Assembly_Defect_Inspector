# Proxy 촬영 계획

현재 선택 제품과 검사 명세·촬영 순서는 [earbud_case_v0](earbud_case_v0/README.md)에 있다.
T04 도구·하드웨어 smoke 완료 근거는 기존 Task와 Evidence에 보존한다. 이번 준비의
정식 촬영 확인량은 0장이다. 첫 목표는 네 상태 각 한 장이며 총수집량은 검토 후 결정한다.
과거 **3 Session × 9 Scenario × 3 Episode × 1 Capture = 81장**은 이전 일반 물체
계획이다. 현재 이어폰 제품의 확정 수량이나 수집 실적이 아니며 90장 제안도 확정하지 않는다.

## Session / Episode / Capture

- Session: 날짜·카메라 설치·배경·조명을 공유하는 촬영 묶음. 제품 설정을 고정한다.
- Episode: 사람이 물체를 한 번 배치한 상태. 제거·재배치는 새 episode_id로 기록한다.
- Capture: 해당 배치의 개별 PNG. 명령 한 번에 한 장이며 ID는 episode + UTC + UUID 일부다.

ID는 대문자 ASCII로 시작하며 대문자/숫자/밑줄/하이픈을 사용한다. session_id는
32자 이내이고 Windows 예약 이름은 금지한다. episode_id는 80자 이내이며 `session_id_`로
시작한다. 같은 배치 재촬영은 같은 episode_id를 유지한다. 도구가 실제 재배치를 감지하지는 않는다.
카메라/source/해상도는 같은 episode 안에서 바꾸지 않는다. 설정 변경은 새 session이다.

같은 배치의 연속 프레임을 독립 데이터로 세지 않는다. 후속 T06에서 session/episode
group을 보존해 거의 같은 사진이 train/val/test에 흩어지지 않게 한다. 같은 환경의 상관성이
크면 session 단위 분리도 검토한다. 현재는 분할 비율을 정하거나 분할을 실행하지 않는다.

## 보관과 검토

[세션 양식](session-template.json)에 실제 관측값을 채워 raw session 옆 session-info.json으로
보관한다. 정식 raw는 `data/proxy/raw/`, sample/CAMERA_SMOKE는 `data/proxy/smoke/` 등
별도 경로를 쓴다. 실제 사진·manifest·완성된 조건 기록은 Git에 넣지 않는다.
T05 전에 사람이 사진 상태·촬영 정답·가독성·group을 검토한다. 저장 성공은 데이터 준비 완료가 아니다.

기존 profile 미선택 v1은 NORMAL, MISSING_A/B/C, EXTRA_OBJECT, POSITION_SHIFT,
OCCLUSION, BLUR, LOW_EXPOSURE 및 CAMERA_SMOKE를 지원한다. 이는 과거 기록 호환용이다.
이어폰은 명시적으로 profile을 선택한다. CAMERA_SMOKE는 모든 버전에서 물체 배치를
가정하지 않아 expected/removed가 빈 목록이고 unexpected_object=false다.
