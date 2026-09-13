"""Collection controller. All camera PNGs go through the existing verified writer.

The event log coordinates files; this is deliberately not a cross-file transaction.
Ground truth, human review, and automatic advisory metrics remain distinct.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import socket
import statistics
import time
import uuid

from training.scripts import capture_proxy as capture
from .guide import digest, read_json
from .session import CollectionSession, connection_matches
from .wizard_plan import expand_plan, target_roi, validate_plan, validate_targets
from .wizard_quality import metrics
from .wizard_store import EventLog, WriterLock, utc_now, write_new_json


def new_id(prefix):
    return prefix+uuid.uuid4().hex[:16].upper()


@dataclass
class PreparedCapture:
    readiness_id: str
    role_id: str
    setup_id: str
    stream_id: str
    prepared_mono: float
    consumed: bool = False


class Collection:
    @staticmethod
    def latest_lineage(root):
        """Continue provenance when a restarted UI creates a revised plan.

        Never import its images/counts. The previous writer must be closed and
        its stored evidence must verify before a new plan can inherit grouping.
        """
        candidates = [(read_json(p)['created_at'], p.parent)
                      for p in Path(root).glob('C*/collection.json')]
        if not candidates:
            return None
        previous = Collection.open(max(candidates, key=lambda item: item[0])[1])
        try:
            return previous.lineage_info()
        finally:
            previous.close()

    def __init__(self, folder, lock, info):
        self.folder, self.lock, self.info = Path(folder), lock, info
        self.profile, self.template, self.guide = info['profile'], info['template'], info['guide']
        self.effective = info['effective']
        self.blocks = self.effective['blocks']
        self.block_by_id = {b['block_id']: b for b in self.blocks}
        self.step_by_id = {s['step_id']: (b, s) for b in self.blocks for s in b['steps']}
        self.setup_id = None
        self.setups, self.rounds, self.bindings = {}, {}, {}
        self.intents, self.attempts, self.current, self.accepted, self.skipped = {}, {}, {}, {}, {}
        self.rules = deepcopy(self.template['quality'])
        self.sessions = {}
        self.failed, self.closed = False, False
        self.log = EventLog(self.folder)
        for event in self.log.events:
            self._apply(event)
        self._reconcile()

    @classmethod
    def create(cls, root, profile, guide, template, has_lamp, source_kind='camera', parent=None):
        validate_plan(template, profile, guide)
        if source_kind not in ('camera', 'sample'):
            raise ValueError('수집 입력 종류 오류')
        if parent and parent['template']['plan_id'] == template['plan_id']:
            if digest(parent['template']) != digest(template) and template['plan_version'] <= parent['template']['plan_version']:
                raise ValueError('변경된 계획은 이전보다 높은 plan_version으로 저장하세요.')
        root = Path(root).absolute()
        capture.plain_path(root)
        root.mkdir(parents=True, exist_ok=True)
        folder = root/new_id('C')
        folder.mkdir()
        lock = WriterLock(folder)
        try:
            info = {'collection_schema_version': 1, 'collection_id': folder.name, 'created_at': utc_now(),
                    'profile': deepcopy(profile), 'profile_sha256': capture.profile_digest(profile),
                    'guide': deepcopy(guide), 'guide_sha256': digest(guide),
                    'template': deepcopy(template), 'template_sha256': digest(template),
                    'effective': expand_plan(template, has_lamp), 'source_kind': source_kind,
                    'parent_collection_id': parent['collection_id'] if parent else None,
                    'initial_origin_group_id': parent['continuation_origin'] if parent else new_id('OG'),
                    'inherited_origin_purposes': parent['origin_purposes'] if parent else {},
                    'review_policy': 'human-batch-review-v1'}
            info['effective_sha256'] = digest(info['effective'])
            write_new_json(folder/'collection.json', info)
            return cls(folder, lock, info)
        except Exception:
            lock.close()
            raise

    @classmethod
    def open(cls, folder):
        folder = Path(folder).absolute()
        capture.plain_path(folder)
        lock = WriterLock(folder)
        try:
            info = read_json(folder/'collection.json')
            fields = {'collection_schema_version', 'collection_id', 'created_at', 'profile', 'profile_sha256',
                      'guide', 'guide_sha256', 'template', 'template_sha256', 'effective', 'effective_sha256',
                      'source_kind', 'parent_collection_id', 'review_policy'}
            fields |= {'initial_origin_group_id', 'inherited_origin_purposes'}
            if (not isinstance(info, dict) or set(info) != fields or type(info['collection_schema_version']) is not int
                    or info['collection_schema_version'] != 1 or info['collection_id'] != folder.name
                    or info['source_kind'] not in ('camera', 'sample') or info['review_policy'] != 'human-batch-review-v1'):
                raise ValueError('수집 사본 형식/정책 오류입니다.')
            validate_plan(info['template'], info['profile'], info['guide'])
            for key in ('guide', 'template', 'effective'):
                if info[key+'_sha256'] != digest(info[key]):
                    raise ValueError('수집 계획 사본 해시가 다릅니다.')
            if info['profile_sha256'] != capture.profile_digest(info['profile']):
                raise ValueError('수집 제품 사본 해시가 다릅니다.')
            if info['effective'] != expand_plan(info['template'], info['effective']['has_lamp']):
                raise ValueError('전개된 계획이 고정된 원본 계획과 다릅니다.')
            return cls(folder, lock, info)
        except Exception:
            lock.close()
            raise

    def close(self):
        self.lock.close()
        self.closed = True

    def _record(self, kind, data):
        if self.failed or self.closed:
            raise capture.CaptureError('수집이 닫혔거나 부분 저장 오류가 있습니다. 원본을 보존하고 다시 열어 검증하세요.')
        try:
            event = self.log.append(kind, data)
            self._apply(event)
        except Exception:
            self.failed = True
            raise

    def _apply(self, event):
        kind, d = event['type'], deepcopy(event['data'])
        if kind == 'setup_created':
            validate_targets(d['roi'], self.template['placements'], (d['camera']['width'], d['camera']['height']))
            if d['lr_mapping'] not in ('screen_left_is_physical_left', 'screen_right_is_physical_left'):
                raise ValueError('L/R 기준 확인이 필요합니다.')
            self.setups[d['setup_id']] = {**d, 'confirmed': False}
            self.setup_id = d['setup_id']
        elif kind == 'setup_confirmed':
            if d['human_confirmed'] is not True:
                raise ValueError('기준 구도는 사람이 확인해야 합니다.')
            self.setups[d['setup_id']]['confirmed'] = True
        elif kind == 'round_started':
            inherited = self.info['inherited_origin_purposes'].get(d['origin_group_id'])
            if inherited is not None and inherited != d['purpose']:
                raise ValueError('이전 계획과 origin_group 용도 충돌')
            for previous in self.rounds.values():
                if previous['origin_group_id'] == d['origin_group_id'] and previous['purpose'] != d['purpose']:
                    raise ValueError('같은 origin_group을 학습/검증/시험 용도에 나눌 수 없습니다.')
            self.rounds[d['round_id']] = d
        elif kind == 'session_bound':
            self.bindings[d['binding_id']] = d
        elif kind == 'prepared':
            pass  # historical human declaration, never restores an armed shutter
        elif kind == 'attempt_intent':
            if d['attempt_id'] in self.intents or d['setup_id'] not in self.setups:
                raise ValueError('촬영 시도 ID/기준 연결 오류')
            self.intents[d['attempt_id']] = d
        elif kind == 'attempt_saved':
            intent = self.intents[d['attempt_id']]
            if d['attempt_id'] in self.attempts:
                raise ValueError('동일 시도 이중 저장 연결')
            attempt = {**intent, **d, 'rejected': False, 'quality_ack': not intent['metrics']['warnings']}
            self.attempts[d['attempt_id']] = attempt
            self.current[intent['role_id']] = d['attempt_id']
        elif kind == 'attempt_cancelled':
            self.intents[d['attempt_id']]['cancelled'] = True
        elif kind == 'quality_acknowledged':
            if d['human_acknowledged'] is not True:
                raise ValueError('품질 보조 경고는 사람 확인이 필요합니다.')
            self.attempts[d['attempt_id']]['quality_ack'] = True
        elif kind == 'attempt_rejected':
            attempt = self.attempts[d['attempt_id']]
            attempt.update(rejected=True, rejection_reason=d['reason'], rearranged=d['rearranged'], held=d.get('held', False))
            if self.current.get(attempt['role_id']) == d['attempt_id']:
                del self.current[attempt['role_id']]
            self.accepted.pop(attempt['block_id'], None)
            if attempt['purpose'] == 'setup_reference':
                self.setups[attempt['setup_id']]['confirmed'] = False
        elif kind == 'batch_accepted':
            block = self.block_by_id[d['block_id']]
            expected = {s['step_id']: self.current.get(s['step_id']) for s in block['steps']}
            if (d['human_confirmed'] is not True or d['policy'] != 'human-batch-review-v1'
                    or d['attempts'] != expected or any(a is None for a in expected.values())
                    or any(not self.attempts[a]['quality_ack'] for a in expected.values())):
                raise ValueError('묶음 확인과 현재 사진 연결이 다릅니다.')
            self.accepted[d['block_id']] = d['attempts']
        elif kind == 'condition_skipped':
            if not isinstance(d['reason'], str) or not d['reason'].strip():
                raise ValueError('생략 이유가 필요합니다.')
            for block_id in d['block_ids']:
                self.block_by_id[block_id]
                self.skipped[block_id] = d['reason']
        elif kind == 'condition_resumed':
            for block_id in d['block_ids']:
                self.block_by_id[block_id]
                self.skipped.pop(block_id, None)
        elif kind == 'quality_calibrated':
            if self.rules['version'] != 1 or d['rules']['version'] != 2:
                raise ValueError('준비 시험 이후 품질 규칙을 덮어쓸 수 없습니다.')
            self.rules = d['rules']
        elif kind in ('paused', 'export_created'):
            pass
        else:
            raise ValueError(f'알 수 없는 수집 이벤트: {kind}')

    def _reconcile(self):
        rows = {}
        for folder in sorted((self.folder/'sessions').glob('S*')):
            session = CollectionSession.open(folder)
            if (session.info['source_kind'] != self.info['source_kind']
                    or capture.profile_digest(session.profile) != self.info['profile_sha256']):
                raise ValueError('수집 입력/제품과 세션 기록이 다릅니다.')
            self.sessions[session.session_id] = session
            for row in session.records:
                attempt_id = row['notes'].removeprefix('dataset-wizard:')
                if attempt_id not in self.intents or attempt_id in rows:
                    raise ValueError('수집 시도에 연결되지 않은 사진이 있습니다. 원본을 보존하세요.')
                intent = self.intents[attempt_id]
                if (row['notes'] != 'dataset-wizard:'+attempt_id or row['session_id'] != intent['session_id']
                        or row['episode_id'] != intent['episode_id'] or row['scenario'] != intent['scenario']):
                    raise ValueError('저장 전 시도와 실제 사진 연결이 다릅니다.')
                rows[attempt_id] = row
        for attempt_id, attempt in self.attempts.items():
            if attempt_id not in rows or attempt['record'] != rows[attempt_id]:
                raise ValueError('수집 기록과 실제 원본이 다릅니다. 원본을 보존하세요.')
        for attempt_id, intent in list(self.intents.items()):
            if attempt_id in self.attempts or intent.get('cancelled'):
                continue
            if attempt_id in rows:
                self._record('attempt_saved', {'attempt_id': attempt_id, 'record': rows[attempt_id], 'recovered': True})
            else:
                self._record('attempt_cancelled', {'attempt_id': attempt_id, 'reason': '중단 후 원본/manifest 없음'})

    def new_setup(self, frame, roi, lr_mapping):
        if not frame.fresh():
            raise capture.CaptureError('연결된 최신 카메라 영상을 확인하세요.')
        validate_targets(roi, self.template['placements'], (frame.camera['width'], frame.camera['height']))
        if lr_mapping not in ('screen_left_is_physical_left', 'screen_right_is_physical_left'):
            raise ValueError('실물 좌우와 화면의 관계를 확인하세요.')
        # A changed setup cannot silently mix into an unfinished multi-state comparison.
        action = self.next_action()
        block = action.get('block')
        if block:
            for step in block['steps']:
                if step['step_id'] in self.current:
                    self.reject(self.current[step['step_id']], '카메라/구도 기준 변경', True)
        setup_id = new_id('SETUP')
        self._record('setup_created', {'setup_id': setup_id, 'camera': dict(frame.camera), 'roi': list(roi),
            'lr_mapping': lr_mapping, 'height_mm': None, 'illuminance_lux': None,
            'device': socket.gethostname(), 'physical_geometry': 'unmeasured', 'source_kind': self.info['source_kind']})
        return setup_id

    def reference_roles(self):
        return [f'{self.setup_id}_REF_{s}' for s in self.template['references']]

    def next_action(self):
        if self.setup_id is None:
            return {'kind': 'setup'}
        setup = self.setups[self.setup_id]
        for role, scenario in zip(self.reference_roles(), self.template['references']):
            attempt_id = self.current.get(role)
            if attempt_id is None:
                return {'kind': 'reference', 'role_id': role, 'scenario': scenario}
            if not self.attempts[attempt_id]['quality_ack']:
                return {'kind': 'quality', 'attempt': self.attempts[attempt_id]}
        if not setup['confirmed']:
            return {'kind': 'setup_review'}
        for block in self.blocks:
            if block['block_id'] in self.accepted or block['block_id'] in self.skipped:
                continue
            if block['phase'] == 'main':
                if any(b['block_id'] not in self.accepted for b in self.blocks if b['phase'] == 'pilot'):
                    return {'kind': 'pilot_incomplete'}
                if block['round_id'] not in self.rounds:
                    return {'kind': 'round', 'block': block}
            for step in block['steps']:
                attempt_id = self.current.get(step['step_id'])
                if attempt_id is None:
                    return {'kind': 'capture', 'block': block, 'role_id': step['step_id'], 'scenario': step['scenario']}
                if not self.attempts[attempt_id]['quality_ack']:
                    return {'kind': 'quality', 'block': block, 'attempt': self.attempts[attempt_id]}
            return {'kind': 'review', 'block': block}
        return {'kind': 'finished'}

    def confirm_setup(self, confirmed):
        if confirmed is not True or self.next_action()['kind'] != 'setup_review':
            raise ValueError('정상/빈자리 원본과 실제 좌우·검사영역을 사람이 확인해야 합니다.')
        self._record('setup_confirmed', {'setup_id': self.setup_id, 'human_confirmed': True})

    def begin_round(self, independent=False):
        action = self.next_action()
        if action['kind'] != 'round' or type(independent) is not bool:
            raise ValueError('새 회차 준비 단계가 아닙니다.')
        block = action['block']
        previous = list(self.rounds.values())[-1] if self.rounds else None
        origin = new_id('OG') if independent else (previous['origin_group_id'] if previous else self.info['initial_origin_group_id'])
        previous_purpose = previous['purpose'] if previous else self.info['inherited_origin_purposes'].get(origin)
        if previous_purpose and previous_purpose != block['purpose'] and not independent:
            raise ValueError('같은 연속 촬영은 다른 용도의 독립 자료가 아닙니다. 오늘은 멈추고 다른 시간에 물체를 치운 뒤 다시 준비하세요.')
        if self.rules['version'] == 1:
            calibrated = deepcopy(self.rules)
            calibrated['version'] = 2
            values = {}
            for b in self.blocks:
                if b['phase'] == 'pilot' and b['block_id'] in self.accepted:
                    for aid in self.accepted[b['block_id']].values():
                        a = self.attempts[aid]
                        values.setdefault(a['scenario'], []).append(a['metrics']['laplacian_variance'])
            calibrated['blur_by_state'] = {s: max(1., min(self.rules['blur_variance'], statistics.median(v)*.3)) for s, v in values.items()}
            calibrated['basis'] = 'human-reviewed pilot; provisional advisory thresholds, not model quality labels'
            self._record('quality_calibrated', {'rules': calibrated})
        self._record('round_started', {'round_id': block['round_id'], 'origin_group_id': origin,
            'purpose': block['purpose'], 'independence_human_declared': independent,
            'independence_verified': False, 'setup_id': self.setup_id})

    def prepare(self, frame, now=None):
        action = self.next_action()
        if action['kind'] not in ('reference', 'capture'):
            raise ValueError('현재 지시/검토를 먼저 확인하세요.')
        setup = self.setups[self.setup_id]
        if (not frame.fresh() or not connection_matches(frame.camera, setup['camera'])
                or frame.image.shape[:2] != (setup['camera']['height'], setup['camera']['width'])):
            raise capture.CaptureError('카메라/해상도가 기준과 다릅니다. 기준 설정을 다시 확인하세요.')
        readiness = PreparedCapture(new_id('READY'), action['role_id'], self.setup_id, frame.stream_id,
                                    time.monotonic() if now is None else now)
        self._record('prepared', {'readiness_id': readiness.readiness_id, 'role_id': readiness.role_id,
                                 'setup_id': self.setup_id, 'human_declaration': True})
        return readiness

    def save_prepared(self, ticket, frame):
        action = self.next_action()
        if (ticket.consumed or action.get('role_id') != ticket.role_id or ticket.setup_id != self.setup_id
                or frame.stream_id != ticket.stream_id or not frame.fresh()
                or frame.received_mono <= ticket.prepared_mono+self.rules['settle_seconds']):
            raise capture.CaptureError('취소/중복/오래된 준비 프레임입니다. 새로 준비하세요.')
        ticket.consumed = True
        setup, block = self.setups[self.setup_id], action.get('block')
        if not connection_matches(frame.camera, setup['camera']):
            raise capture.CaptureError('카메라 설정이 바뀌었습니다. 새 기준을 확인하세요.')
        binding_id = (block['block_id'] if block else 'REF')+'_'+self.setup_id
        conditions = json.dumps({'collection': self.info['collection_id'], 'binding': binding_id}, sort_keys=True)
        if binding_id not in self.bindings:
            session = CollectionSession.create(self.folder/'sessions', self.profile, frame, conditions,
                                                source_kind=self.info['source_kind'])
            self.sessions[session.session_id] = session
            self._record('session_bound', {'binding_id': binding_id, 'session_id': session.session_id, 'setup_id': self.setup_id})
        session = self.sessions[self.bindings[binding_id]['session_id']]
        session.can_continue(self.profile, frame, conditions, self.info['source_kind'])
        previous = [a for a in self.attempts.values() if a['role_id'] == ticket.role_id and a['setup_id'] == self.setup_id]
        if previous and not previous[-1].get('rearranged', False):
            session.scenario, session.episode_id = action['scenario'], previous[-1]['record']['episode_id']
        else:
            session.set_scenario(action['scenario'])
            if previous:
                session.new_episode()
        session.not_before = ticket.prepared_mono+self.rules['settle_seconds']
        placement = next(p for p in self.template['placements'] if p['id'] == block['placement_id']) if block else self.template['placements'][0]
        roi = target_roi(setup['roi'], placement, (frame.camera['width'], frame.camera['height']))
        measurement = metrics(frame.image, roi, self.rules, action['scenario'])
        measurement['pixel_sha256'] = hashlib.sha256(frame.image.tobytes()).hexdigest()
        similar = []
        for a in self.attempts.values():
            distance = (int(measurement['dhash'], 16)^int(a['metrics']['dhash'], 16)).bit_count()
            if distance <= self.rules['similar_hash_distance']:
                similar.append(a['attempt_id'])
        if similar:
            measurement['warnings'].append('SIMILAR_IMAGE')
        if any(a['metrics']['pixel_sha256'] == measurement['pixel_sha256'] for a in self.attempts.values()):
            measurement['warnings'].append('DUPLICATE_EXACT')
        measurement['similar_attempts'] = similar[:20]
        aid = new_id('A')
        round_id = block['round_id'] if block else 'SETUP'
        origin = self.rounds[round_id]['origin_group_id'] if round_id in self.rounds else self.info['initial_origin_group_id']
        intent = {'attempt_id': aid, 'role_id': ticket.role_id, 'setup_id': self.setup_id,
            'block_id': block['block_id'] if block else None, 'round_id': round_id,
            'origin_group_id': origin, 'purpose': block['purpose'] if block else 'setup_reference',
            'condition_id': block['condition_id'] if block else 'SETUP',
            'placement_id': block['placement_id'] if block else self.template['placements'][0]['id'],
            'scenario': action['scenario'], 'session_id': session.session_id, 'episode_id': session.episode_id,
            'readiness_id': ticket.readiness_id, 'metrics': measurement}
        self._record('attempt_intent', intent)
        try:
            session.save(frame, notes='dataset-wizard:'+aid)
            row = session.records[-1]
            self._record('attempt_saved', {'attempt_id': aid, 'record': row, 'recovered': False})
        except Exception:
            self.failed = True
            raise
        return self.attempts[aid]

    def acknowledge_quality(self, attempt_id, confirmed):
        if confirmed is not True or attempt_id not in self.attempts or self.attempts[attempt_id]['rejected']:
            raise ValueError('품질 경고 확인 대상이 올바르지 않습니다.')
        self._record('quality_acknowledged', {'attempt_id': attempt_id, 'human_acknowledged': True,
                                             'semantics': 'warning_seen_not_batch_acceptance'})

    def reject(self, attempt_id, reason, rearranged=False, held=False):
        if (attempt_id not in self.attempts or not isinstance(reason, str) or not reason.strip()
                or type(rearranged) is not bool or type(held) is not bool):
            raise ValueError('재촬영 대상/이유/실제 재배치 여부를 확인하세요.')
        self._record('attempt_rejected', {'attempt_id': attempt_id, 'reason': reason, 'rearranged': rearranged, 'held': held})

    def accept_batch(self, block_id, confirmed):
        action = self.next_action()
        if confirmed is not True or action['kind'] != 'review' or action['block']['block_id'] != block_id:
            raise ValueError('묶음의 모든 상태와 검사 영역을 사람이 한 번 확인해야 합니다.')
        values = {s['step_id']: self.current[s['step_id']] for s in action['block']['steps']}
        self._record('batch_accepted', {'block_id': block_id, 'attempts': values,
                                      'human_confirmed': True, 'policy': 'human-batch-review-v1'})

    def skip_condition(self, reason):
        action = self.next_action()
        block = action.get('block')
        if not block or not isinstance(reason, str) or not reason.strip():
            raise ValueError('현재 촬영 조건과 생략 이유를 확인하세요.')
        ids = [b['block_id'] for b in self.blocks if b['phase'] == block['phase'] and b['round_id'] == block['round_id']
               and b['condition_id'] == block['condition_id'] and b['block_id'] not in self.accepted]
        self._record('condition_skipped', {'block_ids': ids, 'reason': reason})

    def resume_missing(self):
        """Undo a scheduling skip, retaining the original skip event and reason."""
        self._record('condition_resumed', {'block_ids': list(self.skipped)})

    def pause(self):
        self._record('paused', {'readiness_restored': False})

    def summary(self):
        accepted_ids = {aid for group in self.accepted.values() for aid in group.values()}
        result = {'main_target': sum(len(b['steps']) for b in self.blocks if b['phase'] == 'main'),
                  'pilot_target': sum(len(b['steps']) for b in self.blocks if b['phase'] == 'pilot'),
                  'main_accepted': 0, 'pilot_accepted': 0, 'saved': len(self.attempts), 'pending': 0,
                  'retained_retake': sum(a['rejected'] for a in self.attempts.values()), 'by_condition': []}
        result['held'] = sum(a.get('held', False) for a in self.attempts.values())
        result['retained_retake'] -= result['held']
        hashes = {}
        for a in self.attempts.values():
            hashes.setdefault(a['record']['image_sha256'], []).append(a['record']['capture_id'])
        result['exact_duplicate_groups'] = [ids for ids in hashes.values() if len(ids) > 1]
        for block in self.blocks:
            counts = Counter()
            states = []
            for step in block['steps']:
                attempts = [a for a in self.attempts.values() if a['role_id'] == step['step_id']]
                accepted = int(self.current.get(step['step_id']) in accepted_ids)
                pending = int(step['step_id'] in self.current and not accepted)
                states.append({'scenario': step['scenario'], 'target': 1, 'saved': len(attempts),
                    'accepted': accepted, 'pending': pending, 'retained_retake': sum(a['rejected'] and not a.get('held') for a in attempts),
                    'held': sum(a.get('held', False) for a in attempts),
                    'missing': 1-accepted, 'skip_reason': self.skipped.get(block['block_id'])})
                counts.update(accepted=accepted, pending=pending)
            result[block['phase']+'_accepted'] += counts['accepted']
            result['pending'] += counts['pending']
            result['by_condition'].append({k: block[k] for k in ('block_id', 'phase', 'round_id', 'condition_id', 'placement_id')} | {'states': states})
        result['missing'] = result['main_target']-result['main_accepted']
        result['complete'] = result['missing'] == 0 and result['pilot_accepted'] == result['pilot_target'] and result['pending'] == 0
        return result

    def lineage_info(self):
        purposes = dict(self.info['inherited_origin_purposes'])
        for r in self.rounds.values():
            purposes[r['origin_group_id']] = r['purpose']
        origin = list(self.rounds.values())[-1]['origin_group_id'] if self.rounds else self.info['initial_origin_group_id']
        return {**self.info, 'continuation_origin': origin, 'origin_purposes': purposes}

    def export(self):
        self._reconcile()  # actual PNG/manifest/hash validation immediately before handoff
        destination = self.folder/'exports'/new_id('EXPORT')
        destination.mkdir(parents=True)
        accepted_ids = {aid for b, group in self.accepted.items() if self.block_by_id[b]['phase'] == 'main' for aid in group.values()}
        outputs = {'images_for_labeling': [], 'training_candidates': [], 'validation_candidates': [],
                   'test_reserved': [], 'sample_only': [], 'excluded_or_pending': []}
        purposes = {}
        for aid, a in self.attempts.items():
            row = a['record']
            item = {k: a[k] for k in ('attempt_id', 'role_id', 'round_id', 'origin_group_id', 'setup_id',
                                     'condition_id', 'placement_id', 'purpose', 'scenario')}
            item.update(collection_id=self.info['collection_id'], capture_id=row['capture_id'], session_id=row['session_id'],
                step_id=a['role_id'] if a['block_id'] else None, plan_version=self.template['plan_version'],
                product_id=self.profile['product_id'], profile_version=self.profile['profile_version'],
                episode_id=row['episode_id'], image_path=str(self.folder/'sessions'/row['image_path']),
                image_sha256=row['image_sha256'], source_kind=row['source_kind'],
                objects_removed=row['object_configuration']['objects_removed'],
                profile_sha256=self.info['profile_sha256'], plan_sha256=self.info['effective_sha256'])
            if row['source_kind'] == 'sample':
                outputs['sample_only'].append(item)
            elif aid in accepted_ids:
                previous = purposes.setdefault(a['origin_group_id'], a['purpose'])
                if previous != a['purpose']:
                    raise ValueError('용도별 origin_group 충돌: 내보내기 중단')
                outputs['images_for_labeling'].append(item)
                bucket = {'train_candidate': 'training_candidates', 'validation_candidate': 'validation_candidates', 'test_reserved': 'test_reserved'}[a['purpose']]
                outputs[bucket].append(item)
            else:
                item['reason'] = a.get('rejection_reason') or ('준비/기준 자료' if a['purpose'] in ('preparation', 'setup_reference') else '검토 대기 또는 미수집 조건')
                outputs['excluded_or_pending'].append(item)
        try:
            for name, rows in outputs.items():
                write_new_json(destination/(name+'.json'), rows)
            write_new_json(destination/'collection_summary.json', self.summary())
            write_new_json(destination/'product_and_plan.json', {'objects': self.profile['objects'],
                'profile': self.profile, 'template': self.template, 'effective': self.effective,
                'review_policy': self.info['review_policy'], 'annotation_status': 'NOT_STARTED', 'training_status': 'NOT_STARTED'})
            self._record('export_created', {'folder': destination.name, 'human_labeling_required': True})
        except Exception as exc:
            raise capture.CaptureError(f'인계 목록 저장 실패. 부분 파일 보존: {destination}: {exc}') from exc
        return destination
