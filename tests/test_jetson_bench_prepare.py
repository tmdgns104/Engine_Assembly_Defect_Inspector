"""Focused preparation checks without SSH, hardware, or model inference."""

import ast
import json
import unittest
from pathlib import Path

from scripts.connect_jetson_bench import authorize_command
from scripts.prepare_jetson_bench import sha256


ROOT = Path(__file__).resolve().parents[1]


class BenchPreparationTests(unittest.TestCase):
    def test_authorization_is_append_only_and_quoted(self):
        command = authorize_command("ssh-ed25519 AAAA note'$(false)")
        self.assertIn("grep -qxF --", command)
        self.assertIn(">> ~/.ssh/authorized_keys", command)
        self.assertNotIn("StrictHostKeyChecking", command)
        self.assertIn("'\"'\"'", command)

    def test_scripts_parse_without_running_hardware(self):
        for name in ("connect_jetson_bench.py", "prepare_jetson_bench.py", "probe_jetson_bench.py"):
            ast.parse((ROOT / "scripts" / name).read_text(encoding="utf-8"))

    def test_actual_staging_provenance_and_separate_expectations(self):
        staging = ROOT / "runs/jetson_bench_001/staging_v001"
        if not staging.exists():
            self.skipTest("Local staging not created; no protected dataset discovery")
        manifest = json.loads((staging / "manifest.json").read_text(encoding="utf-8"))
        expected = json.loads((staging / "smoke_expectations.json").read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["images"]), 4)
        self.assertEqual({x["scenario"] for x in expected},
                         {"NORMAL", "MISSING_LEFT", "MISSING_RIGHT", "MISSING_BOTH"})
        self.assertEqual(manifest["jetson_execution"], "NOT_RUN")
        self.assertEqual(manifest["onnx"]["inputs"][0]["shape"], [1, 3, 640, 640])
        for item, truth in zip(manifest["images"], expected):
            self.assertNotIn("scenario", item)
            self.assertEqual(truth["provenance"]["round_id"], "B03")
            self.assertEqual(item["sha256"], sha256(staging / item["image"]))
        self.assertEqual(manifest["model_sha256"], sha256(Path(manifest["model_path"])))


if __name__ == "__main__":
    unittest.main()
