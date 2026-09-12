"""Product-configured human guidance. Image storage remains CollectionSession's job."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time

from training.scripts import capture_proxy as capture

PLAN_NAME = 'guide-plan.json'
REVIEWS_NAME = 'guide-reviews.jsonl'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def read_json(path):
    capture.plain_path(path)
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=capture.unique_json_object)


def text_valid(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 2000


def validate_guide(config, profile):
    capture.validate_profile(profile)
    if (not isinstance(config, dict) or set(config) != {
            'guide_schema_version', 'setup', 'review_checks', 'conditions', 'steps', 'completion_message'}
            or type(config['guide_schema_version']) is not int or config['guide_schema_version'] != 1):
        raise ValueError('촬영 안내 설정 버전/필드를 확인하세요.')
    if not all(text_valid(config[k]) for k in ('setup', 'review_checks', 'completion_message')):
        raise ValueError('촬영 안내 문장은 비어 있지 않은 문자열이어야 합니다.')
    conditions, steps = config['conditions'], config['steps']
    if not isinstance(conditions, list) or not 1 <= len(conditions) <= 20:
        raise ValueError('촬영 조건은 1~20개여야 합니다.')
    ids = []
    for condition in conditions:
        if (not isinstance(condition, dict) or set(condition) != {'id', 'label', 'instruction'}
                or not all(text_valid(condition[k]) for k in condition)
                or not re.fullmatch(r'[A-Z][A-Z0-9_]{0,39}', condition['id'])):
            raise ValueError('촬영 조건 ID/이름/안내를 확인하세요.')
        ids.append(condition['id'])
    if len(set(ids)) != len(ids):
        raise ValueError('촬영 조건 ID가 중복됩니다.')
    if not isinstance(steps, list) or len(steps) != len(profile['scenarios']):
        raise ValueError('모든 제품 상태를 한 번씩 안내해야 합니다.')
    scenarios = []
    for step in steps:
        if (not isinstance(step, dict) or set(step) != {'scenario', 'instruction'}
                or not all(text_valid(step[k]) for k in step)):
            raise ValueError('단계의 상태/안내를 확인하세요.')
        scenarios.append(step['scenario'])
    if len(set(scenarios)) != len(scenarios) or set(scenarios) != set(profile['scenarios']):
        raise ValueError('안내 상태가 제품 프로필과 다르거나 중복됩니다.')
    return config


def default_guide(profile):
    steps = []
    for scenario, rule in profile['scenarios'].items():
        removed = rule['objects_removed']
        kept = [item for item in profile['objects'] if item not in removed]
        extra = '추가 물체를 배치하세요.' if rule['unexpected_object'] else '불필요한 물체를 치우세요.'
        steps.append({'scenario': scenario, 'instruction':
            f"유지: {', '.join(kept) or '없음'}. 제거: {', '.join(removed) or '없음'}. {extra} 손을 빼세요."})
    return {'guide_schema_version': 1,
        'setup': '카메라 높이·각도와 조명을 고정하세요. 실제 검사 범위에서 물체를 배치하고 조건란에 기록하세요.',
        'review_checks': '원본에서 대상 전체, 선명도, 반사·가림, 선택한 실제 상태를 확인하세요.',
        'conditions': [{'id': 'BASELINE', 'label': '기준 조건',
                        'instruction': '같은 카메라·조명·물체 방향을 유지하며 모든 상태를 촬영하세요.'}],
        'steps': steps, 'completion_message': '이 조건의 확인 촬영을 마쳤습니다. 학습에 충분한 데이터라는 뜻은 아닙니다.'}


def load_guide(profile_path, profile):
    path = Path(profile_path).with_name('capture-guide.json')
    config = read_json(path) if path.exists() else default_guide(profile)
    return validate_guide(config, profile)


class GuidedRound:
    """One condition, all product states, human review after each verified PNG.

    A saved PNG without a review is always pending, including after a crash.
    Reviews never remove images or rewrite ground truth in the manifest.
    """
    def __init__(self, session, config, condition_id):
        self.session = session
        self.config = deepcopy(validate_guide(config, session.profile))
        self.condition = next((c for c in config['conditions'] if c['id'] == condition_id), None)
        if self.condition is None:
            raise ValueError('촬영 안내 조건이 설정에 없습니다.')
        self.prepared = False  # physical readiness is never restored from disk
        self.sync()

    @classmethod
    def create(cls, session, config, condition_id):
        if session.records or session.read_only or session.failed:
            raise capture.CaptureError('안내 촬영은 새 빈 촬영 묶음에서 시작하세요.')
        guide = cls(session, config, condition_id)
        plan = {'guide_plan_schema_version': 1, 'session_id': session.session_id,
                'profile_sha256': capture.profile_digest(session.profile),
                'config': guide.config, 'config_sha256': digest(guide.config), 'condition_id': condition_id}
        path = session.folder/PLAN_NAME
        try:
            with path.open('x', encoding='utf-8', newline='\n') as stream:
                json.dump(plan, stream, ensure_ascii=False, allow_nan=False, indent=2)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
        except Exception as exc:
            session.failed = True
            raise capture.CaptureError(f'안내 사본 저장 실패: {path}. 원본을 보존하고 새 묶음을 사용하세요: {exc}') from exc
        guide.select_step()
        return guide

    @classmethod
    def open(cls, session):
        path = session.folder/PLAN_NAME
        if not path.exists():
            if (session.folder/REVIEWS_NAME).exists():
                raise ValueError('사람 검토 기록은 있지만 안내 사본이 없습니다. 원본을 보존하세요.')
            return None  # legacy/manual captures are not retroactively guided captures
        plan = read_json(path)
        keys = {'guide_plan_schema_version', 'session_id', 'profile_sha256', 'config', 'config_sha256', 'condition_id'}
        if (not isinstance(plan, dict) or set(plan) != keys
                or type(plan['guide_plan_schema_version']) is not int or plan['guide_plan_schema_version'] != 1
                or plan['session_id'] != session.session_id
                or plan['profile_sha256'] != capture.profile_digest(session.profile)
                or plan['config_sha256'] != digest(plan['config'])):
            raise ValueError('안내 사본/제품/해시 연결이 다릅니다. 원본을 보존하세요.')
        return cls(session, plan['config'], plan['condition_id'])

    @property
    def complete(self):
        return self.index == len(self.config['steps'])

    @property
    def step(self):
        return None if self.complete else self.config['steps'][self.index]

    def sync(self):
        path = self.session.folder/REVIEWS_NAME
        reviews = []
        if path.exists():
            capture.plain_path(path)
            for line in path.read_text(encoding='utf-8').splitlines():
                reviews.append(json.loads(line, object_pairs_hook=capture.unique_json_object))
        records = self.session.records
        if len(reviews) > len(records) or len(records) - len(reviews) > 1:
            raise ValueError('안내 사진/검토 건수가 다릅니다. 추가 저장을 중단하고 원본을 확인하세요.')
        index, rejected = 0, 0
        for position, row in enumerate(records):
            if index >= len(self.config['steps']) or row['scenario'] != self.config['steps'][index]['scenario']:
                raise ValueError('안내 순서와 촬영 정답이 다릅니다. 원본을 확인하세요.')
            if position == len(reviews):
                break
            review = reviews[position]
            if (not isinstance(review, dict) or set(review) != {'review_schema_version', 'capture_id',
                    'image_sha256', 'step_index', 'decision', 'reviewed_at', 'note'}
                    or type(review['review_schema_version']) is not int or review['review_schema_version'] != 1
                    or review['capture_id'] != row['capture_id'] or review['image_sha256'] != row['image_sha256']
                    or type(review['step_index']) is not int or review['step_index'] != index
                    or review['decision'] not in ('accepted', 'rejected')
                    or not isinstance(review['note'], str) or len(review['note']) > 2000
                    or (review['decision'] == 'rejected' and not review['note'].strip())):
                raise ValueError('사람 검토 기록/사진 연결이 올바르지 않습니다.')
            stamp = datetime.fromisoformat(review['reviewed_at'])
            if capture.utc_time(stamp).isoformat() != review['reviewed_at']:
                raise ValueError('사람 검토 시각은 UTC여야 합니다.')
            if review['decision'] == 'accepted':
                index += 1
            else:
                rejected += 1
        self.index, self.rejected = index, rejected
        self.pending_record = records[-1] if len(records) > len(reviews) else None

    def select_step(self):
        if self.step:
            self.session.set_scenario(self.step['scenario'])

    def prepare(self):
        if self.complete or self.pending_record or self.session.failed:
            raise capture.CaptureError('현재 사진을 검토하거나 새 안내 촬영을 시작하세요.')
        self.select_step()
        self.session.not_before = time.monotonic()
        self.prepared = True

    def save(self, frame):
        if not self.prepared or self.pending_record or self.complete:
            raise capture.CaptureError('안내대로 실제 배치한 뒤 준비 확인을 누르세요.')
        if self.session.scenario != self.step['scenario']:
            raise capture.CaptureError('안내 상태가 변경되었습니다. 준비를 다시 확인하세요.')
        self.prepared = False
        path = self.session.save(frame)
        self.sync()
        return path

    def review(self, accepted, note=''):
        if type(accepted) is not bool or not isinstance(note, str) or len(note) > 2000:
            raise ValueError('사람 검토 응답 형식이 올바르지 않습니다.')
        if self.pending_record is None or self.session.failed or self.session.read_only:
            raise capture.CaptureError('검토할 사진이 없거나 기록을 수정할 수 없습니다.')
        if not accepted and not note.strip():
            raise ValueError('재촬영 이유를 적으세요. 이전 원본은 삭제하지 않습니다.')
        row = self.pending_record
        review = {'review_schema_version': 1, 'capture_id': row['capture_id'], 'image_sha256': row['image_sha256'],
                  'step_index': self.index, 'decision': 'accepted' if accepted else 'rejected',
                  'reviewed_at': datetime.now(timezone.utc).isoformat(), 'note': note.strip()}
        path = self.session.folder/REVIEWS_NAME
        capture.plain_path(path)
        try:
            with path.open('a', encoding='utf-8', newline='\n') as stream:
                stream.write(json.dumps(review, ensure_ascii=False, allow_nan=False)+'\n')
                stream.flush()
                os.fsync(stream.fileno())
            self.sync()
        except Exception as exc:
            self.session.failed = True
            raise capture.CaptureError(f'사람 검토 기록 실패: {path}. 진행 중단; PNG/기록을 삭제하지 마세요: {exc}') from exc
        self.prepared = False
        self.select_step()
