# 프로젝트 작업 원칙

- 현재 편집 원본은 `jetson/`(장치 실행)과 `notebook/`(개발·촬영·배포 도구)이다. 루트 README에서 설치본/개발본/채택 상태를 구분한다. 옛 루트 src/apps/training/scripts와 runs 후보를 새 원본으로 고치지 않는다.
- 기존 STATUS·현재 Task·관련 계약부터 확인하고 완료 증거를 재사용한다. 소스·배포 구조는 루트 README와 `notebook/deployment/README.md`, 엔진 종료 실패 증거는 `runs/engine_dynamic_pose_002/fixes/ENGINE-PRODUCT-TRACK-ROBUSTNESS-002/STATUS.md`를 따른다.
- 구현 우선 + 변경 영향에 맞춘 검증: 짧은 관련 점검을 병행하고 사용할 후보에서 최종 회귀를 묶는다. 작은 수정마다 전체 재생·회귀·재배포를 반복하지 않는다. 세부 원칙은 `CODEX_INSPECTION_APP_V1_KO.md`의 2026-09-28 절을 따른다.
- 현재 사용자 변경·원본·Journal/Evidence·모델·승인 기록을 보존한다. E04 보호 자료는 열람·추론·정리 대상에서 제외한다. 실제 PLC 출력 승인, PASS/NG 극성, 요청·제품·결과 연결, 카메라 장애 보호는 줄이지 않는다.

## JETSON-RUNTIME-ONLY

- Jetson은 실행 장비이며 개발 이력 보관소가 아니다. 상주 Runtime은 `/home/jetson/oned_device_bench/current` 한 벌이다(2026-09-28 전환 완료). 실제 release ID·해시로 적용을 확인한다.
- 개발 소스·테스트·재생·촬영/학습 자료·검증 결과·과거 버전은 노트북에 보관한다. 기존 archive/backup 또는 `archives/jetson`을 사용한다.
- 노트북의 기존 패키징/배포 스크립트를 확장해 명시적 allowlist/manifest로 필요한 코드·HMI·설정·자산·기동 점검만 배포한다. 전체 runs/fixes나 과거 후보를 영구 복사하지 않는다. 운영 import/self-test 의존성과 MOCK gateway를 이름만 보고 제외하지 않는다.
- Jetson 네이티브 검증은 필요한 파일만 `/home/jetson/oned_device_bench/tmp/verify` 한 곳에 임시 반입한다. 결과·오류·버전 식별정보를 노트북으로 회수하고 무결성을 확인한 뒤 해당 임시 사본을 정리한다. 회수 실패 시 원본을 보존한다.
- 실행 환경·overlay·모델·운영 데이터는 별도 보호한다. candidate라는 이름만으로 삭제하지 않는다. 코드 업데이트로 Journal/Evidence·승인·가상환경을 덮어쓰거나 이전 이력 조회를 깨뜨리지 않는다. SQLite 실행 중에는 DB 본체만 복사하지 않는다.
- 프로젝트 관리 경로만 KEEP_RUNTIME / KEEP_DATA / ARCHIVE_TO_PC / TEMPORARY / UNKNOWN으로 분류한다. 링크·실제 프로세스 의존성을 확인하고 UNKNOWN과 E04는 삭제하지 않는다.
- 현재 v004의 남은 검증/채택 여부를 먼저 정리한다. 단일 경로 전환·기존 자료 제거는 배포 대상과 정상 실행 확인 뒤 수행한다. 미검증/실패 후보를 최신이라는 이유로 승격하지 않는다.
- 업데이트 중 새 패키지·직전 복구본만 일시 허용한다. 완료 후 이전 버전은 검증된 노트북 백업으로 보관한다. 기존 자료 삭제는 백업 검증 + 새 실행본 확인 + 정확한 삭제 목록·예상 확보 용량 제시 뒤 사용자에게 한 번 승인받는다. 승인된 경로만 삭제하며 심볼릭 링크를 따라가지 않는다.
- OS·JetPack/CUDA/TensorRT·SSH/Tailscale·네트워크·다른 프로젝트·전역 설정은 변경하지 않는다. launcher/service·노트북 실행 경로와 기존 `/auto` 주소를 함께 확인한다.
