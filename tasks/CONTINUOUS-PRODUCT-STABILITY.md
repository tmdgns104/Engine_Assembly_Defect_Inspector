# 연속 제품 접수 안정화

현재 작업: 2026-10-15 사용자 요청. 기존 4회 성공과 별도로 반복되는 PREVIOUS_PRODUCT_IDENTITY_OR_EXIT_UNPROVEN의 최초 원인을 실제 운영 기록에서 확인한다. 현재 STOP·현장 감독 조건 및 수정 후 5회 시험 범위 확인됨.

## 계약 및 완료 근거

- 기준 운영 Release engine-integrated-32d132a4256d4ef8/source7ec9d25. HEAD 문서 차이만으로 교체하지 않는다.
- 실제 상태/Journal/C 이벤트/Runtime 소비 프레임을 보존하고 제품 분리와 Request의 순서를 재현한다.
- 마지막 신뢰 관측과 신규 진입 근거를 유지하는 최소 상태 전이 수정. 시간 경과·Request LOW를 이탈로 만들지 않는다. STOP/통신/저장/epoch/중복 결과 보호와 모델/PLC/EDS/카메라는 유지.
- 기존 실패·수정 후 성공 회귀, 카메라 epoch·일시적 bbox/누락·제품 근거 부족·중복·취소 검증. UI는 관찰 대기와 실제 미실행을 구분하는 문구만 수정.
- 노트북 일관된 백업·SHA·집중 네이티브 검증 후 current 한 벌에 적용. 실제 START 한 번으로 정상/결품 5회: 고유 ID/새3원본/final/Result→Done/Request 해제/LED/재가동/자동 다음 접수 대조.
- 정상 사이클마다 Reset/권한/CLI/Codex 준비 명령 없음. 현장 시험 성공과 격리 테스트를 구분. 다른 TASK 시작 없음.

## 진행

- 실제 baseline 185파일 SHA 일치, Release32d132a4/source7ec9d25. 최근 요청10·11은 분리 근거 없이 30초 후 ERROR, 촬영0장. 그 당시 소비 bbox는 링에서 이미 덮여 최초 물리 관측 실패 원인은 확정 불가. 현재 요청13 COMPLETE/PASS·STOP·출력0·Worker/저장/Assembly 유휴.
- 재현된 코드 결함: 짧은 누락이 신규 진입 문맥을 지워 이전 제품 bbox와 비교하며 영구 invalid. Request가 진입 근거 확정보다 먼저 올라오면 이전 LOW 관측이 있어도 현재 LOW를 다시 요구하고 identity_block을 고정.
- 기존 이동·겹침·누락 한계 안에서 신규 진입 재관측, 연속 근거 창은 다시 시작. 같은 연결에서 이미 관찰한 이전 트랜잭션 종료와 요청 전 최초 진입이 일치할 때만 아직 검사 미할당인 현재 요청을 해소. STOP/epoch/통신/저장/기한/늦은 다른 제품은 우회하지 않음.
- 소비 프레임1024/최초 차단 체크포인트4×128을 메모리에 제한 기록, 일반 상태에는 포함하지 않음. UI는 관찰 대기와 실제 요청 미실행 구분만 변경.
- 수정 전 4개 실패(누락2조건·Request경합·UI), 수정 후 PC/ARM64 각각143개 통과(실제 PLC/카메라 없는 회귀). 기존 실제 shape-outlier 재생 포함. Windows 내부 소켓 제한 및 네이티브 테스트의 HTML 경로 누락을 확인해 환경을 보완하고 동일 회귀 완료.
- 현재 STOP 및 모형 벨트 밖 보관 확인 후 마지막 제품 문맥을 기존 유지보수 경로로 1회 종료. 원본/판정 보존, 새 권한0/결과 재송신 없음. 실제 5회 현장 시험은 아직 미수행.
- 비공개 증거: runs/continuous_stability_001/PRECHECK, PC_TESTS.json/log, NATIVE_TESTS.json/log, CONTEXT_CLOSED.json. DB·사진·개인 설정은 Git에 포함하지 않음.
