# 검증 근거 읽기

- `stl_validation.json`: 최종 소스에서 8개 STL을 새로 export한 결과. 소스/검증기/STL SHA256, 도구 버전, 실제 mesh 치수, 높이, 간섭 검사와 preview를 포함한다.
- `optical_fov` 항목: HARDWARE-CAD-003 최종33개 자세/429개 부품·자세 조합의 실제 STL 교차 검사. FOV90°/70°와 측면 법선 여유5 mm는 잠정 설계 조건이며 실제 영상 검증이 아니다.
- `optical_predicate_tests.txt`: 최종 build에서 실행한 광학 교차 알고리즘7개 테스트 결과. 면 관통·완전 포함·빈 cavity·여유 경계를 포함한다.
- `validator_selfcheck.json`: **CAD-002 당시 기록**. 실제 STL 구멍 중심을 메모리에서1 mm 이동했을 때 치수 검사가 실패하는지 확인한 음성 대조이며 이번 새 실행 결과로 세지 않는다.
- `scope_verification.json`: V2/보호 파일/ML 패키지 목록/V0-T05 보존 검사. `verify_scope.py`는 이 PC에 남아 있는 기존 환경 snapshot을 읽으므로 새 clone의 독립 CAD build에 필수인 검사는 아니다.
- `.txt`: OpenSCAD 원문 출력. 과거 진단 로그가 포함될 수 있으며 **최종 JSON에 나열된 검사만 최종 PASS 근거**로 사용한다.

OpenSCAD 교차 검사에서는 교차 형상이 비어 있으면 exit1과 `Current top level object is empty`가 나온다. 검증기는 메시지, 결과 STL 부재, ERROR/WARNING 부재를 함께 확인한다. 일반적인 exit1을 성공으로 바꾸지 않는다.

기계 CSG의 의도된 접촉면에는0.02 mm 수치 여유를 사용한다. 광학 triangle clipping은 별도의1e-7 mm epsilon을 쓰며 광학 Deck CSG는5 mm 확대 envelope를 축소하지 않는다. 실제 출력 STL을 축소하거나 자동 repair하지 않는다. 상세 범위와 한계는 [DESIGN.md](../DESIGN.md)와 [OPTICAL_VALIDATION.md](../OPTICAL_VALIDATION.md)에 있다. 실제 장비 치수와 출력품을 검사한 결과로 해석하지 않는다.
