# 현재 검사에 필요한 AI 자산

기본 검사 모델 두 개는 `jetson/products/ENGINE_Z3005_5/`에 있습니다. `dynamic_parts_005/model.plan`은 부품, `envelope_v007_fp16/model.plan`은 엔진 전체 검출에 사용합니다. 기존 TensorRT 바이트와 manifest 해시를 보존했습니다.

`misassembly_runtime/FROZEN_MANIFEST.json`의 28개 파일은 기존 운영 실행본의 참고 오조립 분석 의존성입니다. 전체 위치 검출 PT 1개·부품별 분류 PT 4개, 기준 자산과 동결 추론 소스를 포함합니다. 상대 경로가 해시 계약에 포함되어 하위 `runs/` 이름을 유지합니다. 학습 이력 전체를 공유하는 폴더가 아닙니다.

다운로드 후 각 manifest의 SHA256으로 확인할 수 있습니다. 원본 모델 변환·재학습은 이번 작업에서 하지 않았습니다. 참고 오조립 분석은 현재 최종 PASS/FAIL을 바꾸지 않습니다. 모델 파일 포함과 새 장치에서 실제 CUDA/TensorRT 실행 검증은 서로 다른 항목입니다. 지원 장치와 라이선스 안내는 `jetson/products/README.md`를 따릅니다.
