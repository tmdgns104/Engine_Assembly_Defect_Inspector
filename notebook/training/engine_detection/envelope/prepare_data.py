"""Verify only the explicit development allowlist; preserve all source labels."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'source_candidate/engine_dynamic_pose_v001'
TRAIN = Path('D:/OneDevice_Worktrees/jetson-p0-004c0/runs/manual_tracking_dev/engine_parts_CFA8507_v001/outputs/run_20260921T082749Z_709634')


def main():
    rows = json.loads((SOURCE / 'source_index.json').read_text(encoding='utf-8'))['items']
    assert len(rows) == 216
    assert {r['review_id'] for r in rows} == {f'D{i:03}' for i in range(1, 217)}
    receipts = []
    mismatches = []
    for row in rows:
        rid, split = row['review_id'], row['split']
        number = int(rid[1:])
        assert row['round_id'] == ('E01' if number <= 72 else 'E02' if number <= 144 else 'E03')
        assert split == ('train' if number <= 144 else 'val')
        original = TRAIN / f'dataset/images/{split}/{rid}.png'
        content = original.read_bytes()
        assert hashlib.sha256(content).hexdigest() == row['image_sha256'], rid
        parts = (TRAIN / f'dataset/labels/{split}/{rid}.txt').read_text(encoding='utf-8').splitlines()
        combined = (SOURCE / f'labels_combined/{split}/{rid}.txt').read_text(encoding='utf-8').splitlines()
        if [x for x in combined if x.split()[0] != '3'] != parts:
            mismatches.append(rid)
        assert len([x for x in combined if x.split()[0] == '3']) == 1
        receipts.append({'id': rid, 'split': split, 'sha256': row['image_sha256'], 'parts_unchanged': True})
    (ROOT / 'input_verification.json').write_text(json.dumps({'rows': receipts, 'e04_used': 0, 'train': 144, 'val': 72, 'zip_parts_differ_from_approved': mismatches, 'label_authority': str(TRAIN/'dataset/labels')}, indent=2), encoding='utf-8')
    shutil.copytree(ROOT.parent/'engine_package_integration_001/candidate_runtime', ROOT/'candidate_runtime', ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    print('Verified 216 images; approved part labels retained; E04 reads 0. ZIP label differences:', mismatches)


if __name__ == '__main__':
    main()
