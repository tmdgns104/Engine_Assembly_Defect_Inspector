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

## 2026-10-18 추가 요구: 위치·카메라 편차와 운전 영상

사용자 추가 지시를 현재 A/B/C 안정화 작업에 통합한다. 기존 후보/회귀/속도 결과 보존.
허용 위치·각도·카메라 편차는 현장 영상 분포로 측정하며 임의 cm/px 범위를 만들지 않는다.
정상→PASS/OK, 결품→FAIL/NG, REVIEW→NG, 유효 거래 ERROR→NG. 원인/원본 보존;
거래 완료와 유효 새3장 검사 성공을 분리한다. 3초·0.6초·3장·400ms·부품/STOP 보호 유지.
검출 안정성은 제품 선택→자세→슬롯→motion 초기화→3장 집계까지 점검한다.
정상 위치/각도 편차, STOP에서 바꾼 카메라 위치, 미세 진동, 실제 이동/가림/화면 이탈,
결품/빈 벨트/다른 물체를 분리 검증한다. 보정·별도 검증 구간도 분리한다.
원본 운전 영상은 기존 자료/수집 경로로 충분한지 먼저 평가한다. 현재 승인 범위는
기존 Worker·인증·fresh STOP·RequestLOW·검사/저장 유휴의 최대5초 진단 촬영뿐이다.
운전 중 신규 수집/접근 정책 변경은 부담·안전조건·변경범위를 보고하고 별도 확인받는다.
진단에서 START/STOP/모터 제어 없음. 운전 중 벨트/카메라에 손대도록 요구하지 않는다.
최종 같은 실행본·한START·PLC+Jetson 정상/오른쪽파이프 결품 혼합30, 이전 구간 합산 금지.


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
2026-10-17 후속 목표는 결품만30회→정상·결품 혼합30회. 사용자가 현재 운영본으로 먼저 시험하고 이후 수정하도록 선택했으므로 새로운 운영 변경은 하지 않는다. 정상 첫30 통과는 아래 증거로 보존하고 새 시험과 합산하지 않는다. tracking session 교체만으로 저장준비가 해제되는 격리 재현 POST37_READINESS_REPRO.json은 개선 후보의 근거이며 운영 수정/실물 PASS가 아니다.
현재 사용자가 배기구만 빠진 모형과 가운데 문양만 빠진 모형을 각각 준비했다. A/B/C 대신 실제 상태 이름으로만 안내한다. 실제STOP·빈벨트→기록기5851→START/IDLE/기준37·새요청0→노트북LAN 분리 확인 후 두 결품을 번갈아30회 투입하도록 안내했다. FAIL 후 배출/재가동하면 계속하고 오류·재가동불가이면 추가START 없이 알리도록 했다. 운영555c3a43053ce4ce/같은boot/Worker2741 유지. 기대정답은 수집기 평가 목록에만 저장되며 Detector에 전달하지 않는다. 정확한 순서·실제 횟수·완료/유효사진/정확도는 재연결 후 감사 대기. 정상·결품 혼합30은 아직 미실행이다.
증거 runs/mixed_stability_20261017/{fail_OPERATOR,fail_READY,fail_START,fail_PLAN,fail_NOTEBOOK_DISCONNECTED}.json; Jetson data/engine_dynamic_pose_002/acceptance/continuous30_20261017_attempt12_fail. 수집기 기준파일 읽기 경합은 PREPARATION_ISSUE.json으로 보존하고 동일 실행 PID로 복구, 장치 프로그램 변경 없음. 다음 행동은 사용자 완료/멈춤 응답 뒤 STOP·LAN재연결을 한 번에 하나씩 안내한다.

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
CAPTURE STABILITY TASK AUTHORIZED / CANDIDATE NOT DEPLOYED
2026-10-17 최신 첨부TASK의 촬영 안정 판정 개선을 진행한다. 원시ERROR4건1feea8a2/680c0018/45062997/7e21efd2 모두 촬영DEADLINE_EXCEEDED, 후보11·거부9/11/11/10. 이전e14586d0와 같은 안정연속3장 부족 경로. 8건 비교증거·32자산SHA·24원본 보존, 마지막3장으로 전체촬영창을 복원하지 않는다. 운영a8afabe667e881ed 변경 없이 STOP/LOW확인. motion후보10PASS, Worker포함23건 중 품질불량 기대1건 불일치 확인중. docs/STATUS.md 최신 및 runs/capture_stability_20261017 참조. 대상영역0.008 초과 실례가 남아 적용/재부팅/30회 미실행. 다음: Worker·같은원본/native비교·결품회귀·C시계열·최소UI.

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
# 실제 30회 연속 운전 시험

## 2026-10-17 현재 승인 기준과 진행 위치

최신 현장: attempt09에서 실제 START/IDLE/새 카운터0 확인 → 사용자 노트북 LAN 분리/SSH 단절 확인 → 정상 모형 연속 투입. 사용자가 약14번째로 추정하나 정확한 횟수는 모른다고 했고, 검사 후 멈췄다고 명시했다. 실제 STOP 버튼 확인 완료. 노트북 LAN 재연결 후 Jetson 원기록으로 실제 완료 수와 최초 오류를 확인할 예정이다. 30회 성공 아님; 수정/재시작/새 START 없음. GitHub source commit `01cf5ff` push·원격SHA 확인. 이하 준비 기록은 보존한다.

최신진행: `f03d3f570a172c5f` 실제적용·189파일SHA확인·재부팅자동복귀 완료. 새boot `c050e0e3-9cd9-4b69-80de-76932fd6616d`, Main1078/Worker2758/NRestarts0, WAIT_START. 추가31.36초7프레임정상. 기존rawPASS/미전송건은검증된ABORTED추가로보존,가짜PLC완료없음. 사용자정상모형준비확인. Jetson자체GET-only 기록 PID4503, `data/engine_dynamic_pose_002/acceptance/continuous30_20261017_attempt09`. START 실신호/IDLE/RequestLOW/오류없음/카운터0 확인. 사용자노트북LAN분리 및 SSH접속단절 확인 후 정상30회연속투입안내; 실제건수·결과검증대기. 아래후보대기문장은직전단계기록이며최신진행이우선한다.

최신 사용자 TASK가 아래 과거정상PASS 전용기준보다 우선한다. **연속처리 안정성과AI정확도를 분리**한다. 같은운영본·한START로 새원본3장→실제AI→필수저장→C의Result/Done→RequestLOW→다음요청 정리가30회 이어져야 한다. REVIEW/실제결품FAIL은기존NG/Done으로끝나고다음검사를허용하며, 그판정만으로시험을중단하지않는다. 사진없는ERROR·실제시스템장애·거래소유권불명확·수동소프트웨어복구는별도실패로남긴다. 3/10체크포인트도같은연속시도이며, 재시작·수정전성공수는합산하지않는다. 노트북/Codex/SSH/웹/PC수집기는검사필수요소가아니어야한다. 최종실물시험은PLC·Jetson단독조건을확인한다.

현재 후보 `engine-integrated-f03d3f570a172c5f`, 운영 `a807de46a264aa3e`. 촬영3초/원 trigger부터처리·원본저장15초 분리와기동잔여IPC복구8파일. 관련Windows/ARM64 각338실행(337PASS+1skip), C/Python격리7PASS(한START12회지연matrix), startupARM64 39PASS,추가queued-result5PASS. 합성시험을실물30으로세지않는다. 후보 staged, **아직배포·재부팅전**. 사용자STOP·벨트모형제거 확인및실제STOP/LOW/출력0 대조완료. c7f…원PASS/미전송기록을기존append-only절차로보존정리할읽기전용검증완료. 사용자sudo 시작명령대기. 증거 `runs/runtime_audit_20261017`, 단일감사보고서 `docs/CONTINUOUS_RUNTIME_AUDIT.md`. 단독30회/장시간안정성 미달성, GitHub최신화 대기.

## 과거 시험 기록 — 당시 기준과 실패를 그대로 보존

2026-10-16 사용자 승인: 실제 30회 동안 오류 없는 연속 운전을 목표로 시험한다. 직전 재부팅 성공 1건은 제외한다. 정상 조립 모형의 반복 투입을 기본으로 운전 안정성을 먼저 확인한다. 기대 상태는 시험 기록에만 남기며 Detector/판정 입력으로 주입하지 않는다.

현재 실행본 engine-integrated-1e913c895d7f9969, 기존 모델·PLC·판정 정책 유지. 0/30, 실제 시험 대기. 사용자 STOP·빈 벨트 확인(“비웠어”). 별도 재시작/Reset/권한 부여 없이 START 한 번 후 새 투입·요청을 관찰한다. 각 회 고유 ID/새 원본/SQLite 저장/최종판정/Result→Done/Request 해제·물리 표시등·재이송을 연결한다. 한 제품이 완전히 배출된 후 다음 투입을 안내한다.

오류·잘못된 판정·중복/유실·카메라 또는 Worker 교체·통신 장애·소프트웨어 개입·관측 누락은 숨기지 않는다. 발생하면 물리 STOP 요청 후 해당 시도를 보존하고 원인을 확인한다. 수정이나 재시작 후 재시험은 새 attempt이며 앞선 성공 수를 합쳐 30연속 성공으로 표시하지 않는다. 기존 Assembly REVIEW는 별도로 집계하고 조립 정확도 PASS로 바꾸지 않는다.

수집: Windows 읽기 전용 HTTP 관측, Jetson 실제 추론/원기록. runs/continuous_30_20261016/에 시작 카운터·상태·저장 검사·물리 확인을 보존. STATUS.jsonl은 2초 간격 상태 관측이며 짧은 오류 전체를 보장하지 않으므로 종료 시 Jetson 이벤트/로그도 대조한다. 요청→PLC 완료 latency의 각 값/최대/p50/p95와 실제 경과 시간을 보고한다. 30회 성공은 해당 시간·조건의 시험 결과이며 무기한 신뢰성 보장이 아니다.

최초 동작은 관측기 시작→빈 벨트 START→정상 모형 1회 투입. 사용자 물리 행동은 한 번에 하나씩 요청. 기존 원본/백업 보존, 학습/튜닝/전처리/임계값 변경 없음.

## Attempt 1 — 1회 실행, 정상 판정 연속 성공 0/30
사용자 START·정상 모형 투입 후 38d34a9e292c4897b2c589e405498cbb: SQLite COMPLETE/REVIEW, PART_ASSIGNMENT_UNCERTAIN. 새3PNG+overlay SHA 검증. frame7562/7564 pipe_left 미검출,7563 score0.349562645<기준0.5 LOW_CONFIDENCE; slot overlap≈1/pose OK. 원본에서 해당 파이프가 보이고 흰 가이드와 겹치나 접촉·저점수의 시각적 원인은 미확정. Assembly REVIEW 별도. 최종 REVIEW→PLC NG, Result/Done/completed 각1증가·RequestLOW. 동일 Worker2669/epoch 유지, 현재 오류null. 사용자 STOP(정지했어) 및 Mc_Run=false 확인. 임계값/모델/코드 변경 없음. 실제 가이드 접촉 여부 질문 대기; 이 실패를 제외한 누적을30연속 성공으로 표시하지 않음. Evidence runs/continuous_30_20261016/TRIAL01_* 및 STATUS.jsonl.

현장 확인: 사용자가 흰색 측면 가이드에 '닿거나 걸쳤어요'라고 답했다. 실제 접촉은 사용자 관측으로 확인, 저점수의 인과는 미확정. 다음 시도는 가이드 비접촉 배치 조건으로 구분하고 같은 모델/임계값을 유지하며0/30부터 새로 기록한다. 첫 실패를 소프트웨어 정상/배치만의 문제로 확정하거나 삭제하지 않는다. STOP 유지 중 모형을 벨트 밖으로 옮기는 행동부터 요청한다.

접촉 대상 재확인: 컨베이어의 흰색·밝은 회색 측면 가이드라고 설명한 후 사용자가 '응 살짝 닿았어'로 확인했다. 약한 접촉 사실만 확정하며 원인 단정 없음. 다음 실제 행동은 STOP 유지 상태에서 모형을 벨트 밖으로 내려 빈 벨트를 만드는 것.

Attempt 2 준비: STOP·빈 벨트 질문에 사용자 '응' 확인. 기존 관측기 종료 후 attempt02/에 읽기 전용 관측을 새로 시작했다. 실제 START 전0/30, baseline request/result/done/completed=2. 모델/임계값/서비스 변경 없음. 관측 프로세스 session87328. 다음 행동은 빈 벨트 START1회.

Attempt2 1/30 확인: 59d25ada6a9b49e4a078a8f8f21c0276, 기본PASS/최종PASS/AssemblyREVIEW. 새3PNG+overlay SHA 및 SQLite COMPLETE·final durable·PLC completion 확인. Result/Done/completed=3, RequestLOW. 사용자 정상등·재가동·배출 모두 확인. 요청→게시11.375초. 다음2회차는 서비스 재시작·Reset·START 없이 같은 정상 모형의 새 물리 투입.

Attempt2 2/30: 31a59833f92c472480c6013827d392cb, 기본PASS/최종PASS/AssemblyREVIEW. 새3프레임(기존과ID중복없음),4asset해시,SQLite COMPLETE/final durable/PLC completion 확인. 요청→게시5.559초. 사용자 초록LED·재가동 확인; 배출 완료는 명시 확인 전이므로 다음 안내에 완전 배출 조건 유지. 서비스/Reset/START 추가 없음.

Attempt2 3/30: 1b6d4ee23c7945fea6719dfb1a2a8f99 기본/최종PASS,AssemblyREVIEW. 새3프레임·4asset SHA·SQLite/final durable/PLC completion 확인. 요청→게시18.774초로 지연 편차 존재. 사용자 초록LED·재가동·배출 모두 확인. 추가STOP/START/Reset/재시작 없음.

Attempt2 4/30: 8acf41b4de1d43b292fac2188ed313eb 기본/최종PASS,AssemblyREVIEW. 새3프레임·4asset SHA·SQLite/final durable/PLC completion 확인. 요청→게시7.236초. 사용자 초록LED·재가동·배출 모두 확인. 같은Worker2669/epoch, 추가STOP/START/Reset/재시작 없음.

Attempt2 5회차 FAIL:31d3b24a13a749f1afe20fac516b8b5f 기본PASS→조립FAIL→최종NG. pipe_left OUTWARD_SPLAYED 3장일치(0.789/0.570/0.537),원본3장/4asset SHA/SQLite/PLC 완료 확인. 정상투입 기대와 불일치로 연속4성공 뒤 중단 요청. 사용자 '추가 조립은 참고사항 아니었나' 질문으로 요구/현재 정책 불일치 발견. 현재 BASIC_WITH_CONFIRMED_ASSEMBLY_FAIL_V1은 조립FAIL을 최종NG에 반영; 임의 변경 없음. 오조립 실제 정답·현장 오탐 미확정. 물리STOP 확인 대기, 마지막 Mc_Run=true/RequestLOW. 추가 투입 안내 없음.

정책 변경 승인: 사용자가 '미결합만 PASS/FAIL', '오조립은 최종 pass/fail에 영향을 끼치면 안되'를 명시했다. BASIC_PRESENCE_ASSEMBLY_REFERENCE_V2 후보: 오조립FAIL도 기본결과를 변경하지 않음, 참고결과 및 원본/저장/장치 보호 유지. 저장된5회차 정책 비교와 Windows70pass/1Linuxskip, Node UI검증. 이전NG 기록 수정 없음. 실제PLC STOP/LOW·유휴 확인, attempt2 종료(5회실행/4연속성공). 새 정책 배포 후 별도시도0/30. Jetson sudo인증 필요; 적용 전.

2026-10-16 reboot-context followup: presence-only release8ec7803406389df2 deployed/185SHA verified; first reboot autostart hardware ready but old product31d3b24a blocked. Operator STOP/empty confirmation recorded via existing close API, no grants/replay/result changes, WAIT_START. Second reboot requested after guarded readiness; SSH/ping unavailable; user power-cycled after no-monitor confirmation. Reboot readiness acceptance pending. New gate + context regression14PASS; Windows sandbox asyncio socket stall diagnosed and same tests passed with loopback permission. No runtime source/model/threshold change in this followup.

Controlled reboot after context closure verified: boot53d5f9c7, Main1165/Worker2702, 185SHA, camera/model/PLC ready/WAIT_START, no manual postboot recovery. Disconnect→ready95.34s (sampled); same Worker/newframes63.8s. Earlier failed boot/USB recovery retained, cause unproven. No new product request yet; new policy attempt0/30. Acceptance evidence runs/reboot_context_20261016/ACCEPTANCE.json.

Attempt03 ended after4 actual cycles/3consecutivePASS. IDs and timings in runs/continuous_30_20261016/attempt03/ATTEMPT_RESULT.json. First actual assemblyFAIL remained finalPASS per user policy; trial4 product-selection scores<0.5 prevented all part evaluation but old function returnedFAIL. Operator STOP+empty confirmed; same-ID context closure recorded. Minimal unassessed-product REVIEW correction deployed c3df373d33beb51f after170file/SQLite backup; 9PC/9ARM64PASS, stored1–3PASS retained/4REVIEW. Actual reboot5868d22b and soleWorker2696 camera/model/PLC/WAIT_START verified without manual recovery. No model/threshold change; no live product under final correction. Detection confidence instability remains; do not blindly repeat or count REVIEW as a successful normal test. Final STOP.

Attempt04: user directly started continuous normal-engine feeding under unchanged c3df release. Requests1-7 finalPASS, each3newPNG+overlay SHA/SQLite COMPLETE/final durable/PLC cyclic completion verified. Request8 4e2a205635e34c3dbc1dcdcac467be5e ERROR NO_VALID_CURRENT_PRODUCT_AT_PLC_REQUEST, no part inference/images,30.069s publication. Track1 frozen at5390, eligibility lost5387,5419 WAIT_AREA_CLEAR/MISSED_OBSERVATION_LIMIT. Operator confirmed engine stopped inside camera area atERROR, then STOP and removed engine. Empty preview is AFTER removal, not error-time evidence. Initial cycles recovered from durable records; physical LED/exit confirmations not individually obtained. Attempt stopped7recordedPASS/8requests,30goal NOT MET. No runtime/model/threshold changes. Next: existing bounded diagnostic capture of one new passage to determine loss-of-detection cause. Evidence runs/continuous_30_20261016/attempt04/ATTEMPT_RESULT.json.

Attempt04 followup: existing maintenance close API recorded actual operator STOP+engine removal against latest physically inspected request7 0e7f298f8bdc44cfb38c2c8cde5771ed (request8 was not_executed). Receipt grants0/replayfalse; PLC counters/output unchanged. Same cameraWorker2696, error/identitynull, diagnostic capture IDLE. Next human action requested: empty-belt physical START, no product yet. After reply enable bounded existing capture, then one diagnostic insertion, separate from 30-cycle qualification. No deployed code change/reboot required for this diagnostic operation.

After user START, bounded diagnostic capture POST was rejected403 PHYSICAL_BUTTONS_ONLY_IN_STANDALONE_MODE; no capture started and no bypass. Existing GET-only laptop observer now saves full status, displayed preview (not raw/model input), and consumed trace for max30min/30new results or firstnonPASS. session63705; evidence diagnostic_after_attempt04/readonly_run01. User requested continuous feeding with full product separation; instructed one at time and STOP on nonPASS. Runtime unchanged. Initial baseline excludes historical results; final same-ID asset/SQLite/PLC audit still required.

Readonly diagnostic run01: user reported accidentally inserting exhaust-missing model. Request9 6da95738b12c40c8b818895a0db58db7 actualFAIL/EXHAUST_TOP_MISSING, other3slots PRESENT. Same-ID3raw+overlay SHA/SQLite COMPLETE/finaldurable/PLCcompletion verified; classify separately as missing-exhaust case based on userstatement, no label given to detector. Not a normal30 failure/success; normal sequence not started. Operator STOP confirmed/PLC Mc_Runfalse. Need remove/reassemble offbelt then new continuous normal sequence.

Attempt05: operator STOP/removal after accidental exhaust-missing case, offbelt exhaust reassembly confirmed. Existing context close receipt for6da957... grants0/replayfalse. SameRuntime c3df/Worker2696. GET-only observer session46966 under attempt05/observation began before actual START; user START confirmed and sampled Mc_Runtrue/IDLE/cameraReady/identitynull. Normal30 starts0; user instructed continuous single-model feeding after prior exit, no per-cycle chat. On firstnonPASS observer freezestrace/status and stops; raw/SQLite/PLC per-ID finalaudit required. No runtime change.

Attempt05 ended after one partPASS request10 023998fb235048039f765b2a4786eabe with4verified assets (attempt04 separately had28). PLC completion verified; passage failed before next valid cycle, so0fullyaccepted continuous cycles. Consumed43657→43663 sourcegap0.540s >0.5, concurrent service-lock488ms. User STOP+empty confirmed; existing context closure recorded. Candidate only inspection.py product metadata queue2→16; source/freshness/identity gates unchanged. Red4tests onefailure onlostintermediates; relevant59PC/59nativePASS; broader75PC73pass2preexistingfailures independently reproduced. Actual old/candidate diff verified onehunk. See runs/observation_buffer_20261016/CHECKPOINT.md. Pending user sudo transition; no deployment/reboot yet.


Queue-buffer candidate applied as b31d30deafa06bc3; real reboot/autostart verified. {"release": "engine-integrated-b31d30deafa06bc3", "boot_id": "aa1202d3-2be1-4630-afeb-55324432b37e", "files_verified": 185, "observed_disconnect_to_ready_s": 86.79, "ready_observation_span_s": 213.09, "postboot_manual_recovery": false, "previous_result_preserved": true, "live_field_after_patch": "PENDING", "continuous30": "NOT_ACHIEVED", "windows_related_tests": 59, "native_related_tests": 59, "broader_windows_tests": {"tests": 75, "passed": 73, "preexisting_failed": 2}, "unresolved": ["Intermittent envelope observation loss", "Long field response latency", "Long duration stability"]}

Attempt06: 3 actual saved PASS followed by trajectory discontinuity, not 30 success. Source4831→4832 68.011ms; bbox right edge +67.19px, center +33.86px, threshold32px; actual reverse motion not proven (raw failure frames unavailable). New authorized cycle-scoped standalone.py fix preserves past tracking diagnostics and all safety guards; new settled PLC requests require post-request fresh observations. See runs/cycle_scoped_tracking_20261016/CHECKPOINT.md.
{"release": "engine-integrated-d9b96517ee8cc330", "boot_id": "2ad712f0-f04d-44c8-9bd7-3a054a44ef18", "files_verified": 185, "previous_result_preserved": true, "observed_disconnect_to_ready_s": 97.41, "ready_observation_span_s": 90.64, "postboot_manual_recovery": false, "windows_executed_pass": 201, "arm64_executed_pass": 201, "skipped_per_platform": 1, "native_synthetic_ipc_pass": 1, "unchanged_ui_checks": "1 hung / 1 expectation mismatch; not counted PASS", "continuous30": "NOT_ACHIEVED", "field_attempt": "attempt07 started; separately audited", "browser_visual_verification": "Blocked by browser tool URL policy; no workaround", "remaining": ["Actual 30 consecutive acceptance", "Response latency", "Long-duration reliability"]}

Attempt07: {"attempt": 7, "inspection_id": "4c2a3c2053bc4f3c8725427c40dd9d90", "actual_cycles": 1, "consecutive_normal_pass": 0, "target": 30, "acceptance": "NOT_ACHIEVED", "first_failure": "PRODUCT_ENVELOPE_NOT_FOUND", "final_decision": "REVIEW", "plc_decision": "FAIL", "assembly_affects_final": false, "request_token": "12fc0f5b73260297:1:1", "cycle_admission_evidence": {"accepted_at": 189.928870562, "physical_product_identity_proven": false, "policy": "PLC_CYCLE_FRESH_OBSERVATION_V1", "previous_transaction": null, "product_exit_claimed": false, "request_token": "12fc0f5b73260297:1:1", "start_counters": {"completed_count": 0, "done_count": 0, "result_count": 0}}, "software_aggregation_reproduced": true, "model_inference_reexecuted": false, "three_new_frames": true, "raw_images_visually_inspected": true, "visible_observation": "Engine visible in all three originals; no hand or obvious guide overlap visible. Visual inspection alone does not establish part correctness or cause of weak scores.", "scores": [0.37708017230033875, 0.4063781499862671, 0.36192482709884644], "threshold": 0.5, "frame_ids": ["15cc896331b34745a45a95187be23e79-1868", "15cc896331b34745a45a95187be23e79-1871", "15cc896331b34745a45a95187be23e79-1873"], "selected_frame_age_ms": [40.99781799999391, 39.55206200001271, 35.94359899997812], "global_quality_valid": [true, true, true], "part_inference": ["NOT_RUN_WITHOUT_RELIABLE_PRODUCT_POSE", "NOT_RUN_WITHOUT_RELIABLE_PRODUCT_POSE", "NOT_RUN_WITHOUT_RELIABLE_PRODUCT_POSE"], "request_to_first_source_s": 18.848408062000033, "request_to_final_ms": 24170.89475200001, "durable_and_plc_events": true, "assets_verified": 4, "physical_led_conveyor_confirmation": "NOT_YET_CONFIRMED", "stopped": true, "cause_scope": "Current product detection below unchanged threshold, not previous-cycle identity blocking", "visual_cause": "UNCONFIRMED: not enough evidence to isolate lighting, pose, background, or model generalization", "next_cycle_after_prior_tracking_error": "NOT_FIELD_VERIFIED: trial stopped after first REVIEW", "no_runtime_threshold_model_change": true}

User authorized saved-image investigation, reserving model/threshold decision. Jetson9 exact score reproduction; PT21 threshold selection matches, strict box parity fails minIoU0.919173. Spatial sensitivity in both backends (-4px makes0.69→0.46); lighting alone not supported. Report: runs/continuous_30_20261016/attempt07/PRODUCT_DETECTION_INVESTIGATION.md. No runtime/model/threshold edits during investigation; 30notachieved.

## Attempt08 — 실제 2요청, PLC완료1, 기한 결합 재현
ATTEMPT08 STOPPED / CAPTURE-STORAGE DEADLINE COUPLING REPRODUCED / 30 NOT ACHIEVED
2026-10-16 engine-integrated-a807de46a264aa3e에서 실제2요청/부품PASS2/통합final·PLC완료1. 두번째 c7f15ae32e61473db2f607efc11f5ff3는 유효3장·원판정COMPLETE/PASS·4자산 저장됐지만, 촬영3초를 저장기한으로도 사용하는 STATIONARY 경계에서 STORAGE_DEADLINE_EXCEEDED→PYTHON_NOT_READY로 취소. 통합final/PLC전송 없음. 이번 health최대192.385ms<400ms, 이전418ms 갱신지연과 구분. native SQLite/event8자산SHA·6원본픽셀 검증, 실제 운영SHA동일 Service의 fake clock으로 해당 기한 결합 재현.
사용자 STOP 및 실제 PLC STOP/RequestLOW/출력0/Worker·저장유휴 확인. 운영 수정/복구/재전송/새검사 없음. 촬영3초 유지+기존15초 총처리기한 분리 제안은 현재 STATIONARY 취소 동작 변경이므로 미구현·설계승인 대기. warm reboot 자동복귀 미확인/수동power cycle autostart 확인 구분 유지. 상세 runs/continuous_30_20261016/attempt08/ANALYSIS.md. FIELD100 기존수량·보정/검증분할 변경없음.
