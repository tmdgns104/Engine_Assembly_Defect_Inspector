"""Validate station manifests and create a combined manifest; never copy raw."""
import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.capture_windows.engine_exports import merge_manifests
from training.scripts.capture_proxy import load_profile


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifests', nargs='+', type=Path)
    parser.add_argument('--output', type=Path, default=PROJECT_ROOT/'data/engine/combined_manifest.jsonl')
    parser.add_argument('--profile', type=Path, default=PROJECT_ROOT/'training/datasets/engine/engine_model_top_v0/profile.json')
    parser.add_argument('--station-root', action='append', default=[], metavar='STATION_ID=RAW_ROOT',
                        help='Copied raw root containing STATION_A/ or STATION_B/; does not copy or re-encode files')
    args = parser.parse_args(argv)
    try:
        roots = {}
        for value in args.station_root:
            station, root = value.split('=', 1)
            if station in roots or not root:
                raise ValueError('중복 또는 빈 station-root')
            roots[station] = root
        print(json.dumps(merge_manifests(args.manifests, args.output, load_profile(args.profile), roots), ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print('Merge FAILED: '+str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
