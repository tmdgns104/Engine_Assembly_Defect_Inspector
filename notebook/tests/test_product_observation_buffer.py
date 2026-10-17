"""Real queue handoff under a bounded consumer stall; no devices or PLC writes."""
from collections import deque
import queue
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from apps.edge_service.inspection import InspectionService
from src.runtime.product_passage import ProductPassage
from src.vision.inspection_worker import put_latest
from notebook.tests.test_full_frame_request import packet


class ProductObservationBufferTests(unittest.TestCase):
    def launch_queue(self):
        service = NS(manager=NS(Queue=queue.Queue), station={}, production_enabled=True,
            ctx=NS(Process=Mock(return_value=Mock()), RawValue=Mock()),
            preview_times=deque(), worker_target=Mock(), package=NS(root='fixture'))
        with patch('apps.edge_service.inspection.ProcessFlag', return_value=Mock()):
            InspectionService._launch(service)
        return service.products

    def passage(self):
        config = NS(zone_hysteresis=.02, max_center_step_norm=.2,
            max_center_speed_norm_s=1., max_missed_frames=30, max_unobserved_seconds=3.)
        return ProductPassage({'inspection_id':'fixture'}, packet(1, 1.), 'right', tracker_config=config)

    def test_short_consumer_stall_keeps_actual_intermediate_observations(self):
        channel, passage = self.launch_queue(), self.passage()
        # At the field's ~11 observations/s, a 0.63s consumer stall must not
        # discard six valid observations and create a false >0.5s source gap.
        for sequence in range(2, 9):
            put_latest(channel, packet(sequence, 1.+(sequence-1)*.09))
        received = []
        while not channel.empty():
            value = channel.get_nowait()
            received.append(value['sequence'])
            passage.observe(value, 1.75)
        self.assertEqual(received, list(range(2,9)))
        self.assertFalse(passage.invalid, passage.reason)
        self.assertIsNone(passage.proof)  # Buffering is never exit evidence.

    def test_real_source_gap_is_still_rejected(self):
        passage = self.passage()
        passage.observe(packet(2,1.54),1.6)
        self.assertTrue(passage.invalid)
        self.assertIsNone(passage.proof)

    def test_old_buffered_observation_is_still_rejected(self):
        channel, passage = self.launch_queue(), self.passage()
        put_latest(channel, packet(2,1.09))
        passage.observe(channel.get_nowait(),2.2)
        self.assertTrue(passage.invalid)
        self.assertIsNone(passage.proof)

    def test_overflow_remains_bounded_and_cannot_prove_exit(self):
        channel, passage = self.launch_queue(), self.passage()
        self.assertGreater(channel.maxsize,0)
        self.assertLessEqual(channel.maxsize,32)
        for sequence in range(2,102):
            put_latest(channel,packet(sequence,1.+(sequence-1)*.09))
        self.assertLessEqual(channel.qsize(),channel.maxsize)
        passage.observe(channel.get_nowait(),10.2)
        self.assertTrue(passage.invalid)
        self.assertIsNone(passage.proof)

if __name__ == '__main__':
    unittest.main()
