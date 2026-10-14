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

PROJECT = Path(__file__).resolve().parents[1]


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


def collect_release(project_root=PROJECT, *, assembly_assets=None, require_assembly=False):
    project_root = project_root.resolve()
    specification = json.loads((project_root / 'jetson/runtime_allowlist.json').read_text(encoding='utf-8'))
    files = {}
    for name in specification['runtime_files']:
        path = checked_file(project_root / 'jetson', name)
        # 소스에서는 옆의 config를 읽고, 배포 후에는 current/config 링크를 통한다.
        target = 'assets/runtime_config/' + name[7:] if name.startswith('config/') else 'current/' + name
        if target in files:
            raise ValueError('DUPLICATE_PACKAGE_PATH: ' + target)
        files[target] = path
    for name in specification['product_files']:
        files['assets/products/' + name] = checked_file(project_root / 'jetson/products', name)
    # Removing obsolete image entries must not make a local image-backed profile
    # appear deployable. Its dependencies must still be explicitly packaged.
    area_path = files.get('assets/runtime_config/area_clearance.json')
    if area_path:
        area = json.loads(area_path.read_text(encoding='utf-8'))
        for reference in area.get('references', []):
            name = reference['path']
            checked_file(area_path.parent, name)
            target = 'assets/runtime_config/' + name
            if target not in files:
                raise ValueError('AREA_REFERENCE_NOT_ALLOWLISTED: ' + name)
            if hashlib.sha256(files[target].read_bytes()).hexdigest() != reference['sha256']:
                raise ValueError('AREA_REFERENCE_HASH_MISMATCH: ' + name)
    # Assembly models are an explicit, offline asset input. Never silently pick
    # up a developer's ignored historical run or call a core-only bundle complete.
    shadow_spec = project_root / 'jetson/assembly_assets.lock.json'
    if require_assembly and assembly_assets is None:
        raise ValueError('REQUIRED_ASSEMBLY_ASSETS_MISSING')
    if assembly_assets is not None:
        shadow = json.loads(shadow_spec.read_text(encoding='utf-8'))
        frozen_root = Path(assembly_assets).absolute()
        for item in shadow['files']:
            path = checked_file(frozen_root, item['relative_path'])
            if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('FROZEN_SHADOW_DEPENDENCY_CHANGED: ' + item['relative_path'])
            target = 'assets/misassembly_runtime/' + item['relative_path']
            if target in files:
                raise ValueError('DUPLICATE_SHADOW_DEPENDENCY')
            files[target] = path
        files['assets/misassembly_runtime/FROZEN_MANIFEST.json'] = shadow_spec
    files['config/station.example.json'] = checked_file(project_root, 'jetson/station.example.json')
    files['config/runtime.example.json'] = checked_file(project_root, 'jetson/runtime.example.json')
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
        'bundle_scope': ('INTEGRATED_AI_OFFLINE' if assembly_assets is not None else 'CORE_MOCK_ONLY'),
        'assembly_assets_included': assembly_assets is not None,
        'field_automatic_operation_verified': False,
        'files': hashes, 'links': links,
    }
    encoded = (json.dumps(release, indent=2) + '\n').encode('utf-8')
    return files, release, encoded


def build_package(output, project_root=PROJECT, *, assembly_assets=None, require_assembly=False):
    output = output.resolve()
    if output.exists():
        raise FileExistsError('Keep the existing package; choose a new output path: ' + str(output))
    files, release, encoded = collect_release(project_root, assembly_assets=assembly_assets,
                                             require_assembly=require_assembly)
    hashes, links = release['files'], release['links']
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
                info.mode = 0o755 if name == 'current/opener/OpENer' else 0o644
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
    parser.add_argument('--assembly-assets', type=Path,
                        help='Offline frozen inference asset root matching assembly_assets.lock.json')
    parser.add_argument('--require-assembly', action='store_true',
                        help='Fail instead of producing a core MOCK bundle without the four classifiers')
    args = parser.parse_args()
    print(json.dumps(build_package(args.output, assembly_assets=args.assembly_assets,
                                   require_assembly=args.require_assembly), ensure_ascii=False))


if __name__ == '__main__':
    main()
