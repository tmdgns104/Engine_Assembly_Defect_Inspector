# TASK-023 — 최신 프레임 웹 미리보기

완료. 사용자는 STOP 유지와 정상 서비스 재기동, 이후 별도 한 제품 시험을 승인했다. 실제 시험 후 STOP을 확인했다. TASK-022 조립 정렬은 보존한다.

## 계약과 최소 변경
- `/line` 상태·이력 조회는 기존 1초 간격을 유지하고 이미지 요청만 분리한다.
- 한 번에 이미지 요청/디코드 하나, 최신 프레임만 표시. 중복 frame ID를 FPS로 세지 않는다.
- 미리보기 API는 Journal/전체 status 대신 짧은 잠금에서 JPEG·세대·시각을 함께 읽는다.
- 서버 프레임 나이는 Jetson monotonic으로 계산하고 브라우저 요청 시간은 브라우저 clock으로 계산한다.
- 카메라 소유권, 원본/Tracking/안정 3프레임, 모델/PLC/C/조립 정렬은 변경하지 않는다. 첫 단계 측정이 부족할 때만 추가 캡처 분리를 검토한다.

## 검증과 적용
1. 실제 current/source SHA 및 읽기 전용 PLC·Worker 상태 대조.
2. 변경 전/후 30초 이상 서로 다른 표시 frame ID, HTTP 시간, 서버 프레임 나이, Worker 처리속도·PLC health 계측.
3. stale/dead worker/generation/중복/동시 요청 및 느린 상태 조회 회귀.
4. 서비스 정상 종료, current/config/unit/release 및 SQLite backup API 백업을 노트북에서 해시·복원 목록 검증한 뒤 최소 파일 적용.
5. 단일 서비스/카메라/C와 SHA 확인. 실제 대기/검사 중 측정 구분, 미측정은 명시.

목표: 실제 새 프레임 5~10FPS. 합성 테스트를 현장 성능으로 보고하지 않는다.

Evidence: `runs/web_preview_023/` (사진/운영 DB는 Git 제외).

## 결과
- Commit `52df5d22b13130493e3268de744724c9395b2723`, 실제 Release `engine-integrated-8831b41d4448da2d`, 184개 파일 SHA 확인.
- 실제 새 표시 프레임 0.966 → 5.432FPS, 상태 조회는 1Hz 유지. 한 제품 시험 관측에서도 5.487FPS와 BUSY 동안 7개 새 표시 프레임 확인.
- 실제 원시 검사 PASS / Assembly REVIEW / 통합 REVIEW → NG Result 5570 → Done 5571 → Request 초기화·현장 재가동·최종 STOP 확인.
- 상세 측정창·제한·테스트·백업은 `docs/WEB_PREVIEW_LATENCY_REPORT.md`. 조립 정렬 성공은 아니며 TASK-022 후속에서 다룬다.
