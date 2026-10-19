"""Replay frozen preprocessing and fixed classifiers into a NEW local run only."""
import argparse
from pathlib import Path
import shutil

import fit_train


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    source = fit_train.OUTPUT
    destination = Path(args.output).resolve()
    if destination.exists() or not destination.is_relative_to(source.parent):
        parser.error('Output must be a nonexistent directory under runs/engine_preprocessing_recovery_001')
    if args.check_only:
        print('VALID NEW OUTPUT', destination)
        return
    destination.mkdir()
    for name in ['fixed_populations.json', 'baseline_reproduced_records.jsonl', 'baseline_reproduction_verification.json']:
        shutil.copyfile(source/name, destination/name)
    shutil.copytree(source/'alignment', destination/'alignment')
    # Both scripts bind OUTPUT on import. The source run is only read.
    fit_train.OUTPUT = destination
    import run_preprocessing
    import evaluate
    run_preprocessing.main()
    evaluate.main()
    print('REPLAY COMPLETE', destination)


if __name__ == '__main__':
    main()
