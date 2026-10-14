"""Run software-only runtime tests against the canonical jetson/ source tree."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'jetson'), str(ROOT), str(ROOT/'notebook/tests')]

if __name__ == '__main__':
    names = sys.argv[1:]
    if not names:
        raise SystemExit('Provide notebook.tests module or test names; no hardware tests are auto-selected.')
    suite = unittest.TestSuite()
    seen = set()

    def collect(node):
        if isinstance(node, unittest.TestSuite):
            for item in node:
                collect(item)
        elif node.id() not in seen:
            suite.addTest(node)
            seen.add(node.id())

    for name in names:
        collect(unittest.defaultTestLoader.loadTestsFromName(name))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
