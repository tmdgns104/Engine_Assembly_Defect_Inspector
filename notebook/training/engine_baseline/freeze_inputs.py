"""Pin reviewed inputs and run the existing verifier without replacing its reports."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[3]
DATA = PROJECT / 'data/guided_capture_20261001'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = PROJECT / 'runs/engine_misassembly_baseline_training_001' / ('v001_' + stamp)
    output.mkdir(parents=True, exist_ok=False)
    evidence = output / 'input_verification'
    evidence.mkdir()
    files = [DATA / name for name in ('LABELING_SCHEMA_DISCOVERY.md','LABELING_SUMMARY.md',
             'LABELING_VERIFICATION.md','export_train_candidates.jsonl',
             'export_validation_candidates.jsonl','labeling_unresolved_cases.jsonl',
             'labeling_review_manifest.jsonl','_labeling/verify.py','_labeling/verification_results.json')]
    files += [p for p in (DATA / '_labeling').glob('*.json*') if p not in files]
    baseline = json.loads((DATA / '_labeling/source_baseline.json').read_text(encoding='utf-8'))
    files += [DATA / r['path'] for r in baseline['metadata']]
    files = list(dict.fromkeys(files))
    before = {str(p.relative_to(PROJECT)):dict(sha256=digest(p),bytes=p.stat().st_size) for p in files}
    (output / 'input_file_hashes_before.json').write_text(json.dumps(before,indent=2),encoding='utf-8')

    verifier = runpy.run_path(str(DATA / '_labeling/verify.py'), run_name='input_verifier')
    redirections = {str((DATA / '_labeling/verification_results.json').resolve()):evidence / 'verification_results.json',
                    str((DATA / 'LABELING_VERIFICATION.md').resolve()):evidence / 'LABELING_VERIFICATION.md'}
    original_write = Path.write_text
    def redirected_write(path, text, *args, **kwargs):
        target = redirections.get(str(path.resolve()))
        if target is None:
            raise RuntimeError('Verifier attempted an unexpected write: ' + str(path))
        return original_write(target,text,*args,**kwargs)
    def forbidden_append(*args, **kwargs):
        raise RuntimeError('Read-only input verification may not append events')
    with patch.object(Path,'write_text',redirected_write), patch.object(verifier['EventLog'],'append',forbidden_append):
        verifier['main']()
    after = {str(p.relative_to(PROJECT)):dict(sha256=digest(p),bytes=p.stat().st_size) for p in files}
    assert before == after, 'Original metadata or label files changed'

    rows = [json.loads(line) for line in (DATA / 'labeling_review_manifest.jsonl').read_text(encoding='utf-8').splitlines()]
    unresolved = [json.loads(line) for line in (DATA / 'labeling_unresolved_cases.jsonl').read_text(encoding='utf-8').splitlines()]
    active_holds = [r for r in rows if not r['is_superseded'] and r['review_status']!='APPROVED']
    assert Counter(r['split'] for r in active_holds) == {'TRAIN':29,'VALIDATION':1}
    assert [r['display_index'] for r in active_holds if r['split']=='VALIDATION'] == ['V0107']
    selected = []
    for split, expected in [('TRAIN',694),('VALIDATION',155)]:
        name = f'export_{split.lower()}_candidates.jsonl'
        payload = (DATA / name).read_bytes()
        group = [json.loads(line) for line in payload.decode('utf-8').splitlines()]
        assert len(group) == expected
        (output / name).write_bytes(payload)
        selected.extend(group)
    index = [dict(capture_id=r['capture_id'],display_index=r['display_index'],split=r['split'],
                  raw_image_path=r['raw_image_path'],raw_sha256=r['raw_sha256'],
                  selected_for_this_run=r['capture_id'] in {s['capture_id'] for s in selected}) for r in rows]
    (output / 'raw_input_hashes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in index),encoding='utf-8')
    receipt = dict(task='ENGINE-MISASSEMBLY-BASELINE-TRAINING-001',output=str(output),
                   created_at=datetime.now(timezone.utc).isoformat(),input_integrity='PASS',
                   train=694,validation=155,unresolved=len(unresolved),active_holds=dict(Counter(r['split'] for r in active_holds)),
                   label_field='approved_part_states',label_source='codex_visual_review',human_reviewed=False,
                   original_files_unchanged=len(files),verifier_reports_redirected=True)
    (output / 'run.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False),flush=True)


if __name__ == '__main__':
    main()
