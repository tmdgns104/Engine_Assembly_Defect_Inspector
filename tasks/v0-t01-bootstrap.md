Task ID: V0-T01
Title: Bootstrap / Project Foundation
Status: DONE

## Purpose
V0 실험 기반을 안정적으로 시작하기 위해 저장소 구조, 필수 문서, Task 분해, 환경 점검 결과를 한 번에 정리한다.

## Dependencies
- Git 초기 상태 여부
- 필수 시스템 권한(쓰기 권한)

## Allowed Changes
- Git 초기화
- 디렉터리/파일 생성
- 환경 점검 결과 기록
- Task 문서 초안 작성
- 기존 파일 존재 시 보존

## Forbidden Changes
- 기존 데이터/설정 파일 삭제
- 대형 데이터셋 다운로드
- 모델 학습 실행

## Implementation
1. 현재 루트 상태 확인 (빈/기존 파일 여부, git 상태 확인)
2. Git 저장소 초기화
3. 환경 점검 (Windows, Python, pip, Git, GPU, Driver, CUDA)
4. 권장 구조 생성
5. `docs/*`, `tasks/*`, `training/*`, `src/*`, `apps/*`, `tests/*`, `models/*`, `recipes/*`, `config/*`, `data/*`, `scripts/*` 생성
6. V0 대상 Task를 세분화하고 각 Task에 공통 템플릿 적용
7. `docs/STATUS.md`를 실제 진행 상태로 기록
8. `git status`로 변경사항 검증

## Verification
- `git status --short`
- 필수 문서 존재 확인
- Task 목록과 `STATUS.md` 상태 일치 여부
- 디렉터리 구조가 요구사항을 충족하는지 확인

## PASS Criteria
- Repository가 git 저장소로 초기화됨
- V0-T01 결과가 문서화됨
- 다음 Task가 `V0-T02`로 설정됨
- 데이터/학습/모델 실행을 수행하지 않음

## Artifacts
- `README.md`
- `docs/PROJECT.md`
- `docs/REQUIREMENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/STATUS.md`
- `tasks/README.md`
- `tasks/v0-t01-bootstrap.md`
- 생성된 디렉터리 뼈대
