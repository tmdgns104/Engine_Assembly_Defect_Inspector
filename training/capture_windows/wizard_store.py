"""Local single-writer ownership and checksummed append-only events."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from .guide import digest
from training.scripts import capture_proxy as capture


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_new_json(path, value):
    capture.plain_path(path)
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


class WriterLock:
    """OS lock is released on process exit. An existing file is not a stale-lock verdict."""
    def __init__(self, folder):
        path = Path(folder)/'.wizard-writer.lock'
        capture.plain_path(path)
        self.stream = path.open('a+b')
        if path.stat().st_size == 0:
            self.stream.write(b'0')
            self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.stream.close()
            raise capture.CaptureError('다른 창이 이 수집 계획을 사용 중입니다. 그 창을 정상 종료한 뒤 이어하세요.') from exc

    def close(self):
        if self.stream.closed:
            return
        self.stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(self.stream, fcntl.LOCK_UN)
        self.stream.close()


class EventLog:
    def __init__(self, folder):
        self.path = Path(folder)/'collection-events.jsonl'
        self.events = []
        self.failed = False
        capture.plain_path(self.path)
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding='utf-8').splitlines():
            event = json.loads(line, object_pairs_hook=capture.unique_json_object)
            if not isinstance(event, dict) or set(event) != {'event_schema_version', 'seq', 'type', 'at', 'data', 'previous_sha256', 'sha256'}:
                raise ValueError(f'수집 기록 형식 손상: {self.path}. 원본을 보존하세요.')
            body = {k: v for k, v in event.items() if k != 'sha256'}
            previous = self.events[-1]['sha256'] if self.events else None
            if (type(event['event_schema_version']) is not int or event['event_schema_version'] != 1
                    or type(event['seq']) is not int or event['seq'] != len(self.events)+1
                    or event['previous_sha256'] != previous or event['sha256'] != digest(body)
                    or not isinstance(event['type'], str) or not isinstance(event['data'], dict)):
                raise ValueError(f'수집 기록 순서/해시 불일치: {self.path}. 자동 복구하지 않습니다.')
            timestamp = datetime.fromisoformat(event['at'])
            if capture.utc_time(timestamp).isoformat() != event['at']:
                raise ValueError('수집 기록 시각은 UTC여야 합니다.')
            self.events.append(event)

    def append(self, kind, data):
        if self.failed:
            raise capture.CaptureError('수집 기록 저장 실패 후 추가 기록은 차단됩니다. 다시 열어 검증하세요.')
        event = {'event_schema_version': 1, 'seq': len(self.events)+1, 'type': kind,
                 'at': utc_now(), 'data': data,
                 'previous_sha256': self.events[-1]['sha256'] if self.events else None}
        event['sha256'] = digest(event)
        try:
            with self.path.open('a', encoding='utf-8', newline='\n') as stream:
                stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False)+'\n')
                stream.flush()
                os.fsync(stream.fileno())
        except Exception as exc:
            self.failed = True
            raise capture.CaptureError(f'수집 기록 저장 실패: {self.path}. 원본은 보존되며 완료 처리하지 않습니다: {exc}') from exc
        self.events.append(event)
        return event
