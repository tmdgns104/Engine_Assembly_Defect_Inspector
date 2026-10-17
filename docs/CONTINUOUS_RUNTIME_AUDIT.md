# 실제 운영 중단 조건 감사 — 2026-10-17

## Attempt15 — 혼합23건 연속 처리 확인, 촬영 ERROR2건 유지

동일 운영 `engine-integrated-555c3a43053ce4ce`에서 한 번의 실제 START 후 노트북 유선LAN을 분리하고 정상→오른쪽 파이프만 빠진 모형을 교대로 투입했다. 사용자 종료 후 STOP·LAN재연결을 확인했다. 사용자는 정확한 횟수를 세지 못했고 “error가 나와도 연속”이라고 보고했으며, 이후 **순서 준수·추가 START 없이 계속 배출/재가동**을 명시했다. 횟수와 아래 판정은 Jetson 원장·동일 요청 토큰 C기록으로 확정했다. 기대 정답은 사용자 준비·순서에 근거하며 Detector 입력에 전달하지 않았다.

| 구분 | 실제 요청 | PASS | FAIL | ERROR |
|---|---:|---:|---:|---:|
| 정상 모형 | 12 | 11 | 0 | 1 |
| 오른쪽 파이프 결품 | 11 | 0 | 10 | 1 |
| 전체 | 23 | 11 | 10 | 2 |

- **연속 처리:** 23건 모두 SQLite COMPLETE·원본저장·최종영속화·Result→다음sequence Done→RequestLOW→출력0→다음요청 준비를 같은 ID/token으로 검증했다. 중간 C정지·재접속 이벤트 없음. 1회 ERROR 다음2회 FAIL,16회 ERROR 다음17회 PASS가 계속됐다. ERROR의 PLC 전달은 기존 `AI_ERROR_AS_PLC_NG`이며 실제 결품 확정 FAIL과 다르다. 검사 성공이 아니라 오류 처리와 다음 운전 복귀의 증거다.
- **유효 검사:** 21건에서 요청 이후 새3장/고유frameID·PTS증가·같은epoch/generation·촬영3초·안정0.6초 조건을 대조했다. ERROR2건에는 마지막 진단후보3장씩만 보존됐다. 해당6장을 유효촬영으로 세지 않는다. 최대 연속 유효검사14건(요청2–15). 23건시험을30건 또는30회무오류로 표시하지 않는다.
- **원본/저장:** 원본69PNG(유효63+진단6), 전체92자산, 회수165파일의 SHA/크기·원본디코딩픽셀SHA를 대조했다. SQLite `quick_check=ok`, 수집기23행/대기ID0과 원장이 일치. 검사별원본/정답/오류기록 보존, 중복원본0. 서비스 Main8165·Worker8208·NRestarts0·boot `c8d72e3f-d5cf-423a-b832-774394ba8243` 유지.

### ERROR 원인과 실제 사진

| 요청 / 검사ID | 기대 상태 | 후보/거부 | 저장된 마지막3장 제품전체 점수 | 관측 결과 |
|---|---|---:|---|---|
| 1 / `d53cbbd8fe604fad88f4b70d7465f470` | 정상 | 12/12 | 0.458698 / 0.500746 / 0.451100 | FIRST_TARGET_FRAME3·WAIT_STABILITY_INTERVAL4·TARGET_UNCERTAIN5 |
| 16 / `fb7919e27fd24e5fb9d5777cd339d064` | 오른쪽 파이프 결품 | 10/10 | 0.449688 / 0.462019 / 0.468180 | FIRST_TARGET_FRAME1·WAIT_STABILITY_INTERVAL2·TARGET_UNCERTAIN7 |

두 건 모두 촬영기한 `DEADLINE_EXCEEDED`이며 유효 안정프레임0. 제품전체 검출이 기준0.5 아래로 끊기며 안정관찰을 처음부터 다시 시작했고, 0.6초 안정 후 연속3장을3초 안에 얻지 못했다. 이 두 건의 거부 메타데이터에는 `MOTION_ABOVE_THRESHOLD` 같은 실제 변화량 초과가 없다. 모든 WAIT_FOR_STABLE_FRAME을 물체의 실제 이동으로 해석하면 안 된다.

오류원본6장을 실제로 열었다. 한 엔진이 보이며 손가림이나 저장된3장 사이 큰위치이동은 보이지 않는다. 1회는 두굽은파이프·배기구·가운데문양이 보이고,16회는 한쪽굽은파이프가 빠진 모습으로 사용자 순서와 일치한다. 전체3초 원본은 없고 마지막후보3장만 있으므로 완전정지나 물리원인을 확정하지 않는다. 위치/반사/각도/금색손잡이 등 특정원인은 미분리이며 임계값을 낮추지 않았다. `assembly_affects_final=false`를 전23건 검증했고 오조립참고분석은 최종 PASS/FAIL에 영향없다.

### 응답 시간과 남은 한계

첫요청→마지막요청 정리 **429.651초(약7분10초)**. 요청→C의Done해제/완료 시간은 최소4.894초·중앙10.799초·p95 20.744초·최대20.794초(23건 nearest-rank). 총통합최종시간이15초를 넘은 요청4/6은 각각20.334/20.462초였다. 같은시계의 기본결과저장시각은 접수뒤2.362/2.467초였고, 그 뒤 통합최종까지17.621/17.496초가 더 걸렸다. 기본Worker 처리기한15초와 통합최종시간은 다른 범위다. 후속지연구간의 정확한 호출별 원인은 아직 특정하지 않았으며 **모든 응답15초이내**를 통과했다고 하지 않는다.

검출정답 일치21건과 미판정ERROR2건을 함께 남긴다. 추가START나 소프트웨어개입 없이 계속운전되는 동작은 이번23건에서 확인했지만, 혼합30회/오류없는검사/장시간신뢰성은 별도미완료다. C전송/Done/RequestLOW와 사용자물리관측은 대조했고 독립PLC소비ACK는 제공되지않는다. 센서실노출시각은 미확인이며 GStreamerPTS추정으로 신선도를 확인했다. 노트북LAN분리시험이지 노트북전원OFF시험은아니다.

현재 실제STOP·RequestLOW·출력0·저장유휴이며 오류원본을 포함해 모두보존했다. 이번작업은 운영코드/모델/임계값/PLC계약변경이나 재부팅 없이 **현재운영본 시험만** 수행했다. 자동추가투입·임의수정은 하지 않는다. 다음 우선검토는 제품전체 검출의 미판정감소와 기본결과저장 뒤의 통합응답지연이다.

증거: `runs/mixed_stability_20261017/right_retry_AUDIT.json`, `right_retry_FINDINGS.json`, `right_retry_NATIVE.json`, `right_retry_OPERATOR_RUN_REPORT.json`, `right_retry_review/request_{01,16}_original_{1,2,3}.png`. 회수ZIP SHA `9f6217cf7eaaa7b920e5d0afa7d198999adc4f24a9d3d28568ffea18cac3a0cf`. 감사도구는 ERROR결과의 별도스키마·진단후보selected_frame_ids를 실제Worker 저장경로와 대조해 구분했다. 최초 통합시간15초 가정은4·6회에 실패했으며 해당 초과를 숨기지 않고 별도기록했다.


## Attempt15 — 기존 취소 복구 후 정상·오른쪽 파이프 결품 재시험 중

사용자가 STOP·빈 벨트를 확인한 뒤 같은 서비스를 재시작했다. 운영555c3a43053ce4ce·OS boot c8d72e3f는 유지되고 Main8165/CameraWorker8208/NRestarts0이다. 코드·모델·임계값·PLC 계약 변경은 없다. 새 어댑터와 정지 증거를 기존 취소 복구 API로 검증(check)한 뒤 apply했다. request75 원래 CANCELLED/ERROR와 검사행322개·자산행1204개·저장최종201개는 그대로이며 재전송불가 종료 영수증667c0ba10b5b430e8e305b0f8bf5bb4f만 추가했다. 새 원본·판정·허가·PLC쓰기0. 복구후 오류없음, 새영상3개와 현장START대기 화면상태를 확인했다. OS 재부팅이나 제품인식 개선 검증으로 표시하지 않는다.

별도 `continuous30_20261017_attempt15_normal_right_retry`의 기존 GET-only 기록기8522/Worker8208/새카운터0 준비 후 실제 START를 대조했다. 사용자 노트북LAN분리와 SSH3초timeout을 확인하고 정상→오른쪽파이프만결품 15쌍을 안내했다. 앞 모형 완전배출 후 다음 투입, ERROR/재가동불가시 추가START금지 원칙을 유지한다. 현재 횟수·정확도·PLC완료는 미확정이며 이전 실패를 성공으로 합산하지 않는다. 위치 민감성의 근본 수정 없이 사용자가 선택한 현재운영본 시험을 이어가는 것이다.

근거: `runs/mixed_stability_20261017/CANCELLED_ABORT_CHECK.json`, `CANCELLED_ABORT_APPLY.json`, `right_AFTER_RECOVERY.json`, `right_retry_READY.json`, `right_retry_START.json`, `right_retry_PLAN.json`, `right_retry_NOTEBOOK_DISCONNECTED.json`. 원본·모델·DB는 GitHub에 올리지 않는다.


## Attempt14 후속 — STOP 상태에서 위치만 바꾼 대조

사용자는 같은 정상 모형의 방향을 유지하며 진행 방향으로 약2cm 이동했다고 확인했다. 운영 모델·0.5 기준·카메라 Worker2741을 그대로 두고 각 위치에서 서로 다른 12프레임을 기존 GET 프리뷰 메타데이터로 관측했다.

| 위치 | 전체 엔진 점수 범위 | 중앙값 | 기준0.5 이상 |
|---|---:|---:|---:|
| 오류 후 원래 자리 | 0.381231–0.489778 | 0.422677 | 0/12 |
| 이동 후 자리 | 0.767626–0.804196 | 0.784943 | 12/12 |
| 손으로 되돌린 자리 | 0.718430–0.748063 | 0.741304 | 12/12 |

원본 방향 유지·이동 거리는 사용자 조작이며 기계적으로 계측하지 않았다. 첫 이동의 bbox 중심 평균은 x−156.697px/y−14.677px 변했다. 사용자는 복귀 후 ‘되돌렸는데 손으로 해서 맞는지 모르겠다’고 밝혔다. 세 번째 실제 프리뷰에서는 최초 대비 위치와 각도가 조금 다르고 검출 bbox 중심은 x+53.333px/y−20.602px였다. 낮은 점수는 이 수동 복귀 위치에서 재현되지 않았다. 따라서 정확히 같은 위치로 돌아온 A-B-A 재현으로 인정하지 않으며, 추가 수동 맞춤은 요구하지 않는다. 배치 변화와 점수 변화는 관측했지만 위치·각도·반사·배경·시간을 독립적으로 분리한 실험은 아니다.

진단은 새 촬영 요청이나 모델 실행 명령 없이 기존 Worker 결과를 읽었다. 36개 frame ID는 서로 다르며 현재 PLC request75/completed74와 기존 ERROR는 유지됐다. 연속 프레임을 독립적인 정확도 시험으로 세지 않는다. 검사 원본3장·부품 판정·PLC 완료가 새로 생긴 것은 아니며 혼합30/복구 완료도 아니다. 프리뷰 JPEG에는 표시가 포함되므로 모델 입력으로 사용하지 않는다.

근거: `runs/mixed_stability_20261017/right_POSITION_COMPARISON.json`, `right_STOPPED_PRODUCT_SAMPLES.json`, `right_MOVED_PRODUCT_SAMPLES.json`, `right_POSTSTOP_DIAGNOSTIC_PREVIEW.jpg`, `right_MOVED_DIAGNOSTIC_PREVIEW.jpg`. 기존 실패 원장과 아래 분석을 보존한다.
복귀 대조 근거는 `right_RETURN_POSITION_COMPARISON.json`, `right_RETURNED_PRODUCT_SAMPLES.json`, `right_RETURNED_DIAGNOSTIC_PREVIEW.jpg`다.

취소 복구 전에는 사용자 STOP·빈 벨트 확인과 실제 영상/PLC정지/출력0·저장유휴를 대조했다. 일반 제품 종료 경로는 `OWNER_ERROR_BLOCKS_CONTEXT_RECOVERY`로 사전 거부돼 POST하지 않았다. 촬영 전 취소 건은 기존 전용 `aborted_recovery.record_cancelled_abort` 계약을 사용했다. 원기록322건·자산행1204건·저장최종201건의 보존 지문과 SQLite 일관 백업77119488byte/SHA `aa39545e8f3bf6f4130ef7e735d4fcea3a2e497e2717efccf98d37c7ec457063`를 노트북으로 회수하여 quick_check/해시 일치를 확인했다. sudo 원격인증이 없어 사용자 서비스재시작 후 위 Attempt15 준비로 이어졌다. 원본사진을 다시 복제하거나 PLC결과를 재발행하지 않았다. 증거 `right_RECOVERY_PREFLIGHT.json`, `right_BACKUP_MANIFEST.json`, `NOTEBOOK_BACKUP_RECEIPT.json`.

## Attempt14 — 첫 정상 모형이 부품검사 전에 취소됨

정상→오른쪽 파이프만 결품 교대30회는 완료하지 못했다. 실제 첫 요청75, 검사 `9c3882c3a53b4420b7e905c5be732d9c`만 접수됐으며 SQLite `CANCELLED/ERROR`, 이유 `REQUEST_STORAGE_DEADLINE_EXCEEDED`다. 원본 자산0·유효3장0·부품 검사0·통합 최종0·PLC 완료0. 취소 사실은 `storage_success=true`로 영속화했고 SQLite quick_check는ok다. 이를 저장 성공한 제품검사로 세지 않는다. 앞서 완료한74개 거래와 별도이며 추가Result/Done은 발행되지 않았다.

| 단계 | 실제 단조시각(초) | 관측 |
|---|---:|---|
| PLC요청75 접수 | 3937.630917 | Ready유효,health나이28.343ms |
| 첫 현재제품 track확보 | 3960.235785 | 접수후22.605초 |
| 요청저장완료 | 3960.482505 | 총236.238ms,error없음,admit commit포함6.659ms |
| 현재프레임 대기 | 3960.482538 | `ADMISSION_WAIT_CURRENT_FRAME`,provider=`NO_FOREGROUND` |
| 원admission기한 | 3963.235895 | trigger3960.235895부터3초;기한재시작안함 |
| Python오류/차단 | 3963.251039 | 촬영Worker실행전취소,요청동일 |
| C거래중단 | 3963.275950 | `PYTHON_NOT_READY`,새Result/Done0 |

`request_start.py:_poll`은 성공한 저장영수증을 보존하고 `tracked_frame_evidence()`에 맞는 현재 한제품 관찰을 기다린다. 이 검사에서 저장은 완료됐으나 관찰조건이 충족되지 않은 채 원래3초기한이 만료됐다. `_live_error`의 공통 오류명이 STORAGE여서 저장지연으로 오인하기 쉽다. 실제 저장시간·오류없음·`NO_FOREGROUND`대기 기록을 근거로 이번경로를구분한다. 400ms lease만료나재부팅/카메라worker교체의증거는없다. 런타임로그끝에있는과거15:45 BrokenPipe는 이번16:52요청원인으로쓰지않는다.

사용자는검사위치계속정지→STOP·LAN재연결→현재모형네부품모두정상임을확인했다. 모형이그대로있는STOP에서기존Worker의GET프리뷰메타데이터12개만읽었다. 서로다른12프레임모두유효,제품전체검출점수0.381231–0.489778,기준0.5미만으로provider모두NO_FOREGROUND였다. 후속정지진단프리뷰를열어정상모형이보이는것을확인했다. 회색제품박스는관찰기준미달의단서이며최종부품FAIL을뜻하지않는다. screenshot의Tailscale주소로본화면과노트북유선LAN분리는모순되지않으며노트북전원OFF시험은아니다.

이12장은실패후진단표본이며실패당시원본이나3장검사로바꾸지않는다. 원실패의촬영dispatch자체가없어원본PNG가없다. FAULT의runtime/status에는관찰링전체가아닌최근4개만있고,후속전체링회수시요청구간은이미벗어났다. 따라서3초내모든프레임점수/누락률은미측정이다. 최초분석도구의구간선택검증실패는이자료범위차이를보였고,카메라중복/유실의증거로오해하지않도록 `right_OBSERVATION_LIMIT.json`에남겼다. 모델·반사·위치·금색손잡이방향중물리근본원인은아직확정하지않았다.

현재STOP·RequestLOW·출력0·저장유휴,같은운영555c3a43053ce4ce/Main1161/Worker2741/재시작0을확인했다. 기준0.5를임의하향하거나ERROR를FAIL로전환하지않았고운영수정·재부팅·추가START없음. 오른쪽파이프결품모형은이번블록에서아직검사되지않았다. 정상30/결품37의이전유한한성공은보존하지만현재혼합30/전체안정성완료는아니다. 다음은제품전체관찰이약한정상모형조건의원인과검증가능한보정범위를정하는단계다.

근거 `runs/mixed_stability_20261017/right_FAILURE_AUDIT.json`, `right_NATIVE.json`, `right_FAULT.json`, `right_STOPPED_PRODUCT_SAMPLES.json`, `right_POSTSTOP_DIAGNOSTIC_PREVIEW.jpg`, `right_POSTSTOP_PREVIEW_RECEIPT.json`, `right_OPERATOR_SCREENSHOT.png`, `right_OBSERVATION_LIMIT.json`, `right_OPERATOR_AFTER.json`. 원본·모델·DB는GitHub에올리지않는다.

---

이하 당시 준비·이전 시험 기록을 보존한다.

## 현재 후속 — 정상·오른쪽 파이프 결품 혼합30 진행 중

사용자 후속 지시로 정상→오른쪽파이프만미결합 교대30회(15쌍)를 선택했다. 시작 전 준비했던 정상/배기구/문양 3상태 attempt13은 새요청0 상태에서 GET-only기록기6574만 종료했으며 모든 파일을 보존했다. 사용자 정상/오른쪽결품 준비 확인 후 `continuous30_20261017_attempt14_normal_right` 기록기6708을 시작했다. 실제START·카운터74·새요청0·같은Worker2741·운영555c3a43053ce4ce 유지 확인, 노트북LAN분리·SSH단절 확인 후 연속투입을 안내했다. 운영프로그램/모델/임계값/PLC는 변경하지 않았고 재부팅도 반복하지 않았다. 다음 결과는 실제요청75이후 원본/원장/C기록으로 확인하며 현재 미확정이다. 증거 `runs/mixed_stability_20261017/right_READY.json`, `right_START.json`, `right_NOTEBOOK_DISCONNECTED.json`.

## Attempt12 — 결품 37건 연속 처리, REVIEW 8건 별도 보존

사용자는 기존 운영본으로 먼저 시험하겠다고 결정했다. `engine-integrated-555c3a43053ce4ce`·같은 boot `c8d72e3f-d5cf-423a-b832-774394ba8243`·Main1161·CameraWorker2741·NRestarts0를 유지했고 운영 코드·모델·임계값·400ms·PLC 계약을 변경하지 않았다. 정상30과 합산하지 않는 별도 결품 시험이며 사전에 배기구만 빠진 모형과 가운데 문양만 빠진 모형을 준비했다. 기대 정답은 수집 계획에만 두었고 Detector 입력에는 전달하지 않았다.

한 번 실제 START 후 노트북 LAN을 분리했다. 사용자의 “대충30번”과 달리 원장에는 새 요청38–74의 **37건**이 있다. 사용자가 STOP을 누르고 LAN을 재연결한 뒤 기록을 회수했다. 사용자는 “순서를 지켰고, 추가 START 없이 계속 배출·재가동됐어요”라고 일괄 확인했다(`fail_OPERATOR_CONFIRMED.json`). C 로그에서 시험 구간의 STOP/START·재접속·중단은 없었다. 물리 관측과 시스템 기록은 구분한다.

| 구간 | 유효 촬영/저장/PLC 완료 | 판정 | 원본/전체 자산 | 구간 경과 |
|---|---:|---|---:|---:|
| 사전 계획 첫30 | 30/30/30 | FAIL24, REVIEW6, PASS0, ERROR0 | 90/120 | 543.651초 |
| 이후 포함 전체37 | 37/37/37 | FAIL29, REVIEW8, PASS0, ERROR0 | 111/148 | 672.751초 |

첫30 요청→C거래 완료: 최소6.946초·중앙10.852초·p95최근접순위11.498초·최대11.547초. 전체37 중앙10.799초·최대11.552초. 모델 추론만의 시간과 구분한다. Health 누적 최대갱신248.376ms는 서비스 시작 이후 값이며 이번 구간 p95/p99가 아니다.

각 ID의 SQLite COMPLETE·최종영속화1회·PLC완료1회, 동일 boot/connection/request token, C Result→후속sequence Done→RequestLOW→출력0→다음대기 순서를 검증했다. 새3장/고유frameID·PTS증가·요청후source시각·촬영3초·안정0.6초·처리15초·같은epoch/generation과 원본 파일/디코딩픽셀SHA를 대조했다. 모든37건 유효 촬영이며 `PRAGMA quick_check=ok`. 첫30 GET-only 수집기와 원장이 일치한다. 30건에서 수집기가 종료된 뒤에도 운영은 이어졌다. 이후 C 기록에는 사용자 STOP의 PLC_CONTROL_INHIBIT·STOPPED_BASELINE만 있으며, 완료된74번을 취소된 검사로 다시 세지 않는다. 회수시 실제 STOP·RequestLOW·출력0·저장유휴다.

### REVIEW의 직접적인 근거

- 4·6·10·20·24·36회(6건): `PART_ASSIGNMENT_UNCERTAIN`. 카메라/제품 자체 미검출이 아니라 `pipe_left`에 대응하는 `gray_pipe` 검출점수0.323–0.494가 부품 기준0.5보다 낮은 프레임이 있었다.
- 30·34회(2건): `INCONSISTENT_THREE_FRAME_RESULT`. `pipe_left`가 세 장 중 일부 PRESENT, 일부 MISSING으로 바뀌었다.
- 이8건의 각3장에서는 문양 슬롯이 MISSING으로 기록돼 있다. 현행 `jetson/src/decision/engine_dynamic.py:aggregate_three`는 다른 슬롯의 불확실/프레임불일치를 우선하여 전체 REVIEW로 남긴다. 따라서 ‘문양 결품을 못 봄’ 또는 ‘오조립 때문에 FAIL’로 설명하지 않는다. 최종 정책은 계속 `BASIC_PRESENCE_ASSEMBLY_REFERENCE_V2`, `assembly_affects_final=false`다.
- 4회2번째·30회3번째 실제 원본 및 2회 비교 원본을 열었다. 해당 화면 아래쪽 곡선 파이프는 보인다. 점수 흔들림은 저장된 추론 증거로 확인되지만 조명·반사·형상·자세 중 원인 하나를 확정하지 않는다. 임계값 하향, REVIEW→FAIL 변경, 재학습은 하지 않았다.

현재 **30회 이상의 검사·저장·PLC 연속처리는 검증**, **결품30건 모두 확정FAIL은 미달**이다. REVIEW를 실패0 성과에 숨기지 않는다. 표시/처분상 불량 경로로 이동했는지는 사용자 관측과 구분한다. 검출/판정 정확도는 두 모형 반복이며 전체결품 일반화가 아니다. 사용자가 교대 순서를 확인했으므로 배기구결품19건은 FAIL19, 문양결품18건은 FAIL10/REVIEW8로 대조한다. 사용자 준비·순서 확인을 기대정답 근거로 쓰며 모델 결과로 정답을 만들지 않는다. 매개체별 독립 표식·각 투입의 별도 사람 영상검토는 없으므로 두 실물 반복에 대한 평가다. 다음 정상·오른쪽파이프결품 혼합30은 별도 attempt14에서 진행 중이며 결과 미확정이다. 이전37건 뒤 준비key 문제는 이번 구간에서 재발하지 않았을 뿐 수정·해결 증거가 아니다.

근거: `runs/mixed_stability_20261017/fail_AUDIT.json`, `fail_NATIVE.json`, `fail_REVIEW_SUMMARY.json`, `fail_OPERATOR_AFTER.json`, `fail_EVIDENCE.zip` SHA `27c8b6fa08f189ec2af9fc6aba00c847714e3ed04ad6a7c9d9ab75451dd9a67b`(241파일/163870934bytes). 검사 원본·DB·모델은 GitHub에 올리지 않는다. 원본 파일은 그대로 유지하고 노트북에서 읽기 전용 분석만 수행했다. 배포 변경이 없어 재부팅은 반복하지 않는다.

---

## Attempt11 — 실제 단독 30회 검증 통과, 혼합 구간 후속 문제 분리

2026-10-17 실제 재부팅한 `engine-integrated-555c3a43053ce4ce`, boot `c8d72e3f-d5cf-423a-b832-774394ba8243`에서 한 번 START 후 노트북 LAN을 분리했다. 사용자 정상 조립 준비·연속 투입 및 “대충 30번 넘게…잘 되고” 관측과 Jetson 원기록을 대조했다. 노트북 전원 OFF 시험은 아니다. 같은 Main1161·CameraWorker2741, 서비스 재시작0. 첫30건 동안 새 START·STOP·재접속·C abort 없이 이어졌고, 별도 수집기는 30건 저장 후 정상 종료했다. 수집기가 종료된 뒤에도 운영 서비스는 계속 검사했다.

| 구간 | 접수/유효 3장/PLC 완료 | 결과 | 원본 / 전체 이미지 | 구간 경과 |
|---|---:|---|---:|---:|
| 사전에 계획한 첫30건 | 30 / 30 / 30 | PASS30, ERROR0, REVIEW0 | 90 / 120 | 545.150초 |
| 이후를 포함한 전체 | 37 / 37 / 37 | PASS36, FAIL1 | 111 / 148 | 707.301초 |

첫30 요청→C 완료 지연: 최소10.120초, 중앙10.676초, p95(최근접 순위)14.219초, 최대14.325초. 첫 요청부터30번째 거래 정리까지 약9분5초다. 촬영/모델 추론만의 시간이 아니라 최종 저장과 결과 전송을 포함한다. 전체37건 중앙10.675초. 모델·결품 임계값·촬영3초·0.6초 안정·연속3장·처리15초·400ms lease·PLC 계약을 변경하지 않았다.

**검증 근거:** 각 요청 token의 boot/connection/request번호, 같은 ID SQLite COMPLETE·최종 저장1회·PLC 완료 기록1회, C의 `REQUEST_RECEIVED → PYTHON_RESULT_DURABLE → RESULT_CYCLIC_SENT → 후속 sequence DONE → Request LOW → 출력0 → IDLE`를 확인했다. 새 원본111장의 서로 다른 frameID/파일SHA/디코딩 픽셀SHA, 같은 camera epoch/worker generation, PTS 증가·요청 후 source시각·3초 내 선택, 안정0.6초·대상 고정좌표 마스크/57600분모를 대조했다. `PRAGMA quick_check=ok`. 수집기407개 관측은 동일Worker/오류없음이며 첫30 JSON/원본과 원장이 일치한다. 이 표의 실제 거래 완료는 독립 PLC 내부 소비 ACK를 추가로 입증한다는 뜻은 아니다. 물리 정상 배출·재가동은 사용자 일괄 관측이며 매회 LED 확인을 요구하지 않았다.

HealthDiagnostics는 누적 최대갱신간격을 유지한다. 회수 시 최대248.376ms로400ms 미만이다. 첫30/37거래 중 C ready 해제·통신 timeout·재접속은 없었다. 모든 갱신 간격의 p95/p99는 원시 전체표본이 없어 미측정이다. C가 기록한 별도 디스크 쓰기 최대6.568초를 통신 callback 최대20.503ms와 혼동하지 않는다.

**불량 혼합 관측과 STOP 경계:** 1–36은 모델 PASS, 37번 `649f6df9438f4948b8860ae8cd424666`은 `RIGHT_PIPE_MISSING`/FAIL이었다. 사용자는 불량 한 번 FAIL 정상동작, 다른 한 번은 요청 후STOP인 것 같다고 했지만 제거 부품은 기억하지 못했다. 36/37 원본을 실제 열어보면37에는 화면 위쪽 흰 곡선 파이프가 보이지 않는다. 이는 보조 영상 관측이며 물리 L/R 명명과 정답 승인으로 바꾸지 않는다. 정확한 혼합 시작 ID와 두 번째 결품 종류는 미확정; 사후에 PASS를 정상 정답으로 라벨링하지 않는다.

37번은 monotonic1129.347232에 완결됐다. 이후1138.200710 `REQUEST_STORAGE_PENDING`,1138.227925 `READY_FALSE:REQUEST_STORAGE_OWNER_CHANGED`,1138.237911 C `PYTHON_NOT_READY`/DISARMED가 기록됐다.1138.527967에 Python ready가 돌아왔고 실제PLC STOP 기준은1143.447153에 관측됐다. 따라서 이를 “STOP으로 취소된38번 검사”로 보고하면 안 된다.38번째 C 접수/SQLite 검사/취소 기록은 없다. 현재 소스의 `_key()`(런타임·서비스·카메라·PLC·직전 검사 식별 묶음)와 대기 저장 작업의 key 불일치가 준비 해제 경로다. 바뀐 key의 개별 항목은 그 시점에 보존되지 않아 확정하지 않는다. 직전 제품 분리 이벤트와 시간상 인접하지만 인과는 추가 확인이 필요하다. 정지 중1207.997396에도 저장준비 재확인에 따른 해제가 있었으며1208.297393 STOP 기준으로 복귀했다.

**판정:** 이번 첫30회 연속 검증은 PASS. 전체37건의 검사·저장·PLC 거래도 완료됐다. 이후 준비 해제를 숨기지 않고 혼합 연속운전의 남은 문제로 분리한다. 이 약12분 시험으로 장시간 안정성·전체 결품 정확도·오조립 정확도·실PLC 모든 장애복구를 완료했다고 하지 않는다. 현재 STOP·RequestLOW·출력0·저장 유휴·같은Worker를 확인했고 운영코드/장치를 추가 수정·재시작하지 않았다. 노트북 SSH 터널만 복원했다. 실제 브라우저 렌더링은 미검증이다.

근거: `runs/capture_stability_20261017/ATTEMPT11_AUDIT.json`, `FIELD30_NATIVE.json` SHA `d9e20a8fba153dc762bea43418cb9b5a7deca8bd2511f8c00dc3f20e9973ce75`, `FIELD30_CURRENT_STATUS.json`, `ATTEMPT11_BLOCK_RESULT.json`, `ATTEMPT11_STATUS.jsonl`, `ATTEMPT11_EVIDENCE.zip` SHA `19abbc51c88e7ee7cb2acf72e0a8322c2548ce7c8f527ea3815b33830815971b`(241파일,162153253bytes). 원본과 DB·모델은 GitHub에 올리지 않는다. 배포 소스 commit `e5ea81f22789fab2ffffb5109c13c8edca39a6a6`은 GitHub master 일치 확인 완료. 현재 증거 문서만 추가한다. 시험 중 실제 프로그램 변경은 없어 재부팅을 반복하지 않는다.

---

이하 당시 준비·과거 시도 기록을 원문대로 보존한다.

**현재 실물 단계:** attempt11에서 실제 START·요청대기·0건을 확인한 뒤 사용자 노트북 LAN 분리와 SSH 단절을 확인했다. 정상 모형30회 연속 투입 안내 완료, 결과는 Jetson 원기록 회수 전까지 미확정이다. 노트북 전원OFF는 시험하지 않았다. START 확인 도구의 첫 Stop_PB=false 가정 오류를 기존 운영 계약(true)과 대조해 고쳤으며 PLC/운영 소스는 변경하지 않았다.

## 최신 적용·재부팅 증거 — 촬영 안정 후보 적용 완료, 실물 시험 대기

현재 실행본 `engine-integrated-555c3a43053ce4ce`이며 새 boot `c8d72e3f-d5cf-423a-b832-774394ba8243`로 실제 재부팅 자동 기동을 확인했다. 아래의 '적용 전' 문장은 당시 검증 단계 기록이다. 백업 SHA `56d370b47fa7fd52f84a3ee4d9473dedd306e9f2d79c22db6ec8d483687e57f1`, 174파일·SQLite 무결성·기존247개 검사 행/자산/최종결과 보존 확인 후3파일만 교체했다. 전체 운영189파일 해시, 기존 설정·모델·최종판정 정책 유지 확인. 복원 자료는 `runs/capture_stability_20261017/PRECHANGE_BACKUP.tar.gz`와 `NOTEBOOK_BACKUP_RECEIPT.json`; 복구 시 최신 Journal/원본을 과거 DB로 덮어쓰지 않는다.

`AFTER_REBOOT_PROOF.json`: systemd enabled/active, 재시작 없는 자동기동, 단일카메라 Worker2741, 모델/PLC/health 준비, 현재 제품 복구 경고 없음, `검사 준비됨 · 현장 START 대기`. `POSTBOOT_STABILITY.jsonl`: 추가30.685초에 서로 다른 새 프레임7개와 동일Worker 확인. 재부팅으로 끊긴 **노트북 SSH 터널만** 다시 연결했다. 장치 서비스 자동 기동과 노트북 터널 복귀를 구분한다. 실제 브라우저 렌더링은 미검증이며 서버의 화면 데이터/응답을 확인했다.

운영 적용 소스는 위3파일의 SHA와 연결되며 source commit은 현재 GitHub 반영 절차 중이다. 다른 미커밋 수정 없이 만든 공개 내보내기에서도 핵심28+컨베이어16=44개 및 JS2개 통과했다. 첫 내보내기에서 기존 `notebook/deployment` 누락으로 컨베이어 모듈을 불러오지 못한 실패는 보존하고 해당 공개 의존성을 추가한 뒤16개만 재실행했다. 제품 소스 추가 수정은 없었다.

Jetson 자체 GET-only 수집기 PID4393, `data/engine_dynamic_pose_002/acceptance/continuous30_20261017_attempt11`. 같은 결과 수집 함수를 사용해 기존 e0fa…의 실제 JSON·원본을 읽고 저장한 뒤 파일/픽셀SHA를 검증했다(`COLLECTOR_PREFLIGHT.json`). 검사 ERROR는 실패로 남기되 수집기나 화면이 서비스 STOP을 명령하지 않는다. 첫 START 전0건, 사용자 START 질문 대기. 실물 거래수/유효검사수/정확도/실운전 health 최대 간격은 아직 미측정이다. 30회 완료를 주장하지 않는다.

## 2026-10-17 최근 네 ERROR와 대상 영역 촬영 안정 판정 — 적용 전 검증 완료

**현재 운영 a8afabe667e881ed 유지. 후보 555c3a43053ce4ce는 미적용이며 재부팅·새 실물 30회는 미실행이다.**
최신 첨부 TASK에 따라 원시 원인 감사, 최소 수정과 격리 검증을 수행했다. 현재 작업 증거는 `runs/capture_stability_20261017/`이며 현장 원본·DB·모델은 공개 Git에 포함하지 않는다.

### 네 건의 실제 최초 실패

| 검사 ID | 원시 오류 | 후보/거부/폐기 안정 장수 | 마지막 두 쌍의 전체 → 대상 변화율(Jetson) |
|---|---|---|---|
| `1feea8a2ca974e5a99962b183a413588` | DEADLINE_EXCEEDED | 11/9/0 | 0.005191 → 0.000226, 0.004774 → 0.001128 |
| `680c0018a58c4e28915bc02ea5a242f2` | DEADLINE_EXCEEDED | 11/11/0 | 0.036649 → 0.001163, 0.040035 → 0.002483 |
| `450629977150446797e4d6b470565b61` | DEADLINE_EXCEEDED | 11/11/0 | 0.004010 → 0.000417, 0.004340 → 0.000712 |
| `7e21efd276be4ea0b55a90d9d9902029` | DEADLINE_EXCEEDED | 11/10/0 | 0.003524 → 0.000642, 0.003021 → 0.000382 |

각 건에서 `EngineInspector.motion()`의 안정시간 미충족 → `inspection_worker`의 불안정 후보 거부 → 촬영 기한 안에 연속 3장 부족 → `FreshFrameSelector.check_active()`의 `DEADLINE_EXCEEDED`가 확인됐다. `result.reason`은 `FreshFrameError: DEADLINE_EXCEEDED`, fresh-frame terminal도 같았다. 네 건 모두 이전 `e14586d0800243d98bb4a35c768041ff`와 **같은 실패 경로**다. `EXISTING_ERROR_ASSEMBLY_REVIEW`를 원시 원인으로 해석하지 않았다.

네 건의 마지막 진단 3장 각각의 부품 판정은 PASS지만 안정 플래그는 각각 `[false,true,true]`, `[false,false,false]`, `[false,false,false]`, `[false,false,true]`였다. 유효한 연속 3장 검사로 세지 않는다. 모든 후보의 metadata·source time·거부 이유는 있으나 PNG는 마지막 3장만 남았다. 따라서 전체 3초 재현이나 수정 후 이 과거 요청의 성공을 주장하지 않는다. 1fe의 마지막 두 쌍은 이전 기준 아래지만, 앞선 변화와 0.6초 요건 때문에 마감까지 안정 2장만 얻었다.

`PER_ID_AUDIT.json`에 요청/Worker/선택/처리/저장 시각, camera epoch, generation, token, 해당 ID만의 Journal 이벤트와 원본 자산을 연결했다. 8개 비교 검사에서 자산 32개 SHA, 원본 24PNG를 확인했다. 실제 실행본 Main1079/Worker2725, boot081d4e63-96af-4ec0-b49c-174640b3960b, NRestarts0였다.

실제 C token의 request 8–11은 각각 Result→후속 패킷 Done→Request LOW→다음 IDLE로 완료됐고 뒤의 12·13도 처리됐다. 6–13 구간 C 기록에서 STOP/START·재접속은 없었다. 관측 로그만으로 모든 물리 개입 부재를 확정하지 않는다. PLC 거래 완료와 촬영 검사 성공은 별개다. 과거 tracking 진단, 현재 WAIT_START, 누적 ERROR 및 내부 소비 미확인 플래그를 이번 원인으로 쓰지 않았다.

### 최소 수정과 비교 의미

- `engine_inspector.py`: 유효한 단일 product_envelope의 이전/현재 상자 합집합을 **동일 카메라 좌표**의 마스크로 사용한다. 두 crop을 따로 정렬하지 않아 실제 이동은 이전·새 위치에서 픽셀 변화로 남는다. 상자 중심 이동량도 기록하지만 bbox 떨림만으로 실제 이동을 단정하지 않는다. 슬롯 탐색 영역은 가이드까지 넓어질 수 있어 안정 마스크에 넣지 않는다.
- `absdiff >25`, 320×180 비교와 **분모 57,600**, `>0.008` 기준을 유지한다. 마스크 안에서 변한 픽셀만 분자에 넣는다. 따라서 기존과 같이 461개 이상 변화하면 거부한다. 작은 영역의 면적으로 나눠 같은 0.008을 적용했던 중간 후보는 실질적으로 과도하게 엄격해져 채택하지 않았다. 그 실패/재현 결과는 보존했다. 마스크 면적, 고정 분모, 변경 픽셀 수, 마스크 내 비율, 전체 화면 비율을 모두 기록한다.
- 안정 0.6초는 처리 wall time 대신 이미 검증되는 영상 source monotonic 기준이다. 새 요청, epoch/해상도/관측 종류 변경, 시간 역전/반복, 검출 소실·대상 혼동·품질/pose 불확실에서 안정 상태를 이어받지 않는다. 새 요청은 새로 안정 시간을 충족해야 한다.
- `inspection_worker.py`: 요청별 motion 초기화와 거부 증거·연속 후보 초기화 횟수만 보완했다. 촬영 3초, 연속 새 3장, 처리·저장 총 15초, 모델·confidence/NMS·필수 부품/슬롯·PLC/400ms·STOP/실장애 보호는 그대로다.
- `line_details.js`: 선택한 검사 ID의 저장된 기본 원인·촬영 횟수·실패 진단 원본과 같은 ID의 PLC 완료 관측을 표시한다. 조립은 참고로 유지한다. 원시 이유가 없으면 미기록이며, 다른 검사/미리보기의 이유를 붙이지 않는다. 기존 상세 조회만 사용하고 mutation을 추가하지 않았다.

제품 밖의 변화가 기존 안정 판정에 영향을 준다는 것은 차분으로 확인했다. 원본을 열어 배경 밝기/그림자 변화와 제품 내부의 작은 변화도 확인했으나 광원·카메라 진동·금색 손잡이 방향을 물리 원인으로 확정하지 않았다. 유효 bbox/품질/pose에 의존하므로 정지한 손/가림을 완벽히 검출하지 못하며 안전 감시 기능이 아니다.

### 검증 결과와 제한

- 최종 motion·Worker·촬영 회귀: **Windows 44/44, Jetson aarch64 44/44 PASS, skip0**. 바로 앞 후보의 전체 관련 ARM64 162PASS 중 영향 없는 119개는 재사용했다. 최종 변화 경로 44개와 합쳐 관련 고유 163개다.
- 실제 이동/회전, bbox만 떨림, 배경만 변화, 가림 전이/보고된 품질 불확실, 검출 소실/다중 대상, 새 요청/epoch, 처리 지연과 source 시간 구분, 안정 일부 후 이동/기한, 네 결품 FAIL을 격리 검증했다. 기존 3초/15초 분리·늦은 취소 결과·저장 전 전송 방지 회귀도 포함한다.
- C/Python 실제 격리 IPC fixture **2/2 PASS**. 한 START의 PASS→FAIL→REVIEW→ERROR→PASS 거래 및 완료 결과 게시를 검증했다. 실 PLC 시험으로 표시하지 않는다.
- 같은 24개 보존 원본의 순서·source timestamp로 Windows/Jetson 차분을 대조했다. OpenCV 표기 버전은 둘 다5.0.0이나 CPU 구현/반올림으로 몇 픽셀 차이가 있다. 임계값 교차 여부는 일치한다. 과거 e145의 마지막 두 쌍은 실제 Jetson 전체0.015330/0.019774 → 대상0.001302/0.003281이다.
- 기존 개발 E03의 정상·네 결품 원본 D145/D157/D169/D181/D193과 저장된 검출을 사용한 별도 마스크 대조도 통과했다. 배경만 합성 변경했고, 원본/기존 부품 결과는 그대로다. 좌우 촬영 명칭과 저장 슬롯 명칭이 반대인 두 사례는 그대로 남겼다. 새 검출 정확도나 실물 결품 수용으로 세지 않는다. E04/B04 미사용.
- JS 상세 원인/ID 연결·기존 상세 시험 2개 PASS. 정식 브라우저 도구의 접근 정책 제한으로 실제 렌더링 검증은 **UNVERIFIED**이며 우회하지 않았다.
- Jetson CPU motion만 동일 원본24장, 각3회 warmup 후 번갈아20회(각480측정): 기존 중앙0.469ms/p95 1.111ms/최대7.086ms, 후보 중앙0.577ms/p95 1.358ms/최대11.524ms. 중앙 추가 약0.108ms. 전체 추론 지연 또는 실시간 최대 보장은 아니다. 격리시험 전후 동일 Worker·PLC 카운터 확인, 배포 후 health 최대 갱신간격은 아직 미측정이다.
- 최초 Windows sandbox 임시 폴더/IPC 권한, 시험 runner spawn main guard, 오래된 fixture 메서드, Linux AF_UNIX 경로 길이와 import 누락 실패는 모두 보존했다. 원인을 수정한 하니스로 다시 검증했으며 제품 보호 기준을 낮추지 않았다. 최종 배포 검증기의 Windows 경로 구분자 차이도 정규화해 통과했다.
- STOP 상태 진단 clip API는 standalone의 기존 POST 차단 정책으로 거부돼 **수집하지 못했다**. 가드를 해제하거나 별도 카메라를 열지 않았다. 저장되지 않은 전체 촬영창은 계속 미확정이다.

### 적용·실물 시험 인계

후보는 운영 파일3개이며 `EXPECTED_RELEASE.json`, `DEPLOYMENT_VALIDATION.json`에 파일/시험 해시를 고정했다. 이전 운영 a8afabe667e881ed와 설정 해시는 `PREPARATION_LIVE_EVIDENCE.json`에 보존한다. 기존 정지 백업→노트북 전체 파일SHA/SQLite검증→원기록 보존 적용→실제 재부팅 검증 경로를 재사용한다. 새 DB로 덮어쓰거나 과거 ERROR를 정정하지 않는다.

현재 실제 STOP/Request LOW/출력0/유휴를 관측했다. 사용자는 위치 확인을 위해 START 후 STOP했다고 보고했고 요청 카운터는13으로 그대로였다. 적용 전 **현재 빈 벨트 확인을 질문한 상태**이며, 이전의 빈 벨트 답을 재사용하지 않는다. 후보 적용/백업/재부팅/새30회 모두 아직 실행하지 않았다.

다음: 빈 벨트 확인→기존 유지보수 종료 기록→백업/적용/실제 재부팅 자동 기동→보조 수집기의 실제 기존 결과 한 건 읽기·저장 preflight→한 START·같은 실행본·노트북 없는 실물30. 거래/유효촬영/정확도 각각 집계하며 과거 성공을 합산하지 않는다. 3/10은 같은 시도의 점검 지점이다. 실패·누락 원인은 보존한다.

---

상태: **수정본 적용·실제 재부팅 자동 기동 확인 / 노트북 분리 후 실물 30회 시험 진행 안내 / 결과 검증 대기**.
현재 운영본은 `engine-integrated-f03d3f570a172c5f`다. 사용자 START 이후 실제 `Mc_Run=true`, Request LOW, IDLE, 오류 없음과 새 시험 카운터 0을 확인했다. 노트북 LAN 분리 사용자 확인과 SSH 접속 단절을 기록한 뒤 정상 모형 30회 연속 투입을 안내했다. 노트북이 분리된 동안의 실제 완료 수는 재연결 후 Jetson 원기록으로 검증한다.
Git 공개 대상만 내보낸 별도 작업 폴더에서도 관련 회귀 349개 중 344PASS·5skip(비공개 사진 1, Linux 전용 4)을 확인했다. 기존 UI 2건은 해당 회귀 범위에서 미검증으로 남는다. 실제 배포한 8파일과 공개 소스는 줄바꿈을 정규화하면 동일하며, Git의 LF 변환으로 달라진 바이트 해시는 런타임 해시와 구분해 `PUBLICATION_EXPORT_TEST.json`에 보존했다. 모델·원본·SQLite·현장 증거 파일은 Git에 포함하지 않는다.
공개 묶음에 새 런타임 모듈 4개가 빠지지 않도록 기존 allowlist와 관련 계약 시험도 함께 포함한다. 별도 Git 내보내기의 배포 계약 시험 7개가 통과했다(`PUBLICATION_MANIFEST_TEST_v003.json`). 앞선 검사 도구의 notebook import 경로 오류와 Windows 임시 폴더 권한 오류는 로그를 보존했으며, 제품 소스 변경 없이 명시적인 내보내기 경로와 작업 폴더 내 임시 경로로 해결했다. 이 검증은 새 장치의 전체 모델 설치·실물 수용 완료를 뜻하지 않는다.
사용자 최신 TASK(2026-10-17)가 기존 촬영/처리기한 설계 승인 대기를 대체한다.
현재 Task는 `tasks/CONTINUOUS-30-FIELD-001.md`이며 이전 실패/원본은 보존한다.

## 수정 전 실제 실행본과 비교

근거: `runs/runtime_audit_20261017/RUNTIME_BEFORE.json`, `SOURCE_COMPARISON.json`.
운영 `engine-integrated-a807de46a264aa3e`, boot `d1c9285e-c935-44b3-9dad-5dfce734a7aa`.
systemd enabled/active, Main5395, 시작 2026-10-17 12:34:22 KST.
ExecStart는 `envs/app_v1/bin/python -B -X utf8 current/standalone_service.py --config config/standalone.json`.
실제 cwd `current`, 인터프리터 실제 파일 `/usr/bin/python3.10`; 가상환경 명령행 유지.
자식 OpENer5412, Assembly5416, Inspection5447. multiprocessing 보조 프로세스 포함 명령행은 원증거에 보존.
촬영/모델 재시작·PLC 조작 없이 조회했다. PLC STOP/Request LOW, Result/Done0.
카메라/Worker/조립 준비 확인. 이전 c7f15…는 raw COMPLETE/PASS이나 integrated INCOMPLETE/PLC BLOCKED로 유지.

GitHub HEAD와 로컬 HEAD는 `5fe3669318b166ee945d04cc0bd7cafe865f9e23`로 동일하다.
비교 가능한 운영 파일131개 중 로컬 working tree와 바이트 동일127, HEAD와 동일109.
차이4개는 release.json, supervised_panel.html/js, journal/sqlite.py.
sqlite.py는 줄바꿈을 정규화한 본문 차이 없음. 나머지는 배포 범위 결정 전 별도 대조 대상.
메모리 코드를 직접 덤프한 검증은 아니다. 실행시각·Release 응답·과거189파일 배포 증거와 디스크 해시를 연결했으며,
파일 해시만으로 메모리 코드 일치를 단정하지 않는다. 루트 RELEASE_MANIFEST는 과거값이므로 현재 운영 근거로 쓰지 않는다.

운영 SHA256:

| 대상 | SHA256 |
|---|---|
| current/standalone_service.py | fdac0226b17add99f035a87eb8486a5743d112ba7d7081af839b3ac6fb30ff44 |
| current/opener/OpENer | 63ca4b16db530eecc9f95155a40cf758b291a590d85894dc8e9faf7aa0b2f4a4 |
| config/standalone.json | f128f7999c9bdec4a973a22eade5e1042c15436e3b9e6a91f6ebd834bf240a91 |
| config/station.json | 23fab6d7dd0b50c86cfdb1b51d6215e59c25d0bab0a3763f62cbf8e4999773bb |
| config/line_profile.json | 4568dab0cd26311819fc273f3f9b43a6a2578abdd4283dcbbe2c1daf65d0159f |

## 실제 경로와 기존 상태

standalone_service.main → OpenerProcess + OpenerGateway + StandaloneRuntime,
실제 선택: EXISTING_PLC_INSPECTION / OPENER_CYCLIC / PLC_AUTOMATIC_REPEAT /
PLC_REQUEST_TRACKED_FULL_FRAME / STATIONARY. 최종 판정은 BASIC_PRESENCE_ASSEMBLY_REFERENCE_V2.
카메라와 모델은 기존 Inspection Worker만 소유하며 조립은 별도 ProcessAssemblyInspector.

| 동작 | 기존 상태·담당 | 완료 근거 |
|---|---|---|
| 대기 | C IDLE / Handshake ARMED / Service IDLE | 실제 LOW 및 건강·직전 거래 정리 |
| 요청 수락 | C REQUEST_RECEIVED → REQUEST_LATCHED → Service ADMITTING | C boot/connection/request + Writer의 영속 admission |
| 촬영·처리 | Handshake INSPECTING / Service BUSY | 원 trigger와 durable admission 이후의 새 프레임 |
| 원본 저장 | BUSY + storage_pending | Journal.finish 완료와 같은 context의 Writer receipt |
| 조립·통합 저장 | INSPECTION_DURABLE → ASSEMBLY_INSPECTING / final_pending | 조립 evidence + commit_integrated |
| 결과 송신 | IPC_QUEUED → C TEST_RESULT_READY → RESULT_SENT | queued는 송신 완료가 아님; 실제 C 수락/전송 기록 |
| 종료 | DONE_SENT → WAIT_REQUEST_OFF → CLEARING_DONE → READY_NEXT | Result와 다른 후속 패킷 Done, LOW, clear 전송 |
| 다음 대기 | retire_automatic → IDLE | 정리된 거래/기록; 물리적으로 다른 모형이라는 주장은 하지 않음 |

## 차단 조건 표

A 실제 활성, B 다른 모드 비활성, C 수정되어 운영 반영, D 후보만 반영, E 증거 부족.
행 번호는 감사 시작 당시 소스 기준이며 수정 후 diff와 함께 읽는다.

| 분류·조건 | 파일·함수·행 | 설정·시계 | 전→후 / 영향 | 회복·증거 | 조치 |
|---|---|---|---|---|---|
| A 촬영3초가 active deadline까지 대체 | production_admission.py activate:164–176 | station fresh_frame=3000ms, trigger부터; 기존15초 덮음 | BUSY/저장→health false→C취소 | attempt08 c7f… 실제 재현; 늦은 저장은 원PASS 보존, 재전송 금지 | **최초 원인 수정** |
| A 추론/인코딩 뒤 촬영기한 재검사 | inspection_worker.py worker_main:405,463 | selector.check_active, 마지막 선택 이후에도3초 | 유효 원본→ERROR | 경계 fixture로 전후 비교 | **같은 원인 수정** |
| A 늦은/중복/이전epoch 프레임 | fresh_frame.py consider:112 이후 | 요청+epsilon/영속수락 floor, age350ms, 간격150ms, 촬영3초 | 선택 거부/현재 ERROR | 기존 floor/epoch/cancel 회귀 | 유지 |
| A 저장기한·context·Writer 생존 | inspection.py health:203–215 / _storage_completions:163 | 현재 active deadline, generation/epoch/identity | BUSY→RECOVERY/현재 차단 | 원본/SQL 성공과 PLC 완료 구분; 경계 경합 추가 시험 | 기한 범위 수정·보호 유지 |
| A Worker/camera/disk | inspection.py health:187–235 | heartbeat5초, preview2초, 실제disk 여유 | health false→C disarm | 실제 사망/단절은 자동 heartbeat로 은폐 안 함 | 유지 |
| C 요청 시작 동기SQL 지연 | request_start.py tick/_submit; production_admission.prepare/activate | 단일 기존 Writer, durable-before-dispatch | ADMITTING 중 실제제어 검사 지속 | 이전 Windows/ARM64각318실행, native6; 운영 반영 | 재설계 없이 지연 회귀 |
| C 원본/최종/완료감사SQL | result_storage.py _run:40; standalone.py _run:1700 / _storage_wait_health:1658 | bounded writer, Journal try-lock; queue1 | 정상pending은 대기, 실제실패는 차단 | 기존550ms 지연 health최대110.766ms(합성) | 조합 회귀 |
| A Python Ready lease | opener_cyclic.py _connected_loop:171 | 실제 health_update부터400ms | Ready→false; C취소 | 이전418ms 사례, attempt08 최대192.385ms로 이번 원인 아님 | 유지 |
| A C Python heartbeat | engine_commissioning.c CommTick:277 | 마지막IPC heartbeat부터500ms | active→DISARMED | 명령수신 주기; Ready lease와 별개 | 유지 |
| A PLC freshness | engine_callbacks.c.inc EngineInit:105 / CommControlsValid | 마지막 cyclic 입력부터200ms | 입력/출력허가차단 | 실제 C config값; heartbeat와 별개 | 유지 |
| A IPC freshness | opener_cyclic.py decode_snapshot:21/read_snapshot:87 | 생성시각500ms, timeout poll100ms | snapshot없음→HOLD | 기존 poll vs lease 분리 | 유지 |
| A 전체 PLC 거래 상한 | engine_callbacks.c.inc:113 / CommTick:285 | C request_at부터120초, Result/Done/LOW까지 | active→REQUEST_HANDSHAKE_TIMEOUT | 소스 설정 확인; 운영 binary build 대응 추가확인 필요 | 유지 |
| A 요청전 관찰·조립 대기 | standalone.py _trigger_cyclic:1154/_poll_result:1558 | line_profile arrival30초(C accepted_at), assembly30초(조립submit) | 촬영미실행 ERROR 또는 조립시스템실패 | 총상한120초가별도존재;15초를 단계마다 재부여 안 함 | 유지·전체시간계측 |
| A HIGH 잔류2초 | standalone.py _automatic_health:559–568 | disarmed/sync/idle/ready_next에서HIGH 관측부터2초 | 다음요청차단/물리STOP필요 | attempt08은 **수락 후 저장기한→취소의 후속오류**, 처음부터 미수락 아님 | 2초삭제/가짜Done 금지 |
| C 이전 배출 추적 오류 | standalone.py _automatic_health/_start_automatic_observation_window; product_passage.py | 새C cycle+정리된거래+새관측; 과거passage진단 | 과거오류가다음cycle영구차단하지않음 | cycle_scoped_tracking 배포증거; 새 물리제품 증명 아님 | 회귀 |
| B 과거 제품 배출 필수 gate | standalone.py supervised/기존tracking 분기 | 현재 automatic정책과다름 | 다른모드전용 | import/call조건 기준 구분 | 작업 제외 |
| C 완료 후 preview 미검출 | standalone.py _validate_cyclic_final:1357, _completed_observation; completed_evidence.py | automatic/fullframe, 현재검사3원본durable | 과거preview guard대신현재원본검증 | 이전 완료6건; 카메라실제장애/epoch/STOP/세션검사는유지 | 회귀 |
| A 현재cycle/session/STOP 취소 | standalone.py _poll_cyclic/_validate_cyclic_final; CyclicHandshake.poll | 실제controls/token/generation/epoch | INSPECTING→HOLD/BLOCKED | 현재제어유효성필수 | 유지 |
| A IPC 결과 queued→무송신 | opener_cyclic.py _connected_loop:200–211; standalone.py _publish_committed:1479 | queue400ms+healthy+동일key+REQUEST_RECEIVED | 조건실패시pending제거; published_ids는이미추가 | 실제발동 미확인, C120초가유한차단; 명시적실패진단시험필요 | 최초원인수정후 별도검증 |
| A 미완료Journal 복구 | aborted_recovery.py / request_start.py settlement:108 | 동일원거래final/취소/전송증거 | 다음수락보류 | 현재c7f…실제복원; 원PASS를완료거래로위조하지않음 | STOP 기반 append-only 복구 유지 |
| A 조립 참고분석과시스템실패 | integrated_decision.py combine_decisions; standalone.py:1563 | 참고 오조립FAIL은최종영향없음, 실행/저장실패는별개 | 정상참고FAIL은다음cycle가능; 시스템실패BLOCK | V2정책유지 | 임의생략/먼저PASS금지 |
| A C evidence 실패/한도 | engine_evidence.c Writer:29,52 / callbacks | queue128, events12000/16MiB, 별도Writer | 기록실패→출력차단 | 장시간한도실측미확인; 첫30회와장기보장구분 | 보호유지·누적계측 |
| A 기동 잔여IPC 소켓 | opener_process.py __init__:33–36 | 배타owner lock후에도존재하면거부 | 부팅service5회실패 | 10/17 실제, 수동무소유확인/보존이동복구 | 자동기동수용의남은문제 |
| E Windows 수집기 nonPASS 중단 | 기존continuous observer 조건 추적 중 | REVIEW/FAIL시collector종료와서비스차단구분 | 수집기만종료가능 | Jetson영속기록으로30집계하도록점검 | 완료전확인 |
| C 노트북 의존 | standalone_service/main, local Journal/OpENer/Worker | 직접Jetson192.168.50.2↔PLC192.168.50.3 | UI/export ACK를기동조건으로쓰지않음 | 코드상독립; 노트북없는실물은미검증 | 실제 단독30 필요 |

## 최초 수정 단위

원 capture trigger부터 **촬영3초**, **원검사 처리/PNG·Journal 저장15초**를 분리한다.
prepare→Writer admission→dispatch 사이에서15초를 다시 시작하지 않는다.
마지막 선택시각은 원본 metadata의 selected_at_monotonic이며 추론 종료시각과 구분한다.
선택3초 이후 원본은 계속 거부한다. 이미 선택된 사진의 추론/인코딩은 기존15초까지만 허용한다.
후속 조립30초 및 C 거래 전체120초는 기존 계약대로이며,15초가 전체PLC거래 SLA라는 주장은 하지 않는다.
STOP·취소·원본 무결성·Worker 사망·queue/SQL실패·세션소유권·중복전송 보호는 유지한다.

수정 전 `attempt08/DEADLINE_REPRODUCTION.json`을 재사용하고, 새 fixture는 추가로 마지막 추론/인코딩 경계를 검증한다.
합성 회귀는 실물 횟수로 세지 않는다. 이후 같은운영본·한START의30개 완료거래에서 원본3장/판정/Result→Done/LOW/다음수락을 감사한다.
정상제품의 REVIEW/FAIL 분포는 AI성능 항목에 별도로 남긴다. 사진없는ERROR는 실물AI검사완료로 세지 않는다.

## 2026-10-17 검증 후보와 배포 준비

**최신 적용 결과:** `f03d3f570a172c5f` 실제적용및재부팅자동기동 확인. 백업174파일/SQLite 무결성·노트북SHA=`590779f37fa69ad8d98a6b60d2be23bf0669c68254e138bae35313722df7e48d`. 새boot `c050e0e3-9cd9-4b69-80de-76932fd6616d`, systemd enabled/active Main1078 NRestarts0, 단일카메라Worker2758, 운영189파일SHA·모델·PLC ready·WAIT_START. 이후31.36초동안7개서로다른프레임과같은Worker/STOP대기확인. 재부팅후수동복구없음. 이전검사원본·행·final보존,미전송건은기존ABORTED추가,새grant/재전송없음. 실물연속30회와장시간안정성은아직미검증이다. 아래는적용직전준비기록이다.

후보 `engine-integrated-f03d3f570a172c5f`, 운영 `a807de46a264aa3e`에서 정확히8파일만 변경한다. 아직 적용·재부팅·새 실물 시험 전이다. 현재 사용자STOP·모형전부제거 확인과 실제PLC STOP/RequestLOW/출력0을 대조했다. 이전 실패 c7f…는 원본4자산/원판정PASS/통합미완료/미전송을 그대로 보존하며 기존 append-only abort 절차의 읽기 전용 사전검증을 통과했다. 새grant/사진/PLC출력은 생성하지 않았다.

| 확인 | 실제 결과 | 한계 |
|---|---|---|
| 촬영/처리·저장 경계 수정 전 재현 | 유효 마지막사진 추론/인코딩과저장이 촬영창을 넘을 때 실패 재현 | 기존attempt08와 연결, 새로운 실물 아님 |
| 관련회귀 | Windows와ARM64 각각338실행:337PASS+기존자료1skip | 기존 UI2 및 전체패키징자산2 차단은 PASS로 세지 않음 |
| 실제 C/Python 격리 IPC |7PASS, 한START12회 요청/원본/최종저장에350/450/600/1000ms지연 | 합성 PLC·AI, 실제PLC네트워크 미사용 |
| 12회 health 갱신 간격 | 최대114.614ms, p95=102.749ms,p99=110.606ms,488구간 | 400ms 기준 유지; 현장 지연보장은 아님 |
| 기동 잔여소켓 |Windows35PASS+Linux전용4skip / ARM64 39PASS | 실제재부팅 자동기동은 적용 후확인 |
| 송신대기 경계 |추가5PASS: stale/healthfalse/다른session·request/phase불일치 무송신; ambiguoussend 재생금지 | 소켓send도 C수락·PLC완료가아님; C120초의 유한거래상한은유지 |

IPC 감사 보충: `OpenerGateway._connected_loop`의 조건불일치 시 pending 제거가 실제로 존재한다. Python의 published표시만으로 검사완료를 집계하지 않는다. 같은C 거래는120초 상한/health·controls 실패로취소되므로 이 경로 자체를 무한대기라고 단정할 수없다. 현재현장 최초원인으로 입증되지 않아 통신동작을 추가변경하지 않았다. 자동재전송도 추가하지 않았다.

수집기 보충: `notebook/diagnostics/collect_field100.py:167–173`은 ERROR·필수사진부족·시스템fault에서 종료한다. REVIEW/FAIL만으로는 종료하지 않는다. `runs/continuous_30_20261016/observe.py`도 판정을 출력할 뿐 서비스제어를하지않는다. 과거 각회차STOP은 당시정상PASS 시험의 사람개입 절차였다. 새승인기준은 Jetson Journal과실제C Result/Done/LOW의30회 완료이며 수집기 실행유무가 검사허가가아니다.

증거 정정(원본 유지): `IPC_RESULT.json`의 12회항목 `injected_storage_delay_ms=550`은 이전3회fixture의 요약필드가 남은 값이다. 실제12회 지연은 같은항목의 `stage_delays`12개(각단계350/450/600/1000ms)와 동결시험소스를 따른다. 측정치나원본JSON을 고쳐 성공을만들지않았다. PC회귀 완료 뒤 보고용 CANDIDATE누락 오류는 원로그/입력해시를 대조해 별도receipt로복구했다. 추가IPC단위시험 최초Windows실패는fixture의AF_UNIX상수누락이었고, 시스템호출mock을보완한v002에서5PASS했다. 제품코드수정은없었다.

배포사전근거: `runs/runtime_audit_20261017/FINAL_CANDIDATE.json`, `DEPLOYMENT_VALIDATION.json`, `RAW_ABORT_CHECK.json`. 백업은정지후SQLite backup API와전체운영파일SHA를노트북에서검증한뒤에만적용한다. 권한상 원격sudo는비밀번호를요구하여사용자터미널의시작명령을기다린다.

## 2026-10-17 단독 실물 attempt09 결과와 수락 대기 수정

노트북 LAN을 분리한 상태에서 한 START로 **17개 요청 중 16개 PLC 거래가 완료**됐다. 17번째 요청에서 운전이 중단되어 사용자가 STOP 후 LAN을 다시 연결했다. 부품 검사 결과는 **PASS 14건, 촬영 ERROR 2건, 촬영 전 취소 ERROR 1건**이다. 최대 연속 유효 PASS는 13회이며 **30회 안정성 목표는 미달성**이다. 16건 완료를 16건 정상 검사로 바꾸어 집계하지 않는다.

실제 SQLite와 C trace에서 첫 16건 모두 원본 3장·표시 이미지 1장, 통합 결과, Result → 이후 sequence의 Done → Request LOW → Done 해제 → 다음 요청 대기를 확인했다. 64개 자산 SHA 및 SQLite quick_check를 확인했다. C 요청부터 거래 완료까지 최소 9.555초, 중앙값 10.031초, 최대 16.304초다. 첫 요청부터 16번째 완료까지 290.250초였다. 이 짧은 시험을 장시간 안정성으로 표시하지 않는다. 수집기는 첫 ERROR에서 종료됐지만 운영 서비스는 계속 실행됐으며, 이후 건수는 Jetson 원장과 C trace에서 직접 복원했다. 원증거: `runs/runtime_audit_20261017/ATTEMPT09_AUDIT.json`, `FIELD30_NATIVE.json`.

| 사례 | 실제 증거 | 해석과 남은 한계 |
|---|---|---|
| 1번째 `258e0266…` | `DEADLINE_EXCEEDED`, 후보 11장 중 거부 8장. 마지막 진단 사진의 motion_fraction 0.030486, stable=false | 원래 3초 안에 안정된 연속 3장을 확보하지 못함. 저장된 3장 각각의 부품 판정은 PASS여도 촬영 요건 통과가 아님 |
| 15번째 `e64adb5b…` | 같은 촬영 오류, 후보 12장 중 거부 9장. 저장된 진단 사진 3장 모두 stable=false | 작은 순간 변화량만으로 0.6초 연속 안정 시간을 충족했다고 할 수 없음. 원본을 실제 열어 확인했으나 진동·밝기 변화 중 어느 것이 주원인인지 미확정 |
| 17번째 `55766bc5…` | 수락 저장 253.908ms 정상 완료. 같은 camera/worker/track 1. frame 8646→8647에서 eligible true→false 뒤 `ADMISSION_CURRENT_TRACK_OR_REQUEST_CHANGED` | 정확한 8647 provider packet은 보존되지 않아 순간 미검출을 현장 직접 원인으로 확정할 수 없음. 촬영·통합 final·C Result/Done 모두 없음. health lease 만료가 아니라 Python의 명시적 Ready 해제 |

운영 코드에서는 수락 저장 직후의 일시적 영상 부적격과 실제 요청/추적 소유권 변경을 같은 오류로 처리했다. 동일 조건의 격리 재현은 수정 전 실패했다. 후보는 **`src/runtime/request_start.py` 한 파일**만 변경한다. 같은 영속 수락 receipt를 유지하면서 원래 기한 안에서 새 유효 프레임을 기다리고, 재저장·중복 촬영 요청 없이 한 번만 시작한다. 요청·track 변경, STOP/EStop, 카메라/Worker/통신/저장 실패와 기존 기한은 계속 차단한다. 촬영3초·처리15초·Ready400ms·모델·검출/안정화 임계값은 변경하지 않았다. 위 촬영 ERROR 두 건까지 해결됐다고 주장하지 않는다.

검증: Windows 73/73, ARM64 73/73 PASS. 실제 C AF_UNIX 격리 경로는 서로 다른 시험 8개를 검증했다. 새 시험은 같은 수락 receipt에서 미검출 3tick 후 새 프레임으로 3거래를 완료했고 갱신 간격 최대 111.567ms였다. 12거래의 요청/원본/최종 저장 350/450/600/1000ms 지연 회귀도 통과했다. 이는 합성 PLC·사진 시험이며 실물 횟수에 더하지 않는다. 최초 새 C 시험은 시험 변수 초기화 순서의 NameError로 실패했으며, 원로그를 보존하고 해당 모듈 5개를 다시 실행해 통과했다. 운영 PLC 카운터·카메라 소유자는 시험 전후 동일했다.

**적용 상태:** 후보 `engine-integrated-a8afabe667e881ed`는 검증·임시 배치만 완료했다. 현재 운영본은 `f03d3f570a172c5f`이며 실제 적용/재부팅/새 30회는 아직 대기다. 사용자가 현재 STOP·모형 전부 제거를 확인했다. 원격 sudo 인증이 없어 기존 정지 백업 절차의 시작 명령을 요청했다. 기존 17건 전체와 취소 증거를 보존하며, 취소 건은 새 adapter의 실제 STOP 증거가 확인된 뒤 기존 append-only 복구 절차로만 정리한다. 새 결과·가짜 Done·재전송을 만들지 않는다. 상세 검증·배포 준비는 `runs/admission_frame_wait_20261017/FINAL_CANDIDATE.json`에 있다.

## 2026-10-17 수락 대기 수정 적용·실제 재부팅·attempt10 시작

위 임시 배치 상태 이후 사용자 STOP·빈 벨트와 sudo 실행을 받아 **a8afabe667e881ed를 실제 적용**했다. 정지 백업 174파일·SQLite의 SHA256 `f54556de1bc9ba19512c38226563ba47a7d5b1ba6b765cd936a0a34edb5a6d96`를 노트북에서 검증하고, 적용된 운영 파일 189개의 해시를 대조했다. 원래 17건의 검사행·원본·판정은 보존했다. 미전송 17번은 기존 append-only 취소 복구만 기록했으며 가짜 결과·Done·재전송·승인 grant를 만들지 않았다.

유지보수 도구의 실패도 남겼다. C trace 파생 파일의 CRLF/LF 해시 불일치는 원본을 보존하고 기존 예상 해시와 정확히 일치하는 별도 LF 사본으로 수정했다. 취소 기록기의 기본 outbox 10,000 제한은 이미 운영 코드가 사용하던 PC 수집 비필수 정책(`outbox_limit=None`)과 불일치하여 같은 정책으로 맞췄다. 저장 내구성·디스크·STOP 검사는 유지했다. 제품 종료 확인의 두 조회 사이 프레임 만료는 새 유효 프레임을 제한 시간 동안 읽기 전용으로 확인한 뒤 기존 종료 API를 한 번 호출했다. `TRACE_ARTIFACT_CORRECTION.json`, `MAINTENANCE_POLICY_CORRECTION.json`, 실패 로그와 성공 receipt를 함께 보존했다. 배포를 처음부터 반복하거나 실패 기록을 삭제하지 않았다.

**실제 재부팅 확인:** boot `081d4e63-96af-4ec0-b49c-174640b3960b`, systemd enabled/active, MainPID 1079, NRestarts 0. 단일 카메라 Worker 2725, 모델·PLC·준비 상태가 자동으로 복귀했고, 31.054초 동안 같은 Worker의 새 프레임 7개를 추가 확인했다. Jetson 수동 재시작이나 전원·USB 조작은 없었다. 노트북 SSH 터널은 별도로 다시 연결했다. 브라우저 도구가 URL 접근을 정책상 거절하여 실제 렌더링은 미검증이며, 서버 API의 WAIT_START 상태와 영상 갱신은 확인했다. 근거는 `runs/admission_frame_wait_20261017/DEPLOYMENT.json`, `AFTER_REBOOT_PROOF.json`, `POSTBOOT_SUMMARY.log`다.

**새 실물 attempt10:** Jetson 내부 GET-only 기록기 PID 4696, `data/engine_dynamic_pose_002/acceptance/continuous30_20261017_attempt10`. 준비 도구가 BASELINE 작성 중 읽은 초기 오류는 같은 프로세스가 파일 작성을 마친 뒤 확인했으며 중복 실행하지 않았다. 실제 START 후 운전·IDLE·요청/결과/Done/완료 0·카메라 준비를 확인했다. 사용자가 노트북 LAN만 분리했고 SSH timeout을 관측한 뒤 정상 모형 30회 연속 투입을 안내했다. 실물 결과는 아직 원장/C trace 회수 전으로 **30회 성공 미확인**이다. 기존 시험의 성공 수는 합산하지 않는다. 정상 기대 상태는 시험 기록에만 사용한다.

## 2026-10-17 단독 attempt10 — 오류 뒤 후속 검사 계속됨

한 START와 노트북 LAN 분리 상태에서 실제 **5요청/5 PLC 거래**를 확인했다. 순서는 **PASS → PASS → ERROR → PASS → PASS**다. 사용자는 오류 후 검사가 한 번 더 진행됐다고 관측했으며, 원장에는 별개 요청 두 건이 뒤따랐다. 오류를 지우거나 같은 요청을 재검사한 것은 아니다. 각 ID의 원본3장+표시1장 총20자산 SHA, SQLite quick_check, Result → 이후 Done → Request LOW → 거래 종료를 확인했다. 요청→C완료 최소9.498초/중앙10.795초/최대13.345초, 첫요청부터5완료까지84.194초. 정상유효검사4건/촬영오류1건이며 최대연속PASS2, **30회 목표 미달성**이다. 같은boot/Main1079/Worker2725이고 서비스 재시작은 없었다. 수락 취소·Ready 만료·통신 차단은 이번5건에서 없었다.

3번째 `e14586d0800243d98bb4a35c768041ff`의 원인은 `DEADLINE_EXCEEDED`다. 원래 촬영3초 동안 후보11개 중10개가 안정조건을 충족하지 못했고, 한 장만 안정으로 확보했다가 다음 프레임에서 연속성이 깨져 폐기됐다. 마지막 진단 원본3장은 실제 열어 확인했으며 모두 엔진과 네 부품이 보이고 각 프레임의 부품판정은PASS다. 그러나 진단사진을 유효한 연속안정3장으로 대체해서는 안 된다. C는 기존계약의 `AI_ERROR_AS_PLC_NG`로 해당거래를 종료했고 다음 요청2건은PASS로 처리했다. 사용자 STOP 후 RequestLOW/출력0/저장유휴를 확인했으며 복구·재시작·새START를 실행하지 않았다.

변화량을 **운영 Jetson OpenCV5.0.0**에서 원본으로 재계산했을 때 마지막두구간의 motion_fraction=0.0153298611/0.0197743056이 원기록과 정확히 일치했다. 기준0.008 초과 변화픽셀은883/1139개이며, 인접사진의 검출제품상자 합집합 밖이808/950개(91.5%/83.4%)였다. 이는 전체영상 차분 방식(`engine_inspector.py:motion`)이 주변 변화에 크게 영향을 받았다는 증거다. 엔진자체정지·조명·반사·진동의인과는 이 세 장만으로 확정하지 않는다. 이전8후보는메타데이터만있어 전체3초의화면을재구성할수없다. Windows 재계산은 첫구간에서1픽셀 차이로 엄격대조에실패했고, 원실행환경의Jetson에서정확대조했다. 원본·실패스크립트·결과를보존했다. 모델/검출기준/안정임계값/촬영기한은변경하지않았다.

**수집기 준비 결함:** Jetson 내부 GET-only수집기는 첫결과 검증 때 `replay_envelope_thresholds`가 `replay_basic_part_presence`를 지연import하며 모듈누락으로 종료했다. 시작프로세스·BASELINE 확인만으로 준비완료를 보고한 것은 불충분했다. 필수운영원장과원본은독립저장되어5건모두회수했다. 빠진진단의존성만전송하고 다음준비도구는첫결과검증에필요한import를시작전에검사하도록수정했다. 이번실패를새수집기실행으로덮지않았다. 이개발도구보완은운영서비스나카메라변경이아니다.

근거: `runs/admission_frame_wait_20261017/ATTEMPT10_AUDIT.json`, `FIELD30_NATIVE.json`, `FIELD30_AFTER_STOP.json`, `SAVED_MOTION_ANALYSIS.json`, `field_error_originals/`. 실물30회/장시간안정성은계속미달성이고, 임계값완화로PASS를만들지않는다.
