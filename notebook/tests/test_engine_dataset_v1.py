"""V1 acceptance with generated PNGs only; no USB device or real holdout input.

Camera routing tests use detached metadata over synthetic PNGs, as the existing
Wizard regression does. Persisted capture/session records always remain sample.
"""
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from training.scripts import capture_proxy as capture
from training.capture_windows.guide import load_guide
from training.capture_windows.wizard_plan import load_plan, expand_plan, validate_plan, placement_for_action
from training.capture_windows.wizard import Collection
from training.capture_windows import engine_dataset as engine
from training.capture_windows.engine_contract import SCENARIO_LABELS
from training.capture_windows.engine_exports import (export_collection, read_jsonl, write_jsonl,
    validate_export, validate_manifest, merge_manifests, queues_for, write_handoff)
from test_dataset_wizard import wizard_frame

ENGINE_V1 = Path('training/datasets/engine/engine_model_top_v0/profile.json')


def config():
    profile = capture.load_profile(ENGINE_V1)
    guide = load_guide(ENGINE_V1, profile)
    return profile, guide, load_plan(ENGINE_V1, profile, guide)


class Fixture:
    def __init__(self, root, station='STATION_A'):
        self.profile, self.guide, self.plan = config()
        self.col = Collection.create(Path(root)/'raw', self.profile, self.guide, self.plan, True, 'sample',
                                     station=engine.station_settings(station, 'TEST_PC', 'SYNTHETIC_CAMERA'))
        self.col.new_setup(wizard_frame(10000), [.1,.1,.8,.8], 'engine_zero_reference_clockwise')
        self.sequence = 10000

    def photo(self):
        self.sequence += 1
        frame = wizard_frame(self.sequence)
        return self.col.save_prepared(self.col.prepare(frame, now=time.monotonic()-2, engine_angle_confirmed=True), frame)

    def advance(self):
        a = self.col.next_action()
        kind = a['kind']
        if kind in ('capture', 'reference'):
            return self.photo()
        if kind == 'crank_setup':
            self.col.confirm_crank(dict.fromkeys(engine.CRANK_CHECKS, True))
        elif kind == 'state_setup':
            checks = dict.fromkeys(engine.physical_checklist(self.profile, a['scenario']), True)
            self.col.confirm_state_preparation(True, True, checks)
        elif kind == 'quality':
            self.col.acknowledge_quality(a['attempt']['attempt_id'], True)
        elif kind == 'setup_review':
            self.col.confirm_setup(True)
        elif kind == 'round':
            previous = list(self.col.rounds.values())[-1] if self.col.rounds else None
            self.col.begin_round(bool(previous and previous['purpose'] != a['block']['purpose']), repositioned=True)
        elif kind == 'review':
            return self.col.accept_batch(a['block']['block_id'], True)
        else:
            raise AssertionError('Unexpected action '+kind)

    def reach(self, predicate):
        for _ in range(1800):
            action = self.col.next_action()
            if predicate(action):
                return action
            self.advance()
        raise AssertionError('Unbounded synthetic flow')

    def reopen(self):
        path = self.col.folder
        self.col.close()
        self.col = Collection.open(path)


@contextmanager
def camera_routing(collection):
    attempts = deepcopy(collection.attempts)
    for a in attempts.values():
        a['record']['source_kind'] = 'camera'
    with patch.object(collection, 'attempts', attempts), patch.object(collection, '_reconcile'):
        yield


class EngineV1PlanTests(unittest.TestCase):
    def test_main_counts_schedule_and_pilot(self):
        profile, guide, plan = config()
        blocks = expand_plan(plan, True)['blocks']
        main = [b for b in blocks if b['phase'] == 'main']
        self.assertEqual(sum(len(b['steps']) for b in main), 288)
        self.assertEqual(Counter({r:sum(len(b['steps']) for b in main if b['round_id']==r) for r in ('E01','E02','E03','E04')}),
                         {'E01':72,'E02':72,'E03':72,'E04':72})
        self.assertEqual(Counter(s['scenario'] for b in main for s in b['steps']), dict.fromkeys(engine.MAIN_SCENARIOS,48))
        for b in main:
            crank = [s['crank_phase_id'] for s in b['steps']]
            wanted = engine.CRANK_PHASES[1::2] if b['round_id'] in ('E02','E04') else engine.CRANK_PHASES[::2]
            self.assertEqual(crank, [phase for phase in wanted for _ in range(3)])
        first = main[0]['steps']
        self.assertEqual([s['placement_id'] for s in first[:3]], ['ANGLE_000','ANGLE_120','ANGLE_240'])
        pilot = [b for b in blocks if b['phase']=='pilot']
        self.assertEqual(sum(len(b['steps']) for b in pilot),12)
        self.assertEqual({b['scenario'] for b in pilot},{'NORMAL','MISSING_PIPE_LEFT'})
        self.assertGreater(len({s['crank_phase_id'] for b in pilot for s in b['steps']}), 1)

    def test_invalid_crank_split_and_station_rejected(self):
        profile,guide,plan=config()
        for mutate in (lambda p:p['crank_schedule']['E01'][0]['placement_ids'].append('ANGLE_030'),
                       lambda p:p['crank_schedule']['E02'][0].update(crank_phase_id='CRANK_000'),
                       lambda p:p['rounds'][3].update(purpose='train_candidate')):
            candidate=deepcopy(plan);mutate(candidate)
            with self.assertRaises(ValueError):validate_plan(candidate,profile,guide)
        for value in ('CUSTOM','../B','CON','station a',''):
            with self.assertRaises(ValueError):engine.station_settings(value)
        self.assertEqual(engine.station_settings('STATION_B')['e02_lighting_id'],'RIGHT_DOMINANT')
        self.assertEqual(engine.station_settings('STATION_B',e02_lighting_id='LEFT_DOMINANT')['e02_lighting_id'],'LEFT_DOMINANT')

    def test_human_guide_count_and_scenario_disagreement_is_failure(self):
        profile,guide,plan=config()
        guide['steps'][1]['instruction']=guide['steps'][2]['instruction']
        with self.assertRaisesRegex(ValueError,'사람용 촬영 안내'):
            validate_plan(plan,profile,guide)


class EngineV1FullDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Path('.cache').mkdir(exist_ok=True)
        cls.temp=tempfile.TemporaryDirectory(prefix='v1full_',dir='.cache')
        cls.fixture=Fixture(cls.temp.name)
        cls.fixture.reach(lambda a:a['kind']=='finished')
        cls.col=cls.fixture.col
        with camera_routing(cls.col):
            cls.export=cls.col.export(contact_sheets=True)
        cls.rows=read_jsonl(cls.export/'dataset_manifest.jsonl')

    @classmethod
    def tearDownClass(cls):
        cls.col.close()
        cls.temp.cleanup()

    def test_288_216_40_counts_pair_links_and_raw_metadata(self):
        stats=validate_export(self.export)
        self.assertEqual((stats['main_accepted'],stats['yolo_queue'],stats['mask_candidates']), (288,216,40))
        self.assertEqual(self.col.summary()['main_accepted'],288)
        main=[r for r in self.rows if r['split']!='excluded']
        self.assertEqual(Counter(r['split'] for r in main), {'train_candidate':144,'validation_candidate':72,'test_reserved':72})
        index={r['capture_id']:r for r in self.rows}
        for row in main:
            normal=index[row['reference_normal_capture_id']]
            self.assertEqual(normal['scenario'],'NORMAL')
            self.assertEqual(engine.pair_key(row),engine.pair_key(normal))
            self.assertTrue(row['engine_angle_human_confirmed'])
            self.assertTrue(row['crank_phase_human_confirmed'])
            self.assertFalse(row['angle_sensor_verified'])
            self.assertFalse(row['crank_sensor_verified'])
            if row['capture_truth_result'] == 'FAIL':
                self.assertEqual(row['reference_normal_capture_id_at_capture'], row['reference_normal_capture_id'])
        self.assertEqual(len(read_jsonl(self.export/'normal_defect_pairs.jsonl')),180)
        # Original writer's records never claim physical camera acquisition.
        self.assertEqual({a['record']['source_kind'] for a in self.col.attempts.values()},{'sample'})

    def test_auto_export_sample_excluded_and_raw_immutable(self):
        events=[e for e in self.col.log.events if e['type']=='export_created']
        self.assertGreaterEqual(len(events),2)  # final accept auto-export + explicit routing export
        sample=Path(events[0]['data']['folder'])
        self.assertEqual(read_jsonl(sample/'annotation_queue_yolo.jsonl'),[])
        for row in self.rows:
            self.assertEqual(hashlib.sha256(Path(row['image_path']).read_bytes()).hexdigest(),row['image_sha256'])
        self.assertEqual(len(list((self.export/'contact_sheets').glob('*.jpg'))),18)
        index=json.loads((self.export/'contact_sheets/index.json').read_text(encoding='utf-8'))
        reserved={r['capture_id'] for r in self.rows if r['test_reserved']}
        self.assertFalse({cid for sheet in index for cid in sheet['capture_ids']} & reserved)

    def test_mask_selection_balanced_deterministic_and_duplicate_rejection(self):
        a=engine.select_mask_candidates(self.rows)
        b=engine.select_mask_candidates(list(reversed(self.rows)))
        self.assertEqual([r['capture_id'] for r in a],[r['capture_id'] for r in b])
        self.assertEqual(Counter(r['scenario'] for r in a),dict.fromkeys(engine.MAIN_SCENARIOS[1:],8))
        for scenario in engine.MAIN_SCENARIOS[1:]:
            self.assertEqual(Counter(r['crank_phase_id'] for r in a if r['scenario']==scenario),dict.fromkeys(engine.CRANK_PHASES[::2],2))
        duplicate=deepcopy(self.rows)
        for row in duplicate:
            row['quality_metrics']['dhash']='0000000000000000'
        self.assertEqual(len(engine.select_mask_candidates(duplicate)),5)

    def test_missing_or_wrong_reference_never_ready(self):
        rows=deepcopy(self.rows)
        fail=next(r for r in rows if r['round_id']=='E01' and r['scenario']=='MISSING_PIPE_LEFT')
        fail['reference_normal_capture_id']=None
        with self.assertRaisesRegex(ValueError,'labeling_ready'):validate_manifest(rows,self.col.profile,False)
        fail['labeling_ready']=False
        validate_manifest(rows,self.col.profile,False)
        self.assertNotIn(fail['capture_id'],{r['capture_id'] for r in queues_for(rows)[0]})
        normal=next(r for r in rows if r['round_id']=='E01' and r['scenario']=='NORMAL' and r['crank_phase_id']!=fail['crank_phase_id'])
        fail['reference_normal_capture_id']=normal['capture_id']
        with self.assertRaisesRegex(ValueError,'NORMAL Pair'):validate_manifest(rows,self.col.profile,False)

    def test_reserved_exclusion_and_exact_unlock_phrase(self):
        for name in ('annotation_queue_yolo','annotation_queue_mask','training_candidates'):
            self.assertFalse(any(r['test_reserved'] for r in read_jsonl(self.export/(name+'.jsonl'))))
        with self.assertRaises(ValueError):self.col.unlock_final_test('unlock')
        with patch.object(self.col,'final_test_unlocked',True),camera_routing(self.col):
            output=self.col.export()
        self.assertEqual(len(read_jsonl(output/'annotation_queue_yolo.jsonl')),288)
        self.assertEqual(len(read_jsonl(output/'annotation_queue_mask.jsonl')),40)
        self.assertEqual(len(read_jsonl(output/'training_candidates.jsonl')),144)
        self.assertTrue(all(r['split']=='train_candidate' for r in read_jsonl(output/'training_candidates.jsonl')))

    def test_human_docs_csv_queue_and_contract_tamper_fail(self):
        for name, old, new in [
            ('HUMAN_CODEX_DATASET_CONTRACT_KO.md','왼쪽 파이프 누락','오른쪽 파이프 누락'),
            ('DATASET_SUMMARY_KO.md','Main 288','Main 300'),
            ('LABELING_RULES_KO.md','그림자는 포함하지 않음','그림자를 포함함'),
            ('labels.csv','PASS','FAIL'),
            ('LABELING_CONTRACT.json','회색 파이프','회색 배기구'),
            ('annotation_queue_yolo.jsonl','CRANK_000','CRANK_045')]:
            with self.subTest(name=name):
                path=self.export/name;content=path.read_bytes()
                try:
                    text=path.read_text(encoding='utf-8');self.assertIn(old,text)
                    path.write_text(text.replace(old,new,1),encoding='utf-8')
                    with self.assertRaises(ValueError):validate_export(self.export,verify_raw=False)
                finally:path.write_bytes(content)

    def test_merge_station_namespaces_split_hash_and_no_raw_copy(self):
        root=Path(self.temp.name)
        rows=deepcopy(self.rows)
        # A second independent fixture uses different generated pixels and station.
        other=Fixture(root/'station_b','STATION_B')
        try:
            other.sequence=30000
            other.reach(lambda a:a['kind']=='finished')
            with camera_routing(other.col):second=other.col.export()
            second_rows=read_jsonl(second/'dataset_manifest.jsonl')
            self.assertFalse({r['capture_id'] for r in rows}&{r['capture_id'] for r in second_rows})
            # Namespace remains distinct even if two underlying writers reuse IDs.
            raw=next(iter(self.col.attempts.values()))['record']
            self.assertNotEqual(engine.capture_identity(self.col,raw),engine.capture_identity(other.col,raw))
            combined=root/'combined_manifest.jsonl'
            result=merge_manifests([self.export/'dataset_manifest.jsonl',second/'dataset_manifest.jsonl'],combined,self.col.profile)
            before={r['capture_id']:(r['split'],r['image_sha256'],r['station_id']) for r in rows+second_rows}
            after={r['capture_id']:(r['split'],r['image_sha256'],r['station_id']) for r in read_jsonl(combined)}
            self.assertEqual(before,after)
            combined_rows=read_jsonl(combined)
            self.assertEqual(sum(r['split']!='excluded' for r in combined_rows),576)
            self.assertEqual([len(q) for q in queues_for(combined_rows)[:2]],[432,80])
            self.assertFalse(result['raw_modified'])
            with self.assertRaisesRegex(ValueError,'duplicate capture_id'):
                merge_manifests([self.export/'dataset_manifest.jsonl']*2,root/'bad.jsonl',self.col.profile)
            self.assertFalse((root/'bad.jsonl').exists())
        finally:other.col.close()

    def test_merge_rejects_hash_collision_split_changes_and_raw_tampering(self):
        rows=deepcopy(self.rows)
        rows[1]['image_sha256']=rows[0]['image_sha256']
        with self.assertRaisesRegex(ValueError,'hash collision'):
            validate_manifest(rows,self.col.profile,False,True)
        rows=deepcopy(self.rows)
        row=next(r for r in rows if r['test_reserved'])
        row['split']='train_candidate'
        with self.assertRaisesRegex(ValueError,'split'):validate_manifest(rows,self.col.profile,False)
        target=Path(self.rows[0]['image_path']);original=target.read_bytes()
        try:
            target.write_bytes(original+b'tamper')
            with self.assertRaisesRegex(ValueError,'SHA256'):validate_manifest(self.rows,self.col.profile)
        finally:target.write_bytes(original)


class EngineV1LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='v1life_',dir='.cache')
        self.fx=Fixture(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(lambda:self.fx.col.close())

    def test_gates_require_all_checks_and_angle_confirmation(self):
        col=self.fx.col
        self.assertEqual(col.next_action()['kind'],'crank_setup')
        with self.assertRaises(ValueError):col.prepare(wizard_frame(),engine_angle_confirmed=True)
        with self.assertRaises(ValueError):col.confirm_crank({'target_set':True})
        col.confirm_crank(dict.fromkeys(engine.CRANK_CHECKS,True))
        with self.assertRaises(ValueError):col.prepare(wizard_frame())
        self.fx.reach(lambda a:a['kind']=='state_setup')
        with self.assertRaises(ValueError):col.confirm_state_preparation(True,True)
        checks=dict.fromkeys(engine.physical_checklist(col.profile,col.next_action()['scenario']),True)
        checks['hands_clear']=False
        with self.assertRaises(ValueError):col.confirm_state_preparation(True,True,checks)

    def test_partial_save_recovery_retains_crank_angle_and_raw_on_retake(self):
        self.fx.reach(lambda a:a['kind']=='capture' and a['block']['round_id']=='E01')
        col=self.fx.col
        append=col.log.append
        def interrupt(kind,data):
            if kind=='attempt_saved':raise OSError('synthetic interruption after raw PNG commit')
            return append(kind,data)
        with patch.object(col.log,'append',side_effect=interrupt):
            with self.assertRaises(OSError):self.fx.photo()
        self.fx.reopen();col=self.fx.col
        recovered=list(col.attempts.values())[-1]
        self.assertTrue(recovered['recovered'])
        self.assertEqual(recovered['engine_metadata']['crank_phase_id'],'CRANK_000')
        self.assertEqual(recovered['engine_metadata']['engine_angle_target_deg'],0)
        self.fx.reach(lambda a:a['kind']=='capture')
        self.assertEqual(placement_for_action(col.template,col.next_action())['angle_deg'],120)
        old=Path(col.folder/'sessions'/recovered['record']['image_path']);before=old.read_bytes()
        col.reject(recovered['attempt_id'],'synthetic retake',True)
        self.fx.reopen();col=self.fx.col
        self.assertEqual(col.next_action()['kind'],'state_setup')
        self.fx.reach(lambda a:a['kind']=='capture')
        new=self.fx.photo()
        self.assertNotEqual(new['record']['capture_id'],recovered['record']['capture_id'])
        self.assertEqual(old.read_bytes(),before)

    def test_challenge_separate_resume_and_no_error_scenario(self):
        self.fx.reach(lambda a:a['kind']=='state_setup')
        col=self.fx.col
        before=col.summary()['main_accepted']
        col.add_challenge('OTHER_PART_MISSING',details='합성 fixture: 비검사 커버 제거')
        self.fx.reopen();col=self.fx.col
        self.assertEqual(col.next_action()['scenario'],'OTHER_PART_MISSING')
        self.fx.reach(lambda a:a['kind']=='review')
        col.accept_batch(col.next_action()['block']['block_id'],True)
        self.assertEqual(col.summary()['main_accepted'],before)
        self.assertEqual(col.summary()['challenge_accepted'],1)
        with camera_routing(col):output=col.export()
        row=next(r for r in read_jsonl(output/'dataset_manifest.jsonl') if r['scenario']=='OTHER_PART_MISSING')
        self.assertEqual((row['capture_truth_result'],row['purpose'],row['split']),('REVIEW','review_challenge','excluded'))
        self.assertTrue(row['exclude_from_training'])
        self.assertFalse(row['labeling_ready'])
        for bad in ('ERROR','CAMERA_DISCONNECT','CONVEYOR_MOVING'):
            with self.assertRaises(ValueError):col.add_challenge(bad,details='synthetic')
        self.fx.reopen()
        self.assertEqual(self.fx.col.summary()['challenge_accepted'],1)

    def test_unlock_persists_and_physical_reconfirmation_clears_only_gates(self):
        col=self.fx.col
        col.unlock_final_test(engine.UNLOCK_PHRASE)
        self.fx.reopen();col=self.fx.col
        self.assertTrue(col.final_test_unlocked)
        col.confirm_crank(dict.fromkeys(engine.CRANK_CHECKS,True))
        count=len(col.attempts)
        col.reconfirm_physical_state()
        self.assertEqual(col.next_action()['kind'],'crank_setup')
        self.assertEqual(len(col.attempts),count)


if __name__=='__main__':unittest.main()
