# TASK-019 — 저장 중 health 유지 및 중단 기록 복구

상태: **ISOLATED_VERIFIED / STOP_FOR_DEPLOY_APPROVAL**. 운영 배포 및 새 현장 시험은 별도 승인 대상이다.

## 원인과 수정

실패한 현장 검사는 원시 REVIEW(`ENGINE_OR_HAND_MOTION`)와 원본 3장을
Journal COMPLETE로 저장했지만, 필수 조립 검사·통합 최종판정·PLC 결과 발행으로
이어지지 않았다. 공유 service.lock 안에서 원본 파일과 SQLite commit을 기다리면
Runtime health 갱신이 지연된다. 기존 IPC는 0.4초 동안 갱신되지 않은 health를
false로 보내며 C는 요청을 `PYTHON_NOT_READY`로 취소한다.

이 경합은 격리 시험에서 재현했다. 다만 당시 운영 로그에는 이번에 추가한 세부
계측이 없으므로, 과거 한 사건의 ready=false 원인과 lease 만료 시각을 새 계측으로
실측했다고 주장하지 않는다. Class1 timeout/reconnect는 별도 미해결 사항이다.

수정은 하나의 제한된 저장 작업자에게 파일·DB 저장을 맡기고, 카메라/검사 소유자는
검사 ID·Worker generation·camera epoch·요청 token을 유지하게 한다. 원본과
통합 최종판정 모두 durable commit 완료를 확인한 뒤에만 다음 단계로 진행한다.
BUSY는 건강한 검사 진행 상태이며, 실제 Worker/카메라 오류·저장 실패·통신 손실은
여전히 차단한다. lease, timeout, 모델, 임계값, PLC/EDS 계약은 변경하지 않았다.

추가 회귀에서 화면의 짧은 Journal 조회 경합을 저장 실패로 오인하는 문제도 찾았다.
현재 저장 문맥이 없으면 이 경로는 health를 해제하거나 갱신하지 않는다.
정상 Runtime이 다음 주기에 다시 갱신해야 하며, 실제 정지는 기존 lease 만료로
차단된다. known storage에 대해서만 현재 제어·세션·소유자·기한을 확인하여 갱신한다.

## 변경 위치

| 파일 / 함수 | 역할 |
|---|---|
| `apps/edge_service/result_storage.py` / `ResultStorage` | 단일 bounded raw/final 저장 작업자, 완료 통지 |
| `apps/edge_service/inspection.py` / `_monitor_loop`, `_storage_completions`, `health`, `status`, `close` | 동일 검사 소유권 유지, SQL 없는 health, 저장 실패/종료 처리 |
| `src/journal/sqlite.py` / `finish`, `_finish`, `commit_integrated` | 파일 I/O와 DB lock 분리, 취소 재확인, 실제 최종판정 append-only commit |
| `src/runtime/standalone.py` / `_run`, `_storage_wait_health`, `_poll_final_commit`, `_validate_cyclic_final` | DB 대기 중 health, 저장 전/후 문맥 검증, 늦은 결과 차단 |
| 같은 파일 / `_cancel_pending`, `_restore_aborted_inspection`, `_aborted_status` | 중단 상태 표시와 재시작 후 읽기 전용 복원 |
| `src/control/opener_cyclic.py`, `src/runtime/health_diagnostics.py` | 최대 64개 진단 사건, lock/갱신 간격·snapshot age·ready 원인 |
| C `engine_commissioning.c`, `engine_callbacks.c.inc` | ready=false/health 만료 발생 분기 계측 |
| `src/runtime/aborted_recovery.py`, `initial_approval.py` | 독립 ABORTED 증거와 기존 미완료 차단의 제한된 예외 |
| `standalone_web.py`, `line_hmi.html` | 원시 판정/Journal/조립/통합/PLC 발행 상태 분리 |

모델·Pose·Crop·3프레임 판정·Assembly 4/8/10B와 PASS→OK,
FAIL/REVIEW/ERROR→NG 및 Result 다음 패킷 Done 순서는 유지했다.

## 미완료 검사 복구 계약

원본 inspection/result/PNG와 소비된 승인 원장은 수정하지 않는다.
`record_abort()`는 HTTP 운전 기능으로 노출되지 않는 유지보수 함수다. 다음 증거가
모두 있어야 별도의 durable `aborted_cycle:<id>`와 감사 사건을 추가한다.

- 일치하는 요청의 실제 수신→DISARMED 기록, 결과/Done 송신 0회, 취소된 승인.
- 신선한 현재 C snapshot: 별도 연결 문맥, DISARMED, Request/Result/Done/Mc_Run LOW.
- Worker idle, raw/final 저장 및 Assembly 작업 없음. 누락된 필드는 idle로 간주하지 않음.
- 원시 결과 SHA, 요청 token, 세션/프로세스, 승인 ID 일치와 감독자 확인.
- DB 무결성·용량 정상. 기존 final/ABORTED와 충돌하지 않음.

원본 증거가 부족하면 차단한다. final과 ABORTED는 동시에 저장될 수 없다.
과거 승인 ID를 초기화하거나 새 결과를 만들어 넣지 않는다. 현재 운영 DB에는
이 복구 기록을 적용하지 않았다. 배포만으로 첫 제품 시험이 허용되지 않는다.

## 검증과 한계

최종 Git index 소스 21개와 ARM64 시험 입력의 SHA를 대조했다. Python 회귀
**283개 PASS (78.510초)**, C 초기승인 22개 및 감독형/자동 상태기계의 sanitizer 시험
PASS, 전체 OpENer 빌드·동적 의존성 확인 PASS다. 기존 C 정수 변환 경고는 남아 있다.
화면 JavaScript의 통합 완료/미완료 중단 표시 두 경우도 격리 검증했다.

| 격리 최종판정 | 원시 저장(ms) | 최종 commit(ms) | health 최대 간격(ms) | service lock 최대 대기(ms) |
|---|---:|---:|---:|---:|
| PASS | 1047.1 | 567.0 | 140.5 | 0.99 |
| FAIL | 1051.8 | 570.2 | 138.8 | 2.29 |
| REVIEW | 1053.3 | 569.0 | 131.9 | 1.80 |
| ERROR | 1057.3 | 568.4 | 196.9 | 1.26 |

네 경우 모두 Result/Done/완료 각각 1회와 연속 패킷 순서, 같은 요청 중복 차단을
확인했다. 단일 격리 실행의 관측값이며 장시간 성능·현장 AI 정확도 보증은 아니다.
최종 시험 전 실패한 회귀는 private run에 보존하고 통과 근거에서 제외했다.

- 실제 실패 기록의 검증용 SQLite 복사본: 원본 116행·승인 원장 불변,
  독립 ABORTED 후 해당 blocker 1→0, 가짜 integrated_decision 생성 없음.
- 실제 저장 PNG 3장의 동일 바이트/크기와 SHA를 사용한 지연 저장 검사.
- 소프트웨어 전체 경로: 실제 Worker 프로세스·Journal·AssemblyInspector·최종판정·
  IPC·C 상태기계. 카메라/모델 경계는 명시적인 합성 fixture이며 현장 AI 성능 검증이 아니다.
- 원본·최종 commit 각각 550ms 지연과 동시 UI 조회, 네 가지 판정 및 중복/STOP 차단.
- 실제 PLC/카메라에 연결하지 않는 AF_UNIX fixture. 현장 Result/Done은 송신하지 않았다.

## 운영 적용

현재 운영 Release는 `engine-integrated-d247e1e9579ab6e7`이며 이번 수정은 미배포다.
사용자의 별도 운영 적용 승인 후에만 일관된 백업을 재확인하고 단일 current를
전환한다. 미완료 검사의 감독하 복구는 별도 증거 확인을 거치며,
새 현장 한 제품 시험 승인은 기존 소비된 승인과 분리한다.

노트북의 TASK-019 `health_storage_019/DEPLOY_APPROVAL_AND_ROLLBACK.md`와
`CURRENT_D247_BACKUP_RECEIPT.json`에 정확한 복구 파일·해시·서비스 전환 절차를 보관한다.
운영 DB·현장 사진·개인 설정·승인 원장·복구 패키지는 Git에 포함하지 않는다.

검증 C 실행 파일 SHA-256:
`8506ffc28970ae731f02a5aab97b98e8d1d0b199c51b060450facfffc842b82e`.
검증 결과 archive SHA-256:
`50982dad16ce346848e6e93b76c91ecc17f3d8013d6f3d509dcd4f7267dfbb7a`.
직전 운영본 백업 SHA-256:
`aec75fd547f4bf890adbb984174b140a6bc80ede1427604e69a3b7496b8987bb`.

Git의 ARM64 실행 파일은 이번 C 소스로 빌드한 파일로 함께 갱신했다.
실제 장치의 C 파일과 SHA 설정은 변경하지 않았다. 승인 후에는
`DEPLOY_DIFF_MANIFEST.json`의 소스/실행 파일 11개와 C SHA 설정·Release 메타데이터만
한 번의 정지된 서비스 전환에 반영한다. 운영 복구 및 현장 재시험은 **NOT_RUN**이다.
