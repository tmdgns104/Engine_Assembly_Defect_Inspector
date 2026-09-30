# 배포에 포함된 운영 모델·자산

사용자 요청(2026-09-30)에 따라 기존 운영 패키지의 다음 17파일을 Git에 직접 포함합니다. 약 27MB이며, 각 모델은 GitHub의 개별 파일 한도보다 작습니다. 모델은 Git LFS 포인터가 아닌 실제 TensorRT plan입니다.

- `ENGINE_Z3005_5/dynamic_parts_005`: 부품 검출 plan, manifest/Recipe/클래스/전처리/카메라 형식/기동 점검 이미지, Pose 설정·D001 이미지·bank.
- `ENGINE_Z3005_5/envelope_v007_fp16`: 엔진 전체 검출 plan과 해당 manifest/Recipe/클래스/전처리/카메라 형식/기동 점검 이미지.

모델의 학습·변환 출처, 원본 모델 해시, 빌드 환경과 자격 범위는 각 `manifest.json`에 남아 있습니다. 현재 실행 모델이며 새로운 학습/성능 평가 결과를 주장하지 않습니다. 기존 Pose bank와 기동 이미지는 운영 필수 자산입니다. 데이터셋 전체·운영 DB·보호 평가 자료는 포함하지 않습니다.

TensorRT plan은 모델 가중치를 포함하지만 원본 PyTorch 학습 체크포인트나 ONNX가 아닙니다. 다른 GPU/TensorRT 환경으로 옮길 때는 원본 모델에서 재빌드하고 재검증해야 합니다. 이 저장소의 설치 지원 기준은 Orin Nano / TensorRT 10.3 / CUDA 12.6입니다.

자산은 해시 검증을 위해 `.gitattributes`에서 줄바꿈 변환을 끕니다. JSON을 재정렬하거나 저장하면 기존 manifest가 더 이상 일치하지 않을 수 있습니다. `python jetson/install.py --check-only`로 검증하세요.

이 저장소는 외부 프레임워크/학습 도구/런타임에 새로운 라이선스를 부여하지 않습니다. 사용한 도구의 기존 라이선스와 출처 조건은 유지됩니다. TensorRT/CUDA/JetPack은 Git에 재배포하지 않고 NVIDIA 제공 환경을 사용합니다.
