"""Build the Jetson bundle on the notebook using the shared release builder."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'jetson'))
from build_bundle import PROJECT, build_package, checked_file, main


if __name__ == '__main__':
    main()
