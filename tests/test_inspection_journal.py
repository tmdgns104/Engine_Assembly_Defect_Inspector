import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.journal.sqlite import ConflictError, Journal, validate_key


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.journal = Journal(self.root, min_free_bytes=0)
        self.addCleanup(lambda: self.journal.close())
        self.request = {"cell_id": "bench-test", "plc_session_id": 1, "request_id": 1, "cycle_id": 1,
                        "attempt": 1, "recipe_sha256": "recipe1", "source_mode": "mock", "coverage": ["top"]}
        self.package = {"manifest": {"product_id": "fixture", "release_id": "1"}}
        self.raw = {"data": b"fixture-bytes", "kind": "raw", "width": 100, "height": 100}

    def admit(self, request=None):
        return self.journal.admit(request or self.request, self.package)[0]

    def test_idempotence_full_payload_conflict_and_cross_session_ids(self):
        first = self.admit()
        self.assertEqual(self.journal.admit(self.request, self.package), (first, False))
        for change in ({"cycle_id": 2}, {"recipe_sha256": "other"}, {"coverage": ["side"]}):
            with self.assertRaises(ConflictError): self.admit(dict(self.request, **change))
        self.assertNotEqual(first, self.admit(dict(self.request, plc_session_id=2)))
        self.assertEqual(self.journal.metrics()["attempts"], 2)

    def test_integer_id_bounds_and_foreign_keys(self):
        for value in (True, 0, -1, 4294967296, "1"):
            with self.assertRaises(ValueError): validate_key(dict(self.request, request_id=value))
        with self.assertRaises(sqlite3.IntegrityError), self.journal.db:
            self.journal.db.execute("INSERT INTO defects VALUES ('d','missing','x',NULL,'{}')")

    def test_files_then_commit_then_immutable_history_and_asset_lookup(self):
        inspection = self.admit()
        result = self.journal.finish(inspection, {"decision": "PASS", "defects": []}, [self.raw])
        asset = result["assets"][0]
        self.assertEqual(self.journal.asset(asset["asset_id"])[1], self.raw["data"])
        self.assertEqual(self.journal.detail(inspection)["result"]["decision"], "PASS")
        self.assertIsNone(self.journal.finish(inspection, {"decision": "FAIL"}, [self.raw]))
        self.assertEqual(self.journal.detail(inspection)["result"]["decision"], "PASS")
        self.assertEqual(self.journal.history(product="fixture")[0]["package"], self.package)
        self.assertEqual(self.journal.metrics()["released"], 0)

    def test_file_failure_has_no_result_or_outbox(self):
        inspection = self.admit()
        with patch("src.journal.sqlite.atomic_write", side_effect=OSError("disk full")):
            with self.assertRaises(OSError): self.journal.finish(inspection, {"decision": "PASS"}, [self.raw])
        self.assertIsNone(self.journal.detail(inspection)["result"])
        self.assertEqual(self.journal.db.execute("SELECT count(*) FROM outbox").fetchone()[0], 0)

    def test_transaction_failure_preserves_orphans_and_recovery_records_gap(self):
        inspection = self.admit()
        self.journal.db.execute("CREATE TRIGGER fail_outbox BEFORE INSERT ON outbox BEGIN SELECT RAISE(ABORT,'injected commit boundary failure'); END")
        with self.assertRaises(sqlite3.IntegrityError): self.journal.finish(inspection, {"decision": "PASS"}, [self.raw])
        self.assertIsNone(self.journal.detail(inspection)["result"])
        self.assertEqual(self.journal.db.execute("SELECT count(*) FROM events").fetchone()[0], 0)
        self.journal.db.execute("DROP TRIGGER fail_outbox")
        recovered = self.journal.recover()
        self.assertEqual(recovered["interrupted_requests"], 1)
        self.assertEqual(len(recovered["orphan_assets_preserved"]), 1)
        self.assertEqual(self.journal.detail(inspection)["result"]["decision"], "ERROR")

    def test_cancelled_late_pass_is_never_published(self):
        inspection = self.admit()
        self.journal.cancel(inspection, "EXPIRED")
        self.assertIsNone(self.journal.finish(inspection, {"decision": "PASS"}, [self.raw]))
        self.assertEqual(self.journal.detail(inspection)["state"], "CANCELLED")
        self.assertFalse((self.root / "assets").exists())

    def test_restart_keeps_history_and_session_increases(self):
        session = self.journal.new_session("bench-test")
        inspection = self.admit()
        self.journal.finish(inspection, {"decision": "REVIEW"}, [self.raw])
        self.journal.close()
        self.journal = Journal(self.root, min_free_bytes=0)
        self.assertGreater(self.journal.new_session("bench-test"), session)
        self.assertEqual(self.journal.detail(inspection)["result"]["decision"], "REVIEW")

    def test_limits_and_calibration_binding(self):
        self.journal.outbox_limit = 0
        with self.assertRaises(OSError): self.admit()
        self.journal.save_calibration("pkg1", "station1", {"confirmed": True})
        self.assertTrue(self.journal.calibration("pkg1", "station1")["confirmed"])
        self.assertIsNone(self.journal.calibration("pkg2", "station1"))


if __name__ == "__main__": unittest.main()
