# 검사 프로그램 수동 확인·시작

현재 실행 주체는 Jetson의 `engine-inspector.service` 한 개다. Windows 브라우저는 SSH 터널로 화면을 본다. 서비스 시작은 컨베이어 START나 검사 승인과 다르다. 복구 작업 중에는 설비의 실제 STOP을 유지한다.

## 1. Jetson 터미널 — 상태 확인

Windows에서 접속한 SSH 터미널 또는 Jetson 자체 터미널에서 실행한다.

```bash
systemctl status engine-inspector.service --no-pager -l
```

- `active (running)`: 서비스 실행 중. 화면·영상·PLC 준비는 별도 확인한다.
- `inactive`: 서비스가 꺼져 있다.
- `failed`: 시작 또는 실행이 실패했다. 아래 로그로 원인을 확인한다.
- `enabled`: 부팅 때 시작하도록 등록됐다는 뜻이며, 현재 정상 실행을 뜻하지 않는다.

```bash
journalctl -u engine-inspector.service -b -n 50 --no-pager
```

## 2. Jetson 터미널 — 기존 서비스 시작

오류 원인을 해결한 뒤, 서비스가 꺼진 상태에서 실행한다.

```bash
sudo systemctl reset-failed engine-inspector.service && sudo systemctl start engine-inspector.service
```

`reset-failed`는 서비스 실패 표시와 반복 시작 제한을 초기화한다. 검사 DB나 사진은 지우지 않는다. `&&`는 앞 명령이 성공했을 때만 다음 명령을 실행한다. `start`는 기존 서비스 하나를 시작하며 이미 실행 중이면 중복 시작하지 않는다. 비밀번호는 터미널에만 입력한다. 시작 명령이 끝난 뒤 모델·카메라 준비 시간이 필요할 수 있다.

실행 중인 서비스를 다시 시작할 필요가 있는 경우에는 먼저 실제 STOP과 검사·저장 유휴를 확인한 뒤 `sudo systemctl restart engine-inspector.service`를 사용한다. 단순히 화면이 늦다는 이유로 재시작하지 않는다.

검사 Python 파일, 옛 `manage_live.py start`, 별도 카메라 프로그램을 동시에 직접 실행하지 않는다.

## 3. Windows PowerShell — 화면 연결

Jetson 서비스가 정상인데 노트북 주소가 열리지 않을 때 기존 터널 작업을 확인한다.

```powershell
Get-ScheduledTask -TaskName OneDeviceEngineTunnel
```

등록된 작업이 멈춰 있을 때만 시작한다.

```powershell
Start-ScheduledTask -TaskName OneDeviceEngineTunnel
```

브라우저 주소: `http://127.0.0.1:18771/line`. `Running`이면 별도 SSH 터널을 중복 실행하지 않는다. 예약 작업이 없거나 계속 실패하면 작업 등록/포트 소유자를 먼저 확인한다.

## 현재 확인한 특수 오류

2026-10-17 `engine-integrated-f03d3f570a172c5f`부터 기존배타소유잠금·소유권·비활성UNIX소켓·경쟁OpENer부재를확인한경우에만 잔여소켓을 보존이동하고기동한다. 실제재부팅후자동서비스·새카메라영상·PLC준비와START대기를확인했다. 아래수동절차는자동검증에서차단된경우의진단이며,소켓을무조건지우거나검사이력을초기화하는방법이아니다.

`STALE_OR_COMPETING_IPC_SOCKET_REQUIRES_REVIEW`는 이전 통신 소켓 또는 다른 실행 주체가 있다는 뜻이다. `reset-failed`만으로 원인이 해결되지 않는다. 소켓 파일을 임의 삭제하지 않는다. 실제 STOP, 서비스 종료, 프로세스 없음, 소유권 잠금, 소켓 연결 거절, 통신 포트 비점유를 확인한 뒤 기존 점검 도구로 소켓을 보존 이동한다.

2026-10-17 이 절차로 남은 소켓을 보존하고 사용자가 기존 서비스를 시작했다. 현재 실행 상태와 남은 검사 차단은 `runs/startup_recovery_20261017/` 및 `docs/STATUS.md`를 따른다. 웹 접속 복구는 자동 재부팅 안정성이나 연속30 성공을 뜻하지 않는다.
