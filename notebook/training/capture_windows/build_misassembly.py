"""Package the existing collector code as a standalone Windows teammate ZIP."""
from datetime import datetime
import hashlib
from importlib import metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build():
    if sys.platform != 'win32' or sys.maxsize <= 2**32:
        raise RuntimeError('Windows x64 빌드 환경이 필요합니다.')
    output = ROOT / 'dist' / 'engine_misassembly_capture' / datetime.now().strftime('%Y%m%d_%H%M%S')
    output.mkdir(parents=True, exist_ok=False)
    release = output / 'Engine_Misassembly_Capture'
    release.mkdir()
    shutil.copytree(SOURCE / 'assets', release / 'assets', ignore=shutil.ignore_patterns('make_*.py'))
    (release / 'data').mkdir()
    (release / 'logs').mkdir()
    plan = json.loads((release / 'assets/misassembly-plan.json').read_text(encoding='utf-8'))
    (release / '시작 안내.txt').write_text(
        '엔진 오조립 추가 촬영 — Windows x64\n'
        '1. ZIP 전체를 쓰기 가능한 폴더에 압축 해제합니다.\n'
        '2. EngineMisassemblyCapture.exe를 더블클릭합니다.\n'
        '   _internal과 assets를 포함해 폴더 전체를 유지하세요. EXE만 따로 옮기지 마세요.\n'
        '3. 첫 실행에 카메라 후보·해상도를 고르고 영상 연결을 누릅니다. 번호는 모델명이 아닙니다.\n'
        '   촬영자·저장 폴더를 정하고 0° 배치 박스를 맞춘 뒤 설정 완료를 누릅니다.\n'
        '4. 현재 안내대로 엔진 상태·위치를 준비하고 촬영/Space를 한 번 누릅니다.\n'
        '종료 시 전달 폴더 전체를 제작 담당자에게 보냅니다. 데이터는 지정 저장 폴더의 collections 안에 있습니다.\n'
        '정상 사진은 기존 학습용 NORMAL 안내 복사본입니다. 오조립 부분 사진은 복합 오류 사진의 일부를 자른 안내물입니다.\n'
        '부품 상태·실제 회전각은 프로그램이 검사하지 않습니다. 저장 자료는 NOT_REVIEWED 학습 후보입니다.\n'
        f'이 계획은 {len(plan["steps"])}장: 새 오조립 504장 + 정상/결품 부족한 각도 144장 + 정상 장치 대조군 6장입니다.\n'
        '10° 간격 0~350°를 안내합니다. 기존 학습용에서 확인된 상태/각도는 보충 촬영에서 제외했습니다.\n'
        '노란 박스는 회전 공간, 하늘색 박스/화살표는 현재 배치입니다. 정상 기준의 긴 금색 중심축 끝이 아래이면 0°입니다.\n'
        '새 폴더로 업데이트했다면 기존 저장 폴더를 최초 설정에서 선택하세요. 이전 수집은 원래 계획으로 재개합니다.\n'
        '카메라가 끊기거나 저장 오류가 나면 같은 단계에 남습니다. 원본을 삭제하지 마세요.\n',
        encoding='utf-8-sig')
    licenses = release / 'THIRD_PARTY_LICENSES'
    licenses.mkdir()
    for name in ('numpy', 'opencv-python', 'Pillow', 'PyInstaller'):
        dist = metadata.distribution(name)
        for item in dist.files or []:
            if 'license' in item.name.lower() or 'copying' in item.name.lower():
                source = Path(dist.locate_file(item))
                if source.is_file():
                    target = licenses / name / str(item).replace('..', '_parent_')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
    shutil.copyfile(Path(sys.base_prefix) / 'LICENSE.txt', licenses / 'Python-LICENSE.txt')
    for item in sorted((Path(sys.base_prefix) / 'tcl').rglob('license.terms')):
        target = licenses / 'Tcl-Tk' / item.relative_to(Path(sys.base_prefix) / 'tcl')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item, target)
    command = [sys.executable, '-X', 'utf8', '-m', 'PyInstaller', '--noconfirm',
               '--onedir', '--windowed', '--noupx', '--name', 'EngineMisassemblyCapture',
               '--distpath', str(output / 'frozen'), '--workpath', str(output / 'work'),
               '--specpath', str(output), '--paths', str(ROOT / 'notebook'),
               '--exclude-module', 'torch', '--exclude-module', 'matplotlib',
               '--exclude-module', 'pytest', str(SOURCE / 'misassembly_entry.py')]
    with (output / 'build.log').open('w', encoding='utf-8') as log:
        subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    shutil.copytree(output / 'frozen' / 'EngineMisassemblyCapture', release, dirs_exist_ok=True)
    exe = release / 'EngineMisassemblyCapture.exe'
    inputs = list(SOURCE.glob('*.py')) + list((SOURCE / 'assets').glob('*.png'))
    inputs += list((SOURCE / 'assets').glob('*.json'))
    inputs += [ROOT / 'notebook/training/scripts/capture_proxy.py',
               ROOT / 'notebook/training/scripts/verify_proxy_captures.py']
    (release / 'BUILD_INFO.json').write_text(json.dumps({
        'exe_sha256': sha256(exe), 'exe_bytes': exe.stat().st_size,
        'inputs': {str(path.relative_to(ROOT)).replace('\\', '/'): sha256(path) for path in inputs},
        'camera_test': 'NOT_RUN', 'teammate_pc_test': 'NOT_RUN', 'model_bundled': False,
        'data_bundled': False, 'policy_version': 'operator-declared-one-click-v1',
        'distribution': 'onedir_keep_entire_folder',
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    archive = output / 'Engine_Misassembly_Capture.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(release.rglob('*')):
            if path.is_file():
                bundle.write(path, path.relative_to(output))
        for directory in ('data', 'logs'):
            bundle.writestr(f'Engine_Misassembly_Capture/{directory}/', '')
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
    print(json.dumps({'zip': str(archive), 'zip_sha256': sha256(archive),
                      'exe': str(exe), 'exe_sha256': sha256(exe)}, ensure_ascii=False))


if __name__ == '__main__':
    build()
