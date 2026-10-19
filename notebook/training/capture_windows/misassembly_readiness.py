"""Physical round declarations, append-only part reviews and portable candidates.

The capture journal remains the immutable statement of intent. This companion
journal records human actions; no image classifier or count-derived truth exists.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import shutil
import uuid

from PIL import Image

from .wizard_store import EventLog, utc_now, write_new_json
from .misassembly_guidance import SCENARIO_GUIDES

SCHEMA_VERSION = 'engine-part-readiness-v1'
EXPORT_VERSION = 'reviewed-part-candidates-v1'
PART_STATES = {
    'pipe_left': ('CORRECT', 'MISSING', 'UPWARD_ROTATED', 'OUTWARD_SPLAYED'),
    'pipe_right': ('CORRECT', 'MISSING', 'UPWARD_ROTATED', 'OUTWARD_SPLAYED'),
    'exhaust': ('CORRECT', 'MISSING', 'REVERSED', 'SIDEWAYS'),
    'symbol': ('CORRECT', 'MISSING', 'UPSIDE_DOWN'),
}
PURPOSES = ('UNASSIGNED', 'TRAIN', 'VALIDATION', 'TEST_RESERVED')
VISIBILITIES = ('UNKNOWN', 'VISIBLE', 'VERIFIED_ABSENT', 'OCCLUDED', 'OUT_OF_FRAME', 'UNDETERMINABLE', 'BLURRED')
REVIEW_STATUSES = ('NOT_REVIEWED', 'APPROVED', 'HOLD', 'RETAKE')
CONTEXT_KEYS = ('engine_instance_id', 'collection_round_id', 'assembly_episode_id',
                'source_group_id', 'split', 'environment_id', 'environment_description',
                'physical_reassembly_operator_declared', 'physical_reassembly_declared_at',
                'physical_reassembly_operator', 'comparison_group_id', 'comparison_stage')


def new_id(prefix):
    return prefix + uuid.uuid4().hex.upper()


def custom_plan(template, scenarios, angles, positions, *, contrasts=True, pilot=False):
    """Build a fresh round; historical coverage never completes its controls."""
    examples = {s['scenario_id']: s for s in template['steps']}
    if (not scenarios or len(set(scenarios)) != len(scenarios)
            or any(s not in examples or s not in SCENARIO_GUIDES for s in scenarios)
            or not angles or len(set(angles)) != len(angles)
            or any(type(a) is not int or a not in range(0, 360, 10) for a in angles)
            or not positions or len(set(positions)) != len(positions)
            or any(p not in ('CENTER', 'OFFSET_RIGHT') for p in positions)):
        raise ValueError('시나리오·10° 단위 각도(0~350)·중앙/오른쪽 위치를 확인하세요.')
    plan = deepcopy(template)
    plan.update(plan_id=new_id('PILOT_' if pilot else 'CUSTOM_'), plan_version=1,
                collection_mode='pilot' if pilot else 'custom', existing_coverage={},
                coverage_evidence=None, target_basis='operator_selected_round_conditions', steps=[])
    for scenario in scenarios:
        pair = new_id('PAIR_') if contrasts and scenario != 'NORMAL' else None
        blocks = [('NORMAL', 'NORMAL_BEFORE'), (scenario, 'TARGET'), ('NORMAL', 'NORMAL_AFTER')] if pair else [(scenario, 'TARGET')]
        for state, stage in blocks:
            for position in positions:
                for angle in angles:
                    step = deepcopy(examples[state])
                    step.update(step_id=new_id('STEP_'), target_engine_angle=angle,
                                target_position=position, capture_reason='pilot' if pilot else 'new_round',
                                comparison_template_id=pair, comparison_stage=stage)
                    plan['steps'].append(step)
    return plan


def empty_part_review():
    return dict(state=None, status='NOT_REVIEWED', visibility='UNKNOWN',
                reviewer=None, reviewed_at=None, learning_eligible=False)


def validate_split_integrity(rows):
    """All grouping edges must have one purpose, including unknown reservations."""
    reservations, captures = {}, {}
    for row in rows:
        split = row.get('split', 'UNASSIGNED')
        if split not in PURPOSES:
            raise ValueError('알 수 없는 split입니다.')
        if any(re.search(r'(^|[_/\\])E04($|[_/\\])', str(row.get(k, '')).upper())
               for k in ('collection_round_id', 'round_id', 'source_group_id', 'assembly_episode_id', 'raw_relative_path')):
            raise ValueError('보호된 E04는 이 내보내기 범위가 아닙니다.')
        cid = row.get('capture_id')
        if cid in captures and (captures[cid].get('split','UNASSIGNED') != split or captures[cid].get('raw_sha256') != row.get('raw_sha256')):
            raise ValueError('동일 capture_id의 원본 또는 split이 다릅니다.')
        captures[cid] = row
        for key in ('raw_sha256', 'source_group_id', 'collection_round_id', 'assembly_episode_id',
                    'lineage_root_id', 'comparison_group_id'):
            value = row.get(key)
            if not value:
                continue
            token = (key, value)
            if token in reservations and reservations[token] != split:
                raise ValueError(f'교차 split 충돌: {key} / {reservations[token]} / {split}')
            reservations[token] = split
    for row in captures.values():
        previous = captures.get(row.get('supersedes_capture_id'))
        if previous and previous.get('split','UNASSIGNED') != row.get('split','UNASSIGNED'):
            raise ValueError('재촬영 계보의 split이 다릅니다.')


class Readiness:
    def __init__(self, collection, base_plan):
        self.collection = collection
        self.plan = deepcopy(base_plan)
        self.folder = collection.folder/'readiness'
        # Opening legacy data reads only. First explicit new event creates it.
        self.log = EventLog(self.folder)
        self.rounds, self.step_rounds, self.reviews = {}, {}, {}
        self.review_history = []
        self.external_split_rows = []
        self.displayed = {}  # UI session only: never infer display from old reviews.
        for event in self.log.events:
            self._apply(event)

    def _append(self, kind, data):
        self.folder.mkdir(exist_ok=True)
        event = self.log.append(kind, deepcopy(data))
        self._apply(event)

    def _apply(self, event):
        data = event['data']
        if event['type'] == 'round_configured':
            for round_info in data['rounds']:
                key = round_info['collection_round_id']
                if key in self.rounds:
                    raise ValueError('중복 회차 ID입니다.')
                self.rounds[key] = round_info
                for step_id in round_info['step_ids']:
                    if step_id in self.step_rounds:
                        raise ValueError('기존 단계의 회차를 다시 배정할 수 없습니다.')
                    self.step_rounds[step_id] = key
            self.plan['steps'].extend(data.get('added_steps', []))
        elif event['type'] == 'physical_round_started':
            rnd = self.rounds[data['collection_round_id']]
            if rnd['physical_reassembly_operator_declared']:
                raise ValueError('회차 시작 선언 중복입니다.')
            rnd.update(data, started=True)
        elif event['type'] == 'part_review':
            for cid, parts in data['changes'].items():
                current = self.reviews.setdefault(cid, {})
                for part, change in parts.items():
                    if current.get(part, empty_part_review()) != change['before']:
                        raise ValueError('부품 검토 이력 순서가 다릅니다.')
                    current[part] = change['after']
            self.review_history.append(data)
        elif event['type'] == 'external_split_manifest':
            self.external_split_rows.extend(data['identities'])
        else:
            raise ValueError('알 수 없는 데이터 준비도 기록입니다.')

    def _round(self, steps, engine, environment, split, operator, *, started):
        if not engine.strip() or not environment.strip() or not operator.strip() or split not in PURPOSES:
            raise ValueError('엔진 식별자·환경 설명·촬영자·목적을 입력하세요.')
        if engine.strip().upper() == 'E04':
            raise ValueError('E04 보호 식별자를 새 회차에 사용하지 마세요.')
        rid = new_id('ROUND_')
        return dict(collection_round_id=rid, source_group_id=rid, engine_instance_id=engine.strip(),
                    assembly_episode_id=None, split=split,
                    environment_id=new_id('ENV_'), environment_description=environment.strip(),
                    configured_by=operator.strip(), configured_at=utc_now(), started=started,
                    physical_reassembly_operator_declared=False, physical_reassembly_declared_at=None,
                    physical_reassembly_operator=None, step_ids=[s['step_id'] for s in steps])

    def configure(self, engine, environment, split, operator):
        if self.rounds or self.collection.records:
            raise ValueError('이미 시작된 수집의 회차/목적은 변경하지 않습니다. 추가 회차를 만드세요.')
        rnd = self._round(self.plan['steps'], engine, environment, split, operator, started=True)
        self._append('round_configured', {'schema_version': SCHEMA_VERSION, 'rounds': [rnd]})
        return rnd['collection_round_id']

    def add_rounds(self, plan, count, engine, environment, split, operator):
        if type(count) is not int or not 1 <= count <= 100:
            raise ValueError('추가 회차는 1~100 사이로 입력하세요.')
        added, rounds = [], []
        for _ in range(count):
            steps = deepcopy(plan['steps'])
            for step in steps:
                step['step_id'] = new_id('STEP_')
            rnd = self._round(steps, engine, environment, split, operator, started=False)
            for step in steps:
                step['readiness_round_id'] = rnd['collection_round_id']
            added.extend(steps)
            rounds.append(rnd)
        self._append('round_configured', {'schema_version': SCHEMA_VERSION, 'rounds': rounds,
                                          'added_steps': added, 'plan_id': plan['plan_id']})
        return [r['collection_round_id'] for r in rounds]

    def start_round(self, round_id, operator):
        rnd = self.rounds.get(round_id)
        if (rnd is None or not operator.strip() or rnd['physical_reassembly_operator_declared']
                or any(r.get('collection_round_id') == round_id for r in self.collection.records.values())):
            raise ValueError('촬영 전 회차에서만 새 물리적 재조립을 선언할 수 있습니다. 추가 회차를 만드세요.')
        self._append('physical_round_started', dict(collection_round_id=round_id,
            assembly_episode_id=new_id('ASSEMBLY_'),
            physical_reassembly_operator_declared=True, physical_reassembly_declared_at=utc_now(),
            physical_reassembly_operator=operator.strip(), physical_independence_verified=False,
            declaration='operator_declares_engine_reassembled_for_this_round'))

    def context(self, step):
        previous = self.collection.active_record(step['step_id'])
        if previous:
            result = {k: deepcopy(previous.get(k)) for k in CONTEXT_KEYS}
            result['split'] = previous.get('split') or 'UNASSIGNED'
            return result
        rid = self.step_rounds.get(step['step_id'])
        if not rid:
            return dict(engine_instance_id=None, collection_round_id=None, assembly_episode_id=None,
                        source_group_id=self.collection.folder.name, split='UNASSIGNED',
                        environment_id=None, environment_description=None,
                        physical_reassembly_operator_declared=False, physical_reassembly_declared_at=None,
                        physical_reassembly_operator=None, comparison_group_id=None,
                        comparison_stage=step.get('comparison_stage'))
        rnd = self.rounds[rid]
        if not rnd['started']:
            raise ValueError('회차 설정에서 부품을 다시 조립하여 새 회차 시작을 누르세요.')
        result = {k: deepcopy(rnd.get(k)) for k in CONTEXT_KEYS}
        pair = step.get('comparison_template_id')
        result.update(comparison_group_id=rid+'_'+pair if pair else None,
                      comparison_stage=step.get('comparison_stage'))
        return result

    def project(self, row):
        parts = {p: deepcopy(self.reviews.get(row['capture_id'], {}).get(p, empty_part_review())) for p in PART_STATES}
        for part in parts.values():
            part['learning_eligible'] = (part['status'] == 'APPROVED' and row.get('source_kind') == 'camera'
                and row.get('split') in PURPOSES[1:] and row['capture_id'] not in self.collection.superseded)
        result = deepcopy(row)
        result.update(schema_version=SCHEMA_VERSION, planned_part_states=deepcopy(row['part_states']),
                      reviewed_parts=parts, whole_product_reviewed=all(p['status'] == 'APPROVED' for p in parts.values()),
                      capture_status='SUPERSEDED' if row['capture_id'] in self.collection.superseded else 'SAVED')
        result.setdefault('split', 'UNASSIGNED')
        for key in CONTEXT_KEYS:
            result.setdefault(key, None)
        return result

    def _verify_original(self, row):
        path = self.collection.folder/row['raw_relative_path']
        if (not path.resolve().is_relative_to(self.collection.folder.resolve()) or not path.is_file()
                or path.stat().st_size != row['raw_bytes']
                or hashlib.sha256(path.read_bytes()).hexdigest() != row['raw_sha256']):
            raise ValueError('원본 경로/크기/해시 불일치: '+row['capture_id'])
        try:
            with Image.open(path) as original:
                original.verify()
            with Image.open(path) as original:
                if original.size != (row['camera']['width'], row['camera']['height']):
                    raise ValueError('원본 크기 불일치')
        except (OSError, SyntaxError) as exc:
            raise ValueError('원본 이미지 손상: '+row['capture_id']) from exc
        return path

    def mark_displayed(self, capture_id):
        row = self.collection.records[capture_id]
        self._verify_original(row)
        self.displayed[capture_id] = row['raw_sha256']

    def review(self, capture_ids, updates, *, reviewer, reason, displayed_ids):
        ids = list(dict.fromkeys(capture_ids))
        if (not ids or not reviewer.strip() or not reason.strip() or not updates
                or not set(ids) <= set(displayed_ids)
                or not set(ids) <= set(self.displayed) or not set(updates) <= set(PART_STATES)):
            raise ValueError('실제 표시하고 선택한 사진, 검토자, 사유, 검토 부품이 필요합니다.')
        after, now = {}, utc_now()
        for part, value in updates.items():
            state, status, visibility = value.get('state'), value.get('status'), value.get('visibility')
            if status not in REVIEW_STATUSES or visibility not in VISIBILITIES or (state is not None and state not in PART_STATES[part]):
                raise ValueError('부품별 검토 상태/가시성 값이 올바르지 않습니다.')
            eligible = status == 'APPROVED'
            if eligible and (state is None or (visibility != ('VERIFIED_ABSENT' if state == 'MISSING' else 'VISIBLE'))):
                raise ValueError('보이는 부품 또는 부재를 확인한 부품만 승인하세요. 가림은 결품이 아닙니다.')
            after[part] = dict(state=state, status=status, visibility=visibility,
                               reviewer=reviewer.strip(), reviewed_at=now, learning_eligible=eligible)
        changes, hashes = {}, {}
        for cid in ids:
            row = self.collection.records[cid]
            if cid in self.collection.superseded or self.displayed[cid] != row['raw_sha256']:
                raise ValueError('대체되었거나 표시 원본이 바뀐 사진입니다.')
            self._verify_original(row)
            # History stores the human decision. Derived export eligibility can
            # change with supersession/split and must not rewrite that history.
            current = {p: deepcopy(self.reviews.get(cid, {}).get(p, empty_part_review())) for p in PART_STATES}
            changes[cid] = {p: dict(before=current[p], after=deepcopy(v)) for p,v in after.items()}
            hashes[cid] = row['raw_sha256']
        self._append('part_review', dict(schema_version=SCHEMA_VERSION, review_id=new_id('REVIEW_'),
            reviewer=reviewer.strip(), reviewed_at=now, reason=reason.strip(), changes=changes,
            original_sha256=hashes, selected_displayed_capture_ids=ids))

    def summary(self):
        rows = [self.project(r) for cid,r in self.collection.records.items() if cid not in self.collection.superseded]
        declared = {r['collection_round_id']: r for r in rows if r.get('physical_reassembly_operator_declared')}
        train = [r for r in declared.values() if r['split'] == 'TRAIN']
        evaluation = [r for r in declared.values() if r['split'] in ('VALIDATION','TEST_RESERVED')]
        same_engine = any(a.get('engine_instance_id') == b.get('engine_instance_id') for a in train for b in evaluation)
        other_engine = any(a.get('engine_instance_id') != b.get('engine_instance_id') for a in train for b in evaluation)
        return dict(capture_completed=len(self.collection.completed) == len(self.plan['steps']),
                    reviewed_parts=sum(p['status'] == 'APPROVED' for r in rows for p in r['reviewed_parts'].values()),
                    total_part_slots=len(rows)*4, review_completed=bool(rows) and all(r['whole_product_reviewed'] for r in rows),
                    split_assigned=bool(rows) and all(r.get('split') in PURPOSES[1:] for r in rows),
                    split_readiness='OPERATOR_DECLARED_GROUPS_READY' if train and evaluation else 'INSUFFICIENT_INDEPENDENT_EVALUATION',
                    same_engine_reassembly_evaluation=same_engine, different_engine_generalization_evaluation=other_engine,
                    physical_independence_verified=False, training_sufficiency='NOT_ESTABLISHED', model_performance='NOT_TESTED')

    def _peer_rows(self):
        # Metadata only, in sibling collector folders; no legacy/E04 image discovery.
        rows = list(self.collection.records.values()) + self.external_split_rows
        for path in self.collection.folder.parent.glob('M*/collection-events.jsonl'):
            if path.parent == self.collection.folder or 'E04' in path.parts:
                continue
            for event in EventLog(path.parent).events:
                if event['type'] == 'simple_saved':
                    rows.append(event['data'])
        return rows

    def register_split_manifest(self, path):
        """Audit other PCs by selected manifest metadata, without opening images."""
        path = Path(path)
        if any('E04' in p.upper() for p in path.parts):
            raise ValueError('E04 보호 자료는 등록하지 않습니다.')
        data = path.read_bytes()
        rows = [json.loads(line) for line in data.decode('utf-8-sig').splitlines() if line.strip()]
        if not rows or any(not isinstance(r,dict) or not r.get('capture_id') or not r.get('raw_sha256') or r.get('split') not in PURPOSES for r in rows):
            raise ValueError('원본 식별자/해시/split이 있는 후보 manifest를 선택하세요.')
        keys = ('capture_id','raw_sha256','split','source_group_id','collection_round_id',
                'assembly_episode_id','lineage_root_id','comparison_group_id','supersedes_capture_id','round_id')
        identities = [{k:r.get(k) for k in keys} for r in rows]
        validate_split_integrity(self._peer_rows()+identities)
        self._append('external_split_manifest',dict(filename=path.name,sha256=hashlib.sha256(data).hexdigest(),
                                                    identities=identities,registered_at=utc_now()))

    def export_candidates(self, split, capture_ids=None):
        if split not in PURPOSES[1:]:
            raise ValueError('UNASSIGNED를 학습용으로 자동 배정하지 않습니다.')
        if capture_ids is not None and not set(capture_ids) <= set(self.collection.records):
            raise ValueError('알 수 없는 촬영 ID가 선택되었습니다.')
        rows = [self.project(r) for cid,r in self.collection.records.items()
                if cid not in self.collection.superseded and (capture_ids is None or cid in capture_ids)]
        if any(r['split'] != split for r in rows):
            raise ValueError('선택 사진에 다른 split 또는 UNASSIGNED가 포함되어 있습니다.')
        validate_split_integrity(self._peer_rows())
        guide_hashes = {hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__).parent/'assets').glob('*.png')}
        # In a frozen build assets sit alongside the executable.
        import sys
        if getattr(sys, 'frozen', False):
            guide_hashes |= {hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(sys.executable).parent/'assets').glob('*.png')}
        candidates, excluded = [], []
        for row in rows:
            slots = {p: v['state'] for p,v in row['reviewed_parts'].items() if v['learning_eligible']}
            if (row.get('source_kind') != 'camera' or row['raw_sha256'] in guide_hashes or not slots
                    or not row.get('engine_instance_id') or not row.get('collection_round_id')):
                excluded.append(row['capture_id'])
                continue
            self._verify_original(row)
            # Explicit allowlist prevents guide ROI/count profile becoming annotations.
            keys = ('capture_id', 'collection_id', 'session_id', 'execution_session_id', 'step_id',
                    'scenario_id', 'raw_relative_path', 'raw_sha256', 'raw_bytes', 'camera', 'captured_at',
                    'supersedes_capture_id', 'lineage_root_id', 'target_engine_angle', 'measured_angle',
                    'target_position', 'setup_id', 'quality_warnings', 'planned_part_states', 'reviewed_parts') + CONTEXT_KEYS
            candidate = {k: deepcopy(row.get(k)) for k in keys}
            candidate.update(schema_version=SCHEMA_VERSION, export_version=EXPORT_VERSION,
                             plan_id=self.plan['plan_id'], plan_version=self.plan.get('plan_version',1),
                             approved_part_states=slots, whole_product_reviewed=row['whole_product_reviewed'],
                             label_source='human_part_review', derived_parts_inherit_source_split=True,
                             training_accepted=False, physical_independence_verified=False)
            candidates.append(candidate)
        base = '검토후보_'+split+'_'+uuid.uuid4().hex[:8].upper()
        destination = self.collection.folder/(base+'_INCOMPLETE')
        destination.mkdir()
        for row in candidates:
            source = self.collection.folder/row['raw_relative_path']
            target = destination/row['raw_relative_path']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if hashlib.sha256(target.read_bytes()).hexdigest() != row['raw_sha256']:
                raise ValueError('내보낸 원본 해시 불일치')
        (destination/'candidates.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in candidates), encoding='utf-8')
        write_new_json(destination/'summary.json', dict(export_version=EXPORT_VERSION, split=split,
            exported_originals=len(candidates), approved_slots=sum(len(r['approved_part_states']) for r in candidates),
            excluded_capture_ids=excluded, readiness=self.summary(), training_accepted=False,
            split_audit_scope='current collection and sibling collection metadata; imported candidates must be validated together',
            test_reserved_separate=split == 'TEST_RESERVED'))
        write_new_json(destination/'capture-plan.json', self.plan)
        if self.folder.exists():
            shutil.copytree(self.folder, destination/'readiness')
        final = self.collection.folder/base
        destination.rename(final)
        return final
