"""One-click misassembly collection, separate from Wizard's reviewed policy."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import uuid

from training.scripts import capture_proxy as capture
from .session import CollectionSession
from .storage_paths import storage_path
from .wizard_quality import metrics
from .wizard_store import EventLog, WriterLock, utc_now, write_new_json


POLICY_VERSION = 'operator-declared-one-click-v1'
PARTS = ('pipe_left', 'pipe_right', 'exhaust', 'symbol')


def load_capture_plan(path):
    plan = json.loads(Path(path).read_text(encoding='utf-8'),
                      object_pairs_hook=capture.unique_json_object)
    if (plan.get('policy_version') != POLICY_VERSION or not isinstance(plan.get('steps'), list)
            or not plan['steps'] or not isinstance(plan.get('quality'), dict)):
        raise ValueError('간편 촬영 계획 형식이 올바르지 않습니다.')
    ids = set()
    for step in plan['steps']:
        if (not isinstance(step, dict) or not isinstance(step.get('step_id'), str)
                or step['step_id'] in ids or not isinstance(step.get('part_states'), dict)
                or set(step['part_states']) != set(PARTS)
                or not isinstance(step.get('target_engine_angle'), int)
                or not 0 <= step['target_engine_angle'] < 360
                or not isinstance(step.get('target_position'), str)
                or not isinstance(step.get('scenario_id'), str)
                or not isinstance(step.get('assembly_episode_id'), str)
                or not isinstance(step.get('source_group_id'), str)):
            raise ValueError('간편 촬영 단계의 ID/상태/각도를 확인하세요.')
        ids.add(step['step_id'])
    return plan


def capture_profile(plan):
    """Use the existing count profile for PNG storage; pose truth stays in our manifest."""
    normal = {'expected_counts': {'gray_pipe': 2, 'exhaust_top': 1, 'symbol_module': 1},
              'removed_slots': [], 'unexpected_object': False}
    scenarios = {}
    slot_for_part = dict(pipe_left='PIPE_LEFT', pipe_right='PIPE_RIGHT',
                         exhaust='EXHAUST_TOP', symbol='SYMBOL_MODULE')
    object_for_part = dict(pipe_left='gray_pipe', pipe_right='gray_pipe',
                           exhaust='exhaust_top', symbol='symbol_module')
    for step in plan['steps']:
        state = deepcopy(normal)
        for part, value in step['part_states'].items():
            if value == 'MISSING':
                state['removed_slots'].append(slot_for_part[part])
                state['expected_counts'][object_for_part[part]] -= 1
        scenarios[step['scenario_id']] = state
    scenarios['NORMAL'] = deepcopy(normal)
    profile = {'profile_schema_version': 2, 'product_id': 'engine_misassembly_capture_v1',
               'profile_version': 1, 'objects': list(normal['expected_counts']),
               'slots': {'PIPE_LEFT': 'gray_pipe', 'PIPE_RIGHT': 'gray_pipe',
                         'EXHAUST_TOP': 'exhaust_top', 'SYMBOL_MODULE': 'symbol_module'},
               'scenarios': scenarios}
    capture.validate_profile(profile)
    return profile


class SimpleCollection:
    def __init__(self, folder, plan, lock):
        self.folder, self.plan, self.lock = Path(folder), plan, lock
        self.log = EventLog(folder)
        self.session = None
        self.declarations = {}
        self.records = {}
        self.superseded = set()
        self.failed = False
        self._replay()

    @classmethod
    def create(cls, root, plan):
        root = storage_path(root)
        capture.plain_path(root)
        root.mkdir(parents=True, exist_ok=True)
        folder = root / ('M' + uuid.uuid4().hex[:16].upper())
        folder.mkdir()
        lock = WriterLock(folder)
        try:
            write_new_json(folder / 'capture-plan.json', plan)
            write_new_json(folder / 'collection-info.json', {
                'collection_id': folder.name, 'created_at': utc_now(),
                'policy_version': POLICY_VERSION, 'plan_sha256': hashlib.sha256(
                    (folder / 'capture-plan.json').read_bytes()).hexdigest()})
            return cls(folder, plan, lock)
        except Exception:
            lock.close()
            raise

    @classmethod
    def open(cls, folder):
        folder = storage_path(folder)
        plan = load_capture_plan(folder / 'capture-plan.json')
        info = json.loads((folder / 'collection-info.json').read_text(encoding='utf-8'))
        if (info['collection_id'] != folder.name or info['policy_version'] != POLICY_VERSION
                or info['plan_sha256'] != hashlib.sha256((folder / 'capture-plan.json').read_bytes()).hexdigest()):
            raise ValueError('수집 계획/정책이 원본과 다릅니다.')
        lock = WriterLock(folder)
        try:
            return cls(folder, plan, lock)
        except Exception:
            lock.close()
            raise

    def _replay(self):
        saved = {}
        for event in self.log.events:
            data = event['data']
            if event['type'] == 'simple_declared':
                self.declarations[data['declaration_id']] = data
            elif event['type'] == 'simple_saved':
                saved[data['capture_id']] = data
            elif event['type'] == 'simple_superseded':
                self.superseded.add(data['capture_id'])
        # A saved event is counted only after the existing PNG/manifest verifier succeeds.
        sessions = self.folder / 'sessions'
        manifests = {}
        if sessions.exists():
            for path in sessions.glob('S*/session-info.json'):
                session = CollectionSession.open(path.parent)
                for row in session.records:
                    if row['capture_id'] in manifests:
                        raise ValueError('세션 사이에 중복된 촬영 ID가 있습니다.')
                    manifests[row['capture_id']] = row
        for capture_id, row in saved.items():
            raw = manifests.get(capture_id)
            expected_path = 'sessions/' + raw['image_path'] if raw else None
            declaration = self.declarations.get(row.get('declaration_id'))
            step = next((item for item in self.plan['steps'] if item['step_id'] == row['step_id']), None)
            if (raw is None or declaration is None
                    or step is None
                    or declaration['step_id'] != row['step_id']
                    or declaration['operator'] != row['operator']
                    or declaration['part_states'] != step['part_states']
                    or row['part_states'] != step['part_states']
                    or row['target_engine_angle'] != step['target_engine_angle']
                    or row['target_position'] != step['target_position']
                    or row['session_id'] != raw['session_id']
                    or row['scenario_id'] != raw['scenario']
                    or row['raw_relative_path'] != expected_path
                    or row['raw_bytes'] != raw['image_bytes']
                    or row['raw_sha256'] != raw['image_sha256']):
                raise ValueError('저장 기록과 검증된 원본의 대응이 다릅니다. 원본을 보존하세요.')
        if self.superseded - set(saved):
            raise ValueError('재촬영 이력에 대응하는 원본이 없습니다.')
        self.records = saved

    @property
    def completed(self):
        return {row['step_id'] for cid, row in self.records.items() if cid not in self.superseded}

    @property
    def next_step(self):
        return next((step for step in self.plan['steps'] if step['step_id'] not in self.completed), None)

    def declare(self, step, operator):
        if self.failed or self.next_step is None or step['step_id'] != self.next_step['step_id']:
            raise ValueError('현재 단계와 촬영 선언이 다릅니다.')
        declaration = {'declaration_id': 'D' + uuid.uuid4().hex[:16].upper(),
                       'step_id': step['step_id'], 'operator': operator,
                       'declared_at': utc_now(), 'part_states': deepcopy(step['part_states']),
                       'target_engine_angle': step['target_engine_angle'],
                       'target_position': step['target_position'],
                       'physical_state_verified': False, 'angle_measured': False,
                       'meaning': 'operator_requested_capture_after_preparing_displayed_target'}
        self.log.append('simple_declared', declaration)
        self.declarations[declaration['declaration_id']] = declaration
        return declaration

    def prepare_capture(self, step, frame, setup_id, *, source_kind='camera'):
        """Prepare disk/session state before the UI selects its post-click frame."""
        if self.failed or self.next_step is None or step['step_id'] != self.next_step['step_id']:
            raise ValueError('현재 단계가 바뀌었거나 저장이 차단되었습니다.')
        profile = capture_profile(self.plan)
        if (self.session is None or self.session.info['camera'] != frame.camera
                or self.session.info['conditions'] != setup_id or self.session.info['source_kind'] != source_kind):
            self.session = CollectionSession.create(self.folder / 'sessions', profile, frame,
                                                    conditions=setup_id, source_kind=source_kind)
        self.session.can_continue(profile, frame, setup_id, source_kind=source_kind)
        scenario = step['scenario_id']
        if scenario != self.session.scenario:
            self.session.set_scenario(scenario)

    def save(self, step, frame, operator, setup_id, declaration, *, guide_setup=None, source_kind='camera'):
        if self.failed or self.next_step is None or step['step_id'] != self.next_step['step_id']:
            raise ValueError('현재 단계가 바뀌었거나 저장이 차단되었습니다.')
        if (not isinstance(declaration, dict)
                or self.declarations.get(declaration.get('declaration_id')) != declaration
                or declaration['step_id'] != step['step_id'] or declaration['operator'] != operator
                or any(row.get('declaration_id') == declaration['declaration_id'] for row in self.records.values())):
            raise ValueError('현재 촬영 클릭의 선언 기록이 없습니다.')
        if not frame.fresh():
            raise ValueError('오래된 카메라 프레임입니다. 저장하지 않았습니다.')
        self.prepare_capture(step, frame, setup_id, source_kind=source_kind)
        scenario = step['scenario_id']
        # The UI gate already waited for a post-click frame. Session's ordinary
        # state-change clock is later than that selected frame on this path.
        self.session.not_before = frame.received_mono
        quality_roi = guide_setup['quality_roi'] if guide_setup else [0.1, 0.1, 0.8, 0.8]
        try:
            path = self.session.save(frame, notes='simple-step:' + step['step_id'])
            raw = self.session.records[-1]
            # Quality is advisory; compute it after the writer's freshness check.
            measurement = metrics(frame.image, quality_roi, self.plan['quality'], scenario)
            row = {'capture_id': raw['capture_id'], 'declaration_id': declaration['declaration_id'],
                   'operator_declared_at': declaration['declared_at'],
                   'collection_id': self.folder.name,
                   'session_id': raw['session_id'], 'step_id': step['step_id'],
                   'assembly_episode_id': self.folder.name + '_' + step['assembly_episode_id'],
                   'source_group_id': self.folder.name + '_' + step['source_group_id'], 'scenario_id': scenario,
                   'part_states': deepcopy(step['part_states']),
                   'target_engine_angle': step['target_engine_angle'], 'measured_angle': None,
                   'target_position': step['target_position'], 'captured_at': raw['captured_at'],
                   'camera': deepcopy(frame.camera), 'setup_id': setup_id,
                   'source_kind': source_kind,
                   'guide_setup': deepcopy(guide_setup),
                   'raw_relative_path': str(path.relative_to(self.folder)).replace('\\', '/'),
                   'raw_bytes': raw['image_bytes'], 'raw_sha256': raw['image_sha256'],
                   'quality_warnings': measurement['warnings'], 'quality_metrics': measurement,
                   'label_source': 'operator_capture_click_declaration',
                   'operator': operator, 'review_status': 'NOT_REVIEWED',
                   'physical_independence_verified': False,
                   'policy_version': POLICY_VERSION, 'saved_at': utc_now()}
            self.log.append('simple_saved', row)
        except Exception:
            # The old writer may have completed its PNG/manifest. Keep any orphan for audit.
            self.failed = True
            raise
        self.records[row['capture_id']] = row
        return row

    def supersede_last(self):
        active = [row for cid, row in self.records.items() if cid not in self.superseded]
        if not active:
            raise ValueError('다시 찍을 사진이 없습니다.')
        row = active[-1]
        self.log.append('simple_superseded', {'capture_id': row['capture_id'],
                                               'step_id': row['step_id'], 'at': utc_now()})
        self.superseded.add(row['capture_id'])
        return row

    def export(self):
        base = '전달_' + uuid.uuid4().hex[:8].upper()
        destination = self.folder / (base + '_INCOMPLETE')
        destination.mkdir()
        rows = [dict(row, capture_status=('SUPERSEDED' if cid in self.superseded else 'SAVED'))
                for cid, row in self.records.items()]
        manifest = destination / 'capture-manifest.jsonl'
        manifest.write_text(''.join(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n'
                                    for row in rows), encoding='utf-8')
        (destination / 'capture-plan.json').write_bytes((self.folder / 'capture-plan.json').read_bytes())
        shutil.copytree(self.folder / 'sessions', destination / 'sessions') if (self.folder / 'sessions').exists() else (destination / 'sessions').mkdir()
        for row in rows:
            raw = destination / row['raw_relative_path']
            if (not raw.is_file() or raw.stat().st_size != row['raw_bytes']
                    or hashlib.sha256(raw.read_bytes()).hexdigest() != row['raw_sha256']):
                raise ValueError(f"전달 원본 검증 실패: {row['capture_id']}")
        summary = {'policy_version': POLICY_VERSION, 'collection_id': self.folder.name,
                   'completed': len(self.completed), 'target': len(self.plan['steps']),
                   'remaining': len(self.plan['steps']) - len(self.completed),
                   'review_status': 'NOT_REVIEWED', 'training_accepted': False,
                   'raw_root_relative_to_delivery': 'sessions',
                   'send_entire_delivery_folder': True}
        (destination / 'progress.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        final = self.folder / base
        destination.rename(final)
        return final

    def close(self):
        self.lock.close()
