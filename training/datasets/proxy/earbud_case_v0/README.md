# 이어폰 케이스 첫 촬영 준비

제품 ID는 `earbud_case_v0`다. 엔진 모형 도착 전 촬영 → 라벨링 → 데이터 분리 →
학습 → 튜닝 → 평가 → ONNX 변환 → Jetson 실행 → 검사 판정 → DB 저장 → 화면 조회
과정을 준비하기 위한 Proxy 제품이다. 이번에는 **검사 명세와 첫 네 장 촬영 준비**만 한다.

## 배치와 촬영 정답

뚜껑이 열린 케이스 안에 이어폰이 들어 있는 상태를 검사한다. 책상 위 세 칸에
물체를 따로 놓는 방식이 아니다. `earbud_left`는 실제 L 이어폰, `earbud_right`는
실제 R 이어폰, `case`는 케이스다. 옛 이름에 대응하면 OBJ_A/B/C 순서다.
이미지의 좌우만으로 L/R을 정하지 않는다. 실물 표시와 케이스 방향을 확인하고
첫 네 장 동안 방향을 고정해 session-info에 기록한다.

| 순서 / scenario | 사람이 만드는 상태 | objects_removed | episode_id 예 |
|---|---|---|---|
| 1 / NORMAL | 양쪽 이어폰이 열린 케이스의 해당 자리에 있음 | `[]` | `S001_NORMAL_01` |
| 2 / MISSING_LEFT | 왼쪽만 제거, 오른쪽과 케이스 유지 | `[earbud_left]` | `S001_MISSING_LEFT_01` |
| 3 / MISSING_RIGHT | 왼쪽을 되돌리고 오른쪽만 제거 | `[earbud_right]` | `S001_MISSING_RIGHT_01` |
| 4 / MISSING_BOTH | 양쪽 제거, 케이스 유지 | `[earbud_left, earbud_right]` | `S001_MISSING_BOTH_01` |

시나리오와 기대 상태는 촬영자가 선언한 **정답 정보**이며 AI 판정 결과가 아니다.
`objects_expected`는 정상 상태의 세 객체 목록으로, 누락 시나리오에서도 유지한다.
위치 Bounding Box 정답은 별도 라벨링 작업이며 자동 생성하지 않는다.

## 최종 검사 프로그램의 기준 — 이번에는 명세만

| 결과 | 기준 |
|---|---|
| PASS | 열린 케이스와 검사 자리가 충분히 보이고 양쪽 이어폰이 해당 자리에 있는 것으로 확인되며, 사진과 결과의 DB 저장까지 성공 |
| FAIL | 검사 자리가 충분히 보이는 상태에서 한쪽 또는 양쪽 이어폰 누락이 확인됨 |
| REVIEW | 닫힌 뚜껑, 가림, 흐림, 심한 반사, 검사 영역 이탈, 낮은 신뢰도 등으로 확인하기 어려움. 케이스가 보이지 않는 경우도 정상 처리하지 않음 |
| ERROR | 카메라, 모델 실행, 파일 저장 또는 DB 저장 등 시스템 오류 |

시스템 오류는 ERROR로 보고한다. 모델 미검출만으로 누락을 확정하지 않고, 케이스 밖
이어폰을 정상 장착으로 세지 않는다. 각 자리의 존재/비어 있음/확인 불가를 구분할 방법,
좌표, 품질·신뢰도 임계치는 실제 사진과 이후 Validation으로 정한다. 현재는 미정이다.
충전·전기적 접촉·미세 체결 깊이는 검사 범위 밖이다. Detector/Decision/DB/HMI 구현 및
이 기준의 실행 검증은 기존 V0-T11~T14 이후 작업이다.

실제 추론은 **새 이미지, 학습된 모델, 제품별 검사 기준, 이미지 품질과 시스템 상태**만
사용해야 한다. 학습용 scenario, objects_removed, 파일명에 든 MISSING_LEFT 같은 정답을
읽어 PASS/FAIL을 결정하면 안 된다. `profile.json`도 수집 상태를 정의하는 Training
자료다. 추후 Runtime 제품 기준은 별도 Recipe로 작성하고 제거 시나리오를 전달하지 않는다.

## 촬영 조건과 사람의 작업

- 케이스 안 양쪽 자리와 빈자리가 모두 보이는 구도를 선택한다. 수직 하향을 우선하되
  뚜껑이 가리면 시야가 확보되는 고정 구도를 택하고 각도·방향·높이를 기록한다.
- 사진을 찍을 때 손을 화면에서 뺀다. 카메라·조명·배경·케이스 방향은 네 장 동안 유지한다.
- 반사나 흐림으로 이어폰과 빈자리를 구분하기 어려우면 수량을 늘리기 전에 조건부터 고친다.
- 배치 변경은 사람이 하고 매번 새 episode_id를 쓴다. 같은 환경의 네 상태는 같은 session_id다.
  조건 변경이 필요하면 새 session으로 시작하고 이전 촬영과의 관계를 notes에 남긴다.
- 첫 네 장은 구도와 기록 방법 확인용이다. 학습·성능 검증에 충분한 데이터가 아니다.
  전체 수집 규모는 사진 검토 후 따로 결정한다. 과거 81장 계획과 90장 제안은 확정 수량이 아니다.
- 휴대폰 참고 사진은 Jetson 촬영으로 기록하지 않는다. 도구로 점검할 때는 `--sample`로
  처리해 정식 수집과 분리한다. Windows 합성 이미지와 CAMERA_SMOKE도 정식 데이터에서 제외한다.

## Jetson에서 사람이 실행할 순서 — 아직 미실행

현재 카메라 모델·장치 번호·지원 포맷은 **미확인**이다. 과거 장치 번호나 YUYV 22 FPS를
재사용 값으로 확정하지 않는다. 기존 환경에서 다음 조회만 먼저 수행한다.

```bash
v4l2-ctl --list-devices
ls -l /dev/v4l/by-id/ /dev/video*
```

목록에서 후보를 골라 현재 값을 변수에 넣고 조회한다. `Video Capture` 기능 및 포맷을
확인한다. 도구가 없으면 결과를 남기고 멈춘다. 설치나 시스템 변경은 이 안내의 범위가 아니다.

```bash
read -r -p '확인할 현재 카메라 노드: ' CAMERA_NODE
v4l2-ctl --device "$CAMERA_NODE" --all
v4l2-ctl --device "$CAMERA_NODE" --list-formats-ext
```

프리뷰가 필요하면 먼저 구도를 확인하고 **사용자가 프리뷰를 정상 종료**한 뒤 촬영 CLI를
실행한다. 두 프로그램이 같은 카메라를 동시에 열지 않도록 한다. 촬영 명령이 끝나면
카메라가 해제된다. 저장 PNG는 이미지 뷰어로 확인하고 다음 배치를 준비한다.
점유 프로세스를 임의로 종료하지 않는다.

실제 촬영은 Jetson의 저장소 루트 기준 아래 형태다. 독립 폴더를 사용한다면 두 스크립트와
선택한 profile.json을 함께 배치하고 경로를 맞춘다. 지금 Windows에서는 전달·실행하지 않았다.
첫 실행 전 [세션 양식](../session-template.json)을 S001/session-info.json에 복사하고 실제
관측 조건을 채운다. 양식은 사람이 관리하며 촬영 CLI가 읽거나 검증하지 않는다.
`CAMERA_NODE`, `FOURCC`, `WIDTH`, `HEIGHT`, `FPS`를 현재 장치 확인값으로 설정해야 한다.
현재 CLI는 YUYV/MJPG와 양의 정수 FPS를 받는다. 기본값은 현 장치 검증값이 아니다.

```bash
timeout 20s python3 training/scripts/capture_proxy.py \
  --profile training/datasets/proxy/earbud_case_v0/profile.json \
  --camera "${CAMERA_NODE:?현재 노드 필요}" --fourcc "${FOURCC:?확인한 포맷 필요}" \
  --width "${WIDTH:?확인한 폭 필요}" --height "${HEIGHT:?확인한 높이 필요}" --fps "${FPS:?확인한 FPS 필요}" \
  --output-root data/proxy/raw --session-id S001 \
  --episode-id S001_NORMAL_01 --scenario NORMAL --notes "operator arranged both earbuds in open case"

python3 training/scripts/verify_proxy_captures.py --output-root data/proxy/raw --session-id S001
```

먼저 **정상 사진 한 장을 촬영·검토**한다. 이후 표의 상태를 사람이 한 번씩 만들고
episode_id/scenario를 해당 행으로 바꿔 한 명령씩 실행한다. 자동 반복 촬영하지 않는다.
각 사진에서 실물 L/R, 양쪽 자리 가독성, 상태 정답, 손·반사·흐림을 사람이 확인한다.
verifier 성공은 저장 무결성 확인이며 실제 상태·AI 성능·검사 결과의 PASS가 아니다.
실제 촬영과 사진 검토가 끝나기 전 V0-T05 라벨링을 시작하지 않는다.

## 엔진으로 재사용

공통 촬영·파일명·세션 잠금·PNG/JSONL 저장·검증기를 그대로 쓰고 수집 제품의
ID/부품 클래스/시나리오는 JSON으로 교체한다. 촬영 조건은 세션 기록, 정상 조립과
검사 자리는 제품 명세와 향후 Recipe, 학습 모델과 평가 데이터·판정 기준은 별도 자산으로
관리한다. Camera/Detector 인터페이스, 검사 결과 형식, DB 저장 및 화면 구조를 재사용하는
기존 방향을 유지하며 이어폰 전용 프로그램을 만들지 않는다. 실제 엔진 부품명·개수·좌표·
임계치는 엔진 도착 후 정한다. 가상 네 부품 테스트는 설정 교체 경로만 검증한다.
