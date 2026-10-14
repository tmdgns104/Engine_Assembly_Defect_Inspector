import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import tarfile

from jetson import build_bundle


class RuntimeBundleModeTests(unittest.TestCase):
    def test_bundled_opener_remains_executable(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary = root/'OpENer'
            binary.write_bytes(b'fake-executable-for-packaging-only')
            name = 'current/opener/OpENer'
            release = dict(files={name:hashlib.sha256(binary.read_bytes()).hexdigest()},
                           links={'current/config':'../assets/runtime_config'}, release_id='test')
            with patch.object(build_bundle, 'collect_release', return_value=(
                    {name:binary},release,json.dumps(release).encode())):
                output = root/'release.tar.gz'
                build_bundle.build_package(output,root)
            with tarfile.open(output) as archive:
                self.assertEqual(0o755, archive.getmember(name).mode)
