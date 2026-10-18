# 검사 SQLite 보관본

실제 Jetson 원장과 같은 SQLite 형식의 일관된 백업입니다. 운영 중인 DB 본체만 복사하지 않고 SQLite backup API를 사용했습니다. 운영 원본·WAL은 수정하지 않았습니다.

- `snapshots/20261018_post7/journal.sqlite3`: 2026-10-18 18:36 KST 보관본, 368건, 94,973,952 bytes.
- `snapshot.json`: 생성 시각·SHA256·무결성 검사·건수. 과거 진단·실패를 포함하므로 전체 건수를 성공 실적으로 해석하지 않습니다.
- 원본 사진은 포함하지 않습니다. DB의 1,388개 자산 참조는 그대로 보존하며 사진 파일은 Jetson/로컬 Evidence에 남습니다. 조회 페이지는 없는 사진을 명시합니다.

Windows 프로젝트 가상환경에서:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 notebook/view_history.py --data-root database/snapshots/20261018_post7
```

`http://127.0.0.1:18773/history`에서 검색·상세·CSV 내보내기를 사용합니다. Ctrl+C로 종료합니다. 이 서버에는 카메라·PLC·DB 수정 API가 없으며 네트워크 외부에 바인딩하지 않습니다. 기존 FastAPI/uvicorn 환경을 사용합니다.

운영 Jetson에 새 개발본을 적용한 경우 `/history`는 실제 원장을 읽습니다. 보관본을 실행 중인 Jetson DB 위에 덮어쓰지 마세요. 복원은 서비스 정지·원본 백업·무결성 확인이 필요한 별도 작업입니다. GitHub는 실시간 DB 동기화 서비스가 아닙니다.
