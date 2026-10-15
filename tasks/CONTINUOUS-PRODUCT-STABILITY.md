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

## 첫 현장 시도와 진단 잠금 보완

- d376ffc / engine-integrated-a390a7fe1b7c99e8 적용 후 START 한 번으로 정상 PASS → 왼쪽 파이프 결품 FAIL → 정상 PASS 처리. 각각 새 원본3장·고유 ID·Result/Done·Request LOW 및 현장 LED/재가동 확인. 5회 완료는 아님.
- 세 번째 종료 후 유휴 중 health 갱신 간격 423.689ms로 PYTHON_NOT_READY/HEALTH_LEASE_EXPIRED 발생. C 연결1·timeout0, 당시 IPC snapshot age44.86ms. Class1 장애로 분류하지 않는다.
- 상세 소비 프레임 진단의 큰 deepcopy가 Runtime 제어 잠금 아래 실행되는 결함을 재현. 짧게 불변 기록 참조를 잡은 뒤 잠금을 놓고 복사하도록 최소 수정. lease/timeout/판정/PLC 설정 불변.
- 진단 복사 중 제어 잠금 획득 회귀: 이전 구현 FAIL, 수정 후 PASS. 집중 PC/ARM64 각144개 통과. 보완본 현장 적용·진단 부하 관찰 및 5회 재시험은 진행 중.
- 첫 배포 때 카메라 timeout은 직전 코드 복원에서도 지속, 사용자 USB 재연결 후 복구됨. 코드 수정으로 카메라 장애를 해결했다고 주장하지 않는다.

## 완료 — 감독하 연속6회

- 소스 a859b21e00b2d1f661b27e301f4705be74273d04, 실제 engine-integrated-80882c05c181fbd6, 운영185파일 SHA 일치. 새 전체 실행본을 여러 개 상주시키지 않고 current의 검증된2파일+Release만 정상 정지 중 교체.
- 진단 API 반복90초/1024프레임에서 health 최대195ms·차단0. 이후 최초 정상 배출 중 사용자 벨트 접촉1건은 별도 보존; 이것을 과거 소프트웨어 실패 원인으로 확대하지 않음. 동일 코드로 그 문맥만 STOP/실물 확인 후 종료하고 서비스 재시작 없이 재시험.
- 최종 START1회/중간STOP·START·Reset·grant·service restart0: 정상 PASS → 왼쪽 결품 FAIL → 정상 PASS → 오른쪽 결품 FAIL → 정상 PASS → 사용자 추가 요청 문양 결품 FAIL. 모두 새3PNG, 총18프레임 SHA/픽셀/identity·고유검사6개·Journal·Result→바로다음Done·RequestLOW·작업자 LED/재가동 확인. 제품2~6 실제진입근거로 자동접수.
- health 최대380.371ms, raw 저장293~534ms, ready=false0, Cconnection1/timeout0. 짧은 시험 성공이며 health 여유/장시간 Class1/무인복구는 미검증. AssemblyREVIEW는 기존V1정책 아래 보존, 정렬개선 아님.
- 최종 실제STOP·PLCLOW/출력0·유휴·SQLiteok. 노트북 직전백업170파일 SHA1ff338bd... 검증. 상세 docs/CONTINUOUS_PRODUCT_STABILITY_REPORT.md, 비공개 VERIFIED_SIX_TRIALS.json/OPERATOR_CONFIRMATIONS.json. UI/DB 후속 작업 시작 없음.

## 종료 뒤 추가 상태

- 여섯 검사 완료 후 STOP 대기 중 CAMERA_FRAME_TIMEOUT/기존 자동 Worker 복구 반복 발견. 서비스16809/C연결1·Request7/Result7/Done7 유지, 추가 검사 없음. epoch 교체로 과거 제품 문맥이 PREVIOUS_RUNTIME_PRODUCT_EXIT_UNPROVEN으로 복원됨. 이 상태를 다음 검사 준비 완료로 보고하지 않는다.
- 실제6회 동안 동일 Worker·무차단 관측은 보존한다. 카메라 수신 원인은 미확정이며 해당 시간대 USB 커널 로그는 없었다. 위치/각도/조명 유지한 동일 USB 재연결을 사용자에게 요청, 현장 확인 대기. 보호 조건 해제/가짜 이탈/추가 START 없음.
- 이번 작업 임시222파일+링크4개를 노트북 archive SHA d7b852b8062eae25516e2bd0ee160a3ddaa1fedc306d932b5fce7cf3f6afc46a로 검증 후 장치 tmp 작업 경로만 제거. current/data/assets/config 미변경.
