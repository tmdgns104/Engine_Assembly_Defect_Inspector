# Proxy Pilot 촬영 계획 — V0-T04

## 목적과 준비물

실제 엔진이 오기 전에 데이터 획득→라벨→그룹 분할→학습 흐름을 연습한다. 이번 T04는 계획·수집 도구·카메라 경로 점검까지만 하며, Labeling은 T05, Split은 T06, Training은 T07에서 한다.

사용자가 안전한 임시 물체 3개를 골라 `OBJ_A`, `OBJ_B`, `OBJ_C`에 대응시킨다. 서로 형태가 충분히 다르고 가능하면 색도 다르며, 화면 안에 동시에 들어가고 쉽게 재배치할 수 있는 물건을 고른다. 예를 들어 불투명한 작은 상자·종이컵·지우개처럼 구별되는 후보를 고려할 수 있으나 실제 물건 선택은 아직 완료되지 않았다. 날카롭거나 위험한 물건, 과도한 반사·투명 물체는 피한다. 엔진 부품명·slot·tolerance로 이름을 바꾸지 않는다.

카메라를 고정하고 평평한 불투명 바탕의 화면 중앙에 검사 영역을 정한다. 세 물체가 경계에 잘리지 않고 동시에 보이도록 둔다. 위치 기준은 세션 기록의 설명으로 남기며 실제 엔진 좌표를 가정하지 않는다.

## Session / Episode / Capture

- **Session**: 한 촬영 작업 단위. 날짜·카메라 설치·배경·조명 조건을 기록한다. S001/S002/S003을 독립적으로 준비하고, 번호만 바꾼 연속 촬영으로 독립성을 주장하지 않는다.
- **Episode**: 물체를 실제로 한 번 배치한 상태. 물체를 제거하거나 다시 놓고 위치·가림·노출 조건을 바꿨으면 새 episode_id를 사용한다. 카메라·해상도·source도 같은 Episode 안에서 바꾸지 않는다.
- **Capture**: 해당 Episode의 개별 이미지. 도구는 명령 한 번에 한 장을 저장한다. 자동으로 만드는 capture_id는 Episode ID + UTC 시각 + UUID 일부다.

ID는 대문자 ASCII 문자로 시작하고 대문자/숫자/밑줄/하이픈을 쓴다. session_id는 32자 이내이며 Windows 예약 이름은 금지한다. episode_id는 80자 이내이고 반드시 `session_id_`로 시작한다. 긴 ID 대신 `S001_NORMAL_01`처럼 짧고 명확한 이름을 권장한다.

같은 배치에서 연속 프레임을 많이 저장해 서로 다른 데이터처럼 세지 않는다. 재촬영하더라도 배치가 같으면 같은 episode_id를 유지한다. 도구는 실제 물체 재배치를 감지하지 않으므로 사용자가 이를 기록해야 한다.

## 시나리오와 촬영 행동

| Scenario | 사람이 만드는 상태 | metadata의 제거/추가 의도 |
|---|---|---|
| NORMAL | A/B/C를 검사 영역에 모두 배치 | 제거 없음 |
| MISSING_A | A만 제거하고 B/C 유지 | removed=[OBJ_A] |
| MISSING_B | B만 제거하고 A/C 유지 | removed=[OBJ_B] |
| MISSING_C | C만 제거하고 A/B 유지 | removed=[OBJ_C] |
| EXTRA_OBJECT | A/B/C 외 안전한 임시 물건 하나 추가 | unexpected_object=true |
| POSITION_SHIFT | 세 물체 중 하나 위치를 의도적으로 변경 | notes에 변경 설명 |
| OCCLUSION | 물체 일부를 안전한 종이 등으로 가림 | notes에 가림 설명 |
| BLUR | 안전하게 작은 움직임/초점 조건으로 흐림 유도 | notes에 방법 설명 |
| LOW_EXPOSURE | 눈부심 없이 조도를 낮춰 어둡게 만듦 | notes에 조명 설명 |

`object_configuration.objects_expected`는 정상 조립의 목표 목록 A/B/C, `objects_removed`는 촬영자가 선언한 제거 의도다. 이미지에서 검증된 존재 여부나 Bounding Box annotation이 아니다. CAMERA_SMOKE에서는 물체 배치를 가정하지 않아 expected/removed가 모두 빈 목록이다.

## Pilot 규모와 누수 방지

제안: **3 Session × 9 Scenario × 3개의 별도 배치 Episode × 1 Capture = 81장**.

각 Session은 27개의 실제 배치에서 27장을 만든다. 처음에는 S001의 NORMAL 한 배치와 MISSING_A 한 배치만 단계별로 확인한 후 나머지를 진행한다. 필요할 때만 불량 촬영을 추가·재촬영하고 동일 배치의 그룹을 보존한다. CAMERA_SMOKE와 sample 이미지는 81장에 포함하지 않는다.

T06에서 session_id와 episode_id를 모두 유지해 grouping 기준으로 사용한다. 같은 Episode의 거의 같은 이미지를 train/val/test에 흩뜨리지 않는다. 같은 Session끼리 배경·조명 상관성이 크면 Session 단위 분리까지 검토한다. 이번에는 비율·분할을 실행하지 않으며 3개 Session만으로 모든 환경 일반화가 검증됐다고 하지 않는다.

## 보관과 검토

`session-template.json`을 복사해 실제 물체 대응·촬영 조건을 기입하고 raw Session 옆 `session-info.json`으로 보관한다. 정식 raw는 `data/proxy/raw/`, 하드웨어 smoke는 `data/proxy/smoke/` 또는 별도 Jetson 검증 폴더로 분리한다. 실제 raw와 session-info/manifest는 Git에서 제외한다. 소스 코드, 빈 template, schema, 계획과 작은 검증 요약만 Git에서 추적한다.

T05 이전에 사람이 이미지 가독성, 실제 물체/시나리오, 손상/누락, 그룹 정보를 검토해야 한다. 도구의 저장 PASS는 라벨 품질이나 Dataset 준비 완료를 뜻하지 않는다.

## 첫 물리 촬영의 Human Action

카메라 smoke 검증과 계획 확인 후에만 진행한다. 사용자는 우선 세 물체를 고르고 A/B/C 대응을 알려 준다. 다음으로 화면 중앙 검사 영역에 모두 놓고 NORMAL 상태를 확인한다. 그 다음 A만 제거해 MISSING_A를 만든다. 한 번에 전체 81장 행동을 요구하지 않는다.

기존 SSH 인증과 실제 카메라 포맷 확인이 끝나기 전에는 아래 명령을 검증 완료 명령으로 취급하지 않는다. 아래는 Jetson에 두 스크립트를 배치한 폴더에서 사용할 예시다. 현재 지원 포맷이 다르면 실측값으로 바꾼다.

```bash
timeout 20s python3 capture_proxy.py --camera /dev/video0 --fourcc YUYV --width 640 --height 480 --fps 30 --output-root ./data/proxy/raw --session-id S001 --episode-id S001_NORMAL_01 --scenario NORMAL --notes "A B C placed by operator"
```

사람이 A를 제거하고 확인한 다음:

```bash
timeout 20s python3 capture_proxy.py --camera /dev/video0 --fourcc YUYV --width 640 --height 480 --fps 30 --output-root ./data/proxy/raw --session-id S001 --episode-id S001_MISSING_A_01 --scenario MISSING_A --notes "A removed by operator"
```

T04의 정식 Dataset 수집과 계획 승인 여부는 Task 상태에 따르며, 사용자 행동 없이 완료로 표시하지 않는다.
