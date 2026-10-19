# JETSON-PORTABLE-OPERATING-001

2026-10-19 사용자 요청: GitHub `jetson/` 폴더만 다른 Orin Nano에 복사한 뒤 문서의 장치 설정을 거쳐 현재 통합 프로그램을 사용할 수 있게 한다.

- 기준: 실제 적용·재부팅 검증된 `engine-integrated-32c484ac6aeb07f1`, Git `e53ba0b`. 현재 운영 장치 변경·접속 재시도·재학습·현장 재시험 없음.
- 현재 문제: 기존 `install.py/setup.sh`는 CORE MOCK 설치이고 참고 모델은 저장소 루트 assets에 있다. 통합 운영 설정/서비스 안내에는 과거 절차가 섞여 있다.
- 구현: 기존 검증 manifest 200파일을 바이트 그대로 수집한 오프라인 묶음, 별도 신규 장치 설치 진입점, 한국어 시작/설정/중지/검증 문서. 원본 코드·모델은 변경하지 않는다. 사용자 변경은 건드리지 않는다.
- 새 장치의 Python/GPU 환경은 직접 준비한다. 설치기는 패키지·네트워크·서비스를 자동 변경하지 않는다. 기존 설치/원장 덮어쓰기 거부, 설치 직후 새 원장은 빈 상태. 공개 승인된 SQLite368건은 읽기용 보관 폴더로 분리한다. 이후 기존 수동 UI에서 새 기준 진단·사람 확인·영역 저장을 수행한 기록만 최초 PLC 설정에 연결한다.
- 장치별 카메라·station ID·설치 경로·서비스 사용자만 생성한다. PLC 고정 주소/인터페이스/Assembly 계약은 문서로 명시한다. 새 장치의 물리 승인과 기존 현장 성공 증거를 혼동하지 않는다. 기본 물리 전송은 차단한다.
- 수용: `jetson/`만 분리한 입력으로 archive/source 해시 검증, 신규 설치·기존 설치 보존·경로 탈출/손상 거부·7모델·SQLite 무결성·장치 설정·서비스 생성 검증. 새 Orin Nano 실제 GPU/카메라/PLC/재부팅은 장치 미제공으로 UNVERIFIED.
- 추가 사용자 요청: `notebook/`에 촬영→라벨→데이터셋→실제 학습 소스도 함께 게시한다. 기존 도구를 재사용하고, 누락된 엔진 검출 학습 원본6개는 SHA 그대로 이관한다. 부품 참고 분류·전처리 소스와 필요한 데이터 준비 모듈도 포함한다. 학습·새 라벨 승인·E04 접근 없음.
- GitHub: 이번 설치·학습 소스만 선택 게시. 현재 운영 Release와 새 장치 설치 ID를 별도 기록한다. 실제 기본 브랜치는 master이며 main을 새로 만들지 않는다.

상태: 구현·분리 Git 트리 검증·GitHub master 게시 완료.
게시 커밋: `52d5e900f37d2da0953a4b1401e2f73ada55979c`. 원격 필수68파일 blob 대조, public/master·origin/master 추적 확인. 게시 영수증: `docs/verification/GITHUB-PORTABLE-20261019.json`.

- 묶음: 203파일/7모델, 운영 source200 SHA 보존, 70,712,513bytes. 과거 SQLite integrity=ok/368건, 새 활성 DB와 분리.
- Windows 설치15 중14 PASS/Linux전용1skip. Linux 최초 설치·확정 기준/영역·재설정 거부6 PASS. 별도 WSL 설치본 설정 점검 및 systemd unit 정적 검사 PASS. WSL은 x86_64이며 Jetson GPU 실적이 아니다.
- 분리 Git export: 학습 입력·그룹 검사6, 기존 전처리4, 촬영 시작·경로·재개5 PASS. VIA/YOLO/분리/학습/평가 CLI help와 신규 데이터 모듈 import PASS. 원본 학습 소스6 SHA 유지.
- 분리 검사에서 누락된 SCENARIO_GUIDES 의존 파일을 함께 게시하도록 보완. 공개된 기존 촬영 UI 동작은 그대로이며 추가 준비 API의 전체 UI 연결은 이번 범위가 아니다. 임시 시험기의 잘못된 모듈명·작업 위치·sandbox 임시폴더 오류는 각각 수정하고 로그 보존.
- 새 Jetson GPU/카메라/PLC/재부팅과 전체 학습 데이터 재현은 UNVERIFIED. 현재 장치 재배포·학습·실물시험 없음. 상세: `docs/verification/JETSON-PORTABLE-OPERATING-001.json`.
