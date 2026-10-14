"""Real event/Journal boundaries; fixture results never claim hardware AI."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'jetson'))
from src.runtime.production import ProductionRuntime
from notebook.tests.test_standalone_runtime import FinalBoundaryTests

class EventRegression(FinalBoundaryTests):
    def setUp(self):
        super().setUp()
        self.r._diagnostic_events = []
        self.r._event = ProductionRuntime._event.__get__(self.r)

    def test_observation_and_completion_metadata_survive_real_journal(self):
        self.r._event(dict(event='LINE_OBSERVATION_ISSUE', monotonic_s=12.5,
                           runtime_session_id='session', reason='TRACK_ASSOCIATION_OR_GAP_LOST'))
        self.r._finish_without_frames('ERROR', 'NO_INSPECTION', 4)
        self.assertEqual(self.r.history[0]['decision'], 'ERROR')

if __name__ == '__main__': unittest.main()
