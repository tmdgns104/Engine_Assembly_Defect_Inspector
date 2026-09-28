"""Collection state and verified storage; no Tk widgets or camera handles."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
from threading import Lock
import time
import uuid

import cv2
import numpy as np

from training.scripts import capture_proxy as capture
from training.scripts.verify_proxy_captures import verify_session

INFO_NAME = "session-info.json"
CAMERA_KEYS = {"index", "backend", "device_name", "requested_width", "requested_height",
               "width", "height", "fps_reported", "fourcc_reported"}


def load_display(profile_path, profile):
    """Optional UI vocabulary; never changes scenario keys or profile hash."""
    name = profile['product_id']
    labels = {key: key for key in profile['scenarios']}
    path = Path(profile_path).with_name('display.json')
    if path.exists():
        data = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=capture.unique_json_object)
        if (not isinstance(data, dict) or set(data) != {'display_schema_version', 'product_name', 'scenario_labels'}
                or type(data['display_schema_version']) is not int or data['display_schema_version'] != 1
                or not isinstance(data['product_name'], str) or not isinstance(data['scenario_labels'], dict)):
            raise ValueError('display.json 표시 설정 형식이 잘못되었습니다.')
        for key, value in data['scenario_labels'].items():
            if key not in labels or not isinstance(value, str) or not value.strip():
                raise ValueError('display.json 시나리오 표시 이름을 확인하세요.')
        name = data['product_name']
        labels.update(data['scenario_labels'])
    return name, labels


def connection_matches(a, b):
    keys = ('index', 'backend', 'requested_width', 'requested_height', 'width', 'height')
    return all(a[k] == b[k] for k in keys)


def validate_info(info):
    fields = {'session_info_schema_version', 'session_id', 'created_at', 'profile_snapshot',
              'profile_sha256', 'device', 'camera', 'conditions', 'timestamp_semantics', 'source_kind'}
    if not isinstance(info, dict) or set(info) != fields:
        raise ValueError('세션 정보 필드가 올바르지 않습니다.')
    if type(info['session_info_schema_version']) is not int or info['session_info_schema_version'] != 1:
        raise ValueError('지원하지 않는 세션 정보 버전입니다.')
    capture.validate_ids(info['session_id'], info['session_id']+'_CHECK')
    if info['profile_sha256'] != capture.profile_digest(info['profile_snapshot']):
        raise ValueError('세션 제품 설정 해시가 다릅니다.')
    timestamp = datetime.fromisoformat(info['created_at'])
    if capture.utc_time(timestamp).isoformat() != info['created_at']:
        raise ValueError('세션 생성 시각은 UTC여야 합니다.')
    if info['source_kind'] not in ('camera', 'sample'):
        raise ValueError('잘못된 입력 종류입니다.')
    camera = info['camera']
    if not isinstance(camera, dict) or set(camera) != CAMERA_KEYS:
        raise ValueError('카메라 세션 정보 형식이 잘못되었습니다.')
    from .camera import CameraSettings
    CameraSettings(camera['index'], camera['backend'], camera['requested_width'], camera['requested_height'])
    if any(type(camera[k]) is not int or camera[k] <= 0 for k in ('width', 'height')):
        raise ValueError('실제 영상 크기가 잘못되었습니다.')
    if any(not isinstance(info[k], str) for k in ('device', 'conditions', 'timestamp_semantics')):
        raise ValueError('세션 설명은 문자열이어야 합니다.')
    if not info['device'].strip():
        raise ValueError('촬영 장비 식별자가 비어 있습니다.')
    fps = camera['fps_reported']
    if fps is not None and (type(fps) not in (int, float) or not np.isfinite(fps) or fps <= 0):
        raise ValueError('보고 FPS는 양의 유한값 또는 null이어야 합니다.')
    for key in ('device_name', 'fourcc_reported'):
        if camera[key] is not None and not isinstance(camera[key], str):
            raise ValueError('장치/포맷 정보는 문자열 또는 null이어야 합니다.')


class CollectionSession:
    def __init__(self, root, session_id, profile, info, records):
        self.root = Path(os.path.abspath(root))
        self.session_id = session_id
        self.profile = deepcopy(profile)
        self.info = info
        self.records = records
        self.counts = Counter(row['scenario'] for row in records)
        self.last_path = self.root/records[-1]['image_path'] if records else None
        self.scenario = None
        self.episode_id = None
        self.episode_serial = 0
        self.not_before = time.monotonic()
        self.failed = False
        self.read_only = info is None
        self.save_lock = Lock()
        self.last_frame_token = None

    @property
    def folder(self):
        return self.root/self.session_id

    @classmethod
    def create(cls, root, profile, frame, conditions='', source_kind='camera', device=None):
        capture.validate_profile(profile)
        if not frame.fresh():
            raise capture.CaptureError('새 묶음 생성 전에 카메라 영상을 확인하세요.')
        root = Path(os.path.abspath(root))
        capture.plain_path(root)
        root.mkdir(parents=True, exist_ok=True)
        for _ in range(10):
            sid = 'S'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:8].upper()
            folder = root/sid
            try:
                folder.mkdir()
                break
            except FileExistsError:
                continue
        else:
            raise capture.CaptureError('새 촬영 묶음 ID를 만들지 못했습니다.')
        info = {'session_info_schema_version': 1, 'session_id': sid,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'profile_snapshot': deepcopy(profile), 'profile_sha256': capture.profile_digest(profile),
                'device': device or socket.gethostname(), 'camera': dict(frame.camera),
                'conditions': conditions, 'source_kind': source_kind,
                'timestamp_semantics': 'captured_at is UTC software frame receive time; not sensor exposure time'}
        validate_info(info)
        with (folder/INFO_NAME).open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(info, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        return cls(root, sid, profile, info, [])

    @classmethod
    def open(cls, folder):
        folder = Path(os.path.abspath(folder))
        capture.plain_path(folder)
        sid, root = folder.name, folder.parent
        capture.validate_ids(sid, sid+'_CHECK')
        if (folder/'.capture.lock').exists():
            raise capture.CaptureError('활성/중단된 잠금이 있습니다. 소유자를 확인하고 원본을 보존하세요.')
        records = capture.read_manifest(folder/'manifest.jsonl')
        if records:
            verify_session(root, sid)
        elif list(folder.glob('*/images/*.png')):
            raise capture.CaptureError('기록되지 않은 PNG가 있습니다. 삭제하지 말고 확인하세요.')
        info_path = folder/INFO_NAME
        info = None
        profile = records[0].get('profile_snapshot') if records else None
        if info_path.exists():
            capture.plain_path(info_path)
            info = json.loads(info_path.read_text(encoding='utf-8'), object_pairs_hook=capture.unique_json_object)
            validate_info(info)
            if info['session_id'] != sid:
                raise ValueError('세션 폴더와 정보의 ID가 다릅니다.')
            profile = info['profile_snapshot']
            c = info['camera']
            source = f"windows:{c['backend']}:index={c['index']}"
            for row in records:
                if (row.get('profile_sha256') != info['profile_sha256'] or row['camera_source'] != source
                        or row['source_kind'] != info['source_kind'] or row['device'] != info['device']
                        or (row['width'], row['height']) != (c['width'], c['height'])):
                    raise ValueError('세션 정보와 촬영 기록이 다릅니다. 원본을 보존하고 확인하세요.')
        elif not records:
            raise capture.CaptureError('세션 정보나 촬영 기록이 없습니다.')
        return cls(root, sid, profile, info, records)

    def set_scenario(self, scenario):
        capture.object_configuration(scenario, self.profile)
        if scenario != self.scenario:
            self.scenario = scenario
            self.new_episode()

    def new_episode(self):
        if self.scenario is None:
            raise capture.CaptureError('촬영 상태를 먼저 선택하세요.')
        used = {r['episode_id'] for r in self.records}
        while True:
            self.episode_serial += 1
            candidate = f'{self.session_id}_E{self.episode_serial:04d}'
            if candidate not in used and not (self.folder/candidate).exists():
                self.episode_id = candidate
                self.not_before = time.monotonic()
                return

    def can_continue(self, profile, frame, conditions, source_kind='camera'):
        if self.read_only or self.failed:
            raise capture.CaptureError('이 묶음은 읽기 전용입니다. 새 촬영 묶음을 만드세요.')
        if (capture.profile_digest(profile) != self.info['profile_sha256']
                or source_kind != self.info['source_kind']
                or not connection_matches(self.info['camera'], frame.camera)
                or conditions != self.info['conditions'] or socket.gethostname() != self.info['device']):
            raise capture.CaptureError('제품/장비/해상도/촬영 조건이 바뀌었습니다. 새 묶음을 만드세요.')

    def save(self, frame, notes=''):
        if not self.save_lock.acquire(blocking=False):
            raise capture.CaptureError('이미 한 장을 저장 중입니다.')
        try:
            if self.read_only or self.failed or self.episode_id is None:
                raise capture.CaptureError('새 촬영 묶음과 상태를 확인하세요.')
            if not frame.fresh() or frame.received_mono < self.not_before:
                raise capture.CaptureError('상태/배치 변경 뒤의 최신 프레임을 기다리세요. 저장하지 않았습니다.')
            token = (frame.stream_id, frame.sequence)
            if token == self.last_frame_token:
                raise capture.CaptureError('이 프레임은 이미 저장했습니다. 다음 프레임을 기다리세요.')
            c = self.info['camera']
            if not connection_matches(c, frame.camera) or frame.image.shape[:2] != (c['height'], c['width']):
                raise capture.CaptureError('실제 영상 크기/입력이 바뀌었습니다. 새 묶음을 만드세요.')
            if frame.image.dtype != np.uint8 or frame.image.ndim != 3 or frame.image.shape[2] != 3:
                raise capture.CaptureError('원본 BGR 프레임 형식이 올바르지 않습니다.')
            ok, encoded = cv2.imencode('.png', frame.image)
            if not ok:
                raise capture.CaptureError('PNG 인코딩 실패. 파일을 저장하지 않았습니다.')
            png = encoded.tobytes()
            record = capture.make_record(session_id=self.session_id, episode_id=self.episode_id,
                scenario=self.scenario, captured_at=frame.captured_at, width=c['width'], height=c['height'],
                device=self.info['device'], camera_source=f"windows:{c['backend']}:index={c['index']}",
                source_kind=self.info['source_kind'], image_png=png, notes=notes, profile=self.profile)
            try:
                path = capture.save_capture(self.root, record, png)
                result = verify_session(self.root, self.session_id)
                records = capture.read_manifest(self.folder/'manifest.jsonl')
            except Exception as exc:
                self.failed = True
                raise capture.CaptureError(f'저장/검증 실패. 성공 수량은 갱신하지 않았습니다. '
                    f'원본을 삭제하지 말고 {self.folder}의 PNG·manifest·잠금을 확인하세요. 원인: {exc}') from exc
            self.records = records
            self.counts = Counter(result['scenario_counts'])
            self.last_path, self.last_frame_token = path, token
            return path
        finally:
            self.save_lock.release()
