"""Readiness SQL has no product-session input; actual request ownership does."""
import threading
import time
import unittest
from unittest.mock import patch

from notebook.tests import test_request_start_runtime as fixture


class IdleReadinessIdentityTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.RequestStartRuntimeTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        c = self.case
        c.r.handshake.token = None
        c.r.handshake.state = 'ARMED'
        c.phase = 'IDLE'
        c.controls['Inspection_Request'] = False
        c.controller._request_readiness(c.snapshot())
        c.drain_pending()
        self.assertTrue(c.controller.ready(c.snapshot()))

    def test_idle_tracking_rollover_during_SQL_preserves_verified_readiness(self):
        c = self.case
        entered, release = threading.Event(), threading.Event()
        original = c.journal.capacity
        def delayed():
            entered.set()
            if not release.wait(2):
                raise TimeoutError('fixture readiness SQL')
            return original()
        try:
            with patch.object(c.journal, 'capacity', side_effect=delayed):
                c.controller._request_readiness(c.snapshot())
                self.assertTrue(entered.wait(1))
                c.controller._poll(time.monotonic())
                self.assertTrue(c.health_updates[-1][1])
                c.r.session_id = 'next-product-session'
                c.service.production_owner.session_id = c.r.session_id
                c.controller._poll(time.monotonic())
                self.assertIsNone(c.controller.pending['aborted'])
                self.assertTrue(c.health_updates[-1][1])
                release.set()
                c.drain_pending()
        finally:
            release.set()
        self.assertTrue(c.controller.ready(c.snapshot()))
        self.assertIsNone(c.controller.last_error)
        self.assertIsNone(c.r.error)
        self.assertTrue(c.service.commands.empty())

    def test_readiness_still_invalidates_real_execution_owners(self):
        c = self.case
        mutations = (
            (c.service, 'generation', 'other-worker'),
            (c.service, 'session', c.service.session + 1),
            (c.service.package, 'manifest_hash', 'other-package'),
            (c.r, 'epoch', 'other-camera'),
            (c, 'connection', 2),
        )
        for target, name, changed in mutations:
            with self.subTest(field=name):
                original = getattr(target, name)
                setattr(target, name, changed)
                self.assertFalse(c.controller.ready(c.snapshot()))
                setattr(target, name, original)
        c.r._automatic_previous = dict(inspection_id='other-request', request_token='other-token')
        self.assertFalse(c.controller.ready(c.snapshot()))

    def test_SQL_failure_cannot_reuse_old_success_after_tracking_rollover(self):
        c = self.case
        with patch.object(c.journal, 'capacity', side_effect=OSError('fixture unavailable disk')):
            c.controller._request_readiness(c.snapshot())
            c.r.session_id = 'next-product-session'
            c.drain_pending()
        self.assertFalse(c.controller.ready(c.snapshot()))
        self.assertIsNone(c.controller.readiness)
        self.assertFalse(c.health_updates[-1][1])


if __name__ == '__main__':
    unittest.main()
