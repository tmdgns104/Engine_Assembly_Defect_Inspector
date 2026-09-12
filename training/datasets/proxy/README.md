# Proxy Capture Workflow

이 폴더는 작은 Dataset 설계 자료만 추적한다. 현재 제품의 검사 기준과 첫 네 장 순서는 [earbud_case_v0](earbud_case_v0/README.md)에 있다. 공통 [촬영 계획](proxy_capture_plan.md), [세션 양식](session-template.json), [metadata schema](capture-schema.json), [profile schema](profile-schema.json)를 함께 사용한다.

## 실행과 저장 구조

`training/scripts/capture_proxy.py`는 Dataset 수집 전용 CLI다. Production `src/contracts.Camera`의 구현체나 V4L2Camera를 만들지 않는다. 기존 CameraFrame/FrameMetadata와 같은 frame identity·UTC·width/height 의미를 유지하되 수집 스크립트는 독립적으로 배포한다. Detector나 검사 Request/Result를 사용하지 않는다.

Python 3.10 이상과 기존 OpenCV가 필요하다. Windows는 기존 `.venv`를 사용한다. 독립 실행에는 이 스크립트와 `verify_proxy_captures.py`, 선택한 profile.json을 함께 사용한다. JSON은 표준 라이브러리로 읽어 추가 설치가 없다. 현재 장치 확인과 실행은 사람이 Jetson에서 수행한다.

```text
data/proxy/raw/
  S001/
    session-info.json                  사람이 template을 채운 조건 기록
    manifest.jsonl                     성공한 capture metadata 한 행씩
    S001_NORMAL_01/images/<capture_id>.png
    S001_MISSING_LEFT_01/images/<capture_id>.png
```

Windows sample 확인(실제 카메라 접근 없음, 기존 테스트 이미지 경로를 지정):

```powershell
.venv\Scripts\python.exe training/scripts/capture_proxy.py --profile training/datasets/proxy/earbud_case_v0/profile.json --sample <existing-image.png> --output-root data/proxy/smoke --session-id SAMPLE01 --episode-id SAMPLE01_NORMAL_01 --scenario NORMAL
.venv\Scripts\python.exe training/scripts/verify_proxy_captures.py --output-root data/proxy/smoke --session-id SAMPLE01
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

카메라 입력은 Linux OpenCV의 CAP_V4L2를 명시한다. 한 호출에서 startup frame 5개를 읽어 앞의 프레임을 버리고 마지막 한 장만 PNG로 저장한다. 요청 해상도·FOURCC가 실제 협상 결과와 다르면 실패한다. FPS는 요청값과 장치 보고값을 구분하며 실제 처리 성능을 측정한 것으로 해석하지 않는다. `captured_at`은 host가 프레임을 읽은 직후의 UTC 시각이며 센서 노출시각이 아니다. imshow·GUI·VNC·GStreamer display가 필요 없다. OpenCV read가 지연될 수 있으므로 Jetson 명령은 외부 `timeout 20s`로 제한하고 timeout은 실패로 기록한다.

## Metadata와 grouping

v1 JSONL 필드는 schema_version, capture_id, session_id, episode_id, scenario, captured_at, object_configuration, device, camera_source, source_kind, width, height, image_path, image_bytes, image_sha256, notes다. image_path는 output root 기준 상대 경로다. device는 hostname이고 인증정보를 넣지 않는다.

`--profile` 미선택은 기존 v1 OBJ_A/B/C 동작이다. 선택하면 v2가 되며 `profile_snapshot`과 `profile_sha256`을 추가한다. 사본에는 profile_schema_version, product_id, profile_version, objects, scenarios가 있다. 시나리오마다 제거 목록과 unexpected_object를 명시하며 이름의 접미사로 제거 대상을 추측하지 않는다. NORMAL은 제거/추가가 없고 CAMERA_SMOKE는 예약 의미를 재정의할 수 없다.

해시는 `json.dumps(profile, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`의 UTF-8 바이트 SHA256이다. 소스 파일 자체의 바이트 해시가 아니며 공백 차이는 무시한다. verifier는 현재 profile 파일 없이 사본·해시·시나리오 구성을 검증한다. profile을 수정할 때 버전을 올리고 새 session_id를 사용한다. 같은 session에 다른 버전/해시나 v1/v2를 섞으면 거부한다. 이 해시는 우발적 불일치를 찾는 수단이며 사본과 해시를 함께 바꾼 악의적 변조를 인증하는 서명이 아니다.

`source_kind=sample` 또는 `scenario=CAMERA_SMOKE`인 행은 정식 Pilot에서 제외한다. scenario는 물체 배치 의도이며 label이나 검증된 실제 상태가 아니다. 양식의 null도 관측 완료를 뜻하지 않는다.

`capture-schema.json`은 v1/v2 구조 정의이며 v2는 같은 폴더의 `profile-schema.json`을 참조한다. **실행 시 authoritative validator는 `capture_proxy.validate_record()`**이며 scenario-물체 구성 일치, profile 해시, UTC 정규형, session/episode/capture ID와 경로 연계를 추가 검사한다. `read_manifest()`는 session profile과 episode 불변 조건을 검사한다. 임의 필드·bbox label·검사 결과는 거부한다. JSON Schema 전용 라이브러리를 설치하지 않아도 CLI가 검증한다. verifier의 captures/source_counts/scenario_counts는 저장 기록 수이며 AI 판정 집계가 아니다.

## 덮어쓰기·실패·복구

- 새 이미지에는 exclusive create를 사용한다. 기존 capture_id나 image는 덮어쓰지 않는다.
- Session별 `.capture.lock`은 동시에 두 writer가 manifest를 바꾸는 것을 막는다. 기존 lock이 있으면 PID/장치 정보를 확인하고 사용자 또는 현재 작업의 프로세스인지 판단한다. 출처가 불명확한 프로세스를 kill하거나 lock을 자동 제거하지 않는다.
- 이미지를 쓰고 fsync한 후 manifest를 append/fsync한다. 두 파일에 걸친 완전한 transaction은 아니다. 쓰기 실패·전원 중단 시 orphan PNG, 불완전한 JSONL 행이나 lock이 남을 수 있다. 오류를 반환하고 원본을 보존하며, 다음 writer가 이런 불일치를 발견하면 append를 거부한다. 두 파일이 온전히 기록된 후 fsync 오류가 발생한 경우에도 실패 메시지가 날 수 있으므로 재시도 전에 verifier로 실제 상태를 확인한다.
- 복구할 때는 먼저 Session을 백업하고 writer 종료 여부, PNG hash/reload, 마지막 manifest 행을 검사한다. 기존 이미지나 metadata를 추정해 덮어쓰지 않는다. 별도 복구 판단 전까지 새 Session을 만들더라도 동일 실제 배치의 관계를 기록해야 한다.
- `verify_proxy_captures.py`는 writer 종료 후 모든 PNG를 재로드하고 크기·SHA256·metadata 연결·중복과 orphan을 읽기 전용으로 검사한다. 네트워크 파일시스템의 분산 lock이나 악성 동시 파일 변경까지 보장하지 않는다.

## 실기기 근거와 다음 작업

현재 촬영은 [Windows 노트북 USB 카메라 화면](../../capture_windows/README_KR.md)을 사용한다. 기존 V4L2 CLI를 보존하며 같은 저장·검증 함수를 재사용한다.

기존 사용자 실행 CAMERA_SMOKE 3장의 결과는 [V0-T04 검증 기록](../../../docs/verification/V0-T04.txt)에 보존한다. 당시 장치 번호와 포맷은 역사적 관측이며 현재 장치 확인값이 아니다. 이번 작업에서는 Jetson 접속이나 촬영을 하지 않았다. 현재 촬영 안내와 프리뷰 종료 순서는 제품 README를 따른다.
