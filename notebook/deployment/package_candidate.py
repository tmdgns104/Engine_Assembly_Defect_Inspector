"""노트북 전용: 기존 package_candidate.py를 명시적 배포 목록 방식으로 정리.

current 코드와 assets를 묶는다. 업로드·배포·삭제·승인 변경은 하지 않는다.
Journal, 가상환경, 촬영 원본, 개발 시험, 과거 후보는 입력 목록에 없다.
"""
import argparse
import ast
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile

PROJECT = Path(__file__).resolve().parents[2]


def checked_file(root, name):
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
        raise ValueError('INVALID_ALLOWLIST_PATH: ' + name)
    path = root.joinpath(*relative.parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('ALLOWLIST_OUTSIDE_ROOT: ' + name)
    current = path
    while current != root:
        if current.is_symlink():
            raise ValueError('SOURCE_LINK_NOT_ALLOWED: ' + name)
        current = current.parent
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def build_package(output, project_root=PROJECT):
    project_root = project_root.resolve()
    output = output.resolve()
    if output.exists():
        raise FileExistsError('Keep the existing package; choose a new output path: ' + str(output))
    specification = json.loads((project_root / 'notebook/deployment/runtime_allowlist.json').read_text(encoding='utf-8'))
    files = {}
    for name in specification['runtime_files']:
        path = checked_file(project_root / 'jetson', name)
        # 소스에서는 옆의 config를 읽고, 배포 후에는 current/config 링크를 통한다.
        target = 'assets/runtime_config/' + name[7:] if name.startswith('config/') else 'current/' + name
        if target in files:
            raise ValueError('DUPLICATE_PACKAGE_PATH: ' + target)
        files[target] = path
    for name in specification['product_files']:
        files['assets/products/' + name] = checked_file(project_root / 'notebook/deployment/products', name)
    files['config/station.example.json'] = checked_file(project_root, 'notebook/deployment/station.example.json')
    files['config/runtime.example.json'] = checked_file(project_root, 'notebook/deployment/runtime.example.json')
    hashes = {}
    for name, path in sorted(files.items()):
        if path.suffix == '.py':
            ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    links = {'current/config': '../assets/runtime_config'}
    identity = json.dumps({'files': hashes, 'links': links}, sort_keys=True, separators=(',', ':')).encode()
    release = {
        'schema_version': 1,
        'release_id': 'engine-dev-' + hashlib.sha256(identity).hexdigest()[:16],
        'qualification': 'DEVELOPMENT_BASELINE_NOT_PRODUCTION_ACCEPTED',
        'source_baseline_manifest_sha256': specification['source_baseline_manifest_sha256'],
        'physical_output_enabled': False,
        'files': hashes, 'links': links,
    }
    encoded = (json.dumps(release, indent=2) + '\n').encode('utf-8')
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + '.partial')
    with partial.open('xb') as stream:
        with tarfile.open(fileobj=stream, mode='w:gz') as archive:
            for name, path in sorted(files.items()):
                content = path.read_bytes()
                if hashlib.sha256(content).hexdigest() != hashes[name]:
                    raise ValueError('SOURCE_CHANGED_DURING_PACKAGE: ' + name)
                info = tarfile.TarInfo(name)
                info.size = len(content)
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(content))
            link = tarfile.TarInfo('current/config')
            link.type = tarfile.SYMTYPE
            link.linkname = links['current/config']
            archive.addfile(link)
            info = tarfile.TarInfo('current/release.json')
            info.size = len(encoded)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(encoded))
    # 압축 뒤 모든 파일을 다시 읽어 내용 해시까지 확인한다.
    with tarfile.open(partial) as archive:
        expected = set(hashes) | set(links) | {'current/release.json'}
        if set(archive.getnames()) != expected or len(archive.getmembers()) != len(expected):
            raise ValueError('ARCHIVE_MEMBERS_MISMATCH')
        for name, expected_hash in hashes.items():
            if hashlib.sha256(archive.extractfile(name).read()).hexdigest() != expected_hash:
                raise ValueError('ARCHIVE_HASH_MISMATCH: ' + name)
        if archive.extractfile('current/release.json').read() != encoded:
            raise ValueError('ARCHIVE_MANIFEST_MISMATCH')
    partial.rename(output)
    return {'release_id': release['release_id'], 'files': len(files), 'archive': str(output),
            'bytes': output.stat().st_size, 'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_package(args.output), ensure_ascii=False))


if __name__ == '__main__':
    main()
