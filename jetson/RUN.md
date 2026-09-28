# Runtime 실행 안내

이 묶음은 개발본이며 실제 PLC·생산 수용 완료가 아닙니다.
`release.json`은 묶음의 파일 해시, `/api/v1/release`는 시작 때 로드한 식별정보입니다.

`current`와 나란히 `assets`, `config`, 운영 데이터, 확인된 Python 환경을 둡니다.
`current/config` 링크는 `../assets/runtime_config`를 가리킵니다.
장치별 `config/runtime.json`에서 package/station/data_root/pythonpath/port를 지정합니다.

```bash
envs/app_v1/bin/python -B -X utf8 current/manage_live.py start --config config/runtime.json
envs/app_v1/bin/python -B -X utf8 current/manage_live.py status --config config/runtime.json
envs/app_v1/bin/python -B -X utf8 current/manage_live.py stop --config config/runtime.json
```

운영 화면은 `http://127.0.0.1:18771/auto`입니다. 시작만으로 AUTO나 기준 승인이 켜지지 않습니다.
종료 전 AUTO 정지, 활성 검사·요청·저장 완료가 필요합니다.
다른 Python/Worker를 일괄 종료하지 않습니다.
로그/PID 기록은 data_root에 있으며 Journal/Evidence를 삭제하지 않습니다.
장애 때 직전 노트북 백업의 코드·설정으로 복귀하며 운영 데이터·환경은 덮어쓰지 않습니다.
