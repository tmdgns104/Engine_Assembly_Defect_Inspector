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
from .wizard_plan import (expand_plan, target_roi, validate_plan, validate_targets,
                          rotation_plan, placement_for_action, setup_placements)
from .wizard_quality import metrics
from .wizard_store import EventLog, WriterLock, utc_now, write_new_json
from .storage_paths import storage_path
from . import engine_dataset as engine


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
    engine_angle_human_confirmed: bool = False
    motion_mae: float | None = None


class Collection:
    @staticmethod
    def latest_lineage(root):
        """Continue provenance when a restarted UI creates a revised plan.

        Never import its images/counts. The previous writer must be closed and
        its stored evidence must verify before a new plan can inherit grouping.
        """
        candidates = [(read_json(p)['created_at'], p.parent)
                      for p in storage_path(root).glob('C*/collection.json')]
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
        self.blocks = deepcopy(self.effective['blocks'])
        self.block_by_id = {b['block_id']: b for b in self.blocks}
        self.step_by_id = {s['step_id']: (b, s) for b in self.blocks for s in b['steps']}
        self.setup_id = None
        self.state_preparations = {}
        self.crank_preparations = {}
        self.active_challenge_id = None
        self.final_test_unlocked = False
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
    def create(cls, root, profile, guide, template, has_lamp, source_kind='camera', parent=None, station=None):
        validate_plan(template, profile, guide)
        if source_kind not in ('camera', 'sample'):
            raise ValueError('수집 입력 종류 오류')
        if parent and parent['template']['plan_id'] == template['plan_id']:
            if digest(parent['template']) != digest(template) and template['plan_version'] <= parent['template']['plan_version']:
                raise ValueError('변경된 계획은 이전보다 높은 plan_version으로 저장하세요.')
        root = storage_path(root)
        if engine.engine_v1(template):
            station = deepcopy(station or engine.station_settings())
            engine.validate_station(station)
            root = root/station['station_id']/'collections'
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
                    'effective': expand_plan(template, has_lamp, station), 'source_kind': source_kind,
                    'parent_collection_id': parent['collection_id'] if parent else None,
                    'initial_origin_group_id': parent['continuation_origin'] if parent else new_id('OG'),
                    'inherited_origin_purposes': parent['origin_purposes'] if parent else {},
                    'review_policy': 'human-batch-review-v1'}
            info['effective_sha256'] = digest(info['effective'])
            if engine.engine_v1(template):
                info['station'] = station
            write_new_json(folder/'collection.json', info)
            return cls(folder, lock, info)
        except Exception:
            lock.close()
            raise

    @classmethod
    def open(cls, folder):
        folder = storage_path(folder)
        capture.plain_path(folder)
        lock = WriterLock(folder)
        try:
            info = read_json(folder/'collection.json')
            fields = {'collection_schema_version', 'collection_id', 'created_at', 'profile', 'profile_sha256',
                      'guide', 'guide_sha256', 'template', 'template_sha256', 'effective', 'effective_sha256',
                      'source_kind', 'parent_collection_id', 'review_policy'}
            fields |= {'initial_origin_group_id', 'inherited_origin_purposes'}
            if engine.engine_v1(info.get('template', {})):
                fields.add('station')
                engine.validate_station(info.get('station'))
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
            if info['effective'] != expand_plan(info['template'], info['effective']['has_lamp'], info.get('station')):
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
            validate_targets(d['roi'], setup_placements(self.template), (d['camera']['width'], d['camera']['height']))
            if d.get('alignment_roi') is not None:
                from .engine_alignment import validate_alignment
                if not rotation_plan(self.template):
                    raise ValueError('회전 정렬 가이드는 엔진 회전 계획에서만 사용합니다.')
                validate_alignment(d['alignment_roi'], d['roi'], (d['camera']['width'], d['camera']['height']))
            if d['lr_mapping'] not in self.setup_mappings():
                raise ValueError('L/R 기준 확인이 필요합니다.')
            self.setups[d['setup_id']] = {**d, 'confirmed': False}
            self.setup_id = d['setup_id']
            self.state_preparations.clear()
            self.crank_preparations.clear()
        elif kind == 'setup_confirmed':
            if d['human_confirmed'] is not True:
                raise ValueError('기준 구도는 사람이 확인해야 합니다.')
            self.setups[d['setup_id']]['confirmed'] = True
        elif kind == 'round_started':
            if rotation_plan(self.template) and d.get('human_repositioned') is not True:
                raise ValueError('회전 계획 회차의 사람 재배치 확인이 없습니다.')
            inherited = self.info['inherited_origin_purposes'].get(d['origin_group_id'])
            if inherited is not None and inherited != d['purpose']:
                raise ValueError('이전 계획과 origin_group 용도 충돌')
            for previous in self.rounds.values():
                if previous['origin_group_id'] == d['origin_group_id'] and previous['purpose'] != d['purpose']:
                    raise ValueError('같은 origin_group을 학습/검증/시험 용도에 나눌 수 없습니다.')
            self.rounds[d['round_id']] = d
        elif kind == 'session_bound':
            self.bindings[d['binding_id']] = d
        elif kind == 'state_prepared':
            if (not rotation_plan(self.template) or d['block_id'] not in self.block_by_id
                    or d['setup_id'] != self.setup_id or d['human_repositioned'] is not True
                    or d['camera_fixed'] is not True or d['angle_sensor_verified'] is not False):
                raise ValueError('상태 시작의 실제 재배치/카메라 고정 확인이 필요합니다.')
            if engine.engine_v1(self.template):
                scenario = self.block_by_id[d['block_id']]['scenario']
                engine.require_checks(d.get('checklist'), engine.physical_checklist(self.profile, scenario))
            self.state_preparations[d['block_id']] = d
        elif kind == 'crank_prepared':
            engine.require_checks(d['checklist'], engine.CRANK_CHECKS)
            if d['setup_id'] != self.setup_id or d['crank_phase_id'] not in engine.CRANK_PHASES or d['crank_sensor_verified'] is not False:
                raise ValueError('Crank 목표/사람 확인 연결 오류')
            self.crank_preparations[d['key']] = d
        elif kind == 'challenge_added':
            block = d['block']
            if (not engine.engine_v1(self.template) or block['scenario'] not in engine.CHALLENGES
                    or block['phase'] != 'challenge' or block['block_id'] in self.block_by_id):
                raise ValueError('Challenge 촬영 계약 오류')
            self.blocks.append(block)
            self.block_by_id[block['block_id']] = block
            self.step_by_id.update({s['step_id']: (block, s) for s in block['steps']})
            self.active_challenge_id = block['block_id']
            # A challenge changes the physical scene; main gates must run again.
            self.state_preparations.clear()
            self.crank_preparations.clear()
        elif kind == 'final_test_unlocked':
            if not engine.engine_v1(self.template) or d['confirmation'] != engine.UNLOCK_PHRASE:
                raise ValueError('Final Test 명시적 unlock 문구가 필요합니다.')
            self.final_test_unlocked = True
        elif kind == 'physical_reconfirmation_required':
            self.state_preparations.clear()
            self.crank_preparations.clear()
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
            if d['rearranged']:
                self.state_preparations.pop(attempt['block_id'], None)
            if engine.engine_v1(self.template):
                # Retakes can jump backwards to a different handle position.
                self.crank_preparations.clear()
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
            if self.active_challenge_id == d['block_id']:
                self.active_challenge_id = None
                self.state_preparations.clear()
                self.crank_preparations.clear()
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
            expected_profile = (engine.challenge_profile(self.profile) if engine.engine_v1(self.template)
                                and any(r['scenario'] in engine.CHALLENGES for r in session.records) else self.profile)
            # An interrupted challenge may have an empty session but its pinned
            # derived profile is still a valid acquisition snapshot.
            allowed_profiles = {capture.profile_digest(expected_profile)}
            if engine.engine_v1(self.template):
                allowed_profiles.add(capture.profile_digest(engine.challenge_profile(self.profile)))
            if (session.info['source_kind'] != self.info['source_kind']
                    or capture.profile_digest(session.profile) not in allowed_profiles):
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

    def new_setup(self, frame, roi, lr_mapping, alignment_roi=None):
        if not frame.fresh():
            raise capture.CaptureError('연결된 최신 카메라 영상을 확인하세요.')
        validate_targets(roi, setup_placements(self.template), (frame.camera['width'], frame.camera['height']))
        if lr_mapping not in self.setup_mappings():
            raise ValueError('실물 좌우와 화면의 관계를 확인하세요.')
        if alignment_roi is not None:
            from .engine_alignment import validate_alignment
            if not rotation_plan(self.template):
                raise ValueError('회전 정렬 가이드는 엔진 회전 계획에서만 사용합니다.')
            validate_alignment(alignment_roi, roi, (frame.camera['width'], frame.camera['height']))
        # A changed setup cannot silently mix into an unfinished multi-state comparison.
        action = self.next_action()
        block = action.get('block')
        if block:
            for step in block['steps']:
                if step['step_id'] in self.current:
                    self.reject(self.current[step['step_id']], '카메라/구도 기준 변경', True)
        setup_id = new_id('SETUP')
        setup = {'setup_id': setup_id, 'camera': dict(frame.camera), 'roi': list(roi),
            'lr_mapping': lr_mapping, 'height_mm': None, 'illuminance_lux': None,
            'device': socket.gethostname(), 'physical_geometry': 'unmeasured', 'source_kind': self.info['source_kind']}
        if alignment_roi is not None:
            # Display geometry belongs to this setup, not to ground truth or labels.
            setup['alignment_roi'] = list(alignment_roi)
        self._record('setup_created', setup)
        return setup_id

    def setup_mappings(self):
        if rotation_plan(self.template):
            return ('engine_zero_reference_clockwise',)
        return ('screen_left_is_physical_left', 'screen_right_is_physical_left')

    def reference_roles(self):
        return [f'{self.setup_id}_REF_{s}' for s in self.template['references']]

    def next_action(self):
        if self.setup_id is None:
            return {'kind': 'setup'}
        setup = self.setups[self.setup_id]
        for role, scenario in zip(self.reference_roles(), self.template['references']):
            attempt_id = self.current.get(role)
            if attempt_id is None:
                return self.capture_action({'kind': 'reference', 'role_id': role, 'scenario': scenario})
            if not self.attempts[attempt_id]['quality_ack']:
                return {'kind': 'quality', 'attempt': self.attempts[attempt_id]}
        if not setup['confirmed']:
            return {'kind': 'setup_review'}
        ordered = self.blocks
        if self.active_challenge_id:
            ordered = [self.block_by_id[self.active_challenge_id]] + [b for b in self.blocks if b['block_id'] != self.active_challenge_id]
        for block in ordered:
            if block['block_id'] in self.accepted or block['block_id'] in self.skipped:
                continue
            if block['phase'] == 'main':
                if any(b['block_id'] not in self.accepted for b in self.blocks if b['phase'] == 'pilot'):
                    return {'kind': 'pilot_incomplete'}
                if block['round_id'] not in self.rounds:
                    return {'kind': 'round', 'block': block}
            if (rotation_plan(self.template) and block['block_id'] not in self.state_preparations
                    and any(s['step_id'] not in self.current for s in block['steps'])):
                return {'kind': 'state_setup', 'block': block, 'scenario': block['scenario']}
            for step in block['steps']:
                attempt_id = self.current.get(step['step_id'])
                if attempt_id is None:
                    return self.capture_action({'kind': 'capture', 'block': block, 'role_id': step['step_id'], 'scenario': step['scenario']})
                if not self.attempts[attempt_id]['quality_ack']:
                    return {'kind': 'quality', 'block': block, 'attempt': self.attempts[attempt_id]}
            return {'kind': 'review', 'block': block}
        return {'kind': 'finished'}

    def capture_action(self, action):
        if engine.engine_v1(self.template) and engine.crank_gate_key(action) not in self.crank_preparations:
            return {**action, 'kind': 'crank_setup', 'crank_phase_id': engine.crank_for_action(action)}
        return action

    def confirm_crank(self, checks):
        action = self.next_action()
        if action['kind'] != 'crank_setup':
            raise ValueError('현재 Crank 확인 단계가 아닙니다.')
        engine.require_checks(checks, engine.CRANK_CHECKS)
        self._record('crank_prepared', {'key': engine.crank_gate_key(action), 'setup_id': self.setup_id,
            'crank_phase_id': engine.crank_for_action(action), 'crank_sensor_verified': False,
            'checklist': checks, 'preparation_id': new_id('CRANK')})

    def add_challenge(self, scenario, angle_id='ANGLE_000', crank_phase_id='CRANK_000', condition_id='BALANCED', details=''):
        if (not engine.engine_v1(self.template) or scenario not in engine.CHALLENGES
                or self.setup_id is None or not self.setups[self.setup_id]['confirmed'] or self.active_challenge_id):
            raise ValueError('기준 확인 후 Challenge를 선택하세요. 진행 중인 Challenge는 먼저 검토하세요.')
        if angle_id not in {p['id'] for p in self.template['placements']} or crank_phase_id not in engine.CRANK_PHASES:
            raise ValueError('Challenge angle/Crank 목표를 확인하세요.')
        if condition_id not in ('BALANCED', 'ASYMMETRIC') or not isinstance(details, str) or not details.strip():
            raise ValueError('조명과 실제 Challenge 조건 설명을 기록하세요.')
        if scenario == 'CONVEYOR_MOVING':
            raise ValueError('CONVEYOR_MOVING은 향후 실제 공정 Pilot용 예약값이며 현재 UI에서는 비활성입니다.')
        bid = new_id('CHALLENGE')
        block = {'block_id': bid, 'phase': 'challenge', 'round_id': 'CHALLENGE', 'purpose': 'review_challenge',
                 'condition_id': condition_id, 'placement_id': angle_id, 'scenario': scenario, 'details': details,
                 'steps': [{'step_id': bid+'_'+angle_id, 'scenario': scenario, 'placement_id': angle_id, 'crank_phase_id': crank_phase_id}]}
        self._record('challenge_added', {'block': block})

    def unlock_final_test(self, confirmation):
        if confirmation != engine.UNLOCK_PHRASE or not engine.engine_v1(self.template):
            raise ValueError('UNLOCK FINAL TEST LABELING을 정확히 입력하세요.')
        self._record('final_test_unlocked', {'confirmation': confirmation, 'training_still_forbidden': True})

    def reconfirm_physical_state(self):
        self._record('physical_reconfirmation_required', {'reason': 'human resumed physical collection'})

    def confirm_setup(self, confirmed):
        if confirmed is not True or self.next_action()['kind'] != 'setup_review':
            raise ValueError('정상/빈자리 원본과 실제 좌우·검사영역을 사람이 확인해야 합니다.')
        self._record('setup_confirmed', {'setup_id': self.setup_id, 'human_confirmed': True})

    def begin_round(self, independent=False, repositioned=False):
        action = self.next_action()
        if action['kind'] != 'round' or type(independent) is not bool:
            raise ValueError('새 회차 준비 단계가 아닙니다.')
        if rotation_plan(self.template) and repositioned is not True:
            raise ValueError('엔진을 치웠다가 회전 중심에 다시 놓고 카메라 고정을 확인하세요.')
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
        round_data = {'round_id': block['round_id'], 'origin_group_id': origin,
            'purpose': block['purpose'], 'independence_human_declared': independent,
            'independence_verified': False, 'setup_id': self.setup_id}
        if rotation_plan(self.template):
            round_data['human_repositioned'] = True
        self._record('round_started', round_data)

    def confirm_state_preparation(self, repositioned, camera_fixed, checklist=None):
        action = self.next_action()
        if action['kind'] != 'state_setup' or repositioned is not True or camera_fixed is not True:
            raise ValueError('상태에 맞게 부품을 준비하고 엔진 재배치·카메라 고정을 사람이 확인하세요.')
        extra = {}
        if engine.engine_v1(self.template):
            engine.require_checks(checklist, engine.physical_checklist(self.profile, action['scenario']))
            extra['checklist'] = checklist
        self._record('state_prepared', {'block_id': action['block']['block_id'], 'setup_id': self.setup_id,
            'preparation_id': new_id('PHYSICAL'), 'human_repositioned': True, 'camera_fixed': True,
            'angle_sensor_verified': False, **extra})

    def prepare(self, frame, now=None, engine_angle_confirmed=False):
        action = self.next_action()
        if action['kind'] not in ('reference', 'capture'):
            raise ValueError('현재 지시/검토를 먼저 확인하세요.')
        if engine.engine_v1(self.template) and engine_angle_confirmed is not True:
            raise ValueError('현재 Engine 목표 각도를 사람이 확인해야 합니다.')
        setup = self.setups[self.setup_id]
        if (not frame.fresh() or not connection_matches(frame.camera, setup['camera'])
                or frame.image.shape[:2] != (setup['camera']['height'], setup['camera']['width'])):
            raise capture.CaptureError('카메라/해상도가 기준과 다릅니다. 기준 설정을 다시 확인하세요.')
        readiness = PreparedCapture(new_id('READY'), action['role_id'], self.setup_id, frame.stream_id,
                                    time.monotonic() if now is None else now,
                                    engine_angle_human_confirmed=engine_angle_confirmed)
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
        active_profile = (engine.challenge_profile(self.profile) if engine.engine_v1(self.template)
                          and action['scenario'] in engine.CHALLENGES else self.profile)
        conditions = json.dumps({'collection': self.info['collection_id'], 'binding': binding_id}, sort_keys=True)
        if binding_id not in self.bindings:
            session = CollectionSession.create(self.folder/'sessions', active_profile, frame, conditions,
                                                source_kind=self.info['source_kind'])
            self.sessions[session.session_id] = session
            self._record('session_bound', {'binding_id': binding_id, 'session_id': session.session_id, 'setup_id': self.setup_id})
        session = self.sessions[self.bindings[binding_id]['session_id']]
        session.can_continue(active_profile, frame, conditions, self.info['source_kind'])
        previous = [a for a in self.attempts.values() if a['role_id'] == ticket.role_id and a['setup_id'] == self.setup_id]
        if previous and not previous[-1].get('rearranged', False):
            session.scenario, session.episode_id = action['scenario'], previous[-1]['record']['episode_id']
        else:
            session.set_scenario(action['scenario'])
            if previous:
                session.new_episode()
        session.not_before = ticket.prepared_mono+self.rules['settle_seconds']
        placement = placement_for_action(self.template, action)
        roi = target_roi(setup['roi'], placement, (frame.camera['width'], frame.camera['height']))
        measurement = metrics(frame.image, roi, self.rules, action['scenario'])
        if engine.engine_v1(self.template):
            measurement['motion_mae'] = ticket.motion_mae
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
            'placement_id': placement['id'],
            'scenario': action['scenario'], 'session_id': session.session_id, 'episode_id': session.episode_id,
            'readiness_id': ticket.readiness_id, 'metrics': measurement}
        if rotation_plan(self.template):
            intent.update(angle_id=placement['id'], target_angle_deg=placement['angle_deg'],
                          angle_sensor_verified=False,
                          state_preparation_id=self.state_preparations[block['block_id']]['preparation_id'] if block else None)
        if engine.engine_v1(self.template):
            crank = engine.crank_for_action(action)
            intent['engine_metadata'] = {**deepcopy(self.info['station']),
                **engine.truth_fields(self.profile, action['scenario']),
                'engine_angle_id': placement['id'], 'engine_angle_target_deg': placement['angle_deg'],
                'target_engine_angle_deg': placement['angle_deg'],
                'engine_angle_human_confirmed': ticket.engine_angle_human_confirmed, 'angle_sensor_verified': False,
                'crank_phase_id': crank, 'crank_phase_target_deg': int(crank[-3:]),
                'crank_phase_human_confirmed': True, 'crank_sensor_verified': False,
                'crank_preparation_id': self.crank_preparations[engine.crank_gate_key(action)]['preparation_id'],
                'lighting_id': engine.lighting_id(self, intent['condition_id'], action['scenario']),
                'capture_notes': block.get('details', '') if block else ''}
            intent['engine_metadata']['reference_normal_capture_id_at_capture'] = engine.reference_at_capture(self, intent)
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
        if engine.engine_v1(self.template) and self.summary()['complete']:
            return self.export()

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
        result['challenge_accepted'] = 0
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
                if rotation_plan(self.template):
                    states[-1]['placement_id'] = step['placement_id']
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

    def export(self, contact_sheets=False):
        self._reconcile()  # actual PNG/manifest/hash validation immediately before handoff
        if engine.engine_v1(self.template):
            from .engine_exports import export_collection
            return export_collection(self, contact_sheets=contact_sheets)
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
                profile_sha256=self.info['profile_sha256'], plan_sha256=self.info['effective_sha256'])
            configuration = row['object_configuration']
            if self.profile['profile_schema_version'] == 2:
                item.update(expected_counts=deepcopy(configuration['expected_counts']),
                            removed_slots=list(configuration['removed_slots']))
            else:
                item['objects_removed'] = configuration['objects_removed']
            if rotation_plan(self.template):
                item.update({k: a[k] for k in ('angle_id', 'target_angle_deg', 'angle_sensor_verified', 'state_preparation_id')})
            if row['source_kind'] == 'sample':
                outputs['sample_only'].append(item)
            elif aid in accepted_ids:
                previous = purposes.setdefault(a['origin_group_id'], a['purpose'])
                if previous != a['purpose']:
                    raise ValueError('용도별 origin_group 충돌: 내보내기 중단')
                # Keep v1 handoff byte/behavior compatibility. Rotation-plan test
                # reservations never enter the general annotation candidate list.
                if not rotation_plan(self.template) or a['purpose'] != 'test_reserved':
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
