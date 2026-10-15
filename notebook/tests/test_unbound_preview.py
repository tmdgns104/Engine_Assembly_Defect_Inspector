"""Stopped preview loss cannot become the first PLC product's identity."""
import unittest

from notebook.tests import test_automatic_runtime as fixture
from src.tracking.contracts import TrackState, TrackingReason


class UnboundPreviewTests(unittest.TestCase):
    setUp = fixture.AutomaticRuntimeTests.setUp
    observe = fixture.AutomaticRuntimeTests.observe
    frame = fixture.AutomaticRuntimeTests.frame
    poll = fixture.AutomaticRuntimeTests.poll
    trigger = fixture.AutomaticRuntimeTests.trigger
    complete = fixture.AutomaticRuntimeTests.complete
    request_and_complete = fixture.AutomaticRuntimeTests.request_and_complete

    def empty_preview(self, phase='SYNC_LOW'):
        for _ in range(40):
            self.g.s.update(phase=phase, generated=self.now+self.at+.2,
                            received=self.now+self.at+.2)
            self.g.s['controls'].update(Mc_Run=phase=='IDLE', Inspection_Request=False)
            self.poll()
            self.frame(count=0)

    def test_stopped_preview_loss_then_first_request_uses_new_current_track(self):
        old_session = self.r.session_id
        self.empty_preview()
        self.assertNotEqual(self.r.session_id, old_session)
        self.assertIsNone(self.r.product_separation)  # No invented product exit.
        self.assertFalse(self.r._clear(self.now+self.at))
        self.frame()
        self.g.s.update(phase='IDLE')
        self.g.s['controls']['Mc_Run'] = True
        self.poll()
        self.g.s.update(phase='REQUEST_RECEIVED', request_id=1,
                        accepted_at=self.now+self.at+.02)
        self.g.s['controls']['Inspection_Request'] = True
        self.poll()
        self.frame()
        self.trigger(self.at+.1)
        self.assertEqual(len(self.submitted), 1)
        self.assertEqual(self.submitted[0]['runtime_binding']['runtime_session_id'], self.r.session_id)
        self.assertNotEqual(self.r.session_id, old_session)
        self.assertEqual(self.g.automatic_arm.call_count, 0)

    def test_running_unbound_preview_can_reacquire_before_request(self):
        old_session = self.r.session_id
        self.empty_preview('IDLE')
        self.frame()
        self.assertNotEqual(self.r.session_id, old_session)
        self.assertEqual(self.r.coordinator._tracker._state, TrackState.TRACKING)

    def test_repositioned_unbound_preview_does_not_poison_first_request(self):
        # A stopped operator moves the uninspected model from the inspection
        # location to the feed position. This is not an accepted PLC identity.
        self.g.s.update(phase='SYNC_LOW')
        self.poll()
        old_session = self.r.session_id
        moved = dict(x1=.65, y1=.65, x2=.95, y2=.95)
        self.frame(box=moved)
        self.assertEqual(self.r.coordinator._tracker._reason,
                         TrackingReason.TRACK_ASSOCIATION_INVALID)
        self.assertEqual(self.r.coordinator._tracker._state, TrackState.WAIT_AREA_CLEAR)
        self.poll()
        self.frame(box=moved)
        self.frame(box=moved)
        self.assertNotEqual(self.r.session_id, old_session)
        self.assertIsNone(self.r.product_separation)
        self.assertEqual(self.r.coordinator._tracker._state, TrackState.TRACKING)
        self.g.s.update(phase='IDLE')
        self.g.s['controls']['Mc_Run'] = True
        self.poll()
        self.g.s.update(phase='REQUEST_RECEIVED', request_id=1,
                        accepted_at=self.now+self.at+.02)
        self.g.s['controls']['Inspection_Request'] = True
        self.poll()
        self.frame(box=moved)
        self.trigger(self.at+.1)
        self.assertEqual(len(self.submitted), 1)
        self.assertEqual(self.submitted[0]['runtime_binding']['runtime_session_id'],
                         self.r.session_id)
        self.g.automatic_arm.assert_not_called()
        self.g.result.assert_not_called()

    def test_association_loss_after_request_cannot_replace_product(self):
        self.g.s.update(phase='REQUEST_RECEIVED', request_id=1,
                        accepted_at=self.now+self.at+.02)
        self.g.s['controls'].update(Mc_Run=True, Inspection_Request=True)
        self.poll()
        old_session, token = self.r.session_id, self.r.handshake.token
        moved = dict(x1=.65, y1=.65, x2=.95, y2=.95)
        for _ in range(4):
            self.frame(box=moved)
            self.poll()
        self.trigger(self.at+.1)
        self.assertEqual(self.r.session_id, old_session)
        self.assertEqual(self.r.handshake.token, token)
        self.assertEqual(self.submitted, [])
        self.g.result.assert_not_called()

    def test_invalid_association_with_stale_plc_cannot_reacquire(self):
        self.g.s.update(phase='SYNC_LOW', connected=False, fresh=False)
        old_session = self.r.session_id
        moved = dict(x1=.65, y1=.65, x2=.95, y2=.95)
        for _ in range(4):
            self.frame(box=moved)
        self.assertEqual(self.r.session_id, old_session)
        self.assertEqual(self.submitted, [])

    def test_received_request_cannot_replace_frozen_identity(self):
        self.g.s.update(phase='REQUEST_RECEIVED', request_id=1,
                        accepted_at=self.now+self.at+.02)
        self.g.s['controls'].update(Mc_Run=True, Inspection_Request=True)
        self.poll()
        old_session, token = self.r.session_id, self.r.handshake.token
        for _ in range(40):
            self.g.s.update(generated=self.now+self.at+.2, received=self.now+self.at+.2)
            self.frame(count=0)
        self.frame()
        self.assertEqual(self.r.session_id, old_session)
        self.assertEqual(self.r.handshake.token, token)
        self.assertEqual(self.submitted, [])

    def test_completed_product_disappearance_is_not_preview_or_exit(self):
        identifier = self.request_and_complete(1, 'REVIEW')
        old_session = self.r.session_id
        self.empty_preview('IDLE')
        self.frame()
        self.assertEqual(self.r.session_id, old_session)
        self.assertIsNotNone(self.r.product_passage)
        self.assertIsNone(self.r.product_separation)
        self.assertEqual(self.r.product_passage.identity['inspection_id'], identifier)

    def test_stale_or_disconnected_snapshot_does_not_reacquire(self):
        old_session = self.r.session_id
        self.g.s.update(connected=False, fresh=False)
        self.empty_preview()
        self.assertEqual(self.r.session_id, old_session)


if __name__ == '__main__':
    unittest.main()
