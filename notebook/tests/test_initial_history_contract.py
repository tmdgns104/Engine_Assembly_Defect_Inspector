"""Contract-aware admission, using real Journal transactions and approval polling."""
import json
import sqlite3
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from notebook.tests.test_initial_approval import ApprovalTests


class HistoryContractTests(unittest.TestCase):
    setUp = ApprovalTests.setUp
    poll = ApprovalTests.poll
    request = ApprovalTests.request

    def record(self, number=1, *, contract=None, complete=True, authority=None, **markers):
        binding = dict(authority=authority or 'WHOLE_PRODUCT_TRACK_AND_LATCHED_PLC_REQUEST',
                       runtime_session_id='old-session', plc_request_token='token-'+str(number), **markers)
        if contract is not None:
            binding['plc_contract'] = contract
        request = dict(cell_id='test', plc_session_id=1, request_id=number,
                       cycle_id=number, attempt=1, control_mode='production', runtime_binding=binding)
        identifier, _ = self.j.admit(request, {})
        if complete:
            self.j.finish(identifier, dict(decision='ERROR',
                          production_identity=dict(binding, inspection_id=identifier)))
        return identifier

    def eligible(self):
        self.poll()
        path = self.a.root/'challenge.json'
        return not self.a.failed and path.exists() and json.loads(path.read_text())['eligible']

    def test_35_legacy_completions_allow_challenge_without_rewriting_history(self):
        for i in range(1, 36):
            authority = ('WHOLE_PRODUCT_TRACK_AND_LATCHED_MOCK_REQUEST' if i <= 13
                         else 'WHOLE_PRODUCT_TRACK_AND_LATCHED_PLC_REQUEST')
            self.record(i, authority=authority)
        before = list(self.j.db.execute('SELECT * FROM inspections'))
        self.assertTrue(self.eligible())
        self.assertEqual(before, list(self.j.db.execute('SELECT * FROM inspections')))
        self.assertEqual(0, self.j.db.execute("SELECT count(*) FROM service_state WHERE key LIKE 'integrated_decision:%'").fetchone()[0])
        self.assertEqual(0, self.a.db.execute('SELECT count(*) FROM approvals').fetchone()[0])
        self.g.initial_arm.assert_not_called()

    def test_legacy_completion_does_not_require_a_date_cutoff_or_review_file(self):
        self.record()
        self.assertTrue(self.eligible())  # Journal uses today's completion time.
        self.assertFalse((self.a.root/'legacy_completed_review.json').exists())

    def test_accepted_legacy_and_new_contract_both_block(self):
        self.record(1, complete=False)
        self.record(2, contract='OPENER_CYCLIC', complete=False)
        self.assertFalse(self.eligible())

    def test_new_opener_missing_final_blocks(self):
        self.record(contract='OPENER_CYCLIC')
        self.assertFalse(self.eligible())

    def test_explicit_legacy_integrated_contract_missing_final_blocks(self):
        self.record(contract='LEGACY_THREE_BOOL')
        self.assertFalse(self.eligible())

    def test_other_integrated_contract_missing_final_blocks(self):
        self.record(contract='STANDALONE_V3')
        self.assertFalse(self.eligible())

    def test_unknown_contract_blocks(self):
        self.record(contract='FUTURE_CONTRACT')
        self.assertFalse(self.eligible())

    def test_missing_contract_but_new_line_marker_is_not_legacy(self):
        self.record(line_cycle_id=3)
        self.assertFalse(self.eligible())

    def test_unknown_legacy_authority_blocks(self):
        self.record(authority='UNKNOWN')
        self.assertFalse(self.eligible())

    def test_explicit_opener_marker_in_result_cannot_be_hidden_by_request(self):
        identifier = self.record(complete=False)
        self.j.finish(identifier, dict(decision='ERROR', production_identity=dict(
            inspection_id=identifier, plc_contract='OPENER_CYCLIC')))
        self.assertFalse(self.eligible())

    def test_missing_terminal_identity_is_not_recognized_legacy(self):
        identifier = self.record(complete=False)
        self.j.finish(identifier, dict(decision='ERROR'))
        self.assertFalse(self.eligible())

    def test_integrated_final_unlocks_only_complete_not_accepted(self):
        identifier = self.record(contract='OPENER_CYCLIC')
        with self.j.db:
            self.j.db.execute('INSERT INTO service_state VALUES (?,?)',
                ('integrated_decision:'+identifier, json.dumps(dict(decision='ERROR'))))
        self.assertTrue(self.eligible())
        self.record(2, contract='OPENER_CYCLIC', complete=False)
        self.assertFalse(self.eligible())

    def test_new_accepted_after_ready_blocks_grant(self):
        self.record()
        self.assertTrue(self.eligible())
        self.request()
        self.record(2, contract='OPENER_CYCLIC', complete=False)
        self.poll()
        self.assertTrue(self.a.failed)
        self.g.initial_arm.assert_not_called()

    def test_other_connection_commit_invalidates_ready_cache(self):
        identifier = self.record()
        self.assertTrue(self.eligible())
        other = sqlite3.connect(self.j.root/'journal.sqlite3')
        try:
            with other:
                other.execute("UPDATE inspections SET state='ACCEPTED' WHERE inspection_id=?", (identifier,))
        finally:
            other.close()
        self.assertFalse(self.eligible())

    def test_disk_shortage_after_ready_is_not_cached_away(self):
        self.record()
        self.assertTrue(self.eligible())
        self.j.min_free_bytes = 100
        with patch('src.journal.sqlite.shutil.disk_usage', return_value=SimpleNamespace(free=1)):
            self.assertFalse(self.eligible())
        self.g.initial_arm.assert_not_called()

    def test_disk_shortage_disarms_even_with_completed_legacy(self):
        self.record()
        self.j.min_free_bytes = 100
        with patch('src.journal.sqlite.shutil.disk_usage', return_value=SimpleNamespace(free=1)):
            self.assertFalse(self.eligible())
        self.assertTrue(self.a.failed)
        self.g.initial_arm.assert_not_called()

    def test_corrupt_journal_disarms_and_is_not_replaced(self):
        path = self.j.root/'broken.sqlite3'
        payload = b'not-a-sqlite-database'*100
        path.write_bytes(payload)
        bad = sqlite3.connect(path)
        self.addCleanup(bad.close)
        with patch.object(self.j, 'db', bad):
            self.assertFalse(self.eligible())
        self.assertEqual(payload, path.read_bytes())
        self.g.initial_arm.assert_not_called()

    def test_terminal_storage_failure_still_blocks(self):
        identifier = self.record()
        # Isolated corruption fixture only; no operating DB is touched.
        with self.j.db:
            self.j.db.execute("UPDATE inspections SET result_json=json_set(result_json,'$.storage_success',0) WHERE inspection_id=?", (identifier,))
        self.assertFalse(self.eligible())

    def test_missing_completed_at_still_blocks(self):
        identifier = self.record()
        with self.j.db:
            self.j.db.execute('UPDATE inspections SET completed_at=NULL WHERE inspection_id=?', (identifier,))
        self.assertFalse(self.eligible())

    def test_explicit_grant_after_legacy_history_reserves_once(self):
        self.record()
        self.assertTrue(self.eligible())
        self.request()
        self.poll()
        self.assertTrue(self.a.valid())
        self.assertEqual('RESERVED', self.a.db.execute('SELECT state FROM approvals').fetchone()[0])
        self.g.initial_arm.assert_called_once()


if __name__ == '__main__':
    unittest.main()
