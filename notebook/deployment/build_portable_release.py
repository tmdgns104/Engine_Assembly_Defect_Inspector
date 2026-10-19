"""검증한 운영본을 새 장치 설치용 단일 archive로 보존한다. 장치 접속은 없다."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    if not name or path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
        raise ValueError('UNSAFE_ARCHIVE_PATH: ' + name)
    return name


def build(project, manifest_path, sources_path, backup_path, database, output):
    """운영 해시와 일치하는 입력만 사용한다. 기존 산출물은 덮어쓰지 않는다."""
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    sources = json.loads(sources_path.read_text(encoding='utf-8'))
    if output.exists() or output.with_suffix('.partial').exists():
        raise FileExistsError(output)
    contents = {}
    with tarfile.open(backup_path) as backup:
        for name, expected in manifest['files'].items():
            safe_name(name)
            source = sources[name]
            if source.startswith('verified_backup:'):
                data = backup.extractfile(source.removeprefix('verified_backup:')).read()
            else:
                path = project / safe_name(source)
                if not path.resolve().is_relative_to(project.resolve()):
                    raise ValueError('SOURCE_OUTSIDE_PROJECT')
                data = path.read_bytes()
            if sha(data) != expected:
                raise ValueError('OPERATING_SOURCE_HASH_MISMATCH: ' + name)
            # 실제 장치의 주소/승인 설정은 설치 기본값이 아닌 검토용 template이다.
            target = 'templates/' + name[7:] if name.startswith('config/') else name
            contents[target] = data
        for name in ('station.json', 'standalone.json', 'line_profile.json'):
            contents.setdefault('templates/' + name, backup.extractfile('config/' + name).read())
    contents['history/journal.sqlite3'] = database.read_bytes()
    contents['history/snapshot.json'] = database.with_name('snapshot.json').read_bytes()
    snapshot = json.loads(contents['history/snapshot.json'])
    if snapshot.get('sha256') != sha(contents['history/journal.sqlite3']):
        raise ValueError('DATABASE_SNAPSHOT_HASH_MISMATCH')
    metadata = {
        'schema_version': 1, 'source_release': manifest['release_id'],
        'source_commit': 'e53ba0b7e2129a15c898b4857a0880158733ebc1',
        'source_file_hashes': manifest['files'],
        'files': {name: sha(data) for name, data in sorted(contents.items())},
        'model_count': sum(name.endswith(('.pt', '.plan')) for name in contents),
        'database_policy': 'HISTORICAL_COPY_ONLY_NEVER_ACTIVE_JOURNAL',
        'new_device_execution': 'NOT_VERIFIED',
    }
    contents['bundle.json'] = (json.dumps(metadata, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix('.partial')
    with partial.open('xb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode='w') as archive:
                for name, data in sorted(contents.items()):
                    info = tarfile.TarInfo(safe_name(name))
                    info.size = len(data)
                    info.mode = 0o755 if name == 'current/opener/OpENer' else 0o644
                    archive.addfile(info, io.BytesIO(data))
    if partial.stat().st_size >= 100 * 1024**2:
        raise ValueError('GITHUB_FILE_SIZE_LIMIT')
    with tarfile.open(partial) as archive:
        assert archive.getnames() == sorted(contents)
        for name, data in contents.items():
            if sha(archive.extractfile(name).read()) != sha(data):
                raise ValueError('ARCHIVE_ROUNDTRIP_MISMATCH: ' + name)
    partial.rename(output)
    receipt = dict(archive=output.name, sha256=sha(output.read_bytes()),
                   bytes=output.stat().st_size, source_release=metadata['source_release'],
                   source_commit=metadata['source_commit'], files=len(metadata['files']),
                   model_count=metadata['model_count'], new_device_execution='NOT_VERIFIED')
    output.with_suffix('.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'manifest', 'sources', 'backup', 'database', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.project, args.manifest, args.sources, args.backup, args.database, args.output)))


if __name__ == '__main__':
    main()
