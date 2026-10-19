# 고정 운영본 설치 입력

`operating_runtime.tar.gz`는 운영 Release `engine-integrated-32c484ac6aeb07f1`의 파일 200개와 동일한 바이트를 보존합니다. 장치 설정 2개는 `templates/`로 분리하고 station 양식 및 역사 SQLite/메타데이터를 더해 총 203개 파일을 포함합니다. 실행 모델은 7개입니다.

- 묶음 SHA256: `36759e4171c061ddad1459b62cb02cc24ba85ddadedccdf80f3bd3c797187f51`
- 크기: 70,712,513 bytes. Git LFS 포인터가 아닌 실제 압축 파일입니다.
- 출처 checkpoint: `e53ba0b7e2129a15c898b4857a0880158733ebc1`; 실제 코드/자산 식별은 내부 `source_file_hashes`를 사용합니다.
- 역사 SQLite:368검사, SHA256 `19d18d00ed41a54aec793ed298cbca8b0a42e11880def25642ec06d8bb308c8d`. 실행 중 파일 복사가 아닌 검증된 snapshot을 재사용합니다.
- 전체 사진·Windows venv·SSH 키·세션 토큰·기존 운전 승인은 신규 설치 활성 데이터로 반입하지 않습니다.

외부 `operating_runtime.tar.json`과 내부 `bundle.json`에 해시가 있습니다. `python3.10 jetson/install_operating.py --verify`로 확인하고 [설치 안내](../INSTALL_OPERATING_KO.md)를 따릅니다. `jetson/`만 있어도 설치 입력은 완성되며 Python/CUDA 환경은 해당 장치에 준비합니다.

재생성 코드는 [`build_portable_release.py`](../../notebook/deployment/build_portable_release.py)입니다. 검증 manifest·정확한 source map·보존 배포 백업·검증 SQLite를 명시적으로 받으며 같은 출력 파일을 덮어쓰지 않습니다. 개발 후보를 자동으로 최신 운영본에 섞지 않습니다. 로컬 복구 백업 전체는 공개하지 않습니다.
