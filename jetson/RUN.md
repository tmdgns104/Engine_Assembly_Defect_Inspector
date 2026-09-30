# Runtime 실행 안내

이 묶음은 개발본이며 실제 PLC·생산 수용 완료가 아닙니다.
`release.json`은 묶음의 파일 해시, `/api/v1/release`는 시작 때 로드한 식별정보입니다.

`current`와 나란히 `assets`, `config`, 운영 데이터, 확인된 Python 환경을 둡니다.
`current/config` 링크는 `../assets/runtime_config`를 가리킵니다.
장치별 `config/runtime.json`에서 package/station/data_root/pythonpath/port를 지정합니다.
개발 자동 반복은 `plc_bench: false`, `mock_auto_request: true`를 명시합니다.
이때 실제 PLC 연결·읽기·쓰기는 없으며, Track 진입에서 MOCK Request를 만들고
Done 확인 후 OFF합니다. 실제 PLC로 돌아갈 때는 보존한 설정의
`plc_bench: true`, `mock_auto_request: false`를 선택해 재시작합니다.

```bash
envs/app_v1/bin/python -B -X utf8 current/manage_live.py start --config config/runtime.json
envs/app_v1/bin/python -B -X utf8 current/manage_live.py status --config config/runtime.json
envs/app_v1/bin/python -B -X utf8 current/manage_live.py stop --config config/runtime.json
```

운영 화면은 `http://127.0.0.1:18771/auto`입니다. 수동 `start`는 서버만 시작합니다.
이 장치의 사용자 crontab `@reboot`는 `current/boot_live.py --config config/runtime.json`을 실행합니다.
설정에 따라 서버·카메라·HMI를 먼저 준비합니다. 현재 빈 작업면·정상 카메라에서
개발 MOCK은 Request=0이면 AUTO를 켭니다. 실제 PLC 모드는 PLC가 아직 꺼져 있어도
AUTO 추적을 시작하며, PLC에서 유효한 Request=0을 확인한 뒤 요청을 받습니다.
Request가 이미 켜져 있거나 통신·결과 전송이 불명확하면 자동으로 새 검사에 연결하지 않습니다.
고장·복구 필요 상태는 자동 해제하지 않습니다. 로그는 운영 data_root의 `boot_live.log`입니다.
종료 전 AUTO 정지, 활성 검사·요청·저장 완료가 필요합니다.
다른 Python/Worker를 일괄 종료하지 않습니다.
로그/PID 기록은 data_root에 있으며 Journal/Evidence를 삭제하지 않습니다.
장애 때 직전 노트북 백업의 코드·설정으로 복귀하며 운영 데이터·환경은 덮어쓰지 않습니다.
