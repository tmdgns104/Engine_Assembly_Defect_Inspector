"""Use Windows extended paths without changing file names or OS policy."""
import os
from pathlib import Path


def storage_path(value):
    """Normalize the same absolute location for long-path-capable filesystem calls.

    The prefix is a Windows API spelling, not a new directory or dataset layout.
    Keep the existing symlink/junction checks at the collection entry points.
    """
    absolute = os.path.abspath(value)
    if os.name != 'nt' or absolute.startswith('\\\\?\\'):
        return Path(absolute)
    if absolute.startswith('\\\\'):
        return Path('\\\\?\\UNC\\'+absolute[2:])
    return Path('\\\\?\\'+absolute)
