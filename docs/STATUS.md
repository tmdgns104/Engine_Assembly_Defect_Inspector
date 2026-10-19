PORTABLE OPERATING BUNDLE + NOTEBOOK TRAINING SOURCE / GIT EXPORT AND GITHUB MASTER VERIFIED
게시 완료: `52d5e900f37d2da0953a4b1401e2f73ada55979c`, GitHub public/master·원격 필수68파일 해시 확인. `docs/verification/GITHUB-PORTABLE-20261019.json` 참조.
2026-10-19 사용자 요청으로 현재 운영32c4를 다른 Orin Nano에 복사할 jetson/portable 묶음(203파일·모델7개·승인된 SQLite368건)과 신규 설치/환경/GPU 점검·한국어 문서 준비. source200파일 해시 보존. 기존 장치의 승인·원장은 새 장치에 운영 승인으로 복사하지 않으며, 기존 수동 UI의 새 기준/영역 확인 기록이 필요하다. notebook/에 실제 엔진 부품/전체 검출 및 참고 분류 학습 소스·출처·촬영→라벨→분리→학습 안내 추가. 설치·손상/덮어쓰기 거부·Windows/Linux 격리·Git export 의존성/원본SHA·관련 합성 시험 PASS. 실제 기본 브랜치 master 게시 대상 확정. 새 장치 GPU/카메라/PLC/재부팅은 UNVERIFIED이며 현재 Jetson 운영32c4 변경/재학습/추가 실물시험 없음. Task: JETSON-PORTABLE-OPERATING-001. Evidence: docs/verification/JETSON-PORTABLE-OPERATING-001.json.

Previous checkpoint:
CONFIG + UI + HISTORY ACCEPTED / MIXED7 VERIFIED / UI-ONLY UPDATE REBOOT VERIFIED
2026-10-18 최신 운영 engine-integrated-32c484ac6aeb07f1. 설정 중앙화(기존 값 유지), /history 검색·상세·CSV, 부품 위치 원본 crop와 미결합 강조 UI 반영. 실물 시험은 사용자 종료로 실제7건: PASS4/FAIL3, REVIEW0/ERROR0, 원본21장·자산28SHA·저장/PLC완료7 확인. 계획10회 완료 아님. 최종 UI 두파일만 추가 변경; boot c45d184a-3707-4703-995a-8fa89ec76a8e, 서비스 자동시작·단일Worker 새3프레임·모델/PLC 준비·전체200파일·원장368건 보존 확인. 7회 후 UI 준비 중 USB 수신 장애는 사용자 재연결로 복구했으며, 마지막 UI 재부팅 뒤에는 추가 USB 조작/서비스 재시작 없이 준비됐다. 통합 응답10.183~14.324초 및 검출편차/오조립 참고 한계 유지. 추가 실물시험·학습·보정 없음. GitHub public/master 게시·원격 트리 검증 완료. 기능/모델/DB 커밋 3852cdcd58d3cbc2266717e6197a6fc1ee366245. 게시 영수증: docs/verification/GITHUB-RELEASE-20261018.json. Evidence: docs/verification/CONFIG-UI-HISTORY-20261018.json; runs/config_ui_history_20261018/ui_transition/.

Previous checkpoint:
CONFIG + UI + HISTORY / JETSON CANDIDATE QUALIFIED / APPLY AND MIXED10 PENDING
2026-10-18 최신 사용자 승인: 새 기능을 Jetson에 적용·재부팅 후 실제 연속10회 확인, 통과 뒤 GitHub master 최신 확정. 기존 운영0ff4d41638d745ff, 후보4c4b935f8ab0404a. Windows 관련83 / Jetson aarch64 격리28 PASS; 운영 station/profile 값 동일·실제 frozen 제품 검증. 모델/임계값/촬영·PLC 계약 변경 없음. 현재 STOP·빈 벨트 사용자 확인 및 실제 요청LOW·검사/저장유휴 확인. 백업 검증 감시기 대기 중; 적용·재부팅·실물10 및 GitHub반영 미완료. Task: PARAMETER-MANAGEMENT-CALIBRATION-001. Evidence: runs/config_ui_history_20261018/transition/.

Previous checkpoint:
STABILIZATION CLOSED WITH KNOWN LIMITATIONS / CONFIG + UI + HISTORY DEVELOPMENT
2026-10-18 사용자 종료·운영본0ff4d41638d745ff 확정. 최종 실물8건(최초5: PASS/ERROR/PASS/FAIL/PASS, 추가3: FAIL/PASS/FAIL), 모두 저장·PLC완료8. 카메라 수동USB복구 필요/검출 편차 미해결. 추가 현장시험·진단·배포 중단. 다음은 값 보존 설정중앙화와 기존 UI·DB 검색 개발. 상세 docs/STABILIZATION_CLOSEOUT_20261018.md.

Previous checkpoint:
DIAGNOSTIC OWNER FIX APPLIED / REBOOT REQUIRED USB RECOVERY / CURRENTLY READY
2026-10-18 0ff4d41638d745ff 한파일 진단추적ID 수정 적용, 실제 boot2f05f1cb-99b3-4553-a2dc-3b75cc45cecc. 서비스 자동시작은 확인했으나 CAMERA_FRAME_TIMEOUT으로 카메라 준비 실패; 사용자 USB재연결 뒤 현재 새영상/모델/PLC WAIT_START 복구. 무인자동복귀 합격 아님. 원watcher의 REBOOT_AUTOSTART_VERIFIED 문구는 사람USB조치를 관측하지 못하므로 AFTER_REBOOT_ASSESSED.json을 최종판정으로 사용. 193파일대조·기존347검사 보존, 이전 실패도 유지.
다음은 기존20초 단일Worker 진단으로 실제 운전구간 확보. START 실제신호를 직접감시해 채팅답변지연 없이 모형투입 안내. 현재모델/임계값/PLC/검사시간 변경0. 검출약점개선과 혼합30은 미검증, config.py/케이스50은 후속별도. Evidence: runs/inspection_reliability_20261018/run_capture_owner_transition/AFTER_REBOOT_ASSESSED.json.

Previous checkpoint:
RUN POLARITY DEPLOYED / REAL PASS1 / EMPTY RUN CLIP220 / TRACKING-ID DIAGNOSTIC FIX STAGED
2026-10-18 운영9488d93c4d69566e는 적용·실제 재부팅·자동준비 완료(boot873cac0c-b08e-4db1-89f0-4f142a35a2f7). 같은 전환 중복 실행 없음. 새 실검사31c25aaaeb6548299e62f3b512e600eb COMPLETE/PASS, PLC Result/Done/완료1. 진단은 별도220장/19.864초/RAW·pixel SHA 일치이나 전부 빈벨트·요청0이며 실제 검사는 창 종료 약14초 뒤; 전체운전구간 확보 성공 아님.
RUN_CAPTURE_OWNER_CHANGED는 실제Worker/카메라/Service/PLC연결 변경 없이 정상 새요청의 제품추적ID 갱신을 진단owner변경으로 오인한 것. 후보0ff4d41638d745ff는 해당 비교 한 곳만 수정, 실제 장치owner/장애·STOP보호 유지. Windows28/ARM64 49/배포증거4 PASS, 구코드2실패재현. 운영미적용/새후보재부팅미실행; 최신STOP 사용자응답과 현재 빈벨트영상·요청LOW·출력0·저장유휴 확인, 임시전송검증 완료.
다음: 후보 적용·실제 재부팅 → 빈벨트 START의 실제 신호를 즉시 감시해 정상1개 투입 안내 → 실제20초운전 원본·검출·안정·PLC 시간 확보. 엔진점수미달/추가부품후보 개선 채택·편차분포·혼합30은 아직 미검증, 모델/임계값 변경0. 신규기능·config.py·케이스별50회는 이번범위 아님.
Evidence: runs/inspection_reliability_20261018/run_capture_polarity_transition/FIELD_v002_FINDINGS.md 및 FIELD_v002_COVERAGE.json; 후보 run_capture_owner_transition/. 원본/실패/원장 보존, GitHub반영 미실행.

Previous checkpoint:
RUN DIAGNOSTIC POLARITY FIX / APPLIED AND REBOOT VERIFIED / FIELD SEGMENT PENDING
2026-10-18 진단 STOP 신호 해석 한 파일 수정9488d93c4d69566e 적용 및 실제 재부팅 완료. boot 873cac0c-b08e-4db1-89f0-4f142a35a2f7, systemd enabled/active(Main1173/NRestarts0), 전체193파일 해시·단일카메라Worker 새3프레임·모델/PLC 준비 확인. 이 부팅에서는 USB재연결/추가서비스재시작 없음. 검증백업5061b18f4ffd6bb95e3d227a27e66abba60f001733980af6ee33083deb6493e7/178파일/기존346검사 보존.
실제 운영에 반영된 것은 진단 수집 극성 수정이다. v011 fixture가 실제 Stop_PB=true 운전 계약을 놓친 사실, 첫 진단0장 실패와 실제 원검사PASS1건을 그대로 보존한다. v012 관련회귀 통과는 실제 운전 원본수집 성공이나 엔진 검출 오류 감소의 증거가 아니다. 메모리/부하 경로·모델·임계값·400ms·촬영3초/안정0.6초/새3장 변경 없음.
다음은 빈벨트 START 확인 후 정상 모형 한 개 투입, 승인된20초 진단 구간을 확보하고 STOP에서 저장한다. 엔진 점수 미달/저점수 추가부품 후보 문제의 원인별 채택판단, 정상편차 성능과 혼합30 최종수용은 아직 미완료. config.py 및 케이스별50회 보정은 별도 후속작업. 현재 추가 배포 차단 없음; 실제운전자료 확보가 다음 단계다.
Evidence: runs/inspection_reliability_20261018/run_capture_polarity_transition/AFTER_REBOOT_PROOF.json. 이전시험은 run_capture_transition/FIELD_RUN_FINAL_RECEIPT_v001.json. GitHub반영 미실행.

Previous checkpoint:
RUN DIAGNOSTICS / REBOOT VERIFIED / FIRST FIELD CLIP FAILED / ONE-CONDITION FIX STAGED
2026-10-18 engine-integrated-118ae17a9e77ae41 운영 적용, 실제 boot51c70212-8ce6-456d-9088-f22caac290fc에서 systemd enabled/active(Main1093/NRestarts0),193파일SHA·단일Worker2908·새3프레임·모델/PLC WAIT_START 통과. 이 재부팅은 USB재연결/추가서비스재시작 없이 자동복귀했다. 이전 재부팅 카메라 실패가 영구해결됐다는 의미는 아니다. 백업a122608c9643ba176dcba4dd2d74b7207cd3d7c8f5b58450cb59112e4f9c6b7e/176파일/SQLite/기존345건 보존.
첫 실물 진단: START전 모형을 투입 위치에 놓으라는 안내는 기존 빈벨트START→모형투입 절차와 달랐고 사용자 지적을 반영해 재사용하지 않는다. 최초조회 요청0은 순간값이었다. 약11초 뒤 실제요청1 접수, 검사4e0bc5bb15d34ef3aa443cb191afee5a는 COMPLETE/PASS·3선정사진·저장성공,PLC Result/Done/Complete 각1. 현재 원검사346건. 다만 운전진단은 RUN_CAPTURE_START_BEFORE_READY/0장으로 실패; Worker의 SAVED는 종료영수증 저장이며 영상수집 성공이 아니다. 엔진검출/추가부품후보 문제 개선 성공으로 세지 않는다.
실패 원인: 실제운전 Mc_Run=true/Stop_PB=true인데 신규 진단 controller만 Stop_PB=false를 기대했다. 기존 runtime/C 계약은 해제된 STOP회로=true를 요구한다. v01137시험 통과는 사실이나 fixture도 같은 잘못된 극성을 사용해 이 현장문제를 놓쳤다. 실제값으로 RED3실패 재현 뒤 진단 controller 한 파일만 수정했다. PLC/카메라/모델/threshold/400ms/촬영3초·안정0.6초·새3장/메모리경로 변경0. Windows관련25/ARM64v01246PASS·배포증거4PASS; 자원부하시험 재사용(변경경로아님). 후보9488d93c4d69566e/193파일/변경1소스,16입력파일SHA와STOP·유휴 확인; 운영미적용, 새재부팅/운전진단 재시험 미실행.
현재 STOP·빈벨트는 최신 사용자 ‘비웟어’와 새영상으로 확인. 기존진단0장·최초조회·최종원장·실패로그 보존. 다음: 사용자sudo전환→검증백업/한파일통합적용/실제재부팅→빈벨트START 후 모형투입으로 실제20초구간 수집→STOP저장/원본·검출·안정·PLC시각 대조→제품점수미달과저점수추가부품후보 최소개선 채택판단. 새 기능 확장·config.py 통합·케이스별50회보정은 후속 별도 작업이며 이번 선행조건 아님. 사용자 지정 후속문서 C:/Users/user/Downloads/CODEX_CONFIG_PY_MANAGEMENT_KO.md는 미착수.
사용자 제공 PLC 저장파일 SHA c0dff344cb815ae75cffe63c21454384393061abf4fa35e7d46405033c879137의23rung 직접읽음. Mc_Run+PhotoSensor+Sensor_Ready→Move_pending,Move_Timer T#4.5s,Inspecting·NOT Cv_Run 후 Inspect_Delay_Timer T#2s→Inspection_Request. 과거5초문서는 현재저장파일과 다름. 온라인전체동등성 미확인/PLC원본수정0.
Evidence: runs/inspection_reliability_20261018/run_capture_transition/{AFTER_REBOOT_PROOF,FIELD_RUN_FINAL_RECEIPT_v001,PLC_SAVED_LADDER_v001}.json; 후보 run_capture_polarity_transition/ 및 ARM64_v012_RESULT.json. 실제엔진약점감소·위치허용분포·오류없는혼합30은 아직 입증되지 않음. GitHub반영 미실행.

Previous checkpoint:
RUN DIAGNOSTICS / QUALIFIED + STAGED / OPERATOR SUDO TRANSITION PENDING
2026-10-18 사용자 ‘진단 수집 구현·검증 진행’ 승인 반영. STOP에서 준비 후 실제 START로 최대20초/240프레임/총768MiB, 기존 단일 Worker 원본과 이미 계산한 검출·자세·PLC 단계만 메모리 수집한다. RUN 중 이미지 인코딩/파일저장/추가추론 없음; fresh STOP·RequestLOW·출력0·검사/저장유휴의 갱신 lease에서만 저장한다. 기존 STOP≤5초 경로와 인증/오류보호는 유지. 모델·임계값·PLC·촬영3초/안정0.6초/새3장·400ms 변경 없음.
후보 engine-integrated-118ae17a9e77ae41: 기존 통합 manifest191파일+신규2모듈, 소스8개 변경. 운영5fd0e2ab9559458e 유지/미적용. Windows180시험(179PASS/Linux1skip)+후속관련19/15PASS, ARM64전체186PASS+최종변경37PASS(각 중복 포함, 합산 금지). 최종8소스해시와 시험입력 대조, 배포 증거 변조 거부4시험PASS. 전체 개발 패키징은 기존 AREA_REFERENCE_NOT_ALLOWLISTED 오류1건 재현되어 별도 미완료; 운영 전체 manifest/자산을 보존하는 검증된 변경 묶음으로 전환한다.
Jetson 저장원본 메모리부하시험 RUN_LOAD_v005:20초10fps 두번 각200/200픽셀정확일치, 수집 hook p95 1.925/1.875ms·최대4.015ms·probe RSS715.4MiB. 실제 IO health371샘플 모두READY·최대age113.1ms, 관측구간 reason-change unready0, 같은카메라Worker/PLC카운터 유지. 이는 저장사진 반복 부하이며 실물 운전/지연 성능 합격이 아니다. 50fps stress의5ms 초과 진단중단과 HTTP 거래 snapshot지연3건도 보존; 웹캐시와 실제 IO health를 혼동하지 않는다.
사용자 최신 ‘비웠어’·STOP/빈벨트영상 확인. 최초 stage가 남아 있던 MULTIPLE_PRODUCT_AMBIGUITY로 거부되어 실패로그 보존. 기존 인증된 STOP 유지보수 API로 완료검사d7be65cc의 과거관계만 닫아 원검사345건/PLC카운터/판정불변 검증, 신규검사/결과전송/운전명령0. 27개 전송파일SHA와 fresh STOP/유휴 재확인, runtime_issue=null. 새 실제 재부팅·운전중진단·혼합30 미실행. 직전 부팅의 CAMERA_FRAME_TIMEOUT/사용자USB복구 이력도 미해결로 보존.
증거: runs/inspection_reliability_20261018/run_capture_transition/{RUN_QUALIFICATION,DEPLOYMENT_VALIDATION,STOPPED_CONTEXT_CLOSURE}.json 및 TRANSITION_STAGE_VERIFIED.log. 다음: 기존 sudo 전환 시작→노트북 백업SHA/SQLite/원검사 검증→통합적용→실제 재부팅/단일Worker 새영상/PLC준비 검증. 이 단계까지 START 지시 없음. GitHub 반영 미실행.

Previous checkpoint:
INSPECTION RELIABILITY / VERIFIED BUNDLE APPLIED / REBOOT CAMERA FAILED / USB RECOVERY VERIFIED
2026-10-18 사용자 sudo 전환 실행. 노트북 백업 SHA15cf61e18ed923ff2343387ab0d2bee9e7bb6aef86dde8bb1daf2636ceab4307·174파일·SQLite·기존345검사 보존 검증 후 engine-integrated-5fd0e2ab9559458e 적용. 기존 PC111(110PASS/Linux1skip)·ARM64_v006117PASS는 이 8소스 변경 묶음에만 적용한다. 모델·임계값·PLC·촬영3초/안정0.6초/새3장·400ms 변경 없음.
실제 boot c8d72e3f→8ea9cafd-3fcb-4063-8b17-6051f41391dd, systemd enabled/active Main1084/NRestarts0 자동 시작. USB HCAM0 장치 경로는 존재했지만 CAMERA_FRAME_TIMEOUT 반복으로 360초 준비 검증 실패(TRANSITION_WATCH_ERROR/BOOT_OBSERVATIONS 보존). 따라서 무인 재부팅 준비 합격 아님. PLC IPC는 수신 중이었으며 카메라 복구 HOLD에서 공개 handshake snapshot이 null이었다. PLC 물리통신 단절로 단정하지 않는다.
사용자 동일포트 USB 재연결 뒤 기존 서비스 자동복구. AFTER_USB_RECOVERY_PROOF: manifest191파일SHA일치, 단일 /dev/video0 소유Worker10257, 새frame3개·WAIT_START·fresh STOP/LOW·모델/health 준비, 기존345검사 보존. 별도 서비스 재시작/PLC 조작 없음. USB 수동복구와 재부팅 단독 성공 구분. 현재 STOP·빈벨트 유지, 승인된 STOP≤5초 진단 촬영 준비.
최신 첨부 143bf342 추가지시 반영: 검출(A)·움직임(B)·부품검사 자세/가시성(C)의 최초 실패 단계 재현 후 최소 후보 하나 비교. 현재 STATIONARY 실제경로와 상대자세슬롯 재사용. product threshold와 pose-motion 분리는 동시에 변경하지 않는다. 이전bbox/pose를 새증거로 복사하거나 안정/새3장을 강제하지 않는다. 기준선117PASS를 향후 후보 통과로 재사용하지 않는다. 기본 PASS→최종PASS/OK, 기본 FAIL/REVIEW/ERROR→최종FAIL/NG(유효 거래만), 원상태·원인이 별도 보존되며 REVIEW/ERROR는 결품 검출 성공이 아니다. 참고오조립REVIEW로 PASS를 바꾸지 않는다.
운전 중 새 보조수집은 미승인. 기존 단일Worker/비개입/부하제한/누락기록의 구체안 제시 후 한 번 확인하며 STOP 촬영 경로를 완화하지 않는다. 다음: STOP 빈벨트 원본 회수→기존 실패 원본 최초 실패 재현·위치분포 및 인접 기준 비교→별도 검증→실제 위치/카메라 대조→동일 실행본 한START 혼합30. 새 실물30·무인 재부팅 안정성·위치강건성 미완료, GitHub반영 미실행.

후속 B 관측: FIRST_FAILURE_REPLAY_v001에서 오류 원본6장 중5장의 첫 실패는 제품0.5 기준(기존12장 단계출력 재현). 후보0.4에서6장 모두 pose/부품 진행, 정상3장 전부존재/오른쪽결품3장 해당누락 관측; 빈벨트52장 오선택0. 전체요청영상부재로 촬영유효3장/최종성공 미검증, 운영0.5 유지. STOP 빈벨트52원본 회수검증. 정상준비후 촬영도 실제빈벨트여서 정상자료 제외·현재화면 확인 대기. 상세 CONTINUOUS_RUNTIME_AUDIT 및 동일 runs 폴더.

후속 STOP 정상 대조(사용자 실제정지·화면전체확인): STOP_NORMAL_v002 52원본/4.980초·109파일 및 픽셀SHA/PTS검증. 실제 제품점수0.683525–0.754110/기준0.5미만0. 원본시간·기존0.15초간격의 격리재생26장 모두 제품/자세/네부품확인; 초기화된 안정관찰에서21장stable, 최초3장확보 원본시간1.380초(실제PLC응답시간아님). 운영0.5와오프라인후보0.4 동일. NORMAL_SEQUENCE_v001_FINDINGS_v002는 순수3장부품집계PASS와 요청/가시성컨텍스트없이 호출한 진단함수REVIEW를 구분; 후자는실제운영오류아님. 실제PLC검사0/운영기준변경0/위치허용범위·운전중성능미검증. 다음: STOP정상모형제거확인→오른쪽파이프결품대조.

후속 STOP 오른쪽파이프결품 재촬영: 사용자 ‘지금부터다시’ 이후 v002 51원본/4.948초/107파일 SHA·픽셀·PTS확인, 실제원본25/30/50번 시각확인. 제품점수0.805869–0.816665, 재생26장 제품/자세26·stable22, 오른쪽누락26. 첫안정3장 순수부품집계FAIL/RIGHT_PIPE_MISSING(원본시간1.180초, 실제PLC응답아님). 다만3장 배기구슬롯UNCERTAIN: 실제배기구0.909–0.937 정상배정에 별도낮은후보0.256–0.343이추가되어 LOW_CONFIDENCE가 해당슬롯을불확실처리. 제품기준0.5/후보0.4 결과동일; 제품문턱만으로이경로가해결되지않음. 운영기준/코드변경0. 다음은 같은결품모형 방향유지·화면중앙으로이동한 STOP위치대조(사용자배치대기).

후속 동일결품모형 위치대조: STOP_RIGHT_CENTER_v001 52원본/4.984초 SHA/픽셀/PTS검증. 같은실행본·카메라Worker·PLC요청0 유지. 새위치 재생26장 모두제품/자세통과·오른쪽MISSING/나머지PRESENT, 배기구추가후보로인한불확실3/26→0/26 관측. 두위치첫안정3장 순수부품집계RIGHT_PIPE_MISSING/FAIL, 운영검사미실행·후보0.4추가효과없음. 검출중심/자세각의실제차이는 RIGHT_POSITION_COMPARISON_v001.json; 물리cm허용치·반복재현·조명단일원인으로단정하지않음. 다음: 같은모형 STOP작은회전 대조(사용자준비대기).

후속 결품 모형 회전 대조: STOP_RIGHT_ROTATED_v001 52장과 STOP_RIGHT_OPPOSITE_v001 51장 원본/픽셀/PTS 회수 검증. 각 26장 격리 재생에서 제품·자세 26/26, 오른쪽 파이프 MISSING 26/26, 나머지 부품 PRESENT 26/26. 두 첫 안정 3장 순수 집계는 FAIL/RIGHT_PIPE_MISSING이며 실제 PLC 검사는 미실행. 기존 중앙 자세 대비 추정각 변화는 -19.043도와 +161.072도; 후자는 방향을 크게 뒤집은 대조로 보존하며 작은 반대 기울기 검증으로 세지 않는다. 모델·운영 기준 변경 없음. RIGHT_ROTATION_COMPARISON_v001.json에 원본 연결·위치 변화·각도 추정 한계 기록. 사용자에게 STOP에서 긴 금색 손잡이가 화면 오른쪽 아래를 향하는 작은 반대 기울기 배치 안내; 응답 대기.

후속 양쪽 작은 회전 대조 완료(정지 보정 자료): 사용자가 긴 금색 손잡이를 화면 오른쪽 아래로 배치한 STOP_RIGHT_OTHER_TILT_v001 51원본/4.916초·107파일·픽셀SHA/PTS 검증. 재생26장 모두 제품/자세 유효, 오른쪽파이프 MISSING·나머지PRESENT; 최초 안정3장 집계 FAIL/RIGHT_PIPE_MISSING(원본시간1.176초, 실제응답시간아님). 중앙기준 추정각 변화 -19.043도와 +21.516도 두 기울기 모두 동일 결품 결과. 위치도 함께 바뀌었으므로 ±각도 허용범위·각도 단일원인·독립검증 성공으로 일반화하지 않는다. 별도 +161.072도 방향 반전도 보존. 운영 임계값/모델 변경0·실제PLC검사0. 현재 STOP·결품모형이 화면 안에 있으며 다음 물리 행동은 요청하지 않음. 다음: 기존 자료로 부족한 실제 운전 전후 원본을 기존 Worker로 수집하는 구체안 확인. 운전 중 신규 수집은 사용자 승인 전 미구현/미실행.

Previous checkpoint:
INSPECTION RELIABILITY / FINAL PC+ARM64/C PASS / STOP DIAGNOSTIC RELEASE STAGED / NOT APPLIED
2026-10-18 현재 후보 engine-integrated-5fd0e2ab9559458e, 운영555c3a43053ce4ce/bootc8d72e3f/Main8165/Worker182705 유지. 수정8파일: runtime/journal request_start, production_admission, standalone, standalone_web, stopped_capture, misassembly_shadow, frame_matches. 모델·threshold·PLC·3초/0.6초/새3장·400ms 변경 없음.
최종 Windows111 중110PASS/Linux전용1skip(FINAL_WINDOWS_v002), ARM64/실제 C AF_UNIX 격리117PASS/0skip(ARM64_v006_RESULT). 실제PLC/새실물30은미실행. 시험중 실패 원본 보존: Windows spawn 실행기 main-guard 누락, 운영line_view와 다른 오래된기대문구(WEB_BASELINE_CONTRACT로 원본 동일 증명), ARM64 staging HTML누락, 가상프레임큐 overflow/queue.empty 주입경합을 실제put_latest/완료영수증시점주입으로 수정. 운영보호/assertion을 낮추지 않음.
C 동일6원본 ABBA 참고계산16.318→7.434초·출력/픽셀일치, 전체PLC응답/VALID자세정확도아님. B threshold 및 위치편차 성능은 미검증. 새 사용자 지시의 위치·카메라 편차/운전영상 분석은 현재 Task와 CONTINUOUS_RUNTIME_AUDIT에 반영; 상대자세슬롯 구조 확인, TARGET_UNCERTAIN 초기화 실제분포 추가분석. 운전 중 새수집 정책은 미승인. STOP최대5초만 승인.
사용자 최신 ‘비웠어’로 STOP·빈벨트 확인. TRANSITION_STAGE_v002에서 fresh STOP/RequestLOW/출력0, 요청23/완료23/유휴확인. 이전 완료요청23의 inactive PRODUCT_OBSERVATION_GAP 진단은 원기록보존; 전환전검사만 정확한완료token·C수량과대조해 허용. 실제fault거부14경우, 재부팅게이트는엄격유지. current/config/DB/서비스변경아직없음. 원격sudo비인증이라 사용자전환시작만필요.
전환 입력·후보·검증manifest: runs/inspection_reliability_20261018/. 동일Jetson tmp/verify 폴더 stage완료. 다음: device_transition.py transition 사용자sudo시작→watch_transition.py 백업회수/SHA/SQLite/원검사행검증→8파일통합적용→기동·실제재부팅·3새frame/단일Worker/PLC대기→승인된STOP원본촬영→B위치/관찰연속성 분석→필요한최소보정검증→독립혼합30. 원본/기존실패/미커밋보존. GitHub반영미실행.

Previous checkpoint:
INSPECTION RELIABILITY / A CANDIDATE 68 CHECKS PASS / C DUPLICATE MATCHING VERIFIED / NOT DEPLOYED
2026-10-18 사용자 실제 STOP 응답 뒤 새 PLC snapshot(2ms)으로 Mc_Run=false/RequestLOW/출력0/유휴를 확인했다. 같은 운영555c3a43053ce4ce/Main8165/bootc8d72e3f 유지, CameraWorker182705 새영상 수신 복구. 이 작업에서 서비스재시작·재부팅·PLC출력·운영변경 없음. 수동 카메라 점검·재시작 절차는 docs/PROGRAM_START_STOP_KO.md에 기록했다.
A-1 같은 저장 완료 ID의 촬영 전 관찰시간 만료를 미실행ERROR로 영속화하고 기존 NG/Done으로 종결하는 후보, A-2 유휴 저장준비조회에서만 tracking session 분리하는 후보를 수정했다. Windows62 PASS, ARM64/실제 C AF_UNIX 격리68 PASS(0skip); 동일 요청ERROR→다음PASS→FAIL, STOP/저장실패/늦은완료·실제owner변경 보호 포함. 운영·실물 통과 아님. 코드3개/시험해시는 runs/inspection_reliability_20261018/ARM64_v002_RESULT.json.
C: 실제4·6회 참고분석의 pose_matching이 기록된 참고시간 약94%였다. 같은 원본6장 Jetson 계측에서 한프레임6검색 중3검색이 descriptor 바이트·shape·dtype·method까지 동일, 중복약2.94초/장. frozen 코드/모델은 그대로 두고 load_frozen_models의 한프레임 범위에서만 동일 matching을 재사용하는 후보 추가. ABBA 동일6장/각방식2반복, 수치허용1e-6·그외/픽셀정확일치: 기존 참고계산 평균16.318초→7.434초(전체 PLC시간 아님). 여섯 프레임의 참고 자세결과는 기존에도FAILED였으며 VALID 부품분류 정확도 검증으로 세지 않는다. 코드 frame_matches.py, misassembly_shadow.py, runtime_allowlist.json. 근거 REFERENCE_CALLS_v001.json, REFERENCE_COMPARE_v001_RESULT.json/INPUTS.json; 결과회수완료. Windows 관련검사 통과 부분과 Linux fsync미실행은 각로그를따름.
B: 제품 threshold 후보/운영설정은 아직 변경하지 않았다. 현 독립운전 read_only_field_ui가 진단촬영POST를403거부, 우회없이 중단. 사용자가 2026-10-18 ‘정지 상태의 진단 촬영만 허용’ 승인. 새로운 /api/v1/maintenance/diagnostic-capture/{start,stop}는 loopback·same-origin·기존session token+fresh STOP/RequestLOW/IDLE/저장유휴에서만 최대5초·100프레임·128MiB, 같은카메라Worker 사용 후보를 구현중. 운전/요청/owner변경시진단만중지·중단기록. PLC운전·판정경로는추가하지않음.
진단촬영 시험: 일반guard6항목은 동작; 최초 body기본값중복 TypeError는수정. 중첩ASGI웹시험대기 원인조사중이며 STOPPED_CAPTURE_GREEN 실패로그 보존, v002시험에는180초덤프/240초상한. 설치/검증완료 아님. staged stopped_capture.py, standalone_web.py, standalone.py, test_stopped_diagnostic_capture.py. 다음: 웹시험정체 원인수정→정지촬영/변경전체 PC·ARM64/C 회귀→선택변경만백업배포·재부팅→새원본 기반B검증 및 별도혼합30. 사용자 STOP 유지, 새 모형배치 아직 요청하지 않음. 기준/모델/400ms/안정0.6초/촬영3초/새3장 유지, E04/B04 미사용. 기존 실패·운영DB·원본 보존, 아직push안함.

Previous checkpoint:
INSPECTION RELIABILITY / AUTHORIZED A-B-C FIXES / WINDOWS REPRODUCTION
2026-10-18 새 사용자 TASK(a4c679e9 첨부)가 촬영 전 대기 실패·준비 확인 결합의 최소 수정, 제품 검출 후보 오프라인 비교, 저장 이후 지연 계측과 증거 기반 개선을 승인했다. 기존 시험만 진행 제한보다 우선한다. 현장 적용 전 관련 회귀·ARM64/C 검증, 최신 STOP·유휴·백업 확인, 적용 후 실제 재부팅과 별도 혼합30을 수행한다. 모델 재학습/PLC 계약/부품 임계값/400ms/촬영3초·안정0.6초·새3장/내구성은 유지한다. 참고 조립 분석을 결과 전송 뒤로 옮기는 변경은 별도 확인 대상이다.
읽기 전용 점검: 운영 engine-integrated-555c3a43053ce4ce/Main8165, boot c8d72e3f-d5cf-423a-b832-774394ba8243. 코드·패키지·참고분석 자산223개 manifest SHA 일치. 네 문제 모두 아직 운영 미개선. USB HCAM0는 인식되지만 CAMERA_FRAME_TIMEOUT/Worker RECOVERY 관측; PLC API snapshot은 오래되어 현재 STOP 증거로 사용할 수 없다. 사용자 USB 연결 확인. 재시작·PLC 출력·배포 변경 없음. 증거 runs/inspection_reliability_20261018/{LIVE_INVENTORY,LIVE_HASHES,CAMERA_READONLY}.json. 기존 Attempt15 23거래/21유효/ERROR2를 보존하고 새30 성공으로 세지 않는다.
다음: Windows에서 A-1 저장 완료 후 관찰 기한 실패를 같은 ID의 미실행 ERROR로 종결하는 회귀 재현부터 진행한다. 카메라 수동 확인/복구 명령은 docs/PROGRAM_START_STOP_KO.md에 보완했다. 실제 영상 복구·새 실물 시험은 아직 미확인.

Previous checkpoint:
ATTEMPT15 AUDITED / MIXED23 TRANSACTIONS COMPLETE / CAPTURE ERROR2 / THIRTY NOT MET
2026-10-17 동일 운영555c3a43053ce4ce, 한START·노트북LAN분리 정상→오른쪽파이프결품 재시험을 실제 원장으로 확인했다. 요청1–23 총23건: PASS11/FAIL10/ERROR2/REVIEW0. 정상12건=PASS11+ERROR1, 오른쪽결품11건=FAIL10+ERROR1. 사용자 “순서를 지켰고 추가 START 없이 계속됐어요”와 C기록을 대조: 전23건 저장→Result→후속sequence Done→RequestLOW→다음대기, 중간 STOP/재접속/서비스재시작0. ERROR1→다음2 FAIL, ERROR16→다음17 PASS로 계속됐다. 사용자STOP/LAN재연결 뒤 실제STOP·출력0·유휴 확인. 23회 거래연속성은 확인했지만 30회/무오류 합격은 아님; 최대연속유효검사14건.
69원본PNG·92자산/165보존파일SHA·디코딩픽셀SHA·SQLite quick_check ok. 21건은 유효연속3장, ERROR2건의6장은 실패진단후보이며 성공사진으로 세지 않는다. 두 ERROR 모두 DEADLINE_EXCEEDED: 1회 후보12/거부12(TARGET_UNCERTAIN5),16회 후보10/거부10(TARGET_UNCERTAIN7), 안정선택0. 오류원본6장 실제확인: 모형은보이나 제품전체점수1회0.459/0.501/0.451,16회0.450/0.462/0.468으로 기준0.5 주변 미검출이 연속관찰을 끊었다. 큰이동/손가림은 이3장에 보이지 않음; 전체3초영상 없음, 위치·반사·각도 등물리원인은 미확정. ERROR를 실제결품FAIL로 고치지 않음. 기존계약 AI_ERROR_AS_PLC_NG로 거래완료.
전체429.651초, 요청→C완료 중앙10.799초/최대20.794초. 통합최종4·6회20.334/20.462초; 기본결과저장은각2.362/2.467초 후완료, 이후최종까지17.621/17.496초 추가소요. 기본Worker의15초기한과 통합완료시간을혼동하지않음; 총응답15초이내는전건충족아님, 추가구간병목은미확정. 같은Main8165/Worker8208/NRestarts0/bootc8d72e3f 유지. 이번운영코드·모델·임계값·PLC변경/재부팅0. 근거 runs/mixed_stability_20261017/right_retry_{AUDIT,FINDINGS}.json 및right_retry_EVIDENCE.zip(SHA9f6217cf7eaaa7b920e5d0afa7d198999adc4f24a9d3d28568ffea18cac3a0cf), right_retry_review/오류원본6장. 다음은 사용자와 ERROR감소/응답지연 개선범위를정할일이며 자동추가시험·임계값변경하지않음.

Previous checkpoint:
ATTEMPT15 NORMAL–RIGHT-PIPE MIXED30 IN PROGRESS / CANCELLED REQUEST75 SETTLED WITHOUT RESULT
2026-10-17 사용자 STOP·빈벨트 확인과 실제 PLC정지/빈영상 대조 후 기존 취소복구 절차를 재사용했다. 원격sudo인증불가로 사용자가 같은서비스만재시작(Main8165/Worker8208/NRestarts0), OS boot c8d72e3f는같음. 동일운영555c3a43053ce4ce·모델·임계값·계약변경0. 기존322검사·1204자산행·201최종행 보존지문 및77119488byte SQLite백업 SHA aa39545e8f3bf6f4130ef7e735d4fcea3a2e497e2717efccf98d37c7ec457063/quick_check ok를노트북에서검증. 공식 check→apply로 검사75에 CANCELLED_ADMISSION_WITHOUT_PLC_RESULT_V1 영수증667c0ba10b5b430e8e305b0f8bf5bb4f만추가; 기존ERROR/원본행/옛요청카운터75 유지, 새판정·grant·PLC출력0. 복구후ERROR없음/새영상3개/‘검사 준비됨 · 현장 START 대기’ 확인. 근거 right_BACKUP_MANIFEST.json/NOTEBOOK_BACKUP_RECEIPT.json/CANCELLED_ABORT_CHECK.json/CANCELLED_ABORT_APPLY.json/right_AFTER_RECOVERY.json.
사용자가 준비한 정상·오른쪽파이프결품모형을 재사용하여 별도 attempt15_normal_right_retry GET-only기록기8522를 시작했다. 새어댑터 기준 request/result/done/completed=0. 실제START→Mc_Runtrue/IDLE/새요청0을확인한뒤 사용자노트북LAN분리/SSH3초timeout 확인. 정상→오른쪽파이프결품 15쌍/30회투입 안내, 매회응답요구없음. 현재결과는재연결후원장·사진·PLC기록대조까지미확정이며 실패한attempt14와합산하지않음. 위치인식문제를수정한시험이아니라동일운영본복구후재시험이다. 증거 right_retry_READY.json/right_retry_START.json/right_retry_PLAN.json/right_retry_NOTEBOOK_DISCONNECTED.json. 다음: 완료/멈춤응답→실제STOP→LAN재연결→실제횟수/판정/원본/PLC완료감사.
직전 STOP 위치진단은 최초0.381231–0.489778/기준0.5 이상0/12 → 이동후0.767626–0.804196/12/12 → 손으로되돌린후0.718430–0.748063/12/12. 서로다른36프레임/동일이전Worker2741. 사용자는수동복귀위치불확실을밝혔고 실제영상도최초위치·각도와약간다름(bbox중심 최초대비x+53.333px/y−20.602px). 정확한동일위치 A-B-A 재현은미달,배치/반사/시간등단일원인은미확정. 추가수동위치맞춤은종료하고기준변경없음. 근거 right_RETURN_POSITION_COMPARISON.json. 점수회복과취소복구는혼합30성공이아니다.

ATTEMPT14 FIRST NORMAL CANCELLED BEFORE INFERENCE / PRODUCT OBSERVATION BELOW THRESHOLD / STOPPED
2026-10-17 사용자 지정 정상→오른쪽파이프결품 혼합30은 첫정상에서 중단됐다. 실제request75/검사9c3882c3a53b4420b7e905c5be732d9c: CANCELLED/ERROR, REQUEST_STORAGE_DEADLINE_EXCEEDED, 새검사원본0·부품추론0·통합최종0·PLC완료0. 취소사실의SQLite저장은정상이고 이전74완료는보존. 사용자는계속정지관측→실제STOP/LAN재연결→현재네부품정상모형확인. 모형이있는상태/STOP을유지하며서비스재시작·기준변경·추가START없음.
PLC접수후첫제품track확보22.605초. 요청저장236.238ms/error없음(실제admit commit포함6.659ms) 뒤 ADMISSION_WAIT_CURRENT_FRAME/NO_FOREGROUND, 원admission3초기한만료로촬영Worker dispatch전취소. 오류명STORAGE만보고SQLite실패로해석하지않음. 같은모형STOP후진단12서로다른새프레임 제품전체점수0.381–0.490<0.5,전부NO_FOREGROUND. 실제진단프리뷰에모형이보임; 현재위치/모형의제품인식약함은확인됐지만물리원인·과거전체요청프레임 점수는미확정. 실패원본은없고현재프리뷰를실패입력으로사용하지않음. request75전체프레임링은미회수(runtime/status는최근4개만포함);이한계를명시함.
이전attempt12 결품37(FAIL29/REVIEW8)과분리하며혼합30은미달성,오른쪽결품은아직미검사. 현운영555c3a43053ce4ce/같은boot/Main1161/Worker2741/NRestarts0. 새기준을임의적용하지않으며후속은제품전체검출의안정화범위결정. 증거 runs/mixed_stability_20261017/{right_FAILURE_AUDIT,right_FAULT,right_STOPPED_PRODUCT_SAMPLES,right_OBSERVATION_LIMIT,right_OPERATOR_AFTER}.json 및정지후진단프리뷰/사용자스크린샷. 원본/Journal/운영코드보존.

Previous checkpoint:
ATTEMPT12 HUMAN/RECORDS RECONCILED / ATTEMPT14 NORMAL–RIGHT-PIPE MIXED30 IN PROGRESS
2026-10-17 사용자 “순서를 지켰고, 추가 START 없이 계속 배출·재가동” 확인. attempt12 실제37건(첫30 FAIL24/REVIEW6,전체 FAIL29/REVIEW8)은 순서대로 배기구결품19건 전부FAIL·문양결품18건 FAIL10/REVIEW8. PASS0/ERROR0, 유효3장/저장/PLC완료37과 물리연속운전 관측을 대조했다. 문양결품의8REVIEW는 왼쪽파이프의 저점수/프레임불일치이며 확정FAIL 성공으로 세지 않는다. 상태확인은 사용자준비/순서 근거, 모델판정에서 역산하지 않음.
사용자가 다음 시험을 “정상→오른쪽 파이프 반복”으로 변경했다. 아직 START/새검사0건인 3상태 attempt13 GET-only기록기6574만 식별종료,파일보존. 실제운영서비스/카메라/PLC 변경없음. 사용자 정상·오른쪽파이프만미결합 준비확인 후 attempt14_normal_right 별도수집기6708/기준 request=result=done=completed=74/Worker2741 준비. 실제START(Mc_Runtrue/Requestfalse/IDLE/새요청0)→노트북LAN분리/SSH3초timeout 확인. 정상→오른쪽파이프결품 15쌍/30회 연속투입 안내; 실제결과는 대기이며 이전시험과 합산하지 않음.
운영555c3a43053ce4ce/bootc8d72e3f·모델·400ms·임계값·PLC·촬영조건 유지,추가재부팅없음. 노트북터널 복원HTTP200 확인 뒤 단독시험을 위해 다시LAN분리; 렌더링은미확인. 증거 runs/mixed_stability_20261017/{fail_OPERATOR_CONFIRMED,mixed_SUPERSEDED_BEFORE_START,right_OPERATOR,right_READY,right_PLAN,right_START,right_NOTEBOOK_DISCONNECTED}.json. 다음: 사용자완료/중단→STOP→LAN재연결→이번요청75이후 원장·원본·C거래 대조. 상태/판정은원기록을따르며 REVIEW를 FAIL로변경하지않는다.

Previous checkpoint:
ATTEMPT12 FAIL-ONLY TRANSPORT 37 COMPLETE / REVIEW8 / MIXED TEST PENDING
2026-10-17 운영555c3a43053ce4ce를 변경·재시작하지 않고 사용자 한START·노트북LAN분리 결품시험을 수행했다. 실제 새요청38–74 총37건: FAIL29/REVIEW8/PASS0/ERROR0, 유효3장37·SQLite저장37·같은token PLC거래37 완료. 첫30건은 FAIL24/REVIEW6, 새원본90PNG,543.651초. 전체37은111원본/148자산SHA·디코딩픽셀SHA·SQLite quick_check ok,672.751초. 같은bootc8d72e3f/Main1161/Worker2741/NRestarts0. 구간내 C 중단·재접속없음, 종료후 실제STOP만 기록. 회수시Mc_Runfalse/RequestLOW/출력0/유휴.
REVIEW8 원시이유:6건 PART_ASSIGNMENT_UNCERTAIN(왼쪽파이프 gray_pipe 점수0.323–0.494<0.5),2건 INCONSISTENT_THREE_FRAME_RESULT(왼쪽파이프 PRESENT/MISSING 혼재). 문양 슬롯은각3장MISSING이나 다른슬롯불확실을 우선하는 현행집계에 따라 REVIEW. 원본4회2장/30회3장을 열어보면 해당파이프는 보이며 점수불안정의 물리원인은 미확정. 오조립보조판정은 최종에 영향없음. 첫30 거래연속성 확인과30건결품확정FAIL은 구분(후자는미달). 배기구→문양 교대 및 실제무개입배출 관측은 사용자확인대기,모델결과로정답을역산하지않음.
증거 runs/mixed_stability_20261017/{fail_AUDIT,fail_NATIVE,fail_REVIEW_SUMMARY,fail_OPERATOR_AFTER}.json 및 fail_EVIDENCE.zip SHA27c8b6fa08f189ec2af9fc6aba00c847714e3ed04ad6a7c9d9ab75451dd9a67b. 원본보존/모델·임계값·PLC·400ms변경없음. 다음: 사용자투입순서/물리동작확인→정상·결품혼합30 별도준비. 이전준비key후속문제는 이번미재현이며 해결됐다고하지않는다.

Previous checkpoint:
ATTEMPT12 FAIL-ONLY FIELD TEST IN PROGRESS / CURRENT RUNTIME UNCHANGED
2026-10-17 사용자 후속: 정상30과 결품·혼합 연속운전을 별도로 검증. 준비신호 최소수정 제안에는 “현재 운영본으로 시험만 진행”, “시험 한번 해보고 수정하자”로 결정했으므로 운영 수정·재시작·재부팅 없이555c3a43053ce4ce 유지. 격리 재현은 저장준비 중 tracking session 항목만 바뀌어도 REQUEST_STORAGE_OWNER_CHANGED/Ready false가 됨을 확인했으며 실제38번째 검사 실패로 세지 않는다. 모델·400ms·PLC·판정/촬영 조건 변경 없음.
사용자 STOP·빈벨트 및 배기구만 빠진 모형·가운데 문양만 빠진 모형 준비 확인. A/B/C 지시는 이해하기 어렵다는 사용자 교정에 따라 실제 상태 이름으로만 안내한다. 동일 Worker2741/bootc8d72e3f, 새 읽기 전용 수집기5851, 기준 request/result/done/completed=37. 실제START→Mc_Run true·Request false·IDLE·새요청0 확인 후 노트북LAN 분리/SSH 3초timeout 확인. ‘배기구 빠진 모형→문양 빠진 모형’을 번갈아30회(15쌍), 앞 모형 완전배출 뒤 투입 안내. FAIL이면 정상배출시 계속, ERROR/재가동불가면 추가START 없이 알리도록 했다. 현재 정확한 결과는 미확정이며 정상30과 합산하지 않는다. 다음: 사용자 완료/중단→STOP→LAN재연결→원본/원장/C기록 감사. 이후 정상·두 결품 혼합30은 아직 준비/실행 전이다.
기록 runs/mixed_stability_20261017, Jetson acceptance/continuous30_20261017_attempt12_fail. 기존 collect_field100.py를 그대로 재사용하며 기대정답은 수집파일에만 넣음. 준비도구가 BASELINE JSON 저장 중간을 읽은 오류는 보존했고 같은 기록기 PID를 재검증해 READY만 완성했다(재실행/초기화없음). 이전30 결과 GitHub3f416063c2d086363483d06c8f42faf6a9145117 반영 확인. 이번 시험 결과 대기.

Previous checkpoint:
ATTEMPT11 ACTUAL STANDALONE 30 VERIFIED / POST-37 READINESS FOLLOW-UP OPEN
2026-10-17 운영555c3a43053ce4ce·bootc8d72e3f·Worker2741 유지, NRestarts0. 실제 한 START·노트북 LAN 분리 상태에서 첫30건: PASS30/유효3장30/PLC거래30, 새원본90PNG·120자산 검증, 545.150초(9분5초). 전체37건은 PASS36/FAIL1/ERROR0/REVIEW0, 모두 유효3장·같은ID Result→laterDone→RequestLOW→다음대기 확인. 111원본·148자산 파일/픽셀SHA·SQLite ok, 수집기407관측 무장애·30건 정상 종료. 요청→C완료 첫30 중앙10.676초/p95 14.219초/최대14.325초. HEALTH_UPDATE 저장최대248.376ms(400ms 미만; p95/p99 미측정). 정확한 정상/불량 전환 번호·결품 종류는 사용자 기억 불명; 37번 RIGHT_PIPE_MISSING은 모델 판정이며 정답 확정 아님.
37번 완료 뒤 8.89초에 REQUEST_STORAGE_OWNER_CHANGED/WAIT_REQUEST_STORAGE_CHECK로 Ready 해제·C DISARMED 기록. 0.33초 뒤 Ready는 회복했지만 약5.21초 뒤 실제STOP 기준으로 복귀; 38번째 수락/검사/취소 행은 없음. 마지막 사용자 '요청 후STOP인 것 같음'은 관측으로만 보존하며 오류를 STOP 탓으로 단정하지 않음. 첫30 통과와 별도 후속 문제, 장시간/불량혼합 안정성 완료 아님. 현재 실제 STOP/RequestLOW/출력0/저장유휴 확인. 재시작·추가START·판정/임계값 변경 없음.
증거 runs/capture_stability_20261017/{ATTEMPT11_AUDIT,FIELD30_NATIVE,FIELD30_CURRENT_STATUS,ATTEMPT11_TRANSFER}.json 및 ATTEMPT11_EVIDENCE.zip(19abbc51c88e7ee7cb2acf72e0a8322c2548ce7c8f527ea3815b33830815971b). 원기록/과거시도 보존. 배포소스 GitHub e5ea81f22789fab2ffffb5109c13c8edca39a6a6 반영 확인; 이번 결과 문서 반영 진행. 다음: 37완료 이후 준비저하 원인 확인 후 결품정답을 사전에 구분한 별도혼합시험. B04/E04·학습·모델변경 없음.

Previous checkpoint:
ATTEMPT11 PHYSICAL START VERIFIED / LAPTOP LAN DISCONNECTED / 30-CYCLE RESULT PENDING
2026-10-17 새 운영555c3a43053ce4ce·bootc8d72e3f의 실제START신호(Mc_Run/EStop_OK/Stop_PB=true,Request=false),IDLE/오류없음/카운터0/Worker2741/수집4393 확인. 사용자노트북LAN분리와SSH타임아웃확인; PLC–Jetson연결유지·노트북전원OFF미시험. 정상모형30회 한개씩투입 안내, 매회승인없음. 정확한 완료/유효3장/판정분포는 재연결후Journal/C기록대조까지미확정. START확인스크립트최초Stop_PB=false 가정은기존계약true와불일치해거부됐으며도구만수정; PLC극성/운영코드변경없음. 증거 runs/capture_stability_20261017/FIELD30_START_CONFIRMED.json, FIELD30_NOTEBOOK_DISCONNECTED.json. 기존247검사보존·실제재부팅/수집preflight검증완료. GitHub현재변경반영중. 다음: 사용자30회완료/멈춤→필요시실제STOP→LAN재연결→원기록집계. 실패를성공으로합산하지않음.

Previous checkpoint:
TARGET STABILITY DEPLOYED / REBOOT AUTOSTART VERIFIED / ATTEMPT11 START PENDING
2026-10-17 현재 운영 engine-integrated-555c3a43053ce4ce, 새 boot c8d72e3f-d5cf-423a-b832-774394ba8243. 변경3파일·189파일SHA, systemd enabled/active, 단일 카메라Worker2741·모델/PLC 준비·WAIT_START 확인. 추가30.685초7개새프레임/동일Worker. 백업56d370b47fa7fd52f84a3ee4d9473dedd306e9f2d79c22db6ec8d483687e57f1/174파일SHA·SQLite·기존247검사 보존 검증. 모델/부품/PLC/임계값/촬영3초·연속3장·0.6초·15초 유지. Windows/Jetson 최종44각PASS·관련기존119재사용·C2·UI2PASS. 공개소스만 별도44회귀+UI2PASS(첫 내보내기 dependency누락 보존 후16개재검증). Jetson 수집기 실제기존PASS 결과·원본 읽기/저장preflight완료, PID4393/attempt11 준비·새검사0. 사용자STOP·빈벨트확인 및 공식유지보수종료 완료. 현재 실제START한번 질문대기; 이후신호확인→노트북LAN분리→정상30한번에안내. 새실물30 미실행, 안정성달성미주장. 보고 docs/CONTINUOUS_RUNTIME_AUDIT.md, 증거 runs/capture_stability_20261017. GitHub 반영준비.

Previous checkpoint:
TARGET STABILITY VERIFIED / STOPPED APPLY PREPARATION / EMPTY-BELT CONFIRMATION PENDING
2026-10-17 최근4ERROR 각각 DEADLINE_EXCEEDED·안정연속3장부족 확인. 최종 후보555c3a43053ce4ce: 같은 카메라좌표의 envelope합집합 마스크, 기존57600분모/461픽셀거부 유지(작은영역분모 중간후보는 폐기·증거보존), source시간0.6초·요청별초기화·상세원시오류. Windows44/ARM6444 최종PASS+영향없는119회귀재사용,CIPC2·UI2PASS. 실제24원본 마지막쌍 대조·기존4결품 마스크/판정회귀 확인. 전체3초원본없음; POST진단수집 정책차단,우회없음. 운영a8afabe667e881ed/boot081d4e63 유지,Main1079/Worker2725/13거래/STOP. 후보3파일·백업/적용스크립트 준비,운영미적용·재부팅/새30미실행. 사용자START→STOP위치조정 보고,카운터변화없음. 현재모형제거/빈벨트질문대기. 다음: 확인→기존유지보수종료→sudo전환·백업검증·적용/재부팅→실제결과읽고저장 수집preflight→단독30. 증거 runs/capture_stability_20261017, 단일보고 docs/CONTINUOUS_RUNTIME_AUDIT.md. GitHub반영대기;관련없는변경보존.

Previous checkpoint:
CAPTURE STABILITY TASK AUTHORIZED / FOUR RAW ERRORS CONFIRMED / CANDIDATE NOT DEPLOYED
2026-10-17 최신 첨부 TASK가 대상 중심 촬영 안정 판정·최소 상세 표시·검증·정지 적용·재부팅·단독30회를 명시 승인했다. 아래 설명 대기는 과거 기록이다. 운영 a8afabe667e881ed/boot081d4e63/Main1079/Worker2725/재시작0을 GET·읽기 전용 증거로 확인, STOP/RequestLOW, 13요청·13완료. 대상1feea8a2/680c0018/45062997/7e21efd2 모두 raw DEADLINE_EXCEEDED·후보11, 거부9/11/11/10. 직전38731852와 직후e93bce8b/e0fa1b2f, 이전e14586d0 포함8건32자산SHA·24원본 보존. 마지막3장만으로 전체3초를 재현하지 않는다.
후보 engine_inspector.py·inspection_worker.py 및 test_engine_motion.py/test_stationary_inspection_capture.py. 고정 카메라 좌표의 이전/현재 영역 union, 제품bbox와 기존slot영역, source시각, 요청별reset. 수치25/0.008/0.6s·촬영3s/연속3장/처리15s·모델/PLC 유지. RED2 보존 후 motion10PASS. Worker 포함23건은22PASS/품질불량 REVIEW 대 ERROR 기대1건 불일치로 확인 중. 저장pair에는 작은영역0.008 초과 사례가 남아 전부 해결로 판단하지 않음. 운영 적용·재부팅·새실물시험 미실행.
Evidence runs/capture_stability_20261017/{INITIAL_RUNTIME,RAW_SUMMARY,NATIVE_EVIDENCE,SAVED_PAIRS_WINDOWS}.json, RAW_ORIGINALS.zip, MOTION_RED/GREEN.log. 다음: Worker 품질불량 기대를 계약과 대조, ID별 C시계열/원인표, 같은 원본의 native후보 비교·결품회귀·UI최소표시·관련통합시험. GitHub17b9379c 일치, 이번후보 미push. 원기록·무관한변경 보존.

Previous checkpoint:
DESIGN EXPLANATION REQUESTED / NO STABILITY-GATE CHANGE AUTHORIZED YET
2026-10-17 사용자: 오류 검사 중 엔진은 멈춰 있었다고 확인. 관측 진술이며 영상만으로 물리 원인을 확정하지 않음. 제품 영역 중심 안정 판정 수정안에 대해 '변경 전 설명 더 듣기' 선택. 운영 a8afabe667e881ed 그대로; 새 구현·적용·재부팅·시험 시작 없음. STOP·모형 그대로, 5거래/4PASS/촬영ERROR1 보존. GitHub master 17b9379c97a61ff6a9a0f436cc7f055a97920aa7와 로컬HEAD 일치 확인(실제배포소스+2테스트+3보고서,6파일). 다음: 비교 영역 변경의 이유·위험·검증 계획을 설명하고 사용자의 결정을 기다림.

Previous checkpoint:
STANDALONE30 ATTEMPT10 AUDITED / CAPTURE STABILITY ERROR / 30 NOT MET
2026-10-17 a8afabe667e881ed 실제 재부팅 후 한 START·노트북 LAN 분리로 5요청/5PLC거래 완료. 순서 PASS→PASS→ERROR→PASS→PASS, 최대연속유효PASS2. 사용자의 오류 후 추가검사 관측과 일치하며 실제로는 오류 뒤 새요청2건이 있었다. 3번째 e14586d0…는 촬영3초 내 안정연속3장 부족(DEADLINE_EXCEEDED), 후보11/거부10/안정1장폐기. 진단3장의 각 부품검사는PASS지만 유효촬영 성공으로 세지 않는다. 20자산SHA·SQLite·같은ID Result→laterDone→LOW→다음대기 검증. 요청→C완료 9.498–13.345초(중앙10.795), 첫요청→5완료84.194초. 동일boot/Main1079/Worker2725, 서비스재시작0. 요청수락·Ready/통신 중단 없음.
사용자 STOP·LAN재연결 완료, 모형은 그대로 유지 요청. 실제Mc_Runfalse/RequestLOW/출력0·유휴 확인. 별도GET-only수집기는 첫결과의 지연import 누락(replay_basic_part_presence)으로중단; 운영원장·20원본은보존되고 직접회수했다. 준비완료 검증이 부족했던 수집기 오류를 숨기지 않는다. 해당의존성전송과 다음준비시사전import검사를보완하며 새수집기/검사재실행없음.
오류원본3장을실제확인하고 Jetson OpenCV5에서 마지막두변화량1.533%/1.977%를원기록과정확재현(기준0.8%). 변한픽셀의91.5%/83.4%가검출제품bbox밖. 전체영상 움직임검사의주변민감성증거이며 실제진동/조명/엔진정지여부는미확정. 사용자에게오류검사당시정지/움직임관측만질문중. 모델·임계값·촬영기한·운영코드추가변경없음. runs/admission_frame_wait_20261017/ATTEMPT10_AUDIT.json 및 SAVED_MOTION_ANALYSIS.json, docs/CONTINUOUS_RUNTIME_AUDIT.md. 다음: 실제정지관측과기존안정판정의적용범위를대조. 30성공/장시간안정성미달성.

Previous checkpoint:
ADMISSION WAIT DEPLOYED / ACTUAL REBOOT VERIFIED / STANDALONE30 ATTEMPT10 IN PROGRESS
2026-10-17 사용자 STOP·빈 벨트·sudo 실행 후 174파일/SQLite 백업 f54556de… 노트북 검증, a8afabe667e881ed의 요청 수락 대기 1파일 적용 및 189운영해시 확인. 이전17요청·사진·판정 보존, 미전송17번은 append-only 취소 정리만 수행(새결과/전송0). 실제 재부팅 boot081d4e63…, enabled/active Main1079 NRestarts0, 단일 cameraWorker2725, 모델·PLC·health ready/WAIT_START. 추가31.054초 새프레임7개 확인. 재부팅 후 Jetson 수동 재시작/전원·USB 조작 없음. 노트북 터널만 재연결; 브라우저 도구 정책으로 실제 화면 렌더링은 미확인, 서버 상태는 확인.
새 attempt10 Jetson GET-only 기록기4696 준비. 사용자 실제 START 후 Mc_Run=true/RequestLOW/IDLE/카운터0/카메라준비 확인(05:08:29 UTC). 사용자 노트북 LAN 분리 및 SSH timeout 관측(05:09:27 UTC) 후 정상 모형30회 연속 투입 안내. 현재 실제 횟수·결과는 재연결 후 원장/C trace 대조 대기. 이전14PASS/16거래를 합산하지 않는다. 검증 PC73/ARM6473/native격리8과 실물30을 구분하며 기존 촬영ERROR 원인은 미해결 상태로 유지한다. 증거 runs/admission_frame_wait_20261017/DEPLOYMENT.json, AFTER_REBOOT_PROOF.json, FIELD30_START_CONFIRMED.json, FIELD30_NOTEBOOK_DISCONNECTED.json. GitHub 갱신 준비 중.

Previous checkpoint:
ATTEMPT09 AUDITED / ONE-FILE ADMISSION WAIT VERIFIED / SUDO TRANSITION PENDING
2026-10-17 노트북 LAN 재연결 후 실제 요청17/PLC완료16 확인: PASS14, 촬영ERROR2(1·15회), 촬영전취소ERROR1(17회). 최대연속유효PASS13,30미달성. 16건 Result→later Done→LOW→다음대기/64자산SHA/SQLite 검증. 17회는 수락SQL253.908ms 정상 뒤 영상eligible해제; 같은owner/track이나 정확한실패provider는미보존. 기존촬영3초 부족 두건과분리. 운영f03d3f570a172c5f/bootc050e0e3 유지.
동일수락의 순간영상부적격을 원기한내대기로 처리하는 request_start.py 1파일 후보a8afabe667e881ed 검증: PC73/ARM6473PASS,C격리8개검증(최초시험초기화실패보존,수정후5재실행PASS). 요청변경/STOP/실장애/기한/400ms/모델·임계값유지. 사용자가현재STOP·빈벨트확인.17기록보존·취소원장읽기전용preflight통과. 임시배치만완료,백업/적용/재부팅/새실물30미실행. sudo시작명령 질문,백업감시기실행. docs/CONTINUOUS_RUNTIME_AUDIT.md, runs/runtime_audit_20261017/ATTEMPT09_AUDIT.json, runs/admission_frame_wait_20261017/FINAL_CANDIDATE.json. GitHub01cf5ff까지push확인;현재후보미push. 다음: 사용자sudo→백업검증→1파일적용→정지상태취소정리→재부팅자동기동→별도실물30.

Previous checkpoint:
STANDALONE30 ATTEMPT09 STOPPED / RECONNECT AND FIRST-FAULT AUDIT PENDING
2026-10-17 실제 START/IDLE/오류없음/카운터0을 확인한 뒤 사용자 노트북 LAN 분리와 SSH 단절을 관측했다. 정상 모형 연속 투입 중 사용자가 횟수는 불확실하나 약14회이며 검사 후 멈췄다고 확인했다. 실제 STOP 버튼도 눌렀다고 확인했다. 정확한 완료 수·최초 오류는 미확인이고 30회 완료로 집계하지 않는다. 모형은 그대로 유지하며 노트북 LAN 재연결 질문 대기. 재시작·복구·새 START·임계값 변경 없음. GitHub master에 검증된 관련56파일 커밋01cf5ffc3217fc13b1dba4bfbad6f85226429967 push 및 원격SHA 일치 확인. 원본·DB·모델 업로드 없음; 무관한 사용자 변경 보존.

Previous checkpoint:
RUNTIME AUDIT FIX DEPLOYED / ACTUAL REBOOT AUTOSTART VERIFIED / STANDALONE30 PREPARING
2026-10-17 사용자sudo 실행 후174파일/SQLite 백업590779f37fa69ad8d98a6b60d2be23bf0669c68254e138bae35313722df7e48d 노트북검증. 후보 f03d3f570a172c5f 적용·189운영해시확인. c7f…미전송rawPASS는기존검증된append-only ABORTED만기록,870c…완료제품유지보수종료;원본8자산/두검사행/이전final 보존,새grant·재전송0. 실제재부팅 boot c050e0e3-9cd9-4b69-80de-76932fd6616d, enabled/active Main1078 NRestarts0,단일cameraWorker2758,모델·PLC·health ready·WAIT_START. 재부팅후수동복구없음. 추가31.36초7개새프레임/같은Worker/STOP대기확인.
정상모형준비 사용자확인 후기존GET-only 수집기를Jetson내부 PID4503으로실행, data/engine_dynamic_pose_002/acceptance/continuous30_20261017_attempt09. 노트북과분리해도서비스·필수Journal은Jetson소유. 실제START 후Mc_Run=true/RequestLOW/IDLE/오류없음/카운터0 확인. 사용자노트북LAN분리확인·SSH접속단절 관측 후정상모형30회연속투입안내. 단독운전결과는재연결후검증대기. GitHub코드반영준비중(아직push안함). 상세 docs/CONTINUOUS_RUNTIME_AUDIT.md; AFTER_REBOOT_PROOF.json/POSTBOOT_SUMMARY.json/FIELD30_READY.json.

Previous checkpoint:
RUNTIME GUARD AUDIT / VERIFIED 8-FILE CANDIDATE STAGED / SUDO START PENDING
2026-10-17 최신: 사용자STOP·모형전부제거 확인(ㅇㅇ), 실제PLC STOP/RequestLOW/출력0 재확인. 후보 engine-integrated-f03d3f570a172c5f는 촬영/처리저장기한6파일+기동잔여IPC2파일이며 운영 a807… 그대로. PC/ARM64338회 및 nativeIPC7, startupARM64 39PASS에 추가queued-result5PASS. 관련해시동결·기존배포도구재사용·c7f…미전송rawPASS의읽기전용복구검증 완료. 이전원본/판정/PLC카운터불변. 배포백업/실제적용/재부팅/새단독30회 아직미실행. 원격sudo 인증없음 확인. 다음: runtime_audit_20261017/device_transition.py transition 사용자터미널실행→노트북백업검증→8파일적용→append-only중단/이전제품정리→실제재부팅확인. 상세 docs/CONTINUOUS_RUNTIME_AUDIT.md, runs/runtime_audit_20261017/FINAL_CANDIDATE.json. GitHub동기화 아직대기.

Previous checkpoint:
RUNTIME GUARD AUDIT / CAPTURE-STORAGE CANDIDATE VERIFIED / NOT DEPLOYED
2026-10-17 최신 TASK가 운영본 감사·촬영/처리 기한 분리·최소수정·정지배포·재부팅·GitHub·PLC/Jetson 단독30회를 승인했다. 이전 설계승인 대기보다 우선한다. 모델/임계값/PLC wire 변경 없음. 운영 a807de46a264aa3e/Main5395/bootd1c9285e 유지, 새STOP/RequestLOW 관측. GitHub/localHEAD5fe3669, working tree는 더 진행됨. 운영/로컬131파일 중127 byte동일; SQLite 차이는 줄바꿈뿐, supervised UI/release 차이는 보존. 통합 보고서 docs/CONTINUOUS_RUNTIME_AUDIT.md, 원증거 runs/runtime_audit_20261017.
후보: 원 trigger+15초 총기한과3초 촬영 분리; Worker 추론/인코딩이 촬영창을 넘어도 이미 선택한 사진만 처리, Service에서 선택시각 재검증. Writer 완료시각으로 deadline/완료알림 경합 해소, 늦은 저장 정상화 금지. 수정전 실패 재현. Windows/ARM64 각338실행(337PASS+1기존자료skip), C/Python격리7PASS(한START12회, 요청/원본/최종저장 각350/450/600/1000ms). 운영카메라/PLC카운터 불변. PC 보고서 metadata CANDIDATE 누락 오류는 시험완료 뒤 발생; 원로그/입력SHA로 복구하고 실패로그 보존.
기동 잔여IPC 소켓 별도 최소후보: 기존배타lock/사유디렉터리/동일소유socket/OpENer부재/ECONNREFUSED 모두 확인할 때만 보존이동. Journal/요청 리셋없음. 집중Windows39(35PASS+Linux4skip),ARM64 39PASS. 아직배포/재부팅미실행. 추가소스 standalone_service.py/opener_process.py. STOP·빈벨트 물리확인 질문 대기. 다음: STARTUP_ARM64.json회수, 남은IPC미송신/수집기감사·최종source/backup gate 준비, 물리확인 후한번의유지보수명령. 이전 c7f… rawPASS/미전송은 기존append-only abort절차로보존정리; 가짜완료/재전송금지. 단독실물30 미시작.

Previous checkpoint:
WEB/CAMERA MANUALLY RESTORED / AUTOSTART FAILURE AND PRIOR INSPECTION BLOCK REMAIN
2026-10-17 사용자 재부팅 후 SSH는 가능했으나 engine-inspector.service가 잔여IPC소켓으로5회 실패·웹미기동. 사용자STOP 및 종료/무소유/lock/ECONNREFUSED/포트비점유 확인 후 소켓만 ipc.stale-20261017T033349Z로 보존 이동. 사용자가 reset-failed && start 실행. 기존a807de46a264aa3e 그대로, Main5395 active/running·Worker5447 새프레임968→1004·웹HTTP200 및 실제 브라우저 영상갱신/PLC연결 표시 확인. STOP/RequestLOW/출력0. 모델/코드/DB/PLC설정 변경 없음, 기존터널 재사용.
이전 c7f… 실패는 rawPASS/통합INCOMPLETE/PLC차단으로 보존. 검사재개/30연속/재부팅자동복귀 PASS 아님. 촬영3초·총처리15초 분리는 설명 요청 단계, 미승인·미구현. 수동방법 docs/PROGRAM_START_STOP_KO.md, 근거 runs/startup_recovery_20261017/REPORT.md.

이전 체크포인트:
ATTEMPT08 STOPPED / CAPTURE-STORAGE DEADLINE COUPLING REPRODUCED / 30 NOT ACHIEVED
2026-10-16 engine-integrated-a807de46a264aa3e에서 실제2요청/부품PASS2/통합final·PLC완료1. 두번째 c7f15ae32e61473db2f607efc11f5ff3는 유효3장·원판정COMPLETE/PASS·4자산 저장됐지만, 촬영3초를 저장기한으로도 사용하는 STATIONARY 경계에서 STORAGE_DEADLINE_EXCEEDED→PYTHON_NOT_READY로 취소. 통합final/PLC전송 없음. 이번 health최대192.385ms<400ms, 이전418ms 갱신지연과 구분. native SQLite/event8자산SHA·6원본픽셀 검증, 실제 운영SHA동일 Service의 fake clock으로 해당 기한 결합 재현.
사용자 STOP 및 실제 PLC STOP/RequestLOW/출력0/Worker·저장유휴 확인. 운영 수정/복구/재전송/새검사 없음. 촬영3초 유지+기존15초 총처리기한 분리 제안은 현재 STATIONARY 취소 동작 변경이므로 미구현·설계승인 대기. warm reboot 자동복귀 미확인/수동power cycle autostart 확인 구분 유지. 상세 runs/continuous_30_20261016/attempt08/ANALYSIS.md. FIELD100 기존수량·보정/검증분할 변경없음.

이전 체크포인트:
REQUEST START STORAGE / APPLIED / WARM REBOOT UNVERIFIED / POWER CYCLE AUTOSTART VERIFIED
2026-10-16 engine-integrated-a807de46a264aa3e 적용,189파일 해시 확인,174파일/SQLite 백업 SHA 137178e64f816e703d1c7a239c0c82bb20543ffdda7ede95c48dec83b476bbcd 검증. 취소7264…는 최신 STOP/유휴 증거의 append-only 복구만 기록; 원 CANCELLED/ERROR·사진0·통합final없음 및 이전완료05f20…/4자산 보존. 결과재전송0/새grant0/가공검사0. 이전 제품 유지보수 종료도 같은 제한으로 기록.
자동 감시기의 기동 직후 PLC snapshot=None 실패는 원인/오류 파일 보존; 실제 카메라·모델·PLC 준비 후 이어서 복구 성공. 재부팅 직전 WAIT_START/STOP/빈 벨트/health ready 확인. 실제 systemctl reboot 뒤360초 동안 SSH 복귀 미관측, 새 boot ID/자동기동 미확인. 사용자 전원LED켜짐→전원 분리/재연결 확인. 수동 전원 재연결은 정상 warm reboot 성공으로 세지 않는다.
전원 재연결 후 boot f1d0555e-2410-4e66-b4ba-287891ea9908, 서비스 enabled/active·189해시·단일 카메라·모델·PLC준비·WAIT_START 확인. 실물 START 및 30연속은 아직 미실행.
검증: Windows/ARM64 각318회 실행(고유291:290PASS+1기존skip), 합성 IPC6PASS. 550ms 인위 저장 지연 중 준비 갱신최대110.766ms,400ms유지. 실물 성능/장시간 안정성으로 해석하지 않는다. 기존 UI2미검증/전체패키징2기존차단 유지. 모델·임계값·PLCwire 유지. FIELD100 기존13요청/11사진검사/10PLC완료 보존; 새연속30 별도계획, 보정/검증 분할 변경 없음.

이전 체크포인트:
REQUEST START STORAGE / DEPLOYED; MAINTENANCE REFRESH FIX VERIFIED / SUDO PENDING
2026-10-16 요청 시작 저장 분리 9698c9e0850386dd 적용·189파일 검증 완료. 백업171파일/SQLite 보존. 취소7264… 복구의 유휴 소유자/200ms PLC 증거 검증에서 재부팅 전 차단; 새 실물 검사는 시작하지 않음. 기존 원본 취소·완료 행 변경 없음. 원래 감시기 오류와 실패 근거 보존.
읽기 전용 계측에서 snapshot52–64ms, quick_check40–53ms, 이력검증88–91ms로 이전 PLC 확인값이 낡는 것을 확인. 단일 복구 함수가 BEGIN IMMEDIATE 안에서 이력을 먼저 검증한 뒤 동일 요청·STOP·유휴 소유자의 최신 증거를 검증/기록하도록 수정. 기준 완화/결과 재작성/PLC 출력 없음. 기존 동결 proof 경로의 오래된 상태 거부도 유지.
후보 engine-integrated-a807de46a264aa3e: Windows/ARM64 각각318회(고유291개:290PASS+1기존자료skip), 합성 C/Python IPC6PASS, 보조 상태대기3PASS. 실제 장치 적용·재부팅·30연속은 아직 미확인. 기존 UI2미검증/전체패키징2기존차단 유지. 새 sudo 명령 대기. runs/request_start_recovery_20261016/FINAL_CANDIDATE.json 참조.
연속30은 새 검사만 별도 집계; 기존 FIELD100 보정/검증 계획과 이전 실패/성공 수량은 변경하지 않는다.

이전 체크포인트:
REQUEST START STORAGE / VERIFIED CANDIDATE / OPERATOR SUDO START PENDING
2026-10-16 후보 engine-integrated-9698c9e0850386dd: 요청 시작·취소·늦은 결과 감사 저장을 기존 Worker로 분리하고 durable admission 이후 새 프레임만 허용. 미해결 취소 건 준비 신호 차단 및 실제 STOP/미전송 증거 기반 append-only 복구 포함. 원본 취소7264…와 이전완료05f20… 보존, 모델·임계값·400ms·PLC wire 변경 없음.
Windows/ARM64 각각316회 실행(고유289개:288PASS+1기존 자료부족skip), AF_UNIX C/Python6PASS. 550ms 저장 지연/단일START3회에서 갱신최대110.601ms,p95=45.294ms,p99=101.972ms. 합성입력 시험이며 실물30회가 아님. 기존 UI2미검증/전체패키징2기존자산차단 별도 유지.
운영0e8441729f6b85d9 그대로, 실제 STOP/RequestLOW/완료6·Worker2740 확인. 후보/백업검증/재부팅 도구만 staging 완료, sudo 인증 대기(감시기 실행 중). 실제 적용/재부팅/새 실물 검사 미실행. FIELD100 누적13요청/11사진검사/10PLC완료 및 기존 실패 보존. 상세 runs/request_start_storage_20261016/FINAL_CANDIDATE.json.

이전 체크포인트:
REQUEST START STORAGE / IMPLEMENTING AUTHORIZED CHANGE
2026-10-16 사용자 «그럼 진행해보자»: 요청 시작 저장 소유권 분리·계측·회귀 검증·정지 적용·실제 재부팅 확인 후 연속 검증 재개 승인. 400ms·모델·임계값·PLC wire 유지. 현장 안정성 미달성.
Windows 격리 구현·시험 중, Jetson 운영 적용 전. 현장 누적13요청/11사진검사/10PLC완료 보존.

이전 체크포인트:
Current 2026-10-16 FIELD100 SESSION04 STOPPED / SIX PASS THEN REQUEST HEALTH EXPIRY:
Latest: user confirmed STOP and removed engine; fresh native PLC STOP/Request LOW with completed6 verified in STOP_EMPTY_CONFIRMED.json. No recovery/restart/new production edits. Concrete request-start persistence ownership proposal saved as calibration_normal_session04/REQUEST_START_DESIGN.md; design authorization pending because adding pending admission/durable-before-start scheduling exceeds prior completed-result/preview separation. Existing Worker reuse;400ms/model/PLC protections unchanged. Do not apply another isolated event patch without this boundary review.

After verified reboot0e8441729f6b85d9, six actual PASS+PLC completions and24PC/native assets verified. Seventh request7264d428aaf440679dccbf90abcd8933 was accepted then cancelled before images, no final/publication. Health renewal418.234ms exceeded unchanged400ms; overlapping Service-lock wait326.951ms in request-start window. Synthetic request-audit synchronous commit delay reproduces health starvation; exact field syscall remains unproven. Previous final-preview guard not observed in these six completions. User STOP/native STOP confirmed; no latest removal confirmation or recovery/restart. Gold crank bent/straight appearance both present among six PASS originals; seventh no image, no causal direction conclusion. Total13new Crequests/11image inspections/10PLC completions;100 and continuous30 incomplete. See calibration_normal_session04/ANALYSIS.md under runs/envelope_calibration_100_20261016. No further runtime/model/threshold changes.

Previous checkpoint:
Current 2026-10-16 COMPLETED PUBLICATION APPLIED / ACTUAL REBOOT AUTOSTART VERIFIED:
Applied engine-integrated-0e8441729f6b85d9 after notebook170file SHA/SQLite backup verification (a24fce262eaa1a2162ebce4e28364698ac5a9436be3af5376cb6e036077f9246). New boot546d24ac-9edb-4c2f-9c3f-6b339a2acfb2,186file hashes match, enabled/active Main1171,NRestarts0,singlecameraWorker2740,model/health/PLC ready and WAIT_START without product/request recovery block. Additional30.77s/7distinct frames stable. Failed83ad… remains untransmitted; authenticated preboot maintenance closure grant0/no replay. No model/threshold/PLC/400ms change. Physical acceptance and browser visual check remain separate/unverified. Field100 total6requests/5image inspections/4PLC completions; session04 ordinal7 preparing. See runs/completed_publication_20261016/CHECKPOINT.md.

Previous checkpoint:
Current 2026-10-16 COMPLETED PUBLICATION CANDIDATE VERIFIED / APPLY AND REBOOT PENDING:
User approved separating durable request-bound originals from post-inspection preview diagnostics; STOP and empty belt confirmed. Candidate engine-integrated-0e8441729f6b85d9: Windows/ARM64 each219 executed PASS+1existing skip; native synthetic C/Python IPC3PASS. Existing UI2unverified and full packaging2blocked by preexisting local reference asset issue remain explicit, not PASS. Current runtime ff5ebb2792622780 preserved; staged manifest delta only, sudo terminal authentication pending. No model/threshold/PLC/400ms changes. Actual deployment/reboot/field acceptance not yet verified. Failed83adcbf0901c46a08f55bdb2abcbc379 remains stored PASS/untransmitted; totals6requests/5image inspections/4PLC completions. See runs/completed_publication_20261016/CHECKPOINT.md.

Previous checkpoint:
Current 2026-10-16 FIELD100 SESSION03 STOPPED / FINAL PREVIEW GATE:
Reboot/autostart verified ff5ebb2792622780 then actual START and3normal-prepared inspections. REVIEW1/PASS2 durable; first2PLC completed, thirdPASS blocked after final storage by CYCLIC_FINAL_TRACK_EVIDENCE_INVALID. Native SQLite/12asset hashes verified. Last processed track retained ID/cycle and INSPECTED but provider NO_FOREGROUND; current predicate reproduces fault with that provider state. Actual final-preview raw/confidence unavailable, no full-image replay claim. User STOP and native stopped state verified. Proposed separating completed request-bound raw evidence from latest-preview redetection for publication; not applied. All STOP/cancel/session/storage/camera/duplicate protections must remain. Total6new C requests/5image inspections/4PLC completions;100 and30uninterrupted incomplete. See runs/envelope_calibration_100_20261016/calibration_normal_session03/FINAL_GATE_ANALYSIS.md.

Previous checkpoint:
Current 2026-10-16 COMPLETION AUDIT APPLIED / ACTUAL REBOOT AUTOSTART VERIFIED:
Applied engine-integrated-ff5ebb2792622780 after notebook verification of backup531f662096dd77479185c0aed3c0fd45e2c0411035f055eba0f57b39830741b9 (170files/SQLite ok). Actual boot changed to e7e704ef-32c1-40d7-8378-bf3de7b9b43c, systemd enabled/active,185hashes match, single camera Worker2673, model/health/PLC ready, STOP/Request LOW, no product/request recovery block. Further7readiness observations over30.75s with7distinct frames passed; no postboot manual recovery. Browser visual acceptance and physical continuous operation remain unverified. Model/threshold/PLC/400ms unchanged. Notebook collection latency field corrected to actual final inspection_elapsed_ms;11focused tests PASS, old evidence unchanged. Field100 still3new C requests/2actual image inspections; preparing normal calibration session03 from ordinal4. See runs/completion_audit_20261016/AFTER_REBOOT_PROOF.json, POSTBOOT_STABILITY.jsonl and CHECKPOINT.md.

Previous checkpoint:
Current 2026-10-16 COMPLETION AUDIT CANDIDATE VERIFIED / SUDO TRANSITION WAITING:
User authorized minimal storage-owner fix then resume100. Two-file candidate engine-integrated-ff5ebb2792622780 preserves models/thresholds/PLC/400ms lease. Windows and ARM64 each213 executed PASS+1 existing private fixture skip;2 unchanged UI checks remain unverified, not counted PASS. Native C/Python AF_UNIX synthetic tests2PASS including550ms completion-audit stalls through four verdicts. Actual STOP/empty confirmed and existing maintenance closure preserved last inspection/counters with grants0. Operating d9b96517ee8cc330 unchanged; user terminal sudo start pending, notebook backup-verification watcher ready. Actual application/reboot/field acceptance NOT_YET_VERIFIED. See runs/completion_audit_20261016/CHECKPOINT.md. Field100 remains3new C requests/2actual image inspections, incomplete.

Previous checkpoint:
Current 2026-10-16 FIELD100 COLLECTION STOPPED / POST-PUBLICATION HEALTH STALL:
Operating engine-integrated-d9b96517ee8cc330 unchanged. Three new C requests: request7 not executed (sequence gap), request8 REVIEW and request9 PASS. Two actual inspections verified against native SQLite, six original PNG/eight total asset hashes and ordered durable-final/publication/PLC-completion events. No new token for subsequent unaccepted Request HIGH. Operator STOP and model removal confirmed. Health renewal gap435.318ms exceeded unchanged400ms lease after request9 result/Done; service lock wait328.696ms overlaps completion audit. Actual synchronous completion-event path reproduces expiry with synthetic550ms commit stall; exact field blocking syscall unproven. Minimal storage ownership separation proposed, NOT IMPLEMENTED/DEPLOYED. No model/threshold/PLC changes. 100 collection and uninterrupted30 incomplete; actual A/B/C order and LED observations unreconciled. See tasks/ENGINE-ENVELOPE-CALIBRATION-100.md and runs/envelope_calibration_100_20261016/calibration_normal_session02/HEALTH_STALL_ANALYSIS.md.

Previous checkpoint:
Current 2026-10-16 ENVELOPE CALIBRATION100 / PRELIMINARY REPLAY COMPLETE / PHYSICAL COLLECTION PREPARING:
No runtime/model change: engine-integrated-d9b96517ee8cc330, same boot/Main1080/Worker2522, STOP confirmed from PLC. Historical9 inspections/27 original PNG replay: normal8 PASS counts .50=5, .40/.45=6, .30/.35=7; one true exhaust-missing FAIL at every threshold. Guide-associated part REVIEW unchanged. ROI diagnostic not adopted (4normalPASS/3REVIEW/1crop-boundary rejection). Wrong-object and other missing raw evidence insufficient; operating .50 retained. New read-only collector9 focused tests pass, including synthetic REVIEW followed by PASS. Field100 plan70calibration/30validation frozen before collection, no historical samples counted. Operator3models/all4parts removable, now all3 normal prepared. Initial normal30 collection preparing; actual100 and new continuous30 still0. See tasks/ENGINE-ENVELOPE-CALIBRATION-100.md and runs/envelope_calibration_100_20261016/PRELIMINARY_REPORT.md.

Previous checkpoint:
Current 2026-10-16 SAVED-IMAGE DETECTION INVESTIGATION COMPLETE / MODEL DECISION PENDING / 30 NOT ACHIEVED:
Jetson9 saved originals reproduced exact scores (6PASS/3REVIEW). Same-input PT/TRT21 comparisons have identical threshold selections; max confidence delta0.007033, but min box IoU0.919173 fails declared0.98, so no full parity PASS. Synthetic -4px shift changes a success score TRT0.688→0.458 and PT0.690→0.460; spatial sensitivity observed, physical cause not uniquely isolated. Brightness alone contradicted by same-boot bright PASS. User-authorized analysis only; operating model/threshold/preprocessing unchanged. Manual restarted3records separately audited, not continuous30. See runs/continuous_30_20261016/attempt07/PRODUCT_DETECTION_INVESTIGATION.md.

Previous checkpoint:
Current 2026-10-16 CYCLE-SCOPED TRACKING REBOOT VERIFIED / ATTEMPT07 STOPPED 0/30:
First actual cycle 4c2a3c2053bc4f3c8725427c40dd9d90 REVIEW: product scores0.377080/0.406378/0.361925 below unchanged0.5; parts NOT_EVALUATED. Three new originals,4assetSHA,SQLite COMPLETE and PLC completion verified; original images inspected. Not prior-cycle tracking block. Physical STOP confirmed. No threshold/model changes or unchanged repeat. Next-cycle field acceptance and30success remain unverified. See runs/continuous_30_20261016/attempt07/REPORT.md.

Previous checkpoint:
Current 2026-10-16 CYCLE-SCOPED TRACKING / ACTUAL REBOOT READY / ATTEMPT07 IN PROGRESS:
{"release": "engine-integrated-d9b96517ee8cc330", "boot_id": "2ad712f0-f04d-44c8-9bd7-3a054a44ef18", "files_verified": 185, "previous_result_preserved": true, "observed_disconnect_to_ready_s": 97.41, "ready_observation_span_s": 90.64, "postboot_manual_recovery": false, "windows_executed_pass": 201, "arm64_executed_pass": 201, "skipped_per_platform": 1, "native_synthetic_ipc_pass": 1, "unchanged_ui_checks": "1 hung / 1 expectation mismatch; not counted PASS", "continuous30": "NOT_ACHIEVED", "field_attempt": "attempt07 started; separately audited", "browser_visual_verification": "Blocked by browser tool URL policy; no workaround", "remaining": ["Actual 30 consecutive acceptance", "Response latency", "Long-duration reliability"]}

Previous checkpoint:
Current 2026-10-16 CYCLE-SCOPED TRACKING APPLIED / ACTUAL REBOOT OBSERVING / FIELD30 PENDING:
Attempt06: 3 unique actual PASS with SQLite/3-new-PNG/PLC completion, then PRODUCT_PASSAGE_TRAJECTORY_DISCONTINUITY; not 30 success. Authorized urgent task separates settled PLC cycle identity from physical product tracking. One-file standalone.py fix: Windows and ARM64 each 201 executed PASS +1 known fixture skip; native C/Python synthetic IPC 1 PASS. Two unchanged UI checks remain unverified/failed and are not counted PASS. Stopped deployment engine-integrated-d9b96517ee8cc330 verified 185 file hashes, notebook backup170 files+SQLite integrity verified (4d3449f978c4983335b3324294b2097d7ad272bd82bc4b6196162c949c1b3cf5). Actual reboot in progress; do not claim autostart or 30-cycle acceptance yet. See runs/cycle_scoped_tracking_20261016/CHECKPOINT.md. Attempt07 prepared, not started.

Previous checkpoint:
Current 2026-10-16 OBSERVATION BUFFER DEPLOYED / ACTUAL REBOOT READY / FIELD30 PENDING:
{"release": "engine-integrated-b31d30deafa06bc3", "boot_id": "aa1202d3-2be1-4630-afeb-55324432b37e", "files_verified": 185, "observed_disconnect_to_ready_s": 86.79, "ready_observation_span_s": 213.09, "postboot_manual_recovery": false, "previous_result_preserved": true, "live_field_after_patch": "PENDING", "continuous30": "NOT_ACHIEVED", "windows_related_tests": 59, "native_related_tests": 59, "broader_windows_tests": {"tests": 75, "passed": 73, "preexisting_failed": 2}, "unresolved": ["Intermittent envelope observation loss", "Long field response latency", "Long duration stability"]}

Previous checkpoint:
Current 2026-10-16 OBSERVATION BUFFER CANDIDATE VERIFIED / DEPLOYMENT PENDING:
Attempt05 request10 partPASS+SQLite+PLCcomplete, then passage continuity fault sourcegap0.540s; not continuous success. UserSTOP/empty confirmed. One-file candidate observation metadata buffer2→16 preserves short-stall intermediates without lowering safety thresholds. Related59PC/59nativePASS; broader75PC has2preexisting failures reproduced unchanged. Existing runtimec3df remains active; user sudo transition pending. See runs/observation_buffer_20261016/CHECKPOINT.md.

Previous checkpoint:
Current 2026-10-16 CONTINUOUS30 ATTEMPT04 STOPPED: 7 recorded PASS then request8 ERROR after30.069s, no actual part inference. Same-ID SQLite/final/PLC completion verified all8;28assets first7 verified. Operator reported engine inside camera area atERROR, later STOP+removed. Track lost eligibility before request and entered WAIT_AREA_CLEAR/MISSED_OBSERVATION_LIMIT. Visual cause unproven: error-time images absent. Empty preview is after removal. No runtime/model/threshold edits; next bounded existing diagnostic capture. See tasks/CONTINUOUS-30-FIELD-001.md and runs/continuous_30_20261016/attempt04/ATTEMPT_RESULT.json.

Previous checkpoint:
Current 2026-10-16 PRODUCT UNCERTAINTY REVIEW DEPLOYED / REBOOT READY / 30-CYCLE GOAL NOT MET:
Attempt03 after reboot:3 consecutive actual normalPASS (operator LED/restart/exit confirmed), cycle4 1888c8f9476348cdb499f45afda5ef55 FAIL because product scores0.485/0.475/0.463<0.5; all parts NOT_EVALUATED, not confirmed missing. Four unique SQLite/12PNG+4overlay/PLC completions verified, sameWorker2702. STOP/empty confirmed. Corrected only engine_dynamic.py: unassessed product→REVIEW, actual three-frame missing→FAIL retained; no model/threshold/PLC changes. Windows9/native9PASS and saved4-case comparison verified. Release engine-integrated-c3df373d33beb51f /185SHA, notebook170file+SQLite backup76d51bf4… verified. Actual boot53d5f9c7→5868d22b, enabled/activeMain1077/NRestarts0, soleCamera2696/newframes/models/PLC ready, identitynull/WAIT_START without manual recovery. OriginalFAIL preserved. Current STOP, no live inspection under this final patch. Normal detection instability and earlier intermittent boot/USB issue unresolved;30/30 not achieved. See docs/PRODUCT_SELECTION_UNCERTAINTY_20261016.md and docs/REBOOT_CONTEXT_RECOVERY_20261016.md.

Previous stage (historical):
Current 2026-10-16 PRESENCE-ONLY / ONE CLEAN REBOOT READY VERIFIED:
Release engine-integrated-8ec7803406389df2/185SHA match; assembly reference only. Operator STOP/empty context closure preserved old fifth FAIL and PLC counters. Controlled boot4db9fbb0→53d5f9c7 auto-started systemd Main1165/NRestarts0, sole camera Worker2702, new frames/models/health/PLC ready, WAIT_START without Reset/service start/USB/power action. Observed disconnect→ready95.34s, one minute fresh-frame stability. Previous attempted reboot required power/USB recovery; its cause remains unresolved, do not claim repeated/unattended reliability. New readiness/context tests14PASS. New-policy actual30-cycle trial0/30, physical START pending. See docs/REBOOT_CONTEXT_RECOVERY_20261016.md.

Previous stage (historical):
Current 2026-10-16 CONTINUOUS 30 ATTEMPT 2 — CYCLE5 FINAL FAIL / POLICY CLARIFICATION:
4 consecutive normal PASS verified, fifth31d3b24a13a749f1afe20fac516b8b5f basicPASS but assembly left-pipe OUTWARD_SPLAYED3frames caused finalNG under existing V1. Same-ID raw/SHA/SQLite/PLC complete; actual defect vs false positive unconfirmed. User expects assembly reference-only, current policy differs; no policy/model/threshold change applied. Physical STOP requested but not confirmed; latest Mc_Run=true/RequestLOW. No next insertion instructed. See tasks/CONTINUOUS-30-FIELD-001.md.

Previous stage (historical):
Current 2026-10-16 CONTINUOUS 30 ATTEMPT 2 — 4/30 VERIFIED:
Same runtime/Worker2669/epoch, START once. Trial59d25ada6a9b49e4a078a8f8f21c0276: basic PASS/final PASS/Assembly REVIEW,3newPNG+overlay SHA/SQLite/final durable/PLC completion verified; operator normal lamp/restart/exit confirmed. Request→publication11.375s. Previous contact-associated REVIEW attempt preserved, cause not proven. Cycle2 31a59833f92c472480c6013827d392cb also raw/finalPASS, AssemblyREVIEW;3newframes/4assetSHA/SQLite/PLC complete, operator greenLED/restart confirmed. Publication5.559s. Cycle3 1b6d4ee23c7945fea6719dfb1a2a8f99 basic/finalPASS, AssemblyREVIEW; same-ID assets/SQLite/PLC and operator LED/restart/exit verified. Publication18.774s; latency variable. Cycle4 8acf41b4de1d43b292fac2188ed313eb basic/finalPASS, AssemblyREVIEW; same-ID assets/SQLite/PLC and operator LED/restart/exit verified. Publication7.236s. Next cycle5, no STOP/START/reset. See tasks/CONTINUOUS-30-FIELD-001.md and runs/continuous_30_20261016/attempt02/.

Previous stage (historical):
Current 2026-10-16 CONTINUOUS 30 ATTEMPT 1 STOPPED — NORMAL PRODUCT REVIEW:
Actual first trial38d34a9e292c4897b2c589e405498cbb stored/PLC NG completed, successful normal-decision streak0/30. pipe_left low-confidence0.34956<0.5 in frame2, absent detections in frames1/3; original pipe visible, guide overlap observed but causal/contact status unconfirmed. Same Worker/epoch, no service error. Operator STOP and PLCLOW verified. Threshold/model/runtime unchanged. Await physical placement clarification; see tasks/CONTINUOUS-30-FIELD-001.md. Prior successful reboot trial remains excluded.

Previous stage (historical):
Current 2026-10-16 CONTINUOUS 30 FIELD TRIAL PREPARING — 0/30:
User authorized 30 actual consecutive cycles. Same release engine-integrated-1e913c895d7f9969, camera/PLC ready, STOP/LOW observed and operator empty-belt confirmed. Read-only laptop observer active; actual START requested, no new trial yet. Prior reboot trial excluded. No model/threshold/PLC changes. See tasks/CONTINUOUS-30-FIELD-001.md and runs/continuous_30_20261016/.

Previous stage (historical):
Current 2026-10-16 REBOOT AUTOSTART + ONE PHYSICAL PLC CYCLE VERIFIED:
Release engine-integrated-1e913c895d7f9969 / 185 SHA verified. ASGI adapter cleanup + heartbeat snapshot ordering installed after verified notebook backup; models/PLC/thresholds unchanged. Second actual boot c7413789-3af4-4d42-90f3-6def16b9808f, enabled/active Main1077/NRestarts0, sole camera Worker2669 and models/Assembly ready without manual start/reset. Operator START then one actual product a7c2afb0ea0c44228e028da34b968f1b: raw PASS, Assembly REVIEW(SEED_INSUFFICIENT_SPATIAL_BODY_SUPPORT), final PASS under unchanged EXISTING_PASS_ASSEMBLY_REVIEW policy. Same-ID SQLite/3PNG+overlay SHA/history API verified, Result1/Done1/completed1/RequestLOW; operator confirmed normal lamp and conveyor restart, then STOP. Request→PLC completion13.217s, Assembly10.994s: latency not solved. Final STOP/outputs0/ready; next-product identity waits for positive upstream entry. First failed START preserved; long-run/continuous post-reboot reliability and full assembly acceptance not claimed. Report docs/REBOOT_READINESS_REPORT_20261016.md. Task-owned remote verification directories retained pending archive/cleanup; no additional runtime copy launched.

Previous stage (historical):
Current 2026-10-16 REBOOT AUTOSTART PASS / FIRST START HEALTH FAULT / FIX CANDIDATE:
First actual START after boot reached Mc_Run=true but PYTHON_NOT_READY due transient WORKER_HEARTBEAT_LOST, no request/product/result. Operator STOP confirmed. Reproduced health clock-order race (heartbeat renewal after sampled now → negative age); one-file inspection.py candidate snapshots heartbeat first and retains real stale/future checks, adds age diagnostics. Windows44pass/2skip; native3pass. Actual field event lacked heartbeat age, so its cause remains provisional until followup. Candidate staged in tmp/verify/reboot_health_20261016, normal sudo authentication requested after reboot expired prior credentials. Existing 2e55e8af… remains active; do not call field acceptance PASS. See tasks/JETSON-REBOOT-READINESS-001.md.

Previous stage:
Current 2026-10-16 ACTUAL REBOOT AUTOSTART VERIFIED / FIRST FIELD REQUEST PENDING:
JETSON-REBOOT-READINESS-001: installed one-file ASGI adapter shutdown fix, release engine-integrated-2e55e8af6873c9cb/185SHA match. Notebook backup170files SHA43f98f97…/SQLiteok. Windows31pass/1Linuxskip, native4pass with old SIGTERM failure reproduced. Actual boot ID b4f3218f…→6cfd2d60…; service enabled/active Main1076/NRestarts0 automatically, camera sole owner2669/new epoch742233…/frame353, models/Assembly ready and /line200. PLC fresh connected STOP/RequestLOW/output0, no product identity block. User START on empty belt requested; actual post-reboot product result pending. No manual start/reset/grant after reboot, no model/PLC/threshold/latency changes. See tasks/JETSON-REBOOT-READINESS-001.md.

Previous stage:
Current 2026-10-16 REQUEST LATENCY DIAGNOSED / NO PERFORMANCE CHANGE APPLIED:
Read-only same-ID runtime/SQLite/Assembly evidence: last three completed requests→cyclic completion observed 19.840/20.210/23.150s. Latest basic trigger→durable1.427s (storage0.401s), subsequent required Assembly16.528s; pose matching15.507s across3frames, all POSE_QUALITY_REJECTED. Separate earlier no-input request waited30.011s for PREVIOUS_RUNTIME_PRODUCT_EXIT_UNPROVEN then ERROR. No new inspection, output, restart, model/threshold/code change. Next: profile equivalent saved-frame pose matching and preserve current decision/storage/identity contract; isolate identity wait separately. Details docs/REQUEST_LATENCY_20261016.md.

Previous stage:
Current 2026-10-16 CAMERA STARTUP RECOVERED / OPERATOR SCREEN CHECK PENDING:
Existing current release engine-integrated-80882c05c181fbd6 preserved. Stale unowned OpENer IPC socket blocked service before camera initialization; verified stopped service/no owner/free lock+ports/ECONNREFUSED, archived socket, operator restarted existing systemd service. Main5229/Worker5311, UI18771/auto HTTP200, camera_ready true, fresh same-epoch frames276→518, actual conveyor JPEG viewed. PLC STOP/Runfalse/Requestfalse/Resultfalse/Donefalse, new inspections0. Existing TensorRT device0 startup execution observed; no code/model/threshold changes. Previous-runtime product-exit protection remains; no physical inspection or long-run camera recovery acceptance claimed. See docs/CAMERA_RECOVERY_20261016.md. Next: operator confirms current screen, then resolve only actual outstanding readiness conditions.

Previous stage:
Current 2026-10-15 CONTINUOUS PRODUCT STABILITY — SIX SUPERVISED CYCLES VERIFIED:
Source a859b21e00b2d1f661b27e301f4705be74273d04 / current engine-integrated-80882c05c181fbd6,185 SHA match. Bounded entry reobservation and same-request proof ordering fixed; diagnostic deepcopy moved outside health lock. PC144/ARM64144 pass. Actual START once, no intermediate STOP/START/Reset/grant/restart: normal PASS, left missing FAIL, restored PASS, right missing FAIL, restored PASS, user-added symbol missing FAIL. Six unique IDs/18 actual PNG+pixel hashes; all durable final→Result→next cyclic Done→request reset and operator LEDs/restarts. Same service16809/Worker16852/Cconnection1 timeout0. Health max380.371ms, storage293–534ms, recorded ready=false0; limited timing margin remains. First attempt3cycles then diagnostic health failure and separate single physical belt-contact trial are preserved, not counted as success. Final STOP/LOW/output0/idle/SQLiteok. Backup170files SHA1ff338bd... verified. Assembly REVIEW remains under unchanged V1 policy; no general model/long-run/unattended recovery qualification. Details docs/CONTINUOUS_PRODUCT_STABILITY_REPORT.md and tasks/CONTINUOUS-PRODUCT-STABILITY.md. No successor UI/DB task started.

Post-trial STOP observation: CAMERA_FRAME_TIMEOUT caused repeated automatic camera Worker/epoch recovery after the six-cycle window. Main service/C counters unchanged, no new requests. Previous-runtime product identity is now unproven; next-trial readiness is NOT confirmed. USB reconnect with unchanged placement requested; operator confirmation pending. This late condition does not invalidate the six completed cycles but leaves camera/restart stability unresolved.

Previous stage (historical):
Current 2026-10-15 V1 FOUR SUPERVISED CONTINUOUS CYCLES VERIFIED:
Source7ec9d25e204f60a0e2ec7825f1d1560968510611 / operating engine-integrated-32d132a4256d4ef8,185SHA match. Bounded detector-width outlier reassociation, unchanged thresholds/PLC/models/C; PC125+ARM64125 pass. Actual START once, no intermediate STOP/START/Reset/software grants: left missing a489d5fa FAIL, right missing5d1aa003 FAIL, first symbol86131de3 FAIL due one envelope score0.484<0.5 (not three-frame symbol confirmation), repeated symbolcaabb4cb SYMBOL_MODULE_MISSING/FAIL. Twelve distinct actual PNG/pixel/identity checks, all Journal+NG Result->next cyclic Done->requestreset, operator defect LEDs/restarts/finalSTOP. Next three accepted using prior outbound/new upstream entry evidence. Single service12092/Worker12135/Cconnection1,timeout0; trial health max255.45ms,raw storage277-421ms. FinalSTOP/output0/idle/SQLiteok. First symbol detection instability, assemblyREVIEW, long-run Class1/autonomous fault recovery remain limitations. Notebook170file+SQLite backup74a80da9 verified. Details docs/V1_LINE_COMPLETION_REPORT.md and tasks/V1-LINE-COMPLETION.md.

Previous stage (historical constraints below are superseded only by the verified scope above):
Current 2026-10-15 V1 DECISION FIELD VERIFIED / CONTINUOUS OPERATION NOT COMPLETE:
Source6a9dd7a6bea26bbd0f1fbb1e3e251655d5167078 / operating engine-integrated-9f6abef5e3c00168,185SHA match. BASIC_WITH_CONFIRMED_ASSEMBLY_FAIL_V1: reliable basic PASS survives optional assembly geometry REVIEW; confirmed FAIL wins; raw/storage/cancel faults cannot publish. PC147/native147+UI pass. Actual normal b57e91fa PASS/OK10.142s, exhaust missing6d0b4101 FAIL/NG9.134s, restored9aeab7d7 PASS/OK9.231s; each new3PNG and Result->next cyclic Done->requestreset/operator LED+restart. Extra normal reinsertions and a zero-frame identity ERROR are preserved separately; physical STOP and context recovery occurred, so this is not uninterrupted three-cycle success. Final restored outbound bbox growth exceeded existing limit by0.176px and left PRODUCT_PASSAGE_TRAJECTORY_DISCONTINUITY. Final STOP/output0/idle; next-product readiness not accepted. Worker9652/Assembly9630/C9626 connection1 unchanged, timeout0, recorded health max281.48ms. Notebook backup170files+SQLite verified; completed temporary126files archived/hashchecked/removed. See docs/V1_LINE_COMPLETION_REPORT.md and tasks/V1-LINE-COMPLETION.md. No new alignment/model/PLC changes; original histories preserved.


Current 2026-10-15 BASIC MISSING FIELD VERIFIED / CONFIRMED FAIL POLICY DEPLOYED:
Actual one-product inspection5a0708cf:3newPNG/basicFAIL EXHAUST_TOP_MISSING, Assembly geometryREVIEW, old finalREVIEW; NG Result5285 then Done5286, requestreset/operatorrestart+STOP. Postcompletion camera stream fault is separate, continuous readiness not accepted. Prior unsent60aa99de recovered with independent ABORTED after counter-baseline fix, originals preserved. User then set any confirmed component FAIL to finalFAIL. Source887ea3f2 / operating engine-integrated-2719dff19eb79478,185SHA verified; PC28/ARM6428 PASS, saved actual combinationFAIL, historical savedREVIEW unchanged. One service/OpENer and readycamera/Assembly, STOP/nooutput/newrequest0. Notebook170file+SQLite backup07b34251 verified. No new physical trial with changed policy. Reports: docs/BASIC_PART_MISSING_VERIFICATION_REPORT.md and docs/CONFIRMED_FAIL_COMBINATION_FIX.md.

Previous stage (superseded by results above):
Current 2026-10-15 V1 BASIC MISSING CHECK: native saved physical controls NORMAL PASS / EXHAUST MISSING FAIL / RESTORED PASS. Nine original PNG/pixel hashes, actual current source/model/config,185 release files and three aggregate decisions verified. No Assembly/PLC result substitution, no runtime changes. User subsequently authorized one physical missing-exhaust trial; not started because prior17:05 request60aa99de has rawPASS/COMPLETE but cancelled-before-final/storage-deadline and unfinished1. Result/Done stayed2->2. Existing Reset targets older closed product; abort validator assumes cumulative0/newboot and cannot settle this repeated-cycle case unchanged. Minimal recovery scope clarification pending; no new START/result/restart. Evidence: docs/BASIC_PART_MISSING_VERIFICATION_REPORT.md and private runs/basic_parts_missing_verification_001/. Previous matcher experiments ended and preserved; no new alignment algorithm.

Current 2026-10-15 TASK022 MATCHER COMPARISON EXECUTED / OPERATING ALIGNMENT UNRESOLVED:

B/C actual saved-image comparison on27field+13TRAIN, pinned pretrained Kornia0.8.2 CUDA LoFTR; C recenttriplet independenterrors20.57/22.97/23.84px and mirror falseaccept, B repeated-edge errors. No qualified deployment. Same-request relativeLK independently classified12crops CORRECT but anchor/heldgeometry unqualified. Jetson CPU-only savedtriplet118–125ms, full13.745s improvement UNMEASURED. Runtime/model/PLC unchanged. User power interruption recovered via existing stopped/unowned-socket procedure; same engine-integrated-a8d842b879cd14ea/e20ebbd,185SHA, camera/Assembly ready, PLCLOW, initial Result/Done0. Later operator-confirmed independent START produced2 cycles: no-inspection ERROR, then actual3frames/basicPASS/assemblyREVIEW; both cyclic completions observed. Final Request/Result/DoneLOW and physicalSTOP confirmed. Focused5tests PASS. See docs/ASSEMBLY_AI_FIELD_FIX_REPORT.md; no successor task or assistant-issued field trial started.

Previous 2026-10-15 TASK022 INPUT RECOVERY:

### 2026-10-15 미리보기 접수 보완 후 실제 한 제품 재시험
- Runtime 미사용 preview association 복구를 적용했다. 소스 e20ebbd, Release engine-integrated-a8d842b879cd14ea,185 SHA 일치. PC87/ARM64 47 PASS, 정지 백업170파일·SQLite 검증.
- 새 검사 b5f59b4aaf0b4127ba6acdb49e6502b1: 실제3PNG/기본 부품검사 PASS, 조립 2프레임 공간지지 실패·1프레임 네 부품 CORRECT → 통합 REVIEW. Result3064→Done3065·Request 해제·사용자 재가동/STOP 확인. 현재 LOW/IDLE. 촬영 진입 복구 관측, 조립 안정화/최종 PASS·FAIL 미완료.
- PLC4.5초 이송은 사용자 적용·진술 기준이다. PLC를 수정하지 않았고 독립 온라인 동등성은 미검증. 다음 실제 START는 자동 반복하지 않는다. 비공개 증거 input_recovery/preview_reassociation/FIELD_RETEST_REPORT.md.

Current engine-integrated-63ac009827142f1e/185 SHA preserved. Frozen actual preprocess T0001 self +5 predetermined geometric transforms VALID/four CORRECT; not field proof. Retired bridge-B failure localized; current-view manually vetted crops still misclassify normal left pipe and location-dependent exhaust. Operator-staged normal/SIDEWAYS/restored stationary clips53/52/53 raw PNG/pixel SHA verified, body moved between scenes. Normal exhaust3CORRECT vs restored3SIDEWAYS; no production model/crop change or new PLC cycle yet. Stopped notebook backup170files/SQLite verified SHA1175617f. User reboot exposed orphan IPC socket startup rejection; proven unowned socket removed under stopped service+exclusive lock, same service recovered. Postboot residual Request/McRun not admitted, Result/Done0; userSTOP then PLCLOW/IDLE. Assembly input, classification, repeat admission and approved3consecutivefieldtrial remain separate/uncompleted. See tasks/TASK-022-ASSEMBLY-AI-FIELD-FIX.md and private input_recovery evidence.

Previous 2026-10-15 TASK024 LINE UI / RESET DEPLOYED:
Source ba6b9be9b5bb75e074c9e1db2243a7e7b61a6f30 pushed; operating engine-integrated-63ac009827142f1e,185 file SHA match. Per-part presence vs assembly, saved raw/alignment/crops/failure stage, restart-safe display history. User explicitly removed Reset code/identity inputs: exact same-origin local Reset with physical-confirmation button and live STOP/no-output/idle/Journal safeguards; no per-product permissions. Native36 and Node UI/preview regression PASS, actual16 history/3frames/Reset preflight verified. Reset mutation/newSTART/result0; historical product block remains pending actual operator reset. Camera/PLC ready and STOP, NRestarts0, verified notebook backups preserved. Assembly alignment remains unresolved. See docs/LINE_RESULT_AND_RECOVERY_REPORT.md.

Previous 2026-10-15 TASK022 POSE-REUSE FOLLOW-UP CLOSED / ASSEMBLY UNRESOLVED:
Report commit c8d2fce7e5dfddacd78f283fd7d69bd051ca86bb pushed; operating release remains engine-integrated-8831b41d4448da2d, source52df5d2. B geometry rejected on15field+13TRAIN; no deployment. Final read detected user-started additional request2 f2b009674c6c49fa9f92f81091d56e8b: zero observations, PREVIOUS_PRODUCT_IDENTITY_OR_EXIT_UNPROVEN -> ERROR/NG, Result25264 then Done25265, Request cleared. Not actual AI success. User confirmed STOP and physical stop. No active/storage/assembly work; service unchanged. See docs/ASSEMBLY_AI_FIELD_FIX_REPORT.md.

Latest TASK022 pose-reuse follow-up 2026-10-15: ASSEMBLY_NOT_FIXED / B_NOT_DEPLOYED. Current preview commit52df5d2 / Release engine-integrated-8831b41d4448da2d preserved. Same-frame stored D001 poses confirmed; D001/T0001 are distinct reference images. One similarity bridge has held-point errors9.53/13.65/19.44px; isolated body refiner0/15 field and0/13 TRAIN. Old template mirror falseaccept reproduced. No new model/threshold/PLC write/service restart/START. Latest existing preview trial rawPASS -> AssemblyREVIEW -> integratedREVIEW -> NG5570/Done5571 -> requestreset/operatorrestart; STOP/idle verified. Private comparison and visible crops: runs/assembly_ai_022/pose_reuse_followup/. See docs/ASSEMBLY_AI_FIELD_FIX_REPORT.md and docs/WEB_PREVIEW_LATENCY_REPORT.md. Existing unrelated changes preserved.

Latest TASK022 2026-10-15: IN_PROGRESS / ASSEMBLY_REGISTRATION_NOT_DEPLOYED / HISTORICAL_CONTEXT_CLOSED. Operating Worker commit0dc3f77/release engine-integrated-eac535432b143ac5 retained,184file hashes match. After current operator STOP/model-off-belt/hands-off confirmation, exact old tracked inspection2a80c3 context closed via existing maintenance API; SQLite notebook backups verified,130inspections/492assets/2approvals and originals unchanged,only event/outbox/state1each appended,unfinished0 and PLCLOW/Worker+AssemblyIDLE. No grant/replay/AIclear/restart/newSTART. Userv4 move5s/requestdelay2s direct trialbb3c was NO_ACTUAL_INSPECTION/ERROR;NGResult1724->Done1725->requestreset observed,actualAI0/physicalconsumption unverified. New alignment diagnostics remain unqualified: field20 normal exhaust CORRECT/SIDEWAYS/SIDEWAYS persists with one fixed matrix; originalT0001 reference-only ablation fails first normal/missing/restored seed. Fixed-body manual landmarks have uncertainty,not operating calibration; template mirror falseaccept retained as failure. No model/threshold/camera/light change or new alignment deployment. See docs/ASSEMBLY_AI_FIELD_FIX_REPORT.md and private runs/assembly_ai_022/.

Latest fixed-PLC field trial 2026-10-15: START once / 3 consecutive actual cycles / no intermediate STOP or software grant VERIFIED. Release engine-integrated-c04fa92419200551 unchanged. 3 unique IDs,9newPNG,raw+assembly processing+integrated REVIEW,NG Result then next-packet Done,PLC reset/operator restart3times. Assembly classifier NOT_RUN due pose preprocessor rejection; third settled then420.197ms healthgap caused PYTHON_NOT_READY, so sustained readiness NOT_ACCEPTED. Final operatorSTOP and PLCLOW confirmed. Evidence59files verified; report docs/FIXED_PLC_CONTINUOUS_THREE_FIELD_REPORT.md.

Latest TASK020 revision 2026-10-14: ISOLATED_VERIFIED / STOP_FOR_FIELD_DEPLOYMENT_APPROVAL. PLC_AUTOMATIC_REPEAT removes AutomaticAdmission, arm command and per-product grant/ledger; C uses stopped baseline and fresh PLC request. PASS->OK; FAIL/REVIEW/ERROR->NG then next-packet Done retained. Durable identity/STOP/storage guards and original histories preserved. ARM64 Python287 PASS(92.418s), C sanitizer/state/AF_UNIX and build PASS; synthetic-device 3-product owner path has no grants. IPC receipt-clock bug fixed; actual Class1 root cause unresolved, timeout/lease unchanged. Operating engine-integrated-4920568fe3750b64/source45c unchanged; no field writes or deployment. New dev C127cedc4. Report docs/CLASS1_IPC_AND_REPEAT_READINESS_REPORT.md; field exit/PLC recovery/3-product/boot/laptop-off unverified.

Latest TASK019 follow-up 2026-10-14: DEPLOYED / OLD_CYCLE_ABORTED / NEW_TRIAL_BLOCKED_BEFORE_START. Official45c36945928cdcbf04fa667d123a7b5342184adc deployed as engine-integrated-4920568fe3750b64; release186/delta13 SHA verified, C8506ffc2, service41150 enabled-active/NRestarts0 and sole C/camera/Assembly. Approved exact old98c04 recovery appended durable ABORTED+event; original116 inspection/2 approval rows and assets unchanged, blocker1->0, no fabricated final/replay. Fresh stopped backup5393eada and recovery/trial SQLite integrity verified. User separately approved one product; fresh grant attempted once but INITIAL_APPROVAL_FAILED:ValueError, no acceptance/new ledger row. Class1 timeout/reconnect3->4 coincides; exact exception subreason/root cause unrecorded. START never instructed; new inspection/Result/Done0, actual field storage/AI/consumption NOT_RUN. Later idle IPC disconnect health age980.34ms prevents any service-lifetime health PASS. Final connection5/fresh/LOW/DISARMED, approval ineligible; no retry/restart/automatic qualification. Two exact task temporaries removed after notebook archive163items SHA2615e06b verified; current/protected data preserved. Report: health_storage_019/deployment_001/TASK019_DEPLOY_RECOVERY_AND_TRIAL_REPORT.md. Next only scoped Class1/IPC/admission diagnosis and new field approval; do not reuse failed grant or claim physical cycle success.

Historical TASK019 isolated verification 2026-10-14: ISOLATED_VERIFIED / STOP_FOR_DEPLOY_APPROVAL. Single bounded raw/final storage owner keeps cyclic health independent of image/fsync and Journal readers; identity/epoch/generation/durable commit and STOP/lease guards retained. ARM64 Python283 PASS, C initial22 plus supervised/automatic sanitizer suites and full build PASS. Four synthetic-model owner paths delivered Result then next-packet Done exactly once under raw1047-1057ms/final567-570ms storage and UI polling; health maximum196.9ms, unchanged400ms Python lease. Actual archived failure copy preserves116 raw rows/spent approval; independent ABORTED clears only proven blocked transaction, live NOT_APPLIED at this historical stage. Report docs/PYTHON_NOT_READY_FIX_REPORT.md. The follow-up above supersedes its deployment state only.

Latest TASK018 approved first-product trial 2026-10-14: FIELD_CYCLE_FAILED / SAFE_STOP_CONFIRMED / NO_RETRY_AUTHORIZED. Deployed engine-integrated-d247e1e9579ab6e7/db3628d unchanged, current120 direct file hashes preserved. Fresh grant consumed once; PLC Request accepted, inspection 98c04ad398a7422daba705e206b9bae6 ran live Worker with3 fresh PNGs and durable COMPLETE/REVIEW(ENGINE_OR_HAND_MOTION). At request+1.661s C disarmed PYTHON_NOT_READY before Assembly/final: Result0/Done0, no PLC consumption/restart. Shared service lock covers Journal storage and health renewal; actual storage348.686ms, synthetic99ms prior age reproduces400ms lease expiry; actual renewal timestamp absent so exact cause remains unproven. UI bridge incorrectly remains INSPECTION_RUNNING after cancellation; current missing-final Journal blocker1 is real new-contract incompletion, not Legacy35. User STOP confirmed; Mc_Run/Cv_Run/Request/Result/Done LOW. Service34835 enabled-active/NRestarts0, spent approval revoked, no rearm/restart/write. Later Class1 timeouts3/opens4 separate from first fault. Notebook evidence27 hashes/SQLite/3pixel SHA verified; offline lease3cases and IPC/control18tests PASS. Report: supervised_repeat_018/deployment_readiness_001/first_product_trial_001/FIELD_TRIAL_REPORT.md. Next requires scoped lock/health and terminal-state repair, isolated verification, new deployment and field-trial approval; never forge completion or reset Journal/approval.

Historical deployment before trial: DEPLOYED_VERIFIED. Official master db3628dc8bd1d666da9c67239d0deca689efbc5a deployed as engine-integrated-d247e1e9579ab6e7; approved delta15 and Release183 SHA verified. FIRST_PRODUCT_ONLY; no unattended qualification. Notebook stopped backup e1813b44.. verified. Report: supervised_repeat_018/deployment_readiness_001/DEPLOYMENT_RESULT.md.

Latest TASK018 live request diagnosis 2026-10-14: STOP_FOR_DEPLOY_APPROVAL. User confirmed physical STOP. Live engine-supervised-c6f5b94e8adb4e2e matches ab34bf2 source; GitHub db3628dc8bd1d666da9c67239d0deca689efbc5a NOT_DEPLOYED. Current supervised approval0/disarmed/request_id0 prevents REQUEST_RECEIVED and Journal admission; raw Request HIGH was user-observed but historical RX edges are not logged. No new inspection since service startup, no Result/Done; Journal blockers0, camera/assembly/IPC currently ready. Class1 timeouts7/connection8 remain separate unresolved issue. Notebook current/config/unit+consistent SQLite backup SHA bb757f8b... verified; assets57 SHA match. Prepared one 15-file delta engine-integrated-d247e1e9579ab6e7 with latest monitor/code and FIRST_PRODUCT_ONLY commissioning policy; no web pairing, no unverified automatic qualification TRUE. Offline readiness5+focused49 PASS; previous native259 reused. No operating change/restart/grant/PLC write; actual deployment and new field trial require separate approvals. Report docs/PLC_REQUEST_BLOCK_AND_DEPLOYMENT_READINESS.md; exact plan in existing supervised_repeat_018/deployment_readiness_001/.

Latest TASK018 automatic revision 2026-10-14: ISOLATED_PASS / STOP_FOR_FIELD_VALIDATION_AND_DEPLOY_APPROVAL. Normal monitoring has no pairing/per-product approval. PLC_AUTOMATIC_REPEAT uses durable transaction reset plus qualified product-specific passage, not global Area CLEAR; accepted ambiguous requests get bounded Journal ERROR/NG Done. Native Python259+C/AF_UNIX PASS. Operating engine-supervised-c6f5b94e8adb4e2e remains unchanged; no deployment/restart/PLC writes. Sensor-latch online equivalence, actual exit, PLC timeout/STOP and reconnect recovery remain unverified. See docs/PLC_AUTOMATIC_REPEAT_REPORT.md and current TASK018.

Latest 2026-10-14 TASK018 SUPERVISED_REPEAT_TEST / ISOLATED_PASS / STOP_FOR_DEPLOY_APPROVAL:
Canonical jetson/ adds explicit fresh per-product supervisor grants, EAI1 IPCv3 C/Python, durable spent IDs and prior-cycle completion checks. FIRST_PRODUCT_ONLY remains one-shot. /line (and opt-in /auto redirect) offers one authenticated prepare route, actual AI vs PLC disposition/evidence; no web START or automatic CLEAR. Native229 tests, C initial22+supervised sanitizers, real Unix IPC four synthetic outcomes and browser fixture PASS. Deployment delta18files and notebook current/config120files+SQLite backup verified. Prepared engine-supervised-c6f5b94e8adb4e2e NOT_APPLIED; operating engine-integrated-90a914423826735a unchanged. Class1 reconnect6/504.526s remains unresolved; no timeout/lease/model/PLC/EDS changes. Actual3product trial NOT_RUN, requires new field-stop/deploy/supervision approval. See docs/SUPERVISED_REPEAT_INSPECTION_REPORT.md and current run supervised_repeat_018/DEPLOY_APPROVAL_AND_ROLLBACK.md. No AI-miss successor task.

Latest 2026-10-14 TASK017 ASSEMBLY_INTEGRITY_FIXED / ISOLATED_VERIFIED / STOP_FOR_DEPLOY_APPROVAL:
Canonical jetson/ now measures and journals RAW_FRAME_INTEGRITY_V1 instead of defaulting missing integrity to true. Assembly verifies frame identity, source time/epoch/generation and raw/pixel SHA; legacy missing integrity requires verified-PNG remeasurement, missing quality or contradictory evidence is ERROR. Actual failed3-frame KeyError reproduced; PC7/new contract and native211 (previous204+new7) PASS. Frozen CUDA saved-frame replay completes without KeyError, but all3 REVIEW(PRODUCT_COUNT_NOT_ONE/TEMPORAL_SINGLE_PRODUCT_REQUIRED), four classifiers not run without valid crops; integrated REVIEW retained. Operating release engine-integrated-90a914423826735a and current113/frozen28 hashes unchanged; service24786 enabled-active/NRestarts0, original ERROR Journal and consumed/revoked approval preserved. Result/Done counts remain1, no extra output or field trial. Class1 connection7->13 observed, cause unresolved, timeouts unchanged. Notebook evidence/SQLite backups SHA verified. No deployment or successor work; new deployment/retest approval required. Report: docs/ASSEMBLY_INTEGRITY_CONTRACT_FIX_REPORT.md. Private evidence: tag_data_link_008/assembly_integrity_017/.

Latest 2026-10-14 JOURNAL_CONTRACT_FIXED / CANONICAL_SOURCE_DEPLOYED / FIRST_REAL_CYCLE_COMPLETED_WITH_AI_ERROR:
Official GitHub master 011a3f46478b02f34b68a34073ac79241975d1e9; operating source bb3632120e5dda2d161ef38d25fa87a760e9b576, release engine-integrated-90a914423826735a,113 files match latest GitHub jetson/. One engine-inspector.service enabled/active, one C/camera owner. Legacy COMPLETE35 recognized by matching pre-integrated authority/identity and absence of newer contract markers;13 MOCK/22 PLC,136 asset hashes,35 completion events verified. Existing inspection rows and approval ledger preserved; no DB rewrite or per-ID exemption. ACCEPTED/new-contract missing final/corrupt DB/disk shortage still block. PC204(203PASS/1Linuxskip)+bundle1PASS; portable fixture/UI26PASS overlap; native204PASS after test fixture/path repair. First approval READY before operator submission.
Supervised real product 9edd7bf904094733b9f92908bf566c17: request token a3fffda52195efda:2:1;3 new raw frames; existing inspector FAIL, required assembly ERROR(KeyError:'integrity'), final ERROR retained; user-approved policy sent PLC NG Result then Done once. C sequence4528/4529; PLC request/Inspecting reset, Defect_Memory ON, Cv_Run ON; user confirmed physical restart then STOP. PLC consumption supported by state/physical observations, no dedicated ACK exists; do not promote AI accuracy to PASS. Subsequent Class1 reconnect revoked spent approval, no rearm/extra result. Camera/AI service readiness does not imply error-free assembly or continuous operation.
Notebook current/config/unit/SQLite backup verified; runtime rollback package available, actual rollback NOT_RUN. Verified notebook archives and exact inactive staging cleanup PASS; current/assets/config/data/envs/env_candidates and unknowns preserved. Service MainPID24786/NRestarts0 unchanged; final Request/Result/Done/Mc_Run/Cv_Run LOW, spent approval REVOKED. No additional trial. Do not revive per35 review sidecar proposal or old staging as source. No next task started. Assembly integrity error/reconnect root cause/clearance/continuous/reboot/laptop-off remain unverified.
Evidence: tag_data_link_008/first_product_initial_arm_016/field_deployment_001/history_compatibility/contract_classification/JOURNAL_COMPATIBILITY_AND_INTEGRATION_REPORT.md; CYCLE_ANALYSIS.json; FIRST_AI_CYCLE_EVIDENCE.tar.gz.

Latest 2026-10-14 TASK016 DEPLOYED / FIRST_AI_CYCLE_BLOCKED: user approved stopped/supervised whole-candidate install + one trial. Installed engine-first-product-candidate-113a579caa99d978 (109 SHA verified), same systemd enabled-active PID22930/NRestarts0, C22947/camera22970/assembly ready, actual cyclic8B healthy current snapshot, no Explicit writer. Initial approval0/accepted0/Result0/Done0; no START instructed. Preflight discovered legacy Journal COMPLETE35 rows (2026-09-25~29, durable storage) lacking later integrated_decision keys; ACCEPTED0. Installed guard counts those35 and stays disarmed until resolved. Old rows/data preserved; fresh consistent backup5files SHA61000bc1... verified. C logs include3connection timeouts/IPC reconnect; cause unconfirmed, not a reliability PASS. Isolated reviewed-exact-history compatibility candidate engine-first-product-history-dcd13131cb53c30a SHA133bba96008074329ddeb7b04a77ad4f2b49f054758c187bf414ed97fd9132e3, only initial_approval.py/release changed; 45unique ARM64PASS, PC44PASS/1skip, actual DB copy35->0 unchanged SHA. NOT_INSTALLED, reviewapproved=false; pending additional history-guard-change approval. Report D:/OneDevice_Team_project/runs/engine_standalone_plc_autostart_001/v001_20261007T052746Z/tag_data_link_008/first_product_initial_arm_016/field_deployment_001/FIELD_DEPLOYMENT_REPORT.md; proposed change D:/OneDevice_Team_project/runs/engine_standalone_plc_autostart_001/v001_20261007T052746Z/tag_data_link_008/first_product_initial_arm_016/field_deployment_001/history_compatibility/HISTORY_COMPATIBILITY_APPROVAL.md. Same TASK016/run only; do not auto-arm, reset Journal, redeploy old candidate or ask for previously granted install/one-trial permission again. Next approval is solely new history reconciliation scope; investigate link instability before actual motion.

Latest 2026-10-14 TASK016 ISOLATED_PASS / FIELD_NOT_VERIFIED / STOP_FOR_DEPLOY_APPROVAL: explicit durable one-product approval separates first arm from actual CLEAR; FIRST_PRODUCT_ONLY, no automatic rearm after use/STOP/reconnect/restart. Latest user policy PASS_OK_OTHER_NG_V1: AI REVIEW/ERROR retained in Journal, PLC Result1 then Done1; current-context/STOP/EStop/durability guards preserved. Candidate engine-first-product-candidate-113a579caa99d978, SHA e5a7854cca8fc7f4fd4b0fb7e21f814180c676f7e3c75689e5013305c7149127;109 runtime files. PC147=146PASS/1Linuxskip; ARM64 C41; protocol26+24+11+12; fixture real-software E2E4; native package check PASS. PLC4/8/10B/EDS/models/TASK010 TX callback preserved. Operating108 hashes unchanged, servicePID1082 enabled-active/NRestarts0; no operating restart, field output or new camera capture. Native evidence1073 SHAverified; own arm016 temp removed after recovery. Actual AI field cycle/accuracy/reboot/laptop-off NOT_RUN; repeat BLOCKED. Report: D:/OneDevice_Team_project/runs/engine_standalone_plc_autostart_001/v001_20261007T052746Z/tag_data_link_008/first_product_initial_arm_016/PLC_FIRST_PRODUCT_INITIAL_ARM_REPORT.md. Next only explicit whole-runtime deployment + supervised first product approval; no successor auto-execution.

Latest 2026-10-14 TASK015 ISOLATED_VERIFIED / STOP_FOR_DEPLOY_APPROVAL: TASK011-derived PLC_REQUEST_TRACKED_FULL_FRAME candidate engine-plc-full-frame-candidate-659c71d6b8b7cf0d; Zone/stable preview admission separated from Worker quality; same Track/fresh epoch/generation/request and Journal guards retained. Python114=113PASS/1Linuxskip; C30PASS; real local Unix IPC4 outcomes PASS; saved200 metadata oldZone0/newPacket200, 30s deadline198, conditional admission1, same replayTrack200, AreaUNKNOWN200. No actual AI/PLC cycle. C initial arm still requires genuine qualified CLEAR; horizontal field clearance unverified, so first field arm and repeat remain BLOCKED. TASK011/013/014 hashes preserved; 107runtime-file candidate verified, unqualified/transport-disabled configs; no Jetson access, service restart, PLC/EDS/OpENer/model/Journal changes or deployment. No successor work. Report: D:/OneDevice_Team_project/runs/engine_standalone_plc_autostart_001/v001_20261007T052746Z/tag_data_link_008/plc_trigger_full_frame_015/PLC_TRIGGER_FULL_FRAME_INTEGRATION_REPORT.md.

Latest 2026-10-13 TASK014 STOP_FOR_CAPTURE_APPROVAL: isolated maintenance capture prepared,25unique tests+100raw-output parity PASS.5s synthetic113raw/12tensor verified. Operating107hashes unchanged/service1082 active/worker2790 captureIDLE. New field raw/tensor0, bbox unresolved. No service transition/PLC/OpENer/model/Journal writes. Read FIELD_RAW_CAPTURE_READINESS_REPORT.md and approval template before next authorized service stop/capture/restore. No successor work. Report: D:/OneDevice_Team_project/runs/engine_standalone_plc_autostart_001/v001_20261007T052746Z/tag_data_link_008/field_raw_capture_014/FIELD_RAW_CAPTURE_READINESS_REPORT.md.

Latest 2026-10-13 TASK013 STOP / CURRENT_FIELD_VALIDATION_BLOCKED: isolated horizontal texture observer + bbox trace implemented on verified TASK011 archive. 31 unit/regression PASS, 100 synthetic postprocess parity0, 72 native PNG file/pixel hashes verified; calibration18 excluded from development replay54 all expected; synthetic stress39 PASS, initial gray-remnant false-CLEAR5 preserved then corrected. Actual saved200 provider normalization mismatch0; Zone0/200/bottom146 unchanged; raw model/current-image evidence BLOCKED by installed read-only capture API despite approved stopped5s capture (no POST/bypass/restart). Real current-camera clearance/thin-remnant/departure/native latency NOT_VERIFIED; no operational zone proposed, new mode ISOLATED_ONLY and field launcher blocked. TASK011 intact; installed107source/config hashes unchanged, service1082 enabled-active/NRestarts0/camera worker2790/original TypeError retained. No PLC/OpENer/EDS/model/output/Journal changes or deployment. Report: D:/OneDevice_Team_project/runs/engine_standalone_plc_autostart_001/v001_20261007T052746Z/tag_data_link_008/horizontal_geometry_013/HORIZONTAL_CONVEYOR_GEOMETRY_REPORT.md. No successor work.

Latest 2026-10-13 TASK012 STOP_FOR_DEPLOY_APPROVAL / READINESS_BLOCKED: approved position-only physical trial completed; operator START/move/stop then STOP confirmed. Read-only373 PLC/camera samples: sensor rises4/request1; post-request fresh200, active Zone0/200, bottom-edge bbox146/200. User confirmed vertical-to-horizontal camera orientation change. Area UNKNOWN373/373; historical moved-empty90/90 OCCUPIED; mode rename invalid. Candidate9ea6e0 unchanged106runtime hashes; current103source+5config/service preserved. Service1082 enabled/active NRestarts0/original TypeError, no OpENer/result writes. PostSTOP3 allRun/Request/Cv_Run/Result/Done LOW. Zone/clearance/NG exit policy/AI-load lease remain blocked; no deployment or AI field cycle. Report: runs/engine_standalone_plc_autostart_001/v001_20261007T052746Z/tag_data_link_008/field_readiness_012/OPENER_AI_FIELD_READINESS_REPORT.md. Task012 investigation complete; no successor execution.

Latest 2026-10-13 AI_INTEGRATION_011 STOP_FOR_FIELD_APPROVAL: field-success communication010 extended via IPC into installed28d6 Runtime candidate engine-ai-opener-candidate-5f392085692d3385; event TypeError fixed. Native85 Python,19+10 C,26/24 prior protocol,11 AI protocol,11 guards,4 fixture Worker-Journal-assembly-IPC-UDP E2E and whole-package check-only PASS. No deployment/restart/PLC/EDS/model changes; operatingPID1082 original fault retained. field_profilefalse/Zone/clearance remain blocked. Report: runs/engine_standalone_plc_autostart_001/v001_20261007T052746Z/tag_data_link_008/ai_integration_011/OPENER_AI_INTEGRATION_REPORT.md. Next: field readiness + explicit whole-service/publication approval. Actual AI field cycle NOT_VERIFIED.

Latest 2026-10-13 OPENER-COMMUNICATION-010 COMPLETE: actual supervised one-product TEST_NG cycle PASS. PLC request -> C Result seq597 -> Done seq598 -> PLC Defect_Memory/Inspecting/Cycle_Done consumption -> requestOFF/Done reset/Sensor_Ready -> user-observed conveyor restart, then user STOP/actual stop. RX1171/TX1174,0timeout; sampled sensor rises4 but request/result/completion1 each. Synthetic only, no AI bridge. OpENer test stopped/no listeners; servicePID1082 enabled-active,125files unchanged, Explicit publicationfalse and original runtime TypeError preserved.414native evidence files SHAverified.19/26/24 tests and launcher8 PASS. Initial RX timeout root cause unresolved. TEST_PASS/repeated cycles/reboot/laptop-off NOT_RUN. Task scope complete; STOP, no successor work. Current run/tag_data_link_008/communication_trial_010/OPENER_COMMUNICATION_TRIAL_REPORT.md and CHECKPOINT.md. Do not revive old2B/V3 plans.

Latest 2026-10-13 PLC-first EDS correction: user rejected changing the PLC tag grouping to match Adapter. Six existing independent BOOL tag sets preserved, 2B each: Jetson_Done100, Jetson_Result101, Mc_Run150, Stop_PB155, EStop_OK157, Inspection_Request159. Prior grouped4/8 contract superseded (old binary did match its EDS; incompatibility was PLC configuration). Matching corrected EDS SHA1040da16... and native ARM64 SHAf7a43979... installed disarmed at envs/opener; old/new packages verified on notebook. 2 contract tests red then green; structural PASS; installed native6 simultaneous Class1 connections21unique responses each PASS in private loopback. Sysmac corrected import/field PLC connection/result bridge remain NOT_RUN/NOT_IMPLEMENTED. current103regularfiles/config/servicePID1078 preserved; no PLC writes/listener/autostart. Use corrected OPENER_SETUP_KO.md; do not merge tags or add32B arrays. Evidence: current run/tag_data_link_008/plc_tagset_correction/CORRECTION_REPORT.md. Next: user import corrected EDS and map6 same-name tagsets; bridge/one-writer/field-gated validation before activating I/O.

Latest 2026-10-13 OpENer installation: user authorized install + matching EDS. ARM64 OpENer 2.3 pinned d8820ef41ce30dda06d213438ba81c81de33ffe2 installed at /home/jetson/oned_device_bench/envs/opener (dependency, not replacement runtime). ENGINE_6BOOL_COMMISSIONING_DISARMED: Assembly150=8B controls,100=4B result/done,151=10B config; echo removed, Done always0 until bridge implemented. Exact EDS notebook/deployment/plc/Engine_Jetson_OpENer.eds SHA78c0a78c...; guide OPENER_SETUP_KO.md. Actual installed binary identity/lengths + isolated Class1 ForwardOpen/10UDP/ForwardClose PASS. No host listener/autostart; field PLC/Sysmac import NOT_RUN, inspection bridge NOT_IMPLEMENTED, PLC grouped BOOL packing unverified. Existing service1078 active/NRestarts0,103 regular files+config hashes preserved. No global package install/upgrade. PC package+15 evidence files hashes verified; own new build staging removed; old candidate cleanup remains paused. See run/tag_data_link_008/opener_install/INSTALL_REPORT.md. Next: native EDS registration and actual grouped tag layout, inspection bridge/one writer, then field-stopped connection verification; do not call full process complete.
Latest 2026-10-13 PLC source correction: selected file is now 비전검사 푸셔없는버전 3 .smc2, SHA256 9f491ee447dd5736858d07d2174a033a1654501b18f4c53fa641b4bf29b97806. Saved T#2.7s and192.168.50.3 CONFIRMED. Compared23rungs: only Move_Timer PT changed; Ethernet/FINS settings have5 leaf changes, listed in COMPARISON.json. Globals18/network6, local variables, IO map and Program0 task call unchanged. Previous saved-file timer/IP mismatch resolved by new file. Online full equivalence/native compile/cyclic I/O remain NOT_RUN. Filename v3 does not revive old STANDALONE_V3 contract. No PLC/runtime writes/service changes. Evidence: current run/tag_data_link_008/selected_plc_v3/{COMPARISON.json,PLC_BASELINE_REVIEW.md,VERIFICATION.json}. Use this selected source for EtherNet/IP I/O / Tag Data Link work; preserve previous snapshot and results.

Latest 2026-10-13 selected PLC source / CYCLIC_IO_TRANSITION_PENDING: user requires EtherNet/IP cyclic I/O / Tag Data Link and selected D:/머신러닝_학습자료/비전검사 푸셔없는버전 2 .smc2 (SHA256 86e9a78504946be1e22a0767fcb0dfdb53d2895e25eb837abc89ceff534a8fd3). Saved source: NX1P2-9024DT1 project v1.14; Program0 cyclic call; 18 BOOL, 23 rungs, 6 published signals. This source latches Move_pending, stops conveyor command during Inspecting and maintains Inspection_Request; obsolete sensor-direct-pulse assumptions must not drive automatic candidate adoption. Saved timer T#1s/IP192.168.250.1 differ from current user-confirmed timer2.7s and observed PLC IP192.168.50.3. Do not overwrite current field values with saved defaults; online PT/program equivalence NOT_RUN. At03:41:38Z six BOOL reads succeeded including Mc_Run/Stop_PB/EStop_OK; prior inaccessible-tags record is historical. Service enabled/active PID1078 NRestarts0; current transport LEGACY_THREE_BOOL explicit, publication disabled, no Adapter44818/2222 listeners. New cyclic adapter/EDS/connection NOT_IMPLEMENTED/NOT_RUN. No runtime/PLC/model writes or service restart. Evidence: current run/tag_data_link_008/PLC_BASELINE_REVIEW.md, PLC_BASELINE.json, JETSON_READONLY.json, VERIFICATION.json. Existing V3 and uninstalled pulse candidate are not current PLC apply instructions. Candidate cleanup remains user-paused. Next: concrete Adapter/EDS byte contract using these existing signals, then implementation/isolated verification and field-gated Sysmac connection; inspect STOP pending latch, missing timeout, REVIEW/ERROR and common PASS/NG restart limitations without silent PLC changes.

Latest 2026-10-13T02:00:59.408292+00:00: resilience whole runtime engine-dev-28d6e107b0f2a6c3 installed after operator belt-stop confirmation. Service enabled/active PID14688 NRestarts0;161 installed SHA, protected model/config unchanged; notebook predecessor166files+link verified. Bounded8 fresh frames: acquisition/loop/camera all alive. Report: current run/resilience_006/RESILIENCE_REPORT.md. Installed software109 native unique tests PASS; original helper spawn failure retained with focused PASS retry. No real PLC writes/motion/product-cycle test.
Latest user requirement: Inspection_Request is a brief sensor pulse, not a maintained inspection enable. Local PULSE_LATCHED candidate retains one token/arrival through OFF and ignores duplicate edges; PC120(119PASS/1Linuxskip), native11PASS. Candidate NOT_INSTALLED. Installed current still LEVEL_GUARDED; do not claim sensor-OFF continuation live. Existing MC_Run/Stop_PB/EStop_OK all unavailable(CIP_STATUS:0x4) in new read;3original tags readable. One pending user scope question permits only existing3control BOOL network-read publication, no new variables/contract. See PULSE_REQUEST_CHANGE.md. field_profile_verified=False, legacy_publication_enabled=False, old area/actual moving conveyor timing and PLC consumption remain unresolved. Do not rerun300/590/155, installer, reboot or tests without changed scope. Preserve prior evidence, no FORCE/stop bypass; retain current service diagnostic standby. Stage cleanup requires exact-path approval and remains pending.

Latest 2026-10-13 UI follow-up: operator confirmed belt stopped. Whole runtime engine-dev-937eb41d88a30038 applied; 161 hashes verified, only line_hmi.html/standalone_web.py changed. Actual /line shows 검사 대기중, separates preview/last actual result/PLC write state. PC17 and Jetson8 focused tests PASS; desktop1280/mobile390 no overflow or console errors. Models/config/PLC/control unchanged; service enabled/active PID13756, no autorestarts. WAIT_FIELD_PROFILE and writes-disabled remain, no actual PLC cycle tested. Prior TRACK_ASSOCIATION_OR_GAP_LOST preserved then recovered by normal stopped-service restart, root cause not fixed. See current run line_ui_005/UI_VERIFICATION.md. Continue FIRST_CYCLE_PRIORITY.md pending actual-chain work; do not repeat stationary/empty trials or revive historical V3 plans.

Latest 2026-10-13 returned-empty follow-up: operator removed engine. Fresh90 native frames all MATCH; existing1.2s ClearWindow UNKNOWN20/CLEAR70, first clear1.212s.18raw file/pixel SHA verified; references/config frozen, controls unchanged. Full diagnostic release engine-dev-f2f01ff684ad3566 installed,160hashes verified; service enabled/active PID8751,12new operating observations CLEAR. Protected models/PLC/settings unchanged. IMPORTANT: bootstrap retains self-observed-only real-PLC clearance gate, so frozen-reference signal is diagnostic only; area_clearance_enabled=false, WAIT_FIELD_PROFILE, publication disabled. Do not treat raw CLEAR as AUTO permission. Next: field readiness confirmation for empty belt limited physical-button motion/stop, then validate moved belt and full lifecycle. Do not repeat stationary placement/removal. See field_geometry_004/RETURNED_EMPTY_REPORT.md.

Latest 2026-10-13 occupied follow-up: operator placed one normal engine hands-off. Native90 fresh/18PNG file+pixel hashes verified; controls unchanged. Frozen empty-noise occupancy candidate added; PC48 (47pass/1skip), Jetson86PASS, saved36+synthetic11 parity0differences. Test counts: calibration9 excluded, empty holdout9MATCH, occupied18OCCUPIED. Candidate e55724dce60b9a0a NOT_DEPLOYED, candidate_area external replay only. Active6a7f2fbd30a8faa5 PID7519 enabled/active WAIT_FIELD_PROFILE/write-disabled. Next pending single action: remove engine from stopped belt for fresh departure test with frozen references. See current run/field_geometry_004/OCCUPIED_CANDIDATE_REPORT.md.

Latest 2026-10-13: duplicate-request fix installed as engine-dev-6a7f2fbd30a8faa5; service enabled/active,150hashes verified, native79PASS. Original PLC unchanged/writesdisabled. Per-product request-withdrawal hold replaces duplicate global fault; actual field trial NOT_RUN. Current horizontal belt mismatches old vertical inspection area; WAIT_FIELD_PROFILE remains. One pending action: engine removal from stopped belt for geometry check, keep camera/light. See current run legacy_duplicates_003/DUPLICATE_REQUEST_REPORT.md and CHECKPOINT.md.

Current Task: ENGINE-STANDALONE-PLC-AUTOSTART-001 — EXISTING_PLC_COMPATIBILITY_INSTALLED / FIELD_TRIAL_PENDING.
2026-10-07 latest authority: use existing PLC program, no new variables/download. Installed engine-dev-ba44311ba8b82041 selects existing Inspection_Request/Jetson_Result/Jetson_Done. Actual3-tag schema PASS; 150 file hashes match; service enabled/active PID6386, NRestarts0, camera frames advance and mandatory assembly READY. WAIT_PLC_SCHEMA resolved; WAIT_FIELD_PROFILE and result writes disabled pending field trial. Native70 tests PASS, no models/labels/threshold/PLC logic/FORCE changes. Initial port-probe startup failure restored predecessor; final Linux TIME_WAIT regression and actual startup PASS. See current run/EXISTING_PLC_COMPATIBILITY.md and legacy_compat_002/POST_UPDATE_VERIFICATION.json. User field-stop question pending; no motion/output trial. Prior V3 application instructions below are history, not the next action.
Latest UI access (2026-10-07): Sysmac permission/screenshot/activation PASS; harmless menu/tab inputs have no visible effect. Sysmac elevated=True; UIPI hypothesis unconfirmed. No PLC edits/download. See latest COMPUTER_USE_INPUT_CHECK and checkpoint.
Latest next step (2026-10-07): apply completed plc_apply_v3 snippets to a Sysmac offline working copy and Rebuild; native compile/download NOT_RUN. Do not repeat Computer Use recovery or Jetson installation. 22 tags/24 FB inputs/16 outputs/one cyclic call checked, 18 software tests PASS. User reboot changed boot ID; service auto-start/camera/models observed, PLC cycle/laptop-off remain unverified. See PLC_APPLICATION_REPORT.md and CHECKPOINT.md.
2026-10-07T06:28Z: full canonical engine-dev-780822e39a6316f3, 150 SHA matches; engine-inspector.service enabled/active, single owner, new camera frames and frozen assembly READY. Old cron removed. Installer stopped-server retry defect fixed (4 tests); actual authenticated installation PASS. HMI http://100.119.148.89:18771/line opened. PLC V3 missing -> WAIT_PLC_SCHEMA, no result publication; field profile false. No PLC download/motion/reboot/laptop-off test. Service retained in diagnostic wait. Latest run INSTALL_ACCEPTANCE/CHECKPOINT are authoritative; do not rerun installer or previous validations.
Run: D:\OneDevice_Team_project\runs\engine_standalone_plc_autostart_001\v001_20261007T052746Z
New user authority permits production integration, full runtime adoption, systemd and continued service; actual PLC download and motion still field-gated. Reuse prior inspector/PLC ACK evidence; do not restart completed validations.

Latest backup follow-up: named internal Sysmac project located;141files hash-verified. Latest saved ladder/globals match. Native SMC2 and online equality still UNVERIFIED. Evidence: D:/OneDevice_Team_project/releases/plc_online_backup_20261007/sysmac_saved_project_20261007T051145Z/SAVED_PROJECT_RETRIEVAL.json. No PLC writes.

Latest backup follow-up: supplied SMC2 is a2026-09-21 saved project, not a verified current online backup. Variables match; ladder rungs0/1 differ from today's saved snapshot. Byte-verified copy and comparison: releases/plc_online_backup_20261007/saved_reference_20261007T050708Z/. Await current controller-to-PC export; no PLC writes/download or inference rerun.

Latest: ENGINE-LINE-NO-PUSHER-COMMISSIONING-001 — V2_IMPLEMENTED / PARTIAL_WITH_REMAINING_FAILURES.
Updated 2026-10-07T05:01:38.933651+00:00. User approved extended7-tag contract. Whole local/staged candidate engine-dev-af4f9b2ff898f6de, PC73/native36 tests PASS; belt60 same semantics. New-request shadow initialization FAIL (3/3 REVIEW), actual PLC v2 schema NOT_READY. Current canonical untouched/AUTO STOPPED; writes/motion0. Online PLC backup requested; no download/adoption. Read latest task/CHECKPOINT and run/v2_candidate_001/AUTOMATION_COMPLETION_REPORT.md; do not repeat completed300/590/155 or native units.

Latest: ENGINE-LINE-NO-PUSHER-COMMISSIONING-001 / PROTOCOL_NG_001 synthetic NG receipt PASS (actual PLC tags + online ladder). Result=True retained; Done=False cleared; Request=False. AUTO STOPPED. No physical motion/real AI/sensor cycle test. No FORCE/pusher reset. Evidence: current run/protocol_ng_001/RESULT.json. Whole task IN_PROGRESS.

Latest commissioning update: fresh Sysmac save has revised rungs0/1 matching earlier online screen; I/O11 and other15rungs unchanged. Prior visual discrepancy resolved; full online equivalence, physical polarity and no-pusher handshake still pending. No PLC write/motion. See current CHECKPOINT.

Current Task: ENGINE-LINE-NO-PUSHER-COMMISSIONING-001 — READ_ONLY / I/O_AND_CONTROL_GATE_PENDING.
Run: runs/engine_line_no_pusher_commissioning_001/v001_20261007T025600Z
User changed scope to supervised no-pusher commissioning. Belt stopped and pusher/motor absent declared.
Existing Jetson AUTO admission stopped; camera retained, three BOOL reads false, PLC writes0.
Visible NG->Pusher_Request->conveyor inhibit requires contract review before result writes.
Conveyor occupancy candidate preserved locally, NOT_DEPLOYED; do not resume previous auto-arming work.
See current task/CHECKPOINT before next device action.

Timing request follow-up: bounded90.044s read-only monitor1795PLC samples,90Runtime snapshots. Request rising2/falling1, no Done/Result transitions, AUTO STOPPED90/90, PLC read errors0. E2E latency UNMEASURED; two requests NO_INSPECTION. User confirmed engines removed. Saved timing_001/TIMING_REPORT.md and raw observations. Pending explicit scope question: belt-specific occupancy/departure adaptation while preserving model/PLC semantics; no source/runtime modification yet. Do not request more product passes until arming gate is valid.

Reboot follow-up 2026-10-07T02:20Z: boot ID c5ce5f7e-b831-48ec-9523-347a599fa664; automatic boot1637/runtime2079/camera2485 already running. No duplicate start. Camera ready and PLC available. Laptop tunnel restored PID839576; existing scheduled tunnel supervisor retained. Browser /auto verified. AUTO STOPPED due same empty-area UNKNOWN; no bypass/config/model/PLC write. Source evidence: AUTO_STATUS_*.json, TUNNEL_RECOVERY_20261007T021944Z.json.

Current Task: ENGINE-CONVEYOR-HARDWARE-CHECK-001 — HMI_CAMERA_PLC_CONNECTED / AUTO_ARMING_BLOCKED.
Verified at 2026-10-07T02:02:15.699868+00:00. Run: runs/engine_conveyor_hardware_check_001/v001_20261007T015323Z
User explicitly requested existing automatic startup and /auto. This supersedes earlier
SIGSTOP-only authorization: device reboot replaced PID1752; current boot PID1829 already running.
Hub power restored by user; carrier/IP and three PLC BOOL reads PASS.
0-byte managed_runtime.json prevented startup; verified no active launcher, preserved PC hash
and remote corrupt copy, then existing boot regenerated receipt. No code/model/config change.
Current release engine-dev-745e95e832c6b402; runtime3772, camera3831; current frames170→1742.
Laptop tunnel scheduled task started. Browser actual video: http://127.0.0.1:18771/auto
AUTO operating=false/STOPPED, empty-area UNKNOWN: current belt geometry differs from fixed
black-mat geometry contract (left84/right1279/width1195; expected normalized bounds in source).
Do not force CLEAR or weaken gate to claim AUTO active. Need belt-compatible occupancy design
and verification before motion/handshake test; physical tests NOT_RUN.
Old defect task USER_STOPPED: A0 20=18PASS/2falseFAIL,120images verified,no defects executed.
Evidence and details: STARTUP_RESULT.md, CONFIGURATION_CHECK.json, PID_RECEIPT_RECOVERY.json,
AUTO_START_*.json and AUTO_STATUS_*.json. No PLC result write or conveyor command was issued here.
HMI 'conveyor disconnected' is a historical fixed label, not a current hardware measurement.

Latest Task: ENGINE-CONVEYOR-HARDWARE-CHECK-001 — READONLY_CHECK / WAITING_ETHERNET_LINK.
Run: runs/engine_conveyor_hardware_check_001/v001_20261007T015323Z
User stopped ENGINE-SHADOW-DEFECT-VALIDATION-004; A0 actual20=18PASS/2falseFAIL,
120 images recovered/verified, no defects run. See old run/USER_STOPPED.json.
Jetson current preserved. Boot PID1752 remains explicitly paused; no runtime or shadow active.
Ethernet enP8p1s0 NO-CARRIER, source192.168.50.2 absent; SSH is via Tailscale/Wi-Fi.
First action pending: reconnect/check Jetson-to-PLC Ethernet. No PLC writes/motor commands.
Do not revive old WAITING_OPERATOR_FRAMING or restart normal300/saved590/155.

Latest Task: ENGINE-SHADOW-DEFECT-VALIDATION-004 — IN_PROGRESS / WAITING_OPERATOR_FRAMING.
Run: runs/engine_shadow_defect_validation_004/v001_20261007T005012Z
Frozen actual static300 candidate761hashes matched; no300/590/155 rerun. Production114unchanged.
New trial tool local11/Jetson8 tests PASS. Camera live17724/PID165700, SETUP A0 actual0/20.
Three preflight REVIEW (body seed support insufficient); current engine lower than baseline,
lower shaft clipped. One request pending: move whole normal engine slightly UP, hands off.
See run/CHECKPOINT.md before any new action. No defect trial completed or production/PLC changes.

Latest Task: ENGINE-SHADOW-STATIC-ROBUSTNESS-003 — PASS / STOP.
Run: runs/engine_shadow_static_robustness_003/v001_20261006T082404Z
Actual300: {'PASS_CANDIDATE': 300}; falseFAIL=0, REVIEW=0, ERROR=0.
Unique300 and all image/probability evidence verified; shadow stopped and camera released.
Existing590parity/155regression reused, not rerun. No next physical scenario/production/PLC.
Report17727 remains available. Scope: current normal static ENGINE_01 only.

Latest Task: ENGINE-SHADOW-POSE-STABILITY-002 — OBSERVATIONS_COMPLETE / ACCEPTANCE_FAIL.
Run: runs/engine_shadow_pose_stability_002/v001_20261006T063346Z
Preserve prior robustness evidence. No classifier/threshold/label/production/PLC changes.
Saved275 PC/Jetson parity PASS; independent155 unchanged. New LIVE100:97PASS/1falseFAIL/2REVIEW. Rotation180:157PASS/1hand-present false defect/22REVIEW; final20PASS; Track reset. Shadow stopped; no adoption. Check run/CHECKPOINT.md.

Latest Task (2026-10-06, ENGINE-SHADOW-LIVE-ROBUSTNESS-001):

IN_PROGRESS / LIGHTING_DIAGNOSTIC_ONLY. Saved RIGHT20 REVIEW11→2/PASS9→18 using

reciprocal body matching with unchanged gates; CENTER20PASS, LEFT15falseFAIL unchanged.

PC/Jetson255 saved replay, original155 same-platform input/probability changes0,

151processed/4held/604classes maintained. Two glare-sensitive LEFT frames still have

PC/Jetson semantic differences; new classifier LIVE blocked. Camera-only17724 session002
expired normally at04:28:40UTC after bounded1800s;16599preview frames,0classifier inspections.
report17725. User '됬어' interpreted as lamp adjustment complete; saved LIGHT_ADJUSTMENT_001
04:02:40UTC is VALID/4CORRECT/PASS on PC and Jetson. One snapshot only, no LIVE matrix claim.
LEFT placement now confirmed. New20distinct saved camera frames under retained lighting:
PC/Jetson19PASS/1falseFAIL(exhaustREVERSED),80/80classes match. Pipes/symbol20CORRECT.
Failure12 accepted BASELINE pose jumps~7deg; same-raw adjacent-pose diagnostic restores
CORRECT, original error preserved. Further accepted-pose geometry diagnosis required;
no new human motion requested, no LIVE tracking/3-frame matrix completion or gate opening.
Report: lighting_left_stability_001/REPORT.html under current robustness run.
Preview session001 expired at its1800s limit; preserved logs/status and resumed camera-only
session002 at~12:58KST. Fresh frame IDs/PTS and browser status verified; no setting changes.
19 local tests PASS; staged replay18 tests. Protected2792PC/114Jetson intact except verified append-only tunnel log.

No production/PLC/retraining/adoption. New physical normal matrix/tracking NOT_RUN.

Resume: runs/engine_shadow_live_robustness_001/v001_20261006T025124Z/CHECKPOINT.md.



Latest normal position gate: CENTER20PASS;LEFT3PASS/15falseFAIL/2poseREVIEW;RIGHT9PASS/11poseREVIEW (5TOO_FEW_MATCHES,6QUALITY_REJECTED),threeframeRIGHT5PASS/15REVIEW. RIGHT26evidencefiles SHA recoveryPASS,20uniqueframes. Current session010 PID118445,settings/modelsunchanged. NORMAL_STABILITY_GATE_NOT_MET: do notautomatically advance missing/misassembly trials. Preserve original180boundaryfailures and repeatedtrackingLOST. Nextwork: report/diagnose frozen saved evidence; no thresholdrelaxation/retraining/production/PLC. Entire task incomplete.



LatestLEFT checkpoint: A_NORMAL_POSITION_LEFT_ON_00120actual distinctframes3PASS/15falseFAIL/2REVIEW;3frame20REVIEW. Leftpipe OUTWARD6/UPWARD5/CORRECT7/NOINPUT2;symbol UPSIDE10/MISSING5/CORRECT3/NOINPUT2;exhaust REVERSED1/CORRECT17/NOINPUT2;rightpipe18CORRECT/NOINPUT2.2pose rejections.107files SHA recoveryPASS. Actualraw/canonical/crops inspected;strongsymbolglare,2savedPASS symbolcropswashedout=>visibilityrisk,not defectfalsePASS(humanGTnormal). Models/config/thresholdunchanged. Session009 PID114967. NextnormalRIGHT only;defect gateNOT_MET. Fulltaskincomplete.



Latest positionCENTER checkpoint: A_NORMAL_POSITION_CENTER_ON_00120unique actual frames20PASS/all4CORRECT;3frame18PASS/2warmupREVIEW;39files SHA recoveryPASS;raw/canonical/4crops inspected. User CENTER is separate from measured boxcenter[0.5791087651252746, 0.5634471003214518]. Current session008 PID109285. Session007 movement LOST MISSED_OBSERVATION_LIMIT retained;continuous tracking not passed. Camera controls unchanged. Next one action: keep long shaftRIGHT and move engine slightlyLEFT,then A_NORMAL_POSITION_LEFT_ON_001. Full task incomplete.



Latest270deg checkpoint: A_NORMAL_270_ON_00120unique frames20PASS/all4CORRECT;3frame18PASS/2warmupREVIEW;39files SHA recoveryPASS;raw/canonical/4crops inspected. Current shadow session007 PID108066;006rotation LOST retained separately. LightON0/90/180reposition/270static windows20PASS each;original1802PASS18REVIEW retained,continuous rotation tracking NOT_PASS. No config/model/threshold changes. Next one human action: keep long shaftRIGHT,translate whole engine to screenCENTER,then A_NORMAL_POSITION_CENTER_ON_001. Position/defect/occlusion tests NOT_RUN. Full task incomplete.



Latest180deg reposition checkpoint: same session006/Track1,no restart,A_NORMAL_180_ON_REPOSITION_00120unique frames20PASS/all4CORRECT,3frame18PASS/2warmupREVIEW,preprocess20VALID.39files recovered SHA PASS. Original A_NORMAL_180_ON_0012PASS/18REVIEW preserved;left14/right15essential-boundary failures and scale variability remain unresolved. Settings/models unchanged. Next single action: long shaftRIGHT,shortLEFT,A_NORMAL_270_ON_001. Full task incomplete.



Latest180deg checkpoint: A_NORMAL_180_ON_00120actual distinct frames:2PASS/18REVIEW,threeframe20REVIEW;pipe_left14/20andpipe_right15/20crop failures ESSENTIAL_REGION_OUT_OF_SOURCE;exhaust/symbol20CORRECT. Original pipes visible;required region maxy742.11vs720source,scale0.9613to1.1815.82evidencefiles SHA recoveryPASS. Current session006 PID102544. No model/config/threshold change. Next user action: keep long shaftUP and move engine slightly UP(~30screenpx),then separate A_NORMAL_180_ON_REPOSITION_001;do not overwrite failure or advance as passed. Entire task incomplete.



Latest normal90deg checkpoint: A_NORMAL_90_ON_001 frozen20 actual distinct frames all4CORRECT/20PASS;3frame18PASS/2warmupREVIEW;pose/crop failure0. 39evidence files recovered SHA PASS. Session004 rotation tracking LOST AMBIGUOUS_ACTIVE_OBSERVATIONS retained as TRACKING_FAILURE; isolated session005 PID92655 recovered static inspection, not continuous rotation proof. Light/settings/models unchanged. Next human action: long shaft UP, short DOWN (A_NORMAL_180_ON); earlier180trial was before light ON, so current condition not tested. Full task incomplete. See ON_CURRENT_SETUP_progress.json.



Resume checkpoint 2026-10-06 ON_CURRENT_SETUP: A_NORMAL_0 reused from A_NORMAL_LIGHT_ON_001 (20 distinct frames,20PASS,three-frame18PASS/2warmupREVIEW); do not repeat. Session003 was RUNNING but persistent tracker LOST, no new inspection after01:21:55UTC; status/camera controls preserved, STOP then isolated shadow session004 PID89137 RUNNING/INSPECTION_READY verified. Tunnel569548 and report558876 retained, controls unchanged across restart (1280x720MJPG,gain4,WB4500,auto_exposure3,inactive exposure80). Camera auto exposure remains enabled, actual exposure stability not proven. Session003 full451observation log recovered and SHA verified;192 light-on frames allPASS. Earlier180 count was cumulative including comparison20, not180 additional distinct frames. Next action only: normal engine clockwise90degrees from long-shaft-down, long shaft screen-left; user confirmation required before declaring A_NORMAL_90_ON_001 acquisition. Unissued MOVE_LEFT NOT_RUN. See ON_CURRENT_SETUP_progress.json. No model/threshold/crop/alignment or production/PLC changes. Full task incomplete.



Latest live checkpoint 2026-10-06: session003, normal ZERO first20=1PASS/19falseFAIL(exhaustSIDEWAYS). Same two saved crops also misclassified by frozen model on PC. User then switched light on: first20=20PASS, 3-frame18PASS/2warmupREVIEW, all20distinct frame IDs/pixel hashes. Evidence39files recovered with SHA verification. Additional current log snapshot showed180light-on records allPASS; primary frozen comparison remains first20. No model/threshold changes. Lighting-associated improvement observed; causal isolation and defect discrimination NOT_RUN. A_NORMAL_MOVE_LEFT was never instructed: NOT_RUN. Entire SHADOW task IN_PROGRESS; production/PLC NOT_RUN. Next: confirm current session budget and preserve observations; continue one user physical scenario at a time under light-on.



Latest Task (2026-10-06, ENGINE-MISASSEMBLY-JETSON-SHADOW-001):

**OFFLINE_PARITY_PASS / LIVE_HUMAN_TEST_IN_PROGRESS.** First human-normal trial frozen56frames:53PASS/3falseFAIL(exhaustSIDEWAYS), three-frame45PASS/11REVIEW. Actual orientation180deg differs from requested0deg; waiting for user180deg rotation confirmation. Live session002 PID68536. Jetson representative39 and full155 replay PASS after explicit visual/numeric review:151valid,4REVIEW,604slot predictions match PC. Offline median274.86ms/p95 1247.00ms. Live40s camera smoke and browser verified; user declared A_NORMAL_CENTER and live_session_002 starting. Protected PC185/Jetson114 hashes unchanged. Production/PLC NOT_RUN, current release not replaced. Temporary integrated bench only. Detailed checkpoint and next exact action: tasks/ENGINE-MISASSEMBLY-JETSON-SHADOW-001.md. Reports: runs/engine_misassembly_jetson_shadow_001/v001_20261006T000509Z. Offline HTML17723, LIVE17724. Full task not complete.



Previous Task (2026-10-04, ENGINE-PREPROCESSING-RECOVERY-001):

**COMPLETE_WITH_RETAINED_FAILURES.** 기존4모델 동결, TRAIN694/VALIDATION155 전수 재처리/개발회귀평가 완료. VALIDATION110→151유효(35배경여백+6정렬 회복),4보류; TRAIN686유효/8보류. 기존110 crop/예측차이0,604유효부품오분류0. 원본919/보호파일3741해시 보존, 독립 산출물22검사·브라우저23검사·단위4검사 PASS. 새 비교HTML/보고서/소형ZIP: `runs/engine_preprocessing_recovery_001/v001_20261003T033452Z/`. 동일ENGINE_01/Codex라벨 개발회귀이며 독립시험·실제손가림·타엔진·Jetson지연 미검증. 보류V0066/V0100/V0118/V0130 유지. 재학습/운영교체/PLC/commit/push 없음. 스트림DNS/연결오류 자동복구 관측, 영구원인해결 미확정은 별도진단서. 후속통합 지시 전 정지.



Previous Task (2026-10-03, ENGINE-MISASSEMBLY-BASELINE-TRAINING-001):

후속 시각 보고서: 같은 실험 폴더의 `visual_report_v001/REPORT.html`에 검증 절차·155장 전수 사례·원본/정렬/실제 crop·정답/예측·혼동행렬/계산식·학습 추이를 연결했다. 현재 `http://127.0.0.1:17721/visual_report_v001/REPORT.html`, 재열기는 `OPEN_REPORT.cmd`. 실제 브라우저24개 검사(1440/390/360px·필터·행렬 연결·확대·키보드·인쇄 CSS) PASS, 콘솔0오류, 기존 근거14파일 해시 보존. 모델 재학습/라벨 수정 없음.

**LOCAL_BASELINE_EXECUTED / ARTIFACT_VERIFICATION_PASS / PREPROCESSING_FAILURES_REMAIN.** 기존 승인 TRAIN694/VALIDATION155 고정, 원본919·metadata/label39파일 SHA 보존. TRAIN-only 본체 기준·고정영역·224 padding을 구현해 TRAIN602전체유효/63부분/29정렬실패, VALIDATION110전체유효/35부분/10정렬실패를 기록했다. RTX5070 Laptop 기존 환경에서 대표 smoke2 epoch 후 yolo11n-cls 독립 시작4모델 순차 본 학습(11/12/23/11 epoch)과 재로딩/별도 검증 실행. 유효 학습 crop655/612/665/665, 검증132/123/145/145; 각 macro F1=1.000 및 오분류0은 성공 crop에 한정된다. 전체155개 네부품 처리율110/155=71.0%, 분류기만의 simulation 정상11/불량99/판정불가45, 불량 전부정상 오인0/99. 원본/파생3142해시·620예측·분할/라벨/계보·실제 클래스 매핑·전처리 텐서·지표 재계산 PASS. 결과 `runs/engine_misassembly_baseline_training_001/v001_20261002T191929Z/TRAINING_SUMMARY.md`, 검증/모델/crop/manifest 및 `BASELINE_REVIEW_PACKAGE_v2.zip`. 동일ENGINE_01·Codex라벨/개발검증 한계, 전처리 실패는 남아 있다. 보류43건 재승인 없음. Jetson/PLC/운영코드/commit/push 미실행, 이번 단계에서 종료.



이전 작업 (2026-10-02, ENGINE-MISASSEMBLY-LABELING-001):

후속 (2026-10-03): 사진과 실제 부품별 상태 라벨을 함께 보는 읽기 전용 뷰어를 추가하고 열었다. `data/guided_capture_20261001/OPEN_LABELING_VIEWER.cmd` 실행 또는 현재 `http://127.0.0.1:17719/`. 표시919건 manifest 일치, 대표 원본4개 hash, 실제 브라우저 예시/필터/검색/확대/390px 폭 검증 PASS. 상태 분류 라벨이며 bbox/segmentation은 미실행이고 YOLO 검출용 박스 정답이 아님을 명시. 기존 라벨·후보·원본 변경 없음.



**VISUAL_REVIEW_COMPLETE / STRUCTURAL_VERIFICATION_PASS / HUMAN_HOLDS_REMAIN.** `data/guided_capture_20261001` 원본 919장(PILOT7/TRAIN733/VALIDATION179), 부품3,676슬롯을 실제 열람·기록했다. capture APPROVED876/NEEDS_REVIEW43/NEEDS_RECAPTURE0; 심볼 판독 보류29·선언 충돌13·전체 프레이밍1을 억지 승인하지 않았다. 활성885개 native part_review append와 재개 대조 PASS, 대체본34개는 별도 검토 로그에 보존. 전달PNG919개 동일/별도 샘플0, 원본 동일 SHA 중복0, split 간 raw/group/round/lineage 교집합0. 필수7산출물 및 독립 검증9개 PASS(exit0). 학습 후보는 `export_train_candidates.jsonl` 694행, `export_validation_candidates.jsonl` 155행이며 PILOT0. 활성 V0107 선언 충돌과 심볼 보류는 사람 확인 필요. 동일 ENGINE_01 기반이며 독립 사람 정답 대조·다른 엔진 일반화·학습 성능은 미검증. 원본/선언/계보 보존, 학습·Jetson·PLC·PASS/FAIL 로직 변경 없음. 상세: `tasks/ENGINE-MISASSEMBLY-LABELING-001.md`, 데이터 루트의 `LABELING_SUMMARY.md` / `LABELING_VERIFICATION.md`.



이전 작업 (2026-10-02, ENGINE-GUIDED-CAPTURE-AND-HANDOFF-001):

Drive 업로드 경로 후속 수정: 사용자가 전체 전달 폴더 업로드 중 PNG '파일을 찾을 수 없음'을 보고했다. 원래 raw 경로273~278자는 일반 open 실패, extended-path 읽기 성공을 재현했다. `D:/EngineUpload_20261002_155533`에 동일 상대경로/파일명/내용의 전체 사본975파일을 생성, 일반 경로198~203자에서 모든 파일 hash/size/read PASS 및 원래 payload 전후 동일 확인. 추가 UPLOAD_VERIFIED.json 포함976파일, 원본912장/활성879장/NOT_REVIEWED 유지. 실제 Drive 업로드/ChatGPT 열람은 NOT_RUN. `drive-upload-result.json` 참조.



후속 직접 첨부 준비: 상대 ChatGPT의 ZIP 도구 오류/원본 미열람 보고에 따라 `dist/engine_labeling_handoff/direct_upload_12_20261002_145934`에 TRAIN12장(14.5MB)과 원본 manifest 발췌/파일 대응/안내를 생성했다. 파일명·해시·크기·decode·manifest12행 PASS, 촬영 원본/이전 ZIP/라벨 변경 없음. 기존 세부 상태 유지, NOT_REVIEWED. 상대 대화의 실제 열람 성공 및 라벨 검토는 미실행. `direct-upload-result.json` 참조.



**RAW_CAPTURE_HANDOFF_READY.** TRAIN723/VALIDATION156 활성, 총879 활성/912 보존/33 재촬영 대체/누락0. 실제 EXE의 개발검증156/156 및 전체 전달 생성 확인. 모든 원본·계획·원장·계보·교차 split 검사와 전체 ZIP975members/나눔 ZIP3개 전체 SHA-256·size·CRC 검증 PASS. 미검토3516부품 슬롯 유지. 최종 `dist/engine_labeling_handoff/20261002_135609/Engine_Misassembly_Labeling_Handoff.zip` (1,134,785,330bytes; SHA256 `b87cb3eb869aa04da06a3c658b2f615d5158c30150677c2fe2b07ee9b6d98f8d`). 같은 폴더의 HANDOFF_VERIFICATION, 풀린 폴더의 START_HERE 참조. 동일 엔진의 촬영자 재조립 선언 기반 개발검증이며 다른 엔진 일반화/정답 승인/학습 준비 완료 아님. 프로그램/검사 소스 변경·학습·Jetson·PLC·commit/push 없이 종료. Task와 `final-handoff-result.json`에 실제 경로/한계/검증 명령 기록.



이전 진행 (2026-10-02 본 촬영 완료/개발검증 준비):

**2026-10-02 TRAIN_CAPTURE_AND_FULL_HANDOFF_VERIFIED / VALIDATION_PREPARED.** TRAIN723 활성/733 보존/10 대체/누락0, 13시나리오 수량 및 모든 원본·전달본 무결성/계보/재개 검사 PASS. 미검토 유지. 전체 전달 `MEB3977C06A9E4CF2/전달_C3FB3745`. 사용자 실제 정상복원·재조립 완료 선언을 받아 별도 VALIDATION156 수집 `MAE5A0BF948244C27`을 생성·설정하고 EXE를 열었다. 새 정상 창은 OS에서 확인, GUI 관측 도구 timeout으로 재기동 후 영상 직접 확인 UNVERIFIED. 사용자 검증 촬영 및 최종 인계 ZIP 대기. `train-audit.json`/`validation-prepared.json`/Task 참조.



이전 진행:

**PILOT_CAPTURE_AND_FULL_HANDOFF_PASS / MAIN_TRAIN_PREPARED.** 실제 파일럿6단계/활성6/재촬영 이전1 보존 확인. 앱의 전체 전달 생성, 원본7장 해시·크기·디코드·상대경로·계획/선언/그룹·재개/재촬영 검사 PASS; 원본/기록 검사 전후 동일, NOT_REVIEWED 유지. 기존 기능으로 TRAIN723장 새 수집 `MEB3977C06A9E4CF2`를 설정하고 EXE를 다시 열었다. 정상0° 창 제목 확인; 재기동 후 GUI 관측 도구 timeout으로 현재 영상 직접 확인은 미완료. 사용자 본 촬영/VALIDATION/최종 ZIP 대기. 근거: `runs/engine_guided_capture_and_handoff_001/pilot-audit.json`, `train-prepared.json` 및 Task.



초기 준비 기록:

**INITIAL_SETUP_PREPARED / ACTUAL_PILOT_CAPTURE_PENDING.** 다운로드의 지정 문서 전체 확인, 최신 20261001_133611 EXE/ZIP 및48개 입력 hash 대조. 사용자 확인 환경(동일 엔진1대, 상부 카메라1/조명1, 검정 배경, 거리 미측정)에 따라 기존 API로 미검토6장 파일럿을 준비하고 기존 앱 설정을 백업·적용해 실행했다. source 변경/셔터 입력/실제 재조립 선언 없음. 실제 함수의 TRAIN723/VALIDATION156 계획 preview 검증; 본 촬영은 파일럿 저장·재개·재촬영·전체 전달 확인 뒤 준비한다. 최종 원본 인계 ZIP은 촬영 후 생성하며 현재 미완료. 상세: `tasks/ENGINE-GUIDED-CAPTURE-AND-HANDOFF-001.md`.



Latest Task (2026-10-01, ENGINE-MISASSEMBLY-CAPTURE-DATA-READINESS-001):

**COMPLETE / WINDOWS_EXE_SOFTWARE_PASS / CAMERA_PREVIEW_PASS.** 기존 간편 촬영과13개 시나리오/654·723계획을 유지하며 실제 재조립 회차 선언/회차 split 그룹, 별도 부품 검토 이력, 목적별 검토 후보 export,6장 파일럿/추가 회차를 구현했다. source80 tests 및 마지막 readiness17 재실행 PASS. source/ZIP 추출 EXE 각각 self-test8·기존 GUI11(13시나리오)·readiness GUI4 PASS. 실제 DSHOW 후보1의1280×720 최신40프레임 수신, 원본 저장0; 실물 정답/팀원 PC NOT_RUN. 새 ZIP `dist/engine_misassembly_capture/20261001_133611/Engine_Misassembly_Capture.zip` (81,688,704 bytes, SHA-256 `6720a0b54a018d567ffe733840980a1b935d3f6771b9bb2bf56fa5d6a8880605`), 새 BUILD_INFO/VERIFICATION/해시와 한국어 파일럿 안내 포함. 기존 원본/계획/승인 보존, commit/push 및 모델/Jetson/PLC/본 촬영 없음. 상세: `tasks/ENGINE-MISASSEMBLY-CAPTURE-DATA-READINESS-001.md`. 요청 범위 완료 후 중지.



Latest Task (2026-09-30, ENGINE-MISASSEMBLY-CAPTURE-001 전체 시나리오 안내 감사):

**WINDOWS_EXE_ALL_SCENARIO_AUDIT_PASS / TEAMMATE_PC_NOT_RUN.** 정상1/결품5/오조립7의 추가654·신규723단계를 대조하고, 제목·준비 상태·유지 부품·예시 파일·저장 part_states 연결을 통일했다. 현재 촬영과 목록 미리보기, 최근 저장 당시 시나리오를 구분하며 엔진 전체 회전각임을 명시한다. 체크박스0/촬영 입력1회 유지. 소스26건·최종 안내4건, source/최종 추출 EXE GUI 각11항목(13시나리오 선택/예시/실제 sample 저장 대조 포함) PASS. 초기 작은 창 공간 실패를 조정해 재통과했으며 기존 계획/승인/원본을 보존했다. ZIP CRC/1101파일/44입력 hash PASS: `dist/engine_misassembly_capture/20260930_130331/Engine_Misassembly_Capture.zip` (81,584,071 bytes, SHA-256 `8a47fe8a9fb63ebe1384e3320dbde9e953b536f5fb350040526051770c8674ce`). 요청한 LEFT_PIPE_UP을 기존 API로 선택하고 새 EXE 실행; 기존34건 유지/새 촬영0/계획hash 동일. 실물 오조립 저장·팀원 PC NOT_RUN. 상세: `tasks/ENGINE-MISASSEMBLY-CAPTURE-001.md`.



후속 실제 창 관측: 새 EXE의 `[오조립] 왼쪽 파이프 위로 돌아감`/엔진0° 안내, DSHOW 후보1의1280×720 영상, 저장34/654를 직접 확인했다. 현재 목표와 아래 `최근 저장: [결품]`을 구분한다. `scenario-live-left-pipe-up.png`; 실제 셔터/부품 정답 검증은 수행하지 않았다.



Latest Task (2026-09-30, ENGINE-MISASSEMBLY-CAPTURE-001 시나리오/사진 선택 및 촬영 지연):

**WINDOWS_EXE_SCENARIO_GALLERY_VERIFIED / PHYSICAL_CAMERA_THIS_BUILD_NOT_RUN.** 전체 시나리오·각도별 저장 사진 보기, 우선 시나리오 선택, 완료 사진 선택 재촬영을 구현했다. 선택 순서를 재개하며 새 저장 성공 후 이전 사진 대체/원본 보존/완료 수 무증가를 확인했다. 매 촬영마다 이전 PNG 전체를 디코드하던 지연을 새 원본 검증으로 분리하고 전체 재개/전달 검증은 유지했다. 동일 합성 1280×720 저장 비교(mode별 warm-up1/측정3) 중앙값 10.011→0.265초; 카메라/안정 대기 제외이며 실물 지연 보장 아님. 소스 22+29건, source/최종 추출 EXE GUI 각 10항목, 구형 수집 복사본 재개, ZIP CRC/1101파일/44개 입력 hash PASS. 첫 frozen 화면 캡처 실패는 보존하고 동일 EXE 재시험으로 통과했다. 전달: `dist/engine_misassembly_capture/20260930_121329/Engine_Misassembly_Capture.zip` (81,575,865 bytes, SHA-256 `8afcd074b6adfb586666e4d18058f25cddbe2bc6a6225c994a8d1858e2d51b70`). 실제 구버전 34장 상태/지연은 읽기 전용 확인, 사용자 카메라 추가 열기·촬영 원본 변경 없음. 새 실제 카메라·실물 촬영·팀원 PC NOT_RUN. 상세: `tasks/ENGINE-MISASSEMBLY-CAPTURE-001.md`.



Latest Task (2026-09-30, GITHUB-DEPLOYMENT-001):

**PUBLISHED / CHECKOUT_VERIFIED / FRESH_HARDWARE_UNVERIFIED.** 현재 TensorRT 모델 두 개와 Pose·기동 자산을 `jetson/products`에 포함하고, 자체 포함 목록/패키징·새 장치 설치기, Windows 환경 설치/간편 촬영 바로가기와 발표 README를 정리했다. Git export의 깨끗한 소스에서 Windows 68건·Linux 배포 25건·최종 설치 5건 PASS. 새 Windows venv의 pip check·GUI 5건 PASS. 공개 master 구현 `ce49b15`의 로컬/원격 SHA 일치 및 GitHub 모델 바이너리 크기를 확인했고 GitHub Actions 36658234340 SUCCESS. 실제 Jetson/PLC 변경 없음. 새로운 Orin·다른 노트북의 실물 수용은 UNVERIFIED. 동시 진행 중인 촬영 앱 추가 수정은 검증 snapshot 이후 변경으로 보존한다. 상세: `tasks/GITHUB-DEPLOYMENT-001.md`, `docs/verification/GITHUB-DEPLOYMENT-001.json`.



Latest Task (2026-09-30, ENGINE-MISASSEMBLY-CAPTURE-001 기존 자료 연결):

**WINDOWS_EXE_DATASET_EXTENSION_VERIFIED / PHYSICAL_CAMERA_THIS_BUILD_NOT_RUN.** 사용자 정정에 따라 추가 촬영은 기존 라벨링 `source_index.json` 또는 수집 `collection.json` 선택으로 시작한다. 제작 시 감사한 기준 fingerprint를 식별하고 기존 자료 아래 `additional-captures/collections`에 새 원본과 기준 ID 연결을 저장한다. 추가 654장과 전체 새 촬영 723장(새 빈 폴더)을 구분하며, 원래 파일/라벨/승인·원래 수집 계획은 보존한다. 집중 source 13건, source/frozen GUI 각 8항목, 실제 기준 파일 3종 읽기 전용 식별, ZIP CRC/1101파일 내용/43개 입력 hash PASS. 새 ZIP: `dist/engine_misassembly_capture/20260930_110650/Engine_Misassembly_Capture.zip` (81,562,553 bytes, SHA-256 `564c9606e66d1976d3364c61e67d13ca35593f694582dcf617ab91a9c56ffe7d`). 이번 실카메라·실물 엔진·팀원 PC NOT_RUN; 카메라 코드는 이전 physical PASS 빌드와 hash 동일. 상세: `tasks/ENGINE-MISASSEMBLY-CAPTURE-001.md`.



Latest Task (2026-09-30, ENGINE-MISASSEMBLY-CAPTURE-001 사용성/카메라 회귀 수정):

**WINDOWS_FROZEN_UI_AND_HCAM_PREVIEW_VERIFIED / TEAMMATE_PC_NOT_RUN.** 기존 큰 영상·정렬/360° 안내를 복원하고 TRAIN의 실제 ROI를 재사용했으며 꼬리 여유만 추가했다. 10° 새 오조립 504 + 기존 정상/결품 부족 각도 144 + 장치 정상 대조 6 = 654장 계획. 한 클릭 촬영, 준비/저장 중 단계 고정, 자동 다음 안내, 재촬영/재개 유지. EXE 시작 준비가 카메라 첫 영상 15초 한도를 소비하던 원인을 계측하고 준비(30초)/장치 첫 영상(15초) 대기를 분리했다. 저장 준비 후 새 프레임 선택으로 느린 파일 준비의 stale 실패도 수정했다. 집중 source 46건, source writer 8항목, 최종 추출 EXE GUI 7항목, 실제 HCAM01L로 열거된 DSHOW 후보 1의 1280×720 fresh 40프레임 PASS. 최종 ZIP CRC/상대경로/1100파일/41개 빌드 입력 해시 PASS. 전달: `dist/engine_misassembly_capture/20260930_102438/Engine_Misassembly_Capture.zip` (81,552,250 bytes, SHA-256 `a90ac39174d00f19be0c18d7c9182138c54eb97a741803be84fa104a4dce13bf`). 실물 엔진 원본 저장·팀원 PC·후속 검토/학습은 NOT_RUN. 이전 실패/원본/승인 보존, Jetson/PLC 변경 없음. 상세: `tasks/ENGINE-MISASSEMBLY-CAPTURE-001.md`.



Latest Task (2026-09-29, ENGINE-MISASSEMBLY-CAPTURE-001):

**PACKAGE_BUILT_AND_WINDOWS_SYNTHETIC_VERIFIED / PHYSICAL_CAMERA_NOT_RUN.** 기존 `notebook/training/capture_windows`에 클릭 선언과 저장 완료를 분리한 간편 촬영 정책, 상태별 54장 파일럿 계획, 학습용 NORMAL 출처 사진 및 복합 오조립 사진의 부품 부분 안내, Windows 독립 EXE/전달 ZIP을 추가했다. 기존 Wizard/촬영 회귀 47건과 소스 합성 점검, 추출 EXE 자가점검 8항목, ZIP CRC/입력 해시 PASS. 실제 USB 카메라 촬영·팀원 PC 조작·후속 라벨 검토/학습은 NOT_RUN. 배포: `dist/engine_misassembly_capture/20260929_173939/Engine_Misassembly_Capture.zip`; 상세: `tasks/ENGINE-MISASSEMBLY-CAPTURE-001.md`. 기존 수집 원본·승인 기록·Jetson/PLC 변경 없음.



Latest Task (2026-09-29, ENGINE-CONVEYOR-MOTION-001, PLC 상시 AUTO 종료 체크포인트):

**PARTIAL_BLOCKED / 컨베이어 입고 후 재개.** Jetson `current`는 `engine-dev-745e95e832c6b402`, 실제 PLC 이동 벤치 설정, 물리 출력 비활성이다. 직전 릴리스의 실제 재부팅에서 `@reboot` AUTO·HCAM·PLC ARMED 확인, 최신 릴리스는 부팅 코드 변경 없이 managed 배포 후 같은 `boot_live.py`로 AUTO 재가동. 노트북 `/auto` 터널 예약 작업의 배터리 중단 설정을 수정하고 HTTP 200·화면 복구 확인. 최신 실물 요청은 Track 1→고유 3프레임→durable REVIEW→PLC Result=1/Done=1 ACK→Request OFF/Done=0까지 확인했으나 제품 이동이 440ms 수집 구간에 없었다. Sysmac의 Result=0 표시와 PLC 직접 CIP Result=1 읽기가 불일치한다. 빈 Live에서도 작업면 우측 상단을 OCCUPIED로 오인해 Track 1 자동 종료가 막혀 있다. 관련 42개 시험 통과; 실제 이동 PASS·연속 제품·실제 컨베이어·PLC 프로그램의 내부 결과 사용은 미검증. 상세: `tasks/ENGINE-CONVEYOR-MOTION-001.md`.



Latest Task (2026-09-29, ENGINE-CONVEYOR-MOTION-001, PLC 상시 AUTO 후속):

Jetson `current`에 `engine-dev-92ea335890a447e0`과 명시적 `CONVEYOR_MOTION_PLC_BENCH`/`OMRON_CIP_BENCH` 설정을 적용했다. PLC가 꺼져도 빈 화면·정상 카메라에서 AUTO 추적을 시작하며, 유효한 Request=0 확인 후 요청 상승 시 같은 Track/Cycle을 고정해 이동 3프레임 검사를 시작한다. PC 관련 40개 테스트·기존 이동 저장 사례 PASS/REVIEW 보존·Jetson 실행 릴리스/단일 카메라 Worker/AUTO·PLC ARMED·Request=0 확인. 실제 재부팅과 새 릴리스에서 실물 요청→Result/Done 검증은 진행 중이다. 물리 출력은 비활성이고 실제 컨베이어·포토센서·배출은 미시험. 상세: `tasks/ENGINE-CONVEYOR-MOTION-001.md`.



Latest Task (2026-09-29, ENGINE-CONVEYOR-MOTION-001, 전체 시야 후속):

이동 MOCK Capture 영역을 전체 시야로 설정하고 같은 `engine-dev-76fbafd5473fd110`을 Jetson `current`에 적용했다(설정 SHA `661e22f9...abfd`). 합성 경계 잘림 거부·저장된 이동 REVIEW/PASS 보존·관련 10개 테스트 통과. 사용자 손 이동 1회에서 Track 1, 자동 요청, 고유 3프레임 PASS, MOCK ACK/Request OFF, 완전 이탈 뒤 자동 종료 및 다음 제품 대기 확인. 원본에 손이 있고 세 프레임 중심은 종전 영역 안에도 있었으므로 확장된 가장자리와 실제 벨트는 미검증. 관측 약 12 FPS이며 FPS 향상은 이번 설정 변경으로 달성되지 않았다. 증거: `tasks/ENGINE-CONVEYOR-MOTION-001.md`, `archives/jetson/engine-conveyor-motion-001/full-view-motion-inspection.json`.



Latest Task (2026-09-29, ENGINE-CONVEYOR-MOTION-001):

MOVING_BENCH_SOFTWARE_READY — 이동 자율 시험 Track 4에서 3초 frame 수집 deadline과 서비스 취소가 경합해 durable REVIEW 대신 `DEADLINE_EXCEEDED` FAULT가 발생했다. 실패 원본/상태를 노트북에 보존했다. 이동 모드에서만 수집 deadline(3초)과 결과 저장 대기(기존 검사 제한 15초)를 분리한 `engine-dev-76fbafd5473fd110`을 Jetson `current`에 적용하고 관련 36개 시험 통과. 수정 후 HCAM 이동 1회에서 unstable 고유 3프레임 PASS, MOCK durable Result/Done·ACK·Request OFF, 엔진 제거 후 Track 1 자동 종료와 다음 제품 대기 확인. 저장 원본에는 손이 보인다. 프레임 부족의 수정 분기는 focused 재현 시험으로 검증했고 실물 재발 시험은 하지 않았다. 이전 STATIONARY PASS와 이동 Track 2 PASS는 이전 릴리스 `engine-dev-bfb708658d0768f6`의 결과다. 실제 컨베이어·PLC는 미검증이며 기존 전체 회귀는 무관한 earbud fixture 6건 누락으로 미완료. Task/증거: tasks/ENGINE-CONVEYOR-MOTION-001.md, archives/jetson/engine-conveyor-motion-001/.



Latest Task (2026-09-16, JETSON-P0-004B):

DONE / BACKEND_CONTRACT_IMPLEMENTED_CANDIDATE_ONLY — P003 exact32 SHA baseline에서 새 Windows candidate만3수정+factory1추가. Legacy PyTorch/default/명시backend·schema2 TRT 선언·neutral metadata/Worker 연결 검증. TRT는 NOT_IMPLEMENTED, fallback/import/read0; schema-valid는 실행승인 아님. 기존114 regression semantics(원본 tests 보존, task-local mock1개 확장/기존 assert 동일)+새28 PASS, skip0/candidate import origins 확인. DetectionResult/PyTorch 기존 methods 불변, root/P003/P004A/package/DB/assets/PC mirror/Jetson37그룹 SHA 동일. GPU/camera/export/build/deploy0, HEAD/git diff --check PASS, commit·push0. Export/precision/NMS 미정·parser/plugins UNKNOWN/tolerance TBD, ROOT_CAUSE_UNCONFIRMED 유지. P004C 별도승인 전 NOT_STARTED. Report: docs/jetson/JETSON_TRT_BACKEND_CONTRACT.md; Evidence: docs/verification/JETSON-P0-004B.json.



Latest Task (2026-09-16, JETSON-P0-004A):

DONE / PREFLIGHT_COMPLETE_IMPLEMENTATION_NOT_AUTHORIZED — 지정 ChatGPT 대화와 협의한 읽기 전용 TRT 준비 점검. Detector/factory/package/health 경계와 legacy 호환 방향, installed exporter/reader/container/profile/자동 설치 경로, provenance/parity 계약을 정리했다. TRT10.3/ONNX1.22/ORT1.23.2/trtexec 파일 관측, simplify=True의 onnxslim 조건부 부재. 기존 ONNX SHA 동일하나 parity NOT_RUN; export/NMS/loader DECISION_PENDING, precision 승인 NONE/tolerance TBD. SSH2회 metadata/source/hash만, framework import/GPU/camera/export/build0, Jetson 새 파일0, 보호36그룹+overlay/current/로컬462파일 변경0. P003 Runtime/raw FROZEN 유지. 구현 B~F는 별도 초안/NOT_STARTED, 원인 UNCONFIRMED/production 미수용, commit·push0. Task: tasks/JETSON-P0-004A.md; Report: docs/jetson/JETSON_TRT_READINESS_PREFLIGHT.md; Evidence: docs/verification/JETSON-P0-004A.json.



Latest Task (2026-09-16, JETSON-P0-003):

DONE / LATENCY_INSTRUMENTATION_VERIFIED_LAB — R4 결과를 지정 ChatGPT 대화에 공유하고 사용자 계속 진행 요청 범위에서 candidate-only 계측 검증 완료. 새 R2 exact-copy Candidate의 Detector1파일만 optional metadata 추가, root runtime 변경0. 기존102+timing12=114 tests/collector selftest PASS. PID21354 단일 process19.837초, warmup1/warm10cycles/30observations, DB COMPLETE10/REVIEW10/publication10/late0/raw30+overlay10 SHA PASS. NvMap/NVML/allocator/Python/CUDA exception/epoch 변화/invalid selection0. monotonic_ns/기존 sync만 사용(추가0), H2D null·Ultralytics reported timing 별도. host detect p5054.075/p9591.272ms(n30), trigger→durable p50717.406/p95801.362ms(n10), production threshold NOT_DEFINED. 보호36그룹/overlay/current/Windows source/PC mirror/이전 evidence SHA 동일. ROOT_CAUSE_UNCONFIRMED/Conveyor NOT_RUN/commit·push0. P0-004/TRT 자동 착수 없음. Task: tasks/JETSON-P0-003.md; Report: docs/jetson/JETSON_LATENCY_INSTRUMENTATION.md; Evidence: docs/verification/JETSON-P0-003.json.



Latest Task (2026-09-16, JETSON-P0-002R4):

DONE / LONG_LIVED_RUNTIME_STABILITY_PASS_LAB — 단일 PID20883에서 Camera/Detector/CUDA/Journal/session 각1회 초기화 후30/30 full cycles, warmup1/fresh detect90, raw90/overlay30 SHA·ID 연결 PASS. SQLite integrity ok/COMPLETE30/publication30/late0, stderr·Python/CUDA exception·epoch 변화·invalid fresh selection0. process35.803초의30-cycle lab gate이며 endurance/production/root cause resolved가 아니다. MemAvailable2,179,752→2,177,436kB, CUDA allocated12,142,592→12,142,080B/reserved60,817,408B 동일. 원본34그룹/overlay/current/Windows source/PC mirror/이전 evidence SHA 동일, runtime source/환경/시스템/PLC/MQTT/commit·push 변경0. P0_003_ACTUAL_DEVICE_READY=true는 latency instrumentation 시작 한정; ROOT_CAUSE_UNCONFIRMED. Task: tasks/JETSON-P0-002R4.md; Report: docs/jetson/JETSON_LONG_LIVED_RUNTIME_SOAK.md; Evidence: docs/verification/JETSON-P0-002R4.json.



Latest Task (2026-09-16, JETSON-P0-002R3):

DONE / NVMAP_NOT_REPRODUCED_IN_BOUNDED_STAIRCASE — A~H 각1회+H 추가5회, 새 process13개 모두 stderr clean/exit0. Parent 실시간 pipe 수신 monotonic과 Child stage/memory456개, close/BEFORE_PROCESS_EXIT 이후 teardown까지 수집. warmup11/fresh detect28회, Recipe/encode/diagnostic Journal 추가 조합에도 NvMap/NVML/allocator 문자열0·Python exception0. 최초 발생 Case/interval과 직전 memory는 N/A, ROOT_CAUSE_UNCONFIRMED 유지. 계측 타이밍 영향·과거 오류 미해결을 명시하며 P0-003 BLOCKED. 보호33그룹/overlay/current 및 Windows source/PC mirror/이전 evidence SHA 동일. 새 파일은 diagnostics/p0_002r3_nvmap 안에만 생성; source/환경/camera 설정/PLC/MQTT/commit/push0. Task: tasks/JETSON-P0-002R3.md; Report: docs/jetson/JETSON_NVMAP_STAGE_DIAGNOSIS.md; Evidence: docs/verification/JETSON-P0-002R3.json.



Latest Task (2026-09-16, JETSON-P0-002R2):

DONE / REACCEPTANCE_PARTIAL_RUNTIME_ERROR_REPRODUCED — 통합 cold process10/10 PASS(카메라 열린 상태 Detector 전후5프레임, stderr0), 실제 LOCAL_TEST Fresh Frame10/10 PASS/잘못 선택0. 모델 cycle은 Recipe3프레임·REVIEW·raw3/overlay1 SHA·candidate SQLite commit 후 local publish까지 기능 PASS했지만 stderr NvMap error12 재현으로 D runtime 수용 FAIL. NVML assertion/예외 종료 없음, 정확한 출력 단계·물리 원인은 미확정. 오류 확인 후 추가 GPU 재실행·복구0. A 기존102 tests 유지(source 변경0/재실행 안 함), E conveyor NOT_RUN, P0-003_ACTUAL_DEVICE_READY=false/BLOCKED. app_v007/app_v1/overlay/기존 candidate/package/model/DB/assets/PC mirror/Fresh Frame source/settings 전후 SHA 변경0. 새 candidate32/data7/diagnostics85파일; 기존 사용자 변경 보존, commit/push0. Task: tasks/JETSON-P0-002R2.md; Report: docs/jetson/JETSON_INTEGRATED_RUNTIME_REACCEPTANCE.md; Evidence: docs/verification/JETSON-P0-002R2.json.



Latest Task (2026-09-16, ENGINE-DATASET-SKILL-SUITE):

DONE / LOCAL_ARTIFACT_CHECKS_PASS / TEAMMATE_EXECUTION_UNVERIFIED — 촬영 동행·설치/Pilot·카메라/관측 진단·Main/Challenge·검토/재촬영·재개/백업·Export/팀 인계·개발/배포 유지보수의8개 스킬과 공통 계약/시작 문구/목록 작성. 스킬 ZIP33,386 bytes와 기존 EXE/가이드 포함 통합 ZIP95,499,921 bytes를 dist/engine_dataset_wizard/20260916_skill_suite/에 생성. 기존113배포파일 byte 동일; 원본/소스/이전지원ZIP153파일 hash 동일. 스킬 원본8/해제본8 validation, YAML/UTF-8/상대링크/ZIP CRC·hash, 포장기9 tests PASS. 실제 화면·클릭 기능 추가나 EXE 재빌드/카메라 열기/데이터 변경/Jetson 작업/commit·push0. 팀원 PC의 스킬 발견·도구 접근·실제 촬영은 미검증. Task: tasks/engine-dataset-skill-suite.md; Evidence: docs/verification/ENGINE-DATASET-SKILL-SUITE.json.



Latest Task (2026-09-16, ENGINE-DATASET-CODEX-SUPPORT):

DONE / LOCAL_ARTIFACT_CHECKS_PASS / TEAMMATE_EXECUTION_UNVERIFIED — 팀원 앱에 영상이 보인다는 사용자 확인에 따라, Codex 관측 실패와 카메라 실패를 구분하는 프로젝트 스킬·시작 문구·적용 안내를 추가했다. 배포: dist/engine_dataset_wizard/20260916_codex_support/EngineDatasetWizard_CodexSupport.zip (9,149 bytes, 6파일). 기존 EXE에 추가하는 지침이며 화면·클릭 도구나 MCP를 설치하지 않는다. 원본/압축 해제 스킬 validation, UTF-8/YAML, ZIP CRC/원본바이트/덮어쓰기 거부 PASS; 기존 배포·촬영 소스152파일 hash 동일. EXE 재빌드/카메라 열기/데이터 변경/Jetson 작업/commit·push0. 팀원 화면 갱신·도구 접근·실제 촬영 재개는 미검증이며 원격 원인을 확정하지 않는다. Task: tasks/engine-dataset-codex-support.md; Evidence: docs/verification/ENGINE-DATASET-CODEX-SUPPORT.json.



Latest Task (2026-09-16, JETSON-P0-002R):

DONE / FAILURE_NOT_REPRODUCED_WITH_CONTROLLED_EVIDENCE — CASE G INTERMITTENT / ROOT_CAUSE_UNCONFIRMED. 새 process 23개에서 allocation(최대256 MiB), kernel, CPU/CUDA Conv2d, model CPU load/CUDA move/640 warmup, Ultralytics 및 기존 PyTorchDetector 모두 PASS. 최초 실패 단계는 재현되지 않았다. NVML 초기화 성공, compute-process query Not Supported(3); 원래 NvMap/allocator 실패 원인은 미확정이다. app_v007/app_v1/기존 package·model·DB·assets·사용자 패키지/settings·P0-001R overlay·P0-002 candidate 전후 SHA 변경0, Fresh Frame 소스 변경0. 새 diagnostics/p0_002r_cuda에만 진단 파일87개 생성. Windows 외부 Task 문서1개 동시 변경은 별도 기록하고 보존했다. 패키지/allocator/전력/CMA/swap 변경, camera open, PLC/MQTT, commit/push0. 다음은 원래 Candidate 복합 Runtime Gate 재현·재수용이며 P0-002 실제 Fresh Frame 재개는 BLOCKED. Task: tasks/JETSON-P0-002R.md; Report: docs/jetson/JETSON_CUDA_ALLOCATOR_DIAGNOSIS.md; Evidence: docs/verification/JETSON-P0-002R.json.



Latest Task (2026-09-16, JETSON-P0-002):

IMPLEMENTED / CONTRACT_TESTS_PASS / DEVICE_GATE_BLOCKED — Candidate Fresh Frame Trigger/epoch/PTS/age/취소/deadline 계약 및 Worker·Service·원장 연결 구현. 새 27 + 기존 Runtime 75 = 102 tests PASS. Candidate Gate A import/bridge/CUDA, B 카메라 memory-only 5 frames PASS. C는 기존 승인 이미지에서 Detector 1회 시도 중 CUDA allocator NVML_SUCCESS assertion으로 실패해 실제 Fresh Frame/모델 결합/Conveyor acceptance는 NOT_RUN. 별도 app_v008_dev_p0_002 소스 32파일·Python 30 compile 검사, 실패 Gate가 launcher 시작을 차단하여 후보 DB/검사 기록 0. app_v007/app_v1/earbud/model/기존 DB/assets/P0-001R overlay·PC mirror 전후 hash 비교는 verification 참조. 환경 재설치·PLC·MQTT·TRT 변환·Dataset 변경·commit/push 없음. 다음은 CUDA allocator 원인 확인 및 P0-002 Runtime Gate 재수용이며 P0-003 실제 성능 검증은 BLOCKED. Task: tasks/JETSON-P0-002.md; Contract: docs/jetson/JETSON_FRESH_FRAME_CONTRACT.md; Evidence: docs/verification/JETSON-P0-002.json.



Latest Task (2026-09-16, JETSON-P0-001R):

PASS_MINIMUM_ACCEPTANCE / PREPROCESS_READY ? ?? app_v007/app_v1? ???? env_candidates/numpy_compat_001/overlay? NumPy1.26.4? ????? ?? ????. ?? torch2.8/CUDA12.6/OpenCV5?? from_numpy??CUDA ???OpenCV memory smoke PASS, ?? ?? raw1?? ?? Ultralytics ??? [1,3,640,640] FP32 ? ?? ?? ??0.0. model inference/???/?????/DB??/PLC/MQTT0. ??release50/package7/model/DB/assets72/app_v1??1998 ? ?? ??????????? hash ??0; ?? NumPy2.2.6/from_numpy ??? ????? app_v007 ??? ???? ???. Candidate? pip check? OpenCV numpy>=2 ?? ??? ?? pynacl?cffi ???? FAIL; OpenCV downgrade? ?? ??0. P0-002 Candidate ?? ?? ??, ???? Runtime? ?? ????/?? ?? ? BLOCKED. Task: tasks/JETSON-P0-001R.md; Report: docs/jetson/JETSON_RUNTIME_DEPENDENCY_RECOVERY.md; Evidence: docs/verification/JETSON-P0-001R.json. commit/push0. ?? ??/?? ?? ??? ????.



Latest Task (2026-09-16, JETSON-P0-001):

AUDIT_COMPLETE_WITH_FINDINGS / Runtime ?? ?? ??? ? app_v007 ????????????PLC?MQTT?TRT ???commit/push ?? ?? ???21? Gap ?P0-002~007 ?? ??. ?? L4T36.4.7/torch2.8.0/CUDA12.6/TRT10.3.0; ??PC?? ??. OpenCV5.0/NumPy2.2.6 ???? torch.from_numpy? Numpy is not available? ??? ?? ?? ?? PASS? ???? ???. Windows Runtime fixture61???? Python28??/shell???????? PASS. ??release50/???7/?????144/DB???WAL???18???? hash ??. ?? import? Ultralytics ?????? ?? ???? PC read-only SQLite? SHM? ??? ??? ?? ??; ?? ?? hash? ???, ????0. ???release_files(app_v005)? ??accepted_at1? ??? ??. ?? P0-002 Fresh Frame? DRAFT?? ?? ?? ?? ?? ?? ??? ??? ????. Task: tasks/JETSON-P0-001.md; Baseline/Gap: docs/jetson/; Evidence: docs/verification/JETSON-P0-001.json. ?? ?? ?? ??? ??? ????.



Current Phase:

V0 Proxy Inspection System — 진행 중, 전체 완료 아님



Latest Task (2026-09-16, ENGINE-DATASET-WIZARD-V1-RELEASE):

DONE / V1 PREVIEW — EXE + 오프라인 상세/빠른 가이드 배포 ZIP 생성: dist/engine_dataset_wizard/20260916_v1_preview_r2/EngineDatasetWizard_Windows_x64.zip (95,466,551 bytes). 회전 각도 안내·Crank·Station·288계획·E04 잠금 유지. 첫 EXE의 긴 경로 저장 실패를 Collection 경로 정규화로 보완했고 Windows 설정은 변경하지 않았다. 전체281 tests(engine54, 기존 capture/Wizard65 포함)·실제 독립 EXE 합성 저장/재개/계약·일반 시작/종료 PASS. ZIP CRC/입력119해시·HTML3/이미지53경로 PASS. 현재 수집10파일/이전raw11 해시 동일, 실제앱은 정상 종료. 포장 중 촬영/라벨링/E04열람·unlock/commit·push0. 가이드는 DRAFT/TODO10 유지, 실제 전체 Pilot/Main 수용과 팀원 물리 PC는 미검증. 브라우저 도구의 로컬 HTML 보안 차단으로 브라우저 화면 배치도 UNVERIFIED. Main/Pilot0·현재 NORMAL1 PENDING/이전2 RETAKE·새 FAIL0 상태는 유지한다. 아래 배경 정리 대기 상태는 다음 촬영 재개 때 사람이 확인해야 한다. Task: tasks/engine-dataset-wizard-v1-release.md; Evidence: docs/verification/ENGINE-DATASET-WIZARD-V1-RELEASE.json.



Latest Task (2026-09-16, ENGINE-CAPTURE-GUIDE):

새 전체누락 촬영 전 배경 확인 대기: 사용자 제거 완료 뒤 L22에서 대상4개 제거/V8 유지가 보였다. 새 NORMAL L21 오른쪽에 있던 투명 비닐봉투가 사라져 부품 외 배경 차이가 생겼으므로 셔터 전에 중단했다. 봉투를 이전 오른쪽 가장자리 위치로 복원하도록 안내한다. 새 FAIL 저장0, 누적저장3/RETAKE2/Main0, Crank 사람 확인3항목 미체크 유지. 이 단계는 촬영 성공이나 품질 승인이 아니다.



초점 조절 후 NORMAL 기준 재촬영 저장: 사용자가 Crank0 준비 완료를 확인하여 실제 UI 확인/촬영을 실행했다. 새 capture_id 끝be47bd9a48d1, PNG1280×720/SHA256d209df343cbada32f4cc9115c7db42bbc11f170e800b01230628519e6af2ff0d, 품질경고0. 원본에서 문양/경계 개선을 확인했으며 최종 사람 사진 검토는 PENDING이다. 새 Capture ID·이전2원본/기존raw11 해시 보존·동일 바이트 Guide L21 PASS. 누적저장3(RETAKE2), Main/Pilot0. 현재 엔진은 정상이고 다음 MISSING_ALL_TARGETS Crank0 창3항목 미체크로 물리 제거 대기. Evidence: runs/engine_capture_live/focused_normal_verified.json.



초점 조절 후 새 기준 준비: 사용자 정상 재조립 완료와 L19 화면의 파이프2/배기구/문양 및 배기구 방향을 확인했다. 기존2건은 실제 Review UI에서 `초점 조절 전 흐림 · 새 기준 재촬영` 사유로 RETAKE 처리했고 PNG는 보존했다. 기존 설정 저장 경로로 새 setup `SETUP273F8A45848B416C` 생성, 품질/정렬 영역 유지. 현재 실제 Crank0 확인창3항목은 미체크이며 사람 확인 대기다. 새 Dataset 저장0, 누적2건 retained_retake, Main/Pilot0. 실제 RETAKE 화면 L20이 기존 합성20 예시를 대체한다. Evidence: runs/engine_capture_live/focus_retake_verified.json.



수동 초점 해결 관측: 사용자가 렌즈를 손으로 돌려 초점이 맞았다고 확인했다. 실제 Preview L18에서 L16보다 V8 글씨/빨간 부품 경계가 또렷해 보이며, 물리 조절은 사용자가 수행했다. 소프트웨어 AF/이미지 복원/높이 변경 없음. 기존 fixed focus 문구만으로 수동 조절 불가를 추정한 안내를 정정하고 상세/빠른 가이드·하드웨어 사양 근거에 보완했다. 현재 검사 대상 전체누락, 기준2장 미승인·원본 보존·Main/Pilot0. 다음은 정상 부품 복원 후 새 기준 설정/사진에서 전체 대상 선명도 확인이다.



초점 점검 제약 업데이트: 사용자 눈대중 렌즈~엔진 윗면20~30cm, 별도 거치대가 없어 높이 조절 불가. 제안한5cm 이동은 수행되지 않았으므로 카메라 이동/초점 개선으로 기록하지 않는다. 실제 UI 수집 일시정지·Preview 연결 유지, 렌즈 앞 보호필름/오염 확인부터 진행한다. 기준2장 미승인, 신규 Dataset 촬영 없음. 점검 전 실제 화면 L16을 가이드에 추가했고 문서/계약·이미지 검사 PASS(67 PNG/활성56/TODO11), DRAFT 유지.



초점 점검 중: 사용자가 원본 선명도 문제 해결을 요청했다. NORMAL 원본1280×720의 문양/경계 흐림을 확인했으며 원인은 아직 미확정이다. Windows에 HCAM01L 연결이 표시되고 프로젝트 사양은 fixed focus이나 현재 후보2와 장치명 연결/실제 초점 제어 지원은 미검증이다. 기존 사진 확대만 열었고 촬영·설정 변경·사람 승인 없음. 렌즈~엔진 윗면 거리를 확인한 뒤 조정할 예정이며 구도 변경 시 원본 보존 후 기준 사진/정렬을 새로 확인한다. 기준2장 PENDING, Main/Pilot0 유지.



실제 기준 사진2장 검토 대기: 사용자 전체누락 준비 및 새로 들어온 검은 케이블 정리 확인 뒤 MISSING_ALL_TARGETS setup_reference를 기존 UI로 저장했다. 두번째 capture_id 끝9a27055459af, SHA2568281c152b2d3e02c6aa43cd5ec8ca7e132ac28a82fb0a77116b160a1133e31c5. 두PNG1280×720/해시·동일목표조건·첫원본/기존raw11보존 PASS, 자동품질경고0. 현재 실제 사진묶음 창에서 정상/전체누락2장 비교·사람 최종 승인 대기이며 자동 승인하지 않았다. Main/Pilot승인0 유지. 실제리뷰 L15 추가, 가이드66 PNG/활성55/TODO11 DRAFT. Evidence: runs/engine_capture_live/reference_pair_verified.json.



실제 첫 Dataset 저장: 사용자 정상0 준비 완료 확인 후 기존 Wizard 각도 체크/촬영 버튼으로 NORMAL setup_reference1장을 저장했다. PNG1280×720·SHA256·기록 연결 PASS, 자동 품질 경고0, 사람 최종 사진 검토는 PENDING. 첫 실제 capture_id 끝 d2c2627adc8f, 원본 해시841791cfcbc31a650c7a222f1cad711b5a08886047a1c47cc8a22bea847dab59. Guide L12는 원본과 동일 바이트 복사본이고 기존 raw11은 그대로다. Main/Pilot승인0, 라벨링/E04열람/commit·push0. 다음은 MISSING_ALL_TARGETS 기준 사진을 위한 사람 부품 제거이며 현재 Crank 체크 미승인. Guide63 PNG/활성52/TODO11 DRAFT. Evidence: runs/engine_capture_live/first_capture_verified.json. 아래 촬영0 기록은 이전 시점이다.



회전 정렬 보완(사용자 요청): 스티커 없이 맞추는 하늘색 엔진 외곽·중심·배기구 화살표를 추가했다. 목표 Engine 각도에 따라 시계 방향 회전하며 노란 품질 영역은 고정이다. 0° 외곽을 기존 setup event의 선택 필드에 저장하고 이어하기로 복원한다. 원본/Annotation/각도 GT 자동 수정 없음. 미저장 설정 촬영 차단, 촬영 없는 정렬 미리보기 추가. 집중 geometry4/UI6, 전체278(engine51 포함), 문서5/계약·이미지/원본11해시 검사 PASS. 실제 USB0°/120° 표시 확인했지만 실물 엔진 회전·각도 정확도 수용은 아직 아니다. 같은 Collection에서 새 setup SETUPC97BBC14272D4C93 저장, 기존 setup 보존, 촬영0/Main0/라벨링0/E04열람0/commit·push0. 현재 Crank0 사람 체크 대기. 가이드61 PNG/활성50/TODO11로 DRAFT 유지. Evidence: docs/verification/ENGINE-ROTATING-ALIGNMENT.json.



현재 실행 보완: 사용자가 실제 Dataset을 만들면서 가이드를 작성하도록 지시했다. 가이드 전용 사진은 Dataset 촬영으로 세지 않는다. 실제 STATION_A Collection CCFB752B1D2A646A1을 만들고 USB 후보2/DSHOW/1280×720 연결 및 고정 영역 설정을 저장했다. 현재 실제 Crank Phase 사람 확인 창의 세 항목은 미확인 상태이며 첫 기준 촬영 전이다. capture attempts0 / Pilot 승인0 / Main 승인0. 새 실제 사용 화면5개는 images/engine_dataset_capture/live/에 별도 보존한다. native 클릭 도구 연결 실패로 기존 Tk 위젯을 호출하는 로컬 어댑터를 사용하며 저장·검토 로직과 계약은 변경하지 않았다. 전체273개 첫 실행은 UI Space-release1개 실패, 단독1개 및 전체273개 재실행 PASS; 원인 미확인과 최초 로그를 보존한다. 아래 가이드 전용 세션 기록은 당시 근거로 유지한다.



IN PROGRESS / DRAFT — docs/guides/ENGINE_DATASET_CAPTURE_GUIDE_KO.md와 QUICK_GUIDE_KO.md 작성. 실제 Wizard UI 및 계약/계획 기반 표·이미지 출처 검증을 추가했다. USB 후보2/DSHOW/1280×720에서 작업자가 각 상태를 확인한 뒤 실물 6상태 가이드 사진과 Preview 1장을 확보했다. 총50 PNG/활성39장, 실물 보완 TODO11개. 작업자가 배기구 역방향 장착을 지적하여 뒤에 만든 엔진 0°/CRANK_000 기준 3파일의 정상 기준 사용을 취소했다. 원본은 보존하고 해당 사진은 RETAKE 예시에만 사용한다. 잘못 승인한 기준 창을 닫고 재사용 차단 검증을 추가했다. 사용자가 정상 재장착 완료를 확인한 뒤 초기 NORMAL과 배기구 방향을 비교하고 새 기준 3파일을 별도 저장했다. 현재 기준은 06e, 이전 06c는 계속 사용 금지다. 테이프는 필수가 아니고 센서 각도 검증은 없다. 상단 배기구 재배치 전 사진은 보류하고 새 파일로 재촬영했으며 원본 둘 다 보존했다. 목표 각도·Crank는 사람 기준이고 사진 사이 위치 차이가 있다. 문서/계약 검사·가이드 테스트5개·diff 검사 PASS. 이 PASS는 문서 구조 검증이며 물리 정상 판정이 아니다. 실제 기준/사용 화면 보완 진행 중. Main 촬영/라벨링/E04 원본 열람/commit·push 없음, 기존 raw11파일 해시 재검사 동일. 현재 캡처 기록: runs/engine_capture_guide/; Task: tasks/engine-dataset-capture-guide.md. 실물 보완 전까지 완성된 실사용 가이드로 표시하지 않는다.



Latest Task (2026-09-16, ENGINE-DATASET-WIZARD-V1):

DONE / VERIFIED — 기존 360° Wizard/PNG writer/이벤트·재개·검토를 재사용해 Station/Crank/Ground Truth/정상Pair/라벨링 인계를 확장했다. profile v2/3클래스·6상태 유지, plan v3는 상태→Crank→각도 순서이며 Main288/Station(train144/val72/test72). 기본 YOLO216 / E03 Mask40, 두 Station 합성 전체 병합 Main576/YOLO432/Mask80 검증. E04 기본 잠금, 명시적 문구 unlock에도 학습/튜닝 금지. Challenge는 별도 REVIEW·training 제외. 공통 한글/ID 사전에서 Human 문서와 machine 계약을 생성하고 의미·행 연결 불일치는 export 실패. 전체268 tests PASS(Engine41 포함), UI 최소크기/버튼·합성 화면 확인 PASS, diff --check PASS. 기존 raw11파일(PNG2 포함) 동일, 신규 실제 촬영0/라벨링0/학습0/commit·push0. 실장비/실각도·정합/최종 품질은 UNVERIFIED. 기존 EXE/ZIP은 V0 보존(재빌드0), V1 launcher: scripts/start_capture_engine_windows.cmd. 사용법: training/datasets/engine/engine_model_top_v0/README_V1_KR.md; Task: tasks/engine-dataset-wizard-v1.md; Evidence: docs/verification/ENGINE-DATASET-WIZARD-V1.json. 다음은 STATION_A 선택 후 Pilot 첫 화면의 사용자 확인이다.



Latest Task (2026-09-15, ENGINE-DATASET-WIZARD-PORTABLE):

DONE / VERIFIED — 팀원 Windows x64에서 Python/Tkinter 설치 없이 여는 엔진 데이터 수집 EXE/ZIP 생성. 기존 Wizard 진입점을 재사용하고 제품 설정은 EXE 안, 원본/검토·재개는 EXE 옆 data/engine/raw, 시작 로그는 logs에 분리했다. 배포: dist/engine_dataset_wizard/20260915_v1/EngineDatasetWizard_Windows_x64.zip (약74.8MB), 내부 EngineDatasetWizard.exe. 실제 단독 EXE를 한글·공백 폴더로 복사해 Python PATH/환경 변수 없이 다른 cwd에서 Tk·frozen camera worker·합성PNG2·hash·resume/검토 대기 검증 PASS. 일반 무인자 시작 창 응답 확인. 신규4/전체248 tests PASS, ZIP CRC PASS. 실제 촬영/라벨링/학습/Jetson/Runtime 변경/기존 데이터 접근0, commit/push 없음. 별도 물리 팀원 PC·실USB 수용은 미검증, EXE는 미서명. 빌드/사용: scripts/BUILD_CAPTURE_ENGINE_KR.md; Evidence: docs/verification/ENGINE-DATASET-WIZARD-PORTABLE.json. 아래 360도 구현과 실장비 실행 기록을 보존한다.



Latest Task (2026-09-14, ENGINE-DATASET-WIZARD-360-V0):

DONE / VERIFIED — Windows 엔진360° Dataset Wizard 구현·합성 검증 범위. 기존 Wizard/세션/PNG/검토·재개를 재사용했다. profile v2는 gray_pipe2/exhaust_top1/symbol_module1과6상태의 expected_counts/removed_slots를 명시하며 기존v1/이어폰 설정·순서 digest는 유지한다. plan v2의 회차→조명→상태→12목표각도 순서, 회차/상태 실제 재배치 사람 gate, 고정 ROI/원형 목표각도 UI, 부분 저장·검토 대기 resume, E04 일반 라벨 후보 제외를 구현했다. Train0+30n 144장/Val15+30n72장/Test8+30n72장=본수집288, 기준2+Pilot12는 별도. Challenge는 별도 설정/후속 수집 사양이며 main 촬영모드에 넣지 않는다.

최종 전체244개 PASS(실패0/오류0/skip0), 엔진17개 집중 PASS. 기존227개 테스트 무수정, 보호57파일 hash 동일. 실제 Tk 위젯과 실행 진입점은 합성 카메라로 확인했다. launcher: scripts/start_capture_engine_windows.cmd; 안내: training/datasets/engine/engine_model_top_v0/README_KR.md. 실제 엔진 폴더/촬영0, 라벨링0, 학습0, Jetson0, Runtime 변경0, 실제 B04/Test 접근0. 물리 각도 센서 검증·첫 Pilot 품질은 미검증이며 사람 첫 화면 확인 대기. commit/push 없음. Evidence: docs/verification/ENGINE-DATASET-WIZARD-360-V0.json 및 runs/engine_dataset_wizard_360_v0/. 아래 Jetson 실행·실물 수용 기록은 이전 작업으로 보존한다.



Latest Camera Reconnect (2026-09-14 14:13 KST):

사용자가 USB 분리·재연결을 알렸으며 실제 동일 by-id 장치는 존재하나 기존 Worker4242가 CAMERA_FRAME_TIMEOUT/RECOVERY로 종료된 상태를 확인했다. 진행 중 검사0에서 현재 manifest와 같은 earbud_case_v0/app_v001을 기존 활성화/Worker 복구 API로 다시 로드했다. 새 Worker4688, IDLE/camera_ready=true/error=null, cuda:0 자체 추론 및1280×720 미리보기2장 갱신 PASS. 미리보기에 열린 케이스가 보인다. 전후 이력13행 전체 본문과 manifest hash 일치, PC sync 오류0/대기자산0. 복구 전부터 기준 미승인 상태였으며 복구 후에도 calibration_confirmed=false/ready=false를 유지했다. 실제 검사는 정상 제품 기준 촬영·사람 자리 확인 후 가능하다. 신규 검사·승인 요청0, 물리 분리 순간 관찰/단절 중 검사 시험은 미실행. 카메라 재연결 복구 수용 PASS, 전체 실물 수용은 대기 유지. Evidence: runs/inspection_app_v1/camera_reconnect_20260914_1412/verification.json.



Latest Startup (2026-09-14 13:43 KST):

사용자 실행 요청으로 기존 전용 SSH 키 접속 후 Jetson app_v007 Service PID4229/Worker4242, Windows PC 수집기와 양방향 용도의 별도 SSH 터널을 시작했다. 실제 health IDLE/ready=true/camera_ready=true/error=null, PyTorch cuda:0/Orin/입력[1,3,640,640] 자체 추론 완료, USB1280×720 JPEG2장 디코딩·서로 다른 해시 확인. 기존 기준 승인 로드, PC sync error=null/pending_assets0. Edge/PC 이력 ID11개와 결과 본문은 일치하나 a44a968e2a914a47a54e7ecc5a3383c4의 accepted_at 필드는 서로 다름을 기록했으며 원인을 조사하거나 수정하지 않았다. 현재 영상은 제품 없는 흐린 회색 면이므로 실물 배치·초점 및 변경된 구도의 기준 재등록은 사람 확인이 필요하다. 신규 검사/기준 촬영 요청0. HTML/영상 HTTP200 확인, 브라우저 제어 연결이 없어 실제 화면 렌더는 UNVERIFIED. 수동 접속/실행/PC 수집/종료 안내를 apps/edge_service/INSPECTION_APP.md에 보완했다. 실행 재개 수용 PASS, 전체 실물4상태 수용은 기존 대기 유지. Evidence: runs/inspection_app_v1/startup_20260914/verification.json. 코드·모델·환경 설치 변경 없음.



Program Guide (2026-09-14):

사용자 요청에 따라 현재 app_v007/f6403fc의 프로그램 구조·기능·실행 절차를 설명하는 한국어 PPT 26장과 설명 노트를 제작했다. 산출물: runs/program_guide_ppt_20260914/output/OneDevice_프로그램_구조_실행가이드_app_v007_v2.pptx. 소스와 실제 정상1건 근거를 사용하고 기준 진단 REVIEW/제품 검사/Mock/실 엔진·PLC의 범위를 구분했다. 최종 파일 재읽기·26장 렌더 검토·표8개/노트26장/원본2이미지 해시 검사 PASS, 레이아웃 finding/warning0. 실제 PowerPoint 앱 표시는 UNVERIFIED. 신규 프로젝트 시험·모델·장비 실행은 없으며 실물 수용 상태는 아래 그대로다. Evidence: runs/program_guide_ppt_20260914/PPT_RESULT.md 및 build/guide-verification.json.



Latest Physical Normal Inspection (2026-09-14):

사용자가 기준 진단 a7908d3c586f422c9648cbfc97feffac의 보라색 L/R 후보를 명시 승인했다. 별도 Jetson calibration 행 ce3a0337df5243109093e7eae9104ce7의 confirmed=true 및 좌표/기준 사진 연결을 직접 SQLite로 확인했다. 기존 기준 진단 REVIEW와 미승인 당시 후보 원문은 그대로 보존된다.

현재 정상 배치의 신규 제품 검사5031fbaf16a94877b5b6aa46f9e90c03: PASS / 모든 필수 자리와 수량 확인, L/R PRESENT, 결함/미확인0. 새 관측3회와 신규 원본3장+overlay1장, 승인 좌표 고정 사용 확인. Jetson 원장1행과 API 결과 일치, PC 같은 ID1행·결과 본문 일치, 원본/overlay4자산 SHA256 일치·양측 ACKED, 완료/저장시간 이벤트2개 PC 수신·ACKED. 기존9진단 행 해시와 기준 진단 원문 보존. Edge integrity ok/FK위반0.

검사 이력 API에서 같은 ID의 inspect/PASS를 확인했으나 브라우저 실제 이력 표시는 사용자 확인 대기다. 정상 실물 제품 검사1건 검증이며 전체 네 상태 수용 완료가 아니다. 다음은 화면 이력 확인 후 L 누락 한 행동 안내. 기대 normal/PASS는 별도 acceptance_context에만 기록했고 검사 입력에 넣지 않았다. 실 PLC/엔진 시험 아님. Evidence: runs/inspection_app_v1/physical_acceptance/5031fbaf16a94877b5b6aa46f9e90c03/verification.json.



Latest Physical Reference (2026-09-14):

사용자가 정상 케이스 중앙 배치와 두 자리 가시성·손 제거를 확인했다. app_v007에서 새 기준 진단 a7908d3c586f422c9648cbfc97feffac을 실행해 현재 좌표의 L/R 후보 생성, REVIEW/사람 자리 확인 대기를 확인했다. 원본3장+overlay1장 저장/해시 확인, PC 동일 ID 행과4자산 해시 일치. 상태 기대값은 별도 acceptance_context에만 저장했고 판정 입력에 전달하지 않았다. 후보 confirmed=false, 실제 기준 자리 승인은 아직 받지 않았으며 제품 검사도 시작하지 않았다. 원본/후보 사진을 열어 확인했으며 다음은 사용자 보라색 EXPECTED L/R 자리 확인이다. Evidence: runs/inspection_app_v1/physical_acceptance/a7908d3c586f422c9648cbfc97feffac/.



Latest Checkpoint (2026-09-14, CALIBRATION-FIX):

현재 실행 릴리스 app_v007. tasks/inspection-app-v1.md의 기준 등록 수정 범위는 구현·배포 완료, 실물 기준 자리 승인 및 네 상태 수용은 대기다. 검사 화면 http://127.0.0.1:8768 새로고침 후 재개한다.

화면 기록 c92f305afc9348df9ee030d2ec217a95의 실제 원본/관측3회를 확인했다. L/R·case 검출과 품질은 유효했으나 app_v005 reference_proposal이 과거 fixed region과 먼저 비교하여 L/R 모두 배정0이었다. 실행 Jetson 소스와 Windows HEAD878b956의 해시 일치를 확인했다. 실제 활성 패키지 경로는 app_v003의 불변 app_v001이며 manifest/model/recipe hash는 화면 기록과 같고 변경하지 않았다.

기준 등록만 현재 검출 좌표에서 후보를 생성하고 클래스·수량·품질·연속 관측을 검증한다. 동일 클래스 다중 자리 대응은 임의 배정하지 않고 한국어로 자리 지정 필요를 알린다. 후보와 일반 검사 overlay는 결과 calibration_used의 동일 정규화 좌표를 쓴다. 승인 기록은 제품/패키지/촬영/설비 설정 hash/cell/기준 inspection/frame에 연결된다. 새 기준 촬영을 시작하면 이전 승인으로 검사하지 않으며 재시작 후에도 새 승인까지 차단한다. 사람 확인 자동 승인0.

최종 Windows227개 PASS(48.312초), 최종 Jetson 변경 관련14개 PASS(10.011초), 이전 동일 코드 journal/package17개 PASS. Jetson TestClient는 httpx 부재로 UNVERIFIED; Windows API 시험 및 최종 실제 HTTP 승인 전409 CALIBRATION_REQUIRED/HTML 응답/카메라 cuda:0 확인. DOM 계약·한국어·원본 링크 검사 PASS는 실제 브라우저 렌더링 승인이 아니다.

기존 진단5건/이미지20개는 그대로 보존한다. 이번 대조 시 누적 기준 진단9건/이미지36개였으며 전후 전체 원장 행·이미지 해시와 PC36자산을 확인했다. 제품 검사0, 승인 calibration0, DB integrity ok/FK위반0. 실제 정상/L누락/R누락/양쪽누락 검사·DB·화면 수용은 미실행. 모델·신뢰도·겹침 기준·Recipe 불변, 학습/튜닝/실 PLC/실 엔진 미실행. app_v005/v006과 전환 전 data_root 전체 백업을 보존했다.

Evidence: docs/verification/INSPECTION-CALIBRATION-FIX-20260914.json 및 runs/inspection_app_v1/calibration_fix_v006/ (v006 진단/중간 배포와 최종 v007 증거 함께 보존). 다음: 정상 제품 배치 확인 → 현재 기준 사진 촬영 → 사람 자리 승인 → 정상 한 건의 동일 ID 원본/판정/Jetson DB/PC/이력 대조. 그 뒤 누락3상태를 한 행동씩 진행한다.



Latest Checkpoint (2026-09-14, INSPECTION-APP-V1):

현재 Task는 tasks/inspection-app-v1.md. CODEX_INSPECTION_APP_V1_KO.md의 공통 앱 범위로 DB/PC/Mock 제어를 구현했으며, 아래 과거 BENCH의 DB 제외/8767 실행 표기는 당시 기록이다. 현재 Jetson 릴리스 app_v005, 검사 화면 http://127.0.0.1:8768, Windows PC 조회 http://127.0.0.1:8769. 기존 bench_v001은 소스·모델·기록을 보존하고 종료했다.

제품 패키지 hash/schema/클래스/전처리/Recipe/촬영 검증, 같은 클래스 다중 슬롯·수량의 유일 배정, 별도 GPU/카메라 Worker 프로세스, Service 단일 SQLite writer와 PNG→commit→게시, 이력/asset 조회, 패키지 활성화/실패 복원, PC outbox·별도 DB·독립 이미지 ACK, Mock 요청/결과/종료 ACK·복구를 연결했다. Engine 모델/실물 슬롯은 미준비 비활성이다.

실제 Jetson cuda:0/Orin/입력[1,3,640,640], 기존 best.pt SHA256 49f533e4e4e5846d1582564d8efbb38a647ad10348a976db9085d94df16250c1 유지. 격리 app_v1 환경은 기존 사용자 torch2.8.0과 시스템 OpenCV4.8.0을 그대로 사용하며 FastAPI/uvicorn만 별도 설치했다. 실제 USB 기준 진단5건은 대상 부재로 전부 REVIEW, PNG15장+overlay5장·SQLite5행·PC20자산 해시 일치. 생산 검사0건이다. 사람 가시성을 자동 승인하지 않았다.

PC 실제 중단 중3건을 Edge에 보관하고 재연결 후 중복 없이 수집, outbox/이미지 대기0. 동일 Baseline 패키지 실제 재활성화·세션 변경·기존 이력 유지 확인. Service 종료 뒤 자식 Worker가 남던 실패를 보존하고 ASGI lifespan 정리로 수정, 부모/자식 종료와 재시작 확인. 실제 Windows 전체218개 PASS, 마지막 변경 관련14개 및5개 PASS, 최종 Jetson27개 PASS, 릴리스45파일 해시 일치·SQLite integrity ok/FK 위반0. 가상 시간/가짜 Worker 시험은 실물 시험과 구분한다.

남은 수용: 브라우저 실제 표시, 현재 패키지 기준 자리 사람 확인, 정상/L누락/R누락/양쪽누락의 사진·판정·DB·화면, 물리 USB 단절, 사람 준비 후 실제 카메라 Mock 사이클. 모두 대기이며 전체 완료로 표시하지 않는다. B04/재학습/ONNX·TensorRT/실 엔진/실 PLC·모터는 미실행. 실행 안내 apps/edge_service/INSPECTION_APP.md, 증거 docs/verification/INSPECTION-APP-V1-20260914.json 및 runs/inspection_app_v1/.



GitHub publication verification (2026-09-14):

사용자 요청에 따라 촬영 도구 보완/라벨 변환/그룹 분리/Baseline·오류 분석/Jetson BENCH 코드와 검증 기록을 기존 master에 동기화한다. 전체 자동 테스트185개 PASS(50.302초), 새 checkout 임시 폴더 준비 보완 후 관련11개 PASS. 원본 사진·가중치·ONNX/engine·임시 분석·무관한 미커밋 CAD 작업은 게시하지 않는다. ROI 폴더의 복사된 Baseline 보고서와 미검증 환경 설정 주장이 있는 과거 MODEL_SELECTION 문서는 로컬에 보존하며 배포 선택 근거로 게시하지 않는다. 현재 BENCH Baseline 선택은 최신 사용자 지시를 따른다. 실제 실물4상태 검증은 아래와 같이 대기 상태다.



Latest Runtime Checkpoint (2026-09-13 → 09-14, JETSON-BENCH-001):

전용키 자동 SSH 접속 성공. 실제 Jetson Orin Nano/aarch64/L4T36.4.7/Python3.10.12/torch2.8.0 CUDA12.6/Ultralytics8.4.118/OpenCV4.8.0 확인 및 CUDA 연산 성공. 기존 환경을 재설치하지 않고 PyTorch CUDA 단일 경로를 선택했다. TensorRT10.3 설치 존재는 확인했지만 사용하지 않았고 ONNX parity는 NOT_RUN_PT_PATH.

원래 Baseline best.pt를 전송해 SHA256 일치. B03 BASE CENTER 네 상태 원본4장을 Jetson cuda:0에서 실제 추론, 모두 기대 부품 목록 일치(총8객체). 실제 입력은 FP32[1,3,640,640]/rect=False/전체 프레임. 첫 호출5888ms, 다음 세 호출52~59ms는 smoke 관측이며 정식 성능 벤치마크가 아니다.

기존 Camera/Detector 계약 기반 PyTorch/GStreamer adapter와 apps/edge_service/bench.py+bench.html, config/earbud_bench.json 구현. Jetson Python3.10의 StrEnum 호환만 최소 보완. 단일 Worker 소유·요청 후 source PTS·3연속 관측·제품별 자리/가시성 확인·요청별 원본PNG/JSON·중복거부·저장오류/단절 표시. DB/PLC는 후속으로 유지.

실제 USB MJPG1280x720 수신/증가 PTS12프레임/HTTP READY와 이미지 수신 확인. 첫 USB 연결 대기0.5초 실패를 보존하고 초기 프레임만3초 대기로 수정한 뒤 실제 수신 성공. 브라우저 조작 도구 미연결로 사용자의 화면 확인 대기.

Windows/Jetson 계약19개씩, BENCH 집중11개씩 PASS. 모델/배포파일8개 해시 일치. Evidence: docs/verification/JETSON-BENCH-001-20260913.json 및 runs/jetson_bench_001/.

현재 Jetson 서비스 실행 중, 노트북 http://127.0.0.1:8767 (SSH tunnel, 대상은127.0.0.1에만 bind). 정상 기준 자리 사람 확인·실제 네 상태 판정/저장·물리 단절·실제 중복 HTTP 검사는 아직 대기이며 전체 완료가 아니다. 다음 행동은 사용자가 브라우저에서 현재 영상 확인. 실행/종료/위치는 apps/edge_service/JETSON_BENCH.md.



Latest Request / Checkpoint (2026-09-13, JETSON-BENCH-001):

현재 Task는 tasks/jetson-bench-001.md. 최신 사용자 요청이 CODEX_EDGE_VISION_NEXT_KO의 전체 시스템 순서보다 우선한다. 기존 Baseline으로 Jetson 저장 사진 GPU smoke → 실제 USB → 노트북 브라우저 정상/누락 검사 화면까지만 진행한다. 재학습/추가 ROI·768/B04/MES·DB복제·PLC는 이번 범위 밖이며 최종 DB·PLC 요구는 후속으로 유지한다.

원래 baseline_result와 best.pt SHA256 일치. best.onnx 구조/클래스 확인: FP32[1,3,640,640] → [1,7,8400], NMS 노드0. ONNX parity와 Jetson 실행은 미실행.

provenance의 B03 BASE CENTER 네 상태 원본을 각1장 준비하고 해시 대조했다. runs/jetson_bench_001/staging_v001/에 manifest/별도 평가정답/원본 사본4장 보존. 준비 코드 집중 테스트3개 PASS. 실제 GPU·카메라·웹 화면 PASS가 아니다.

현재 실행 중인 SSH 프로세스에서 접속 경로를 확인했으나 BatchMode 인증1회 거절(publickey,password). SSH config 없음. 사용자에게 scripts/connect_jetson_bench.py를 터미널에서 실행해 전용키 인증을 설정하도록 안내했다. 호스트키 검증/네트워크 설정을 변경하지 않았으며 키 생성·대상 설정·환경 probe는 아직 미실행. 접속 인증 뒤 단일 backend를 결정한다.



아래 Current Task/튜닝 미실행 표기는 이전 분석 시점 기록이다. 최신 요청은 위 JETSON-BENCH-001이며 Baseline/ROI 학습을 반복하지 않는다.



Completed:

V0-T01, PLAN-REVISION-001, PLAN-AUDIT-001, V0-T02, V0-T03, V0-T04

V0-T05: DONE / VERIFIED (B01/B02 120장 위치 라벨 사람 승인·YOLO 학습 후보 변환 범위)

V0-T06, V0-T07, PROXY-DATASET-TRAIN-001: DONE / VERIFIED (B03 승인60장·train120/val60·Windows 첫 baseline 완료)

HUMAN-CAPTURE-001-PREP: DONE / VERIFIED (촬영 준비 범위)

WINDOWS-CAPTURE-001: DONE / VERIFIED (소프트웨어 + 최초 실제 USB 촬영 흐름)

WINDOWS-CAPTURE-002: DONE / VERIFIED (제품별 안내 촬영 소프트웨어)

DATASET-WIZARD-001: DONE / VERIFIED (전체 계획 수집 길잡이 소프트웨어)



Current Task:

V0-T08 — 평가·오류 분석 및 실험안 완료 / VERIFIED. 실제 튜닝 실행은 사용자 요청에 따라 미실행.



Latest Checkpoint (2026-09-13, V0-T08 분석 완료):

기존 B03 예측60장/120객체를 조건·배치·상태·클래스별로 분석했다. OPPOSITE 평균confidence0.9433이 BASE0.9661/DIM0.9668보다 낮지만 평균IoU는 BASE0.9134가 가장 낮다. L/R IoU약0.878,case0.958. 최저IoU0002 R0.75872,최저confidence0046 R0.88213. FP0/FN0,IoU<0.75도0이며<0.85는13개다. 최저 두목록의18사진/19객체를 실제 원본·GT/pred·기존예측으로 보조 검토했다. 작은 이어폰 경계 차이와 반사/케이스 경계 불확실성은 원인 후보이며 라벨 수정은 하지 않았다.

ERROR_ANALYSIS.md/error_analysis_detailed.json/error_analysis_supplement.json/error_review_v001/을 기존 실험 폴더에 추가했다. 독립IoU120,분포/합계/순위/원본보존 및 새 집중테스트4개 PASS. Evidence: docs/verification/V0-T08-ERROR-ANALYSIS-20260913.json.

추천은 baseline 유지 대조 + 고정ROI만 변경(1순위) + imgsz768만 변경(2순위). 실제 학습/추론 재실행0,B04 접근0,Jetson0. T08의 과거 실제 튜닝 실행 계획은 후속 대기이며 이번 분석 완료와 구분한다.



Earlier Checkpoint (2026-09-13, Windows 첫 baseline 완료):

PROXY-DATASET-TRAIN-001 DONE / VERIFIED. B03 v003 전체60장 사용자 승인→새 승인본/사람 검토 기록→validation_candidate 변환60장120객체 완료, 보류0. B01/B02 기존 train120장과 B03 val60장, B04 test0 예약으로 T06 구성·누수 검사 PASS. 원본/기존 승인본/수집 기록을 포함한978개 보호 파일 해시 유지.

T07 단일100epoch 실제 학습 exit0 완료: yolov8n.pt, RTX5070 Laptop cuda:0, imgsz640/batch16/seed42/AdamW/FP32. 학습 호출 총313.42초(초기화·마지막 검증 포함), epoch loop300.78초. best/last 재로드 CUDA PASS. best B03 Precision0.9981466 / Recall1.0 / mAP50 0.995 / mAP50-95 0.8334961. B03 예측60장 저장, conf0.25·IoU0.5 class-aware matching TP120/FP0/FN0. IoU가 낮은0002 R(0.759),0055 L(0.774) 예측 이미지 보조 확인; 미검출 사례로 부르지 않는다.

결과: training/experiments/earbud_case_v0_20260913_v001/BASELINE_REPORT.md 및 docs/verification/PROXY-DATASET-TRAIN-001-BASELINE-20260913.json. 데이터: training/outputs/datasets/earbud_case_v0_B01_B03_20260913_v001/dataset.yaml. 새 집중 검사12개 PASS. B04 최종 시험·추가 튜닝·Jetson 배포는 이번에 미실행이며 다음 별도 단계로 남긴다. 전체 엔진 정상/불량 검사·DB 저장 완료를 뜻하지 않는다.



Earlier Checkpoint (2026-09-13, B03 전체 라벨 승인 후 학습 중):

사용자가 "모든사진 OK라는거야 일일이 확인 안받아도되"라고 B03 v00360장 전체의 라벨을 명시 승인했다. 새 project_reviewed_all60_v001.json/human_review_all60_v001.json 저장, 사각형 변경0·120객체·보류0. 기존 초안과 부분 검토 로그는 보존했다. via_to_yolo.py validation_candidate60장 변환 PASS.

T06 DONE: training/outputs/datasets/earbud_case_v0_B01_B03_20260913_v001/에 train120/val60/test0 예약·dataset.yaml/분리 목록/누수 검사 저장. 이미지 SHA 및 origin/session/episode/capture 중복0. 새 데이터 검사8개·오류 집계 검사4개 PASS.

T07 현재 실행 중: training/baseline_config.yaml, yolov8n.pt, CUDA RTX5070 Laptop, imgsz640/100epochs/batch16/seed42/AdamW/FP32. 출력 training/experiments/earbud_case_v0_20260913_v001/baseline, 로그 training/outputs/earbud_baseline_20260913_v001.log. 이미 시작한 동일 baseline을 중복 실행하지 않는다. 완료 여부는 baseline_result.json 또는 baseline_failure.json으로 확인한다. B04 예약 유지·Jetson 미실행.



Earlier Checkpoint (2026-09-13, B03 촬영 완료 후):

B01/B02 승인·YOLO 변환120장 유지. B03 실제60장 저장 및15묶음 사람 촬영 검토 완료, 촬영 검토 대기0. BASE/DIM/OPPOSITE 각20장, 네 상태 각15장이다. 전체 원본222장·49세션이며 과거 재촬영28장도 보존했다. B03는 사용자 촬영 중단·케이스/조명 재준비 확인 후 기존 GUI로 시작했고 origin_group OG697C8F89699D4572 / validation_candidate다. B01/B02의 OG1023298FB0FC4631과 그룹·실제 이미지 해시 중복0. 물리적 독립성은 사람 선언이며 자동 입증이 아니다.

기존 GUI 내보내기 EXPORT6F74307E8E314691와 prepare_via_project.py를 재사용해 별도 B03_20260913 작업 공간을 만들었다. 실제 B03 원본60장을 확대 확인하고120개(L30/R30/case60) pending 사각형을 작성했다. 최신 초안은 training/outputs/labeling/B03_20260913/project_draft_all60_v003.json, 검토 이미지는 같은 폴더의 review_all60_v003/이다. 사람 위치 라벨 승인0, B03 YOLO 변환0. B01/B02 승인본·출력과 원본을 포함한978개 보호 파일 해시 유지. 이전 B03 초안v001/v002도 보존한다.

B04 미시작·최종 시험 예약 유지. 앱의 현재 멈춤은 B04의 용도 전환 보호이며 B03 미완료가 아니다. dataset.yaml/분리 목록/실제 데이터 첫 학습은 아직 미실행이다. 과거 t02_smoke의 모델 파일은 이번 실데이터 학습 결과가 아니다.

근거: docs/verification/PROXY-DATASET-TRAIN-001-B03-CAPTURE-20260913.json 및 docs/verification/PROXY-DATASET-TRAIN-001-B03-LABEL-DRAFT-20260913.json.

현재 다음 작업: B03 최신 초안60장의 실제 부품 종류·사각형 범위만 사람 검토 → 승인 범위 YOLO 변환 → T06 그룹 분리 → Windows 첫 학습. B01/B02 재승인이나 B04 촬영은 요구하지 않는다.



Current Authorization (2026-09-13):

사용자가 오늘 데이터셋 제작과 첫 학습까지 진행하도록 범위를 확장했다. Jetson Orin Nano는 아직 연결하지 않았으며 지금 단계는 Windows에서 수행한다. 이전 촬영 전용 범위의 라벨링·학습 금지는 이번 명시 요청으로 대체되지만 원본 보존·사진별 준비·사람 검토·독립 그룹·시험 예약 정책은 유지한다.

프로젝트 .venv에서 torch2.11.0+cu128 / Ultralytics8.4.146, RTX5070 Laptop GPU의 실제 cuda:0 행렬 연산(유한 결과·합3920)을 앞서 확인했다. 현재 실제 위치 라벨120장은 승인·변환됐으나 baseline 학습은 아직 미실행이다. 이번 파일 작업에서는 GPU를 재실행하거나 환경을 재설치하지 않았다.



Earlier State (B03 완료 이전 기록, 최신 진행은 위 Latest Checkpoint 우선):

사용자 요청으로 브라우저 재연결 시도를 중단하고 허용된 로컬 PNG·VIA JSON 파일 작업을 유지한다. 브라우저의 미저장 내용은 읽지 않았다. 이어가기 위치는 tasks/v0-t05-labeling-validation.md의 Finalization Result와 tasks/v0-t06-grouped-split.md를 따른다.

V0-T05 DONE / VERIFIED — 사용자가 project_draft_all120_v001.json 전체120장의 부품 종류·사각형 범위를 학습용으로 명시 승인했다. 새 project_reviewed_all120_v001.json에120장 confirmed·240개(earbud_left60,earbud_right60,case120)를 기록했고 보류0장이다. human_review_all120_v001.json에 원래 초안/승인본 SHA256·전체 실제 이미지 ID·사용자 응답·기록 시각을 연결했다. 0001·0002·0057·0081을 포함한 경계 불확실성 메모는 사용자 현행 기준 승인으로 해결했으며 기존 메모와 pending 초안 자체는 보존했다. 사각형/클래스 변경0.

제품 schema를 읽는 공통 training/scripts/via_to_yolo.py로 training/outputs/yolo/B01_B02_reviewed_20260913_v001/에 실제 원본 사본120장·YOLO120파일/240객체·출처 목록을 저장했다. 집중 테스트16개 PASS(0.463초). 별도 실제 출력 검사 PASS: 원본/작업용/출력 해시, 클래스·객체 수·양의 유한 좌표·범위·그룹 연결, 픽셀 역변환 최대 오차4.8000061e-08 <= 허용1e-06, 보호368파일 보존. 기존 검토 이미지와 체크포인트는 학습 입력에서 제외했다. 근거는 docs/verification/V0-T05-YOLO.json 및 출력 폴더 independent_audit.json이다.

B02 DONE / VERIFIED — 현재 B01/B02 본수집120장 사람 확정(각60장), 검토 대기0. 원본162장(기준2·준비12·본수집120·과거 재촬영28), 34세션 검증과 599이벤트 체인 확인. B03/B04는 아직 시작하지 않았다.

B01/B02는 같은 origin_group OG1023298FB0FC4631 / train_candidate다. B03을 독립 회차 선언 없이 시작하면 기존 용도 충돌 보호 규칙으로 일시 정지된다. 코드의 '오늘은 멈추고' 문구는 날짜 제한 검사를 뜻하지 않는다. 실제 촬영 중단 후 시간/설치 재준비 사실을 확인해야 하며 선언만으로 물리적 독립성이 검증되는 것은 아니다.

기존 GUI의 라벨링용 자료 정리로 exports/EXPORTA48C70FCE9B94A62/ 생성 완료. 학습·라벨링 후보120장, 검증0·시험0·합성0, 제외42장(기준/준비14+과거 거절28). 그120장의 위치 라벨 승인·YOLO 변환이 완료됐다. B03는 현재 스탠드 계획상60장이나 실제 시작/촬영/라벨0이며 B04는 최종 시험 예약이다. dataset.yaml·그룹 분리 완료·학습 실행은 아직 없다. 기존 수집 기록과 창을 조작하지 않았고 물리적 재준비도 완료로 기록하지 않았다. 다음은 사용자의 실제 B03 설치 재준비 확인이다.



Earlier B01 Checkpoint (historical):

B01 DONE / VERIFIED — 2026-09-13 첫 본수집60장 저장·사람 확정 완료. 전체 계획은 진행 중이며 B02 준비 화면에서 대기한다.

실제 원본102장: 기준2장·준비12장 모두 확정, B01 원본88장 중 현재 유효60장 확정·과거 재촬영 원본28장 보존. 검토 대기0장, B02 촬영0장. 전체 본수집 목표240장 중60장 확정.

조명 정정 이후 사용자가 실제 GUI에서40장을 추가 촬영·묶음 검토했다. 현재 확정 B01은 BASE/DIM/OPPOSITE 각20장, NORMAL/MISSING_LEFT/MISSING_RIGHT/MISSING_BOTH 각15장이다. 같은 B01 origin_group을 유지하고 독립성은 선언하지 않았다.

19개 실제 세션의 PNG/manifest 재로드·크기·해시와 이벤트386개 검증 통과. 모든102장 source_kind=camera,1280×720. 현재 B02 회차 준비 두 체크는 미선택이고 round_started는 B01 하나뿐이다.

마지막 MISSING_BOTH의 SIMILAR_IMAGE는 과거 main_B01_BASE_LEFT/MISSING_BOTH와의 유사도 경고다. 픽셀 해시는 다르며 저장 실패가 아니다.

기존 GUI에서 경고 확인 후 사진을 묶음 검토까지 보존했으며, 이 동작으로 사람 검토 완료를 기록하지 않았다.

사용자가 혼자 진행한 뒤 조명 위치·밝기·거리를 전혀 바꾸지 않았다고 확인했다. 함께 진행할 때는 조명을 바꿨다는 후속 확인에 따라 기준/준비와 BASE 본수집20장은 유지했다.

DIM20장과 OPPOSITE8장을 실제 비교 GUI에서 조명 조건 불일치 사유로 재촬영 처리했다. 기존 batch_accepted14개는 모두 보존되고, 해당28장에 기존 attempt_rejected 이벤트만 추가됐다. 실제 물체 재배치 선언은 모두 false다.

촬영을 막은 확정 묶음 재검토 진입점 누락을 수집 현황→기존 비교 화면 연결로 보완했다. 사용자가 지적한 조명 안내 문제는 조건 전환/재개 시 별도 조명 준비 확인 창으로 보완했다. 조명 확인은 촬영하지 않고 실행 중 UI 상태로만 유지한다.

원본/manifest/계획 사본/이벤트 스키마/품질 임계값/사람 묶음 승인 정책은 변경하지 않았다. 내부 함수 우회로 실제 자료를 정정하지 않았다.

수정 관련21개 테스트, 전체132개 테스트(40.057초), 최종 현황창 라벨 위치 정리 후 관련1개 테스트 통과. 실제 앱 정상 종료 후 기존 실행 파일로 단일 창 재실행, 같은 수집 폴더 복원·검증·재촬영 처리 완료.

수집 폴더: data/proxy/raw/collections/C2709B20787804587/ — 새 계획을 만들지 않고 이 폴더로 이어한다.

스탠드 있음 계획 v1(BASE/DIM/OPPOSITE), 첫 본수집 B01 목표 60장. 화면 왼쪽=실물 L은 사용자 확인 완료.

재시작 후 Windows HCAM01L 존재 확인, DSHOW 후보2를 직접 연결해 실제 작업대 영상1280×720/MJPG 수신을 확인했다. 요청도1280×720이며 FPS·높이·조도는 미확인이다. 이후 사용자가 실제 설치 및 조명 준비 확인을 거쳐 같은 setup으로 B01을 완료했다.

HCAM01L은 Windows 장치 목록에서 확인했으며 앱의 device_name은 null이다. 후보 번호를 영구 장치 식별자로 취급하지 않는다.

실제 영상 읽기 실패로 촬영을 일시 정지했다. 3개 세션의 PNG 8장 재로드·크기·해시와 이벤트 32개를 검증한 뒤 같은 설정으로 재연결했다.

사용자가 실제 설치 유지 여부를 확인했고 앱은 같은 미촬영 단계로 재개했다. 이 복구 중 추가 촬영 0장, 끊김의 정확한 원인은 미확인이다.

미리보기의 미연결 안내문 잔류는 별도 표시 오류로 남아 있다. 실제 PNG에는 안내문/기준 테두리가 없으며 원본 픽셀 해시 대조도 통과했다.

최소 수정은 wizard_app.py/wizard_views.py와 관련 회귀 테스트·사용 안내에 한정했다. CAD·환경·Jetson·학습·라벨링은 변경하지 않았다. 준비 시험 확인은 데이터 충분성의 보장이 아니다.



Software Verification (DATASET-WIZARD-001, historical):

DONE / VERIFIED — 계획/setup/조명/배치/상태 자동 순서, 준비 후 한 장 저장·검증,

품질 보조, 묶음 사람 확인·재촬영·정확한 재개·그룹 용도 예약·라벨링 인계 목록 구현.

130/130 자동 테스트 (기존111 + 추가19), 실제 Tk 창의 합성 입력/비교/확대 확인.

이 소프트웨어 검증 당시 새 계획의 실제 USB 촬영은 사용자 실행 대기였고 본수집 확정 0이었다. 현재 실제 진행은 위 State를 따른다.

기존 WINDOWS-CAPTURE-001의 실제 네 장 및 WINDOWS-CAPTURE-002의 원래 Evidence는 보존한다.



Product Selection:

완료: earbud_case_v0 — 열린 케이스 안의 실제 L/R 이어폰



Capture Tool / Configuration:

JSON profile 선택, v1 호환 + v2 설정 사본/해시, 네 시나리오 지원 완료.

Windows 촬영 창: 제품/상태 선택, DSHOW/MSMF 후보 선택, 실시간 미리보기,

원본 PNG 한 장 저장, 묶음/배치 관리, 기존 기록 검증·수량 복원.

Windows 전체 92/92 테스트 성공 (기존 56개 보존 + 추가 36개).

후속 안내 기능: capture-guide.json, 조건별 새 묶음, 모든 상태의 단계 안내, 준비/원본 검토 게이트.

새 전체 테스트 111/111 (원래 92개 + 안내 기능 19개). 검토 기록은 버전 있는 별도 JSONL이며 기존 manifest는 유지한다.

실제 Tk 창의 합성 입력 검증 이후, HCAM01L / DSHOW 후보2 / 1280×720 / MJPG 영상 수신과 PNG 저장을 확인했다.

장치 보고 FPS는 미확인(null)이다. 후보 번호는 현재 열거 결과이며 영구 장치 identity가 아니다.

실행: scripts/start_capture_windows.cmd (기존 프로젝트 .venv, 추가 설치 없음).

현재 기본 화면: 「시작 / 이어하기」 수집 길잡이. 수동/한 조건 도우미는 고급 설정 또는 --manual로 유지.

기준 사진2장 → 준비 시험12장 → 본수집 초기240장(4회차×3조명×5배치×4상태).

스탠드가 없으면 준비 시험4장/본수집80장으로 조정하며 제외 이유를 보존한다. 충분한 학습량의 보장이 아니다.

수집 계획/이벤트는 별도 v1 파일이며 기존 manifest v1/v2와 GuidedRound의 사진별 검토 정책은 유지한다.



Confirmed Formal Captures:

4장 (2026-09-13): NORMAL 1 / MISSING_LEFT 1 / MISSING_RIGHT 1 / MISSING_BOTH 1.

Session: S20260912T171113_B362774D. 같은 묶음, 실제 배치별 E0001~E0004.

사용자가 실물 배치와 준비를 확인했고, 사용자 요청에 따라 Codex가 GUI에서 상태 선택·저장을 수행했다.

기존 verifier의 reload/크기/기록/해시 검증 성공. 사진은 로컬 Git 제외 경로에만 있다.

이 네 장은 최초 구도·저장 흐름 확인용이다. 새 수집 길잡이의 준비/본수집 수량에 소급 편입하지 않는다.

과거 81장 계획 및 90장 제안을 현재 확정 수량이나 실적으로 사용하지 않는다.



Human Placement / Photo Review:

4개 상태의 사용자 배치 완료 / Codex가 실제 원본 4장을 열어 확인.

열린 케이스와 각 이어폰 상태는 보이나 노이즈·부드러운 윤곽이 관찰되어 구도/저장 확인용으로 유지한다.

최종 촬영 품질과 확대 수집 조건의 사용자 승인은 아직 없다.



V0-T05 / Labeling:

IN PROGRESS — 본수집120장 전체에240개 pending 초안 저장. 기존 review_first4_v001/을 보존하며 누적 검토 자료는 training/outputs/labeling/B01_B02_20260913/review_all120_v001/에 있다. 검토 이미지는 학습 입력이 아니다. 사람 라벨 검토0, B03 미시작.



Historical Next Task (B03 완료 이전; 현재 다음 작업은 Latest Checkpoint 참조):

V0-T05 — 사용자가 현재 VIA 작업을 보존한 뒤 project_draft_all120_v001.json을 Project → Load로 불러와 라벨을 확인·수정한다. 우선0001·0002의 기존 경계와0057 L·0081 R의 어두운 줄기를 확인한다. 전체 사진의 의미 정확성 확인은 별도로 필요하며 실제 확인한 사진만 사람 검토 완료로 기록한다. 이후 B01/B02 라벨 검토→B03 실제 독립 촬영/라벨링→그룹 분리→Windows 첫 학습 목표를 유지한다. 이번 작업에서 브라우저 조작·새 촬영·학습은 실행하지 않았다.

기준 사진 2장과 준비 사진 12장은 모두 사람 확인 완료이며 중복 촬영하지 않는다.

B01 필수60장에 대한 저장과 사람 확정이 완료됐으며 기존 불일치28장은 이력으로 보존한다. B02를 시작할 때 조명 준비 확인→물체 배치→한 장 준비 확인을 분리한다. 촬영은 매번 사람 준비를 확인한다.

B03/B04의 실제 독립 회차 확인을 유지한다. 같은 날이라도 실제 촬영 중단·시간 간격·설치 재준비 사실을 확인해야 하며 같은 연속 촬영을 이름만 바꿔 독립 자료로 취급하지 않는다.

수집 후 기존 T05→T06→T07의 라벨 검증·그룹 분리·baseline 순서를 이어간다. 시험 예약 자료는 학습·튜닝에 쓰지 않으며 기존 프레임 안내 영역을 부품 위치 정답으로 변환하지 않는다.



Evidence / Boundaries:

- 수집 길잡이: tasks/dataset-wizard-001.md; docs/verification/DATASET-WIZARD-001.json; training/capture_windows/DATASET_WIZARD_KR.md.

- 130/130 PASS. 기존 실제 원본/기록을 포함한 보호 파일149개 해시 일치, 패키지42개 버전 유지. 이번 새 실제 촬영0장.

- 안내 촬영 계약: tasks/windows-capture-002.md; 검증: docs/verification/WINDOWS-CAPTURE-002.txt.

- 기존 실제 PNG 4장과 manifest/session-info 총6개 파일 SHA256 일치. 이 사진은 안내 완료 건수로 소급 집계하지 않는다.

- 현재 촬영 화면 계약: tasks/windows-capture-001.md; 사용 안내: training/capture_windows/README_KR.md.

- 현재 검증: docs/verification/WINDOWS-CAPTURE-001.txt. 92/92 PASS, 보호 tracked 파일 150개 해시 일치, 설치 패키지 42개 버전 유지.

- 후속 실기기 검증: docs/verification/WINDOWS-CAPTURE-001-HARDWARE.json. 실제4장과 state/episode/크기/SHA256 연결, 재연결/GUI 수량 복원 확인. 단순 장치 목록 인식과 실제 프레임 수신·저장을 구분한다.

- 선행 준비 계약: tasks/human-capture-001-prep.md.

- 준비 검증: docs/verification/HUMAN-CAPTURE-001-PREP.txt; 보호 파일 229개 해시 일치, 기존 v1 sample 3장 검증 성공.

- 검사 명세·촬영 순서: training/datasets/proxy/earbud_case_v0/README.md.

- 기존 V0-T02 GPU smoke, T03 공통 계약, T04 수집 도구·사용자 실행 하드웨어 검증은 완료 상태와 원래 Evidence를 유지한다.

- T04 CAMERA_SMOKE 3장은 USER-EXECUTED / VERIFIED인 과거 관측이며 정식 데이터에서 제외한다. 현재 카메라 모델·노드·지원 포맷은 미확인이다. 당시 노드/FPS를 현재 값으로 가정하지 않는다.

- 이번 Windows 후속 작업은 사용자 승인 후 지정 USB 카메라를 연결하고, 실제 배치 준비 확인마다 한 장씩 저장했다. 자동 burst 촬영, Jetson 접속, CAD 수정, 환경 설치, 라벨링/분할/학습/튜닝/평가/변환/PLC 제어 없음.

- 합성 sample 검증은 실제 촬영·검사 성공·모델 성능 검증으로 집계하지 않는다.

- Detector/Decision/DB/HMI 구현은 기존 후속 Task 범위다. 준비 완료는 V0 완료가 아니다.


Commissioning follow-up: saved Sysmac I/O11 and ladder17 read directly, six saved copies hash-identical. Online equivalence unresolved (start/stop contact discrepancy). Computer Use native pipe unavailable; no mouse/PLC write. See current CHECKPOINT/sysmac_saved_source.

2026-10-13 EDS operator clarification: official unmodified OpENer EDS copied to notebook/deployment/plc/opener_reference/opener_sample_app.eds (upstream d8820ef41ce30dda06d213438ba81c81de33ffe2; SHA verified). README_KO.md gives exact library-install path. This is OFFLINE_LIBRARY_REFERENCE_ONLY, not a project-ready EDS: stock32/32 bytes and echo sample are incompatible with the current inspection application. Do not transfer stock connections to the PLC. Project Adapter/EDS byte contract remains NOT_IMPLEMENTED; actual Sysmac import/cyclic I/O NOT_RUN. No runtime/PLC changes. Next: finish matching adapter/EDS and existing6-tag layout; user does not need to source/write an EDS. Cleanup remains paused. Evidence: tag_data_link_008/EDS_REFERENCE_VERIFICATION.json.



## TASK-021 — PLC 자동 반복검사 배포 준비 (2026-10-14)

기준52ba2d4. 오래된 공개 allowlist 사진9개 제거, 유지보수 UI/Profile 누락 보완, 명시적 오프라인 필수 조립 자산 lock/패키지 검사. ARM64 Runtime287·배포31 PASS. 통합 패키지 engine-dev-267cd78f13b7bde8 /172파일. 실제 운영 engine-integrated-4920568fe3750b64는 미변경. Journal 이전 제품 이탈 proof0건, PLC 온라인 동등성/timeout·STOP/실물출구/Class1 안정성 미검증으로 자동운전 활성화 BLOCKED. 보고서: [TASK021](PLC_AUTOMATIC_DEPLOYMENT_READINESS_REPORT.md). 현장 교체/PLC 쓰기/START/Result·Done NOT_RUN. STOP_FOR_FIELD_DEPLOYMENT_APPROVAL.
