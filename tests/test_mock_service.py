import unittest
import test_inspection_service


class MockIntegrationTests(unittest.TestCase):
    setUp=test_inspection_service.ServiceTests.setUp
    tearDown=test_inspection_service.ServiceTests.tearDown
    wait_for=test_inspection_service.ServiceTests.wait_for
    def test_mock_request_stored_then_acks_and_terminal_block_switch(self):
        service=self.service
        # Deliberate fixture-only confirmation; fake Worker/Detector cannot count as hardware PASS.
        service.calibration={'confirmed':True}
        view={'product_identity':'human_confirmed','alignment_confirmed':True,'visible_slots':{'first':True,'second':True}}
        with service.lock:
            service.mock.recover();service.mock.start(True,view)
            with self.assertRaises(ValueError):service.activate(self.root/'package')
        self.wait_for(lambda:service.mock.state=='HOLD')
        self.assertFalse(service.status()['ready'])
        self.assertTrue(service.mock.result_ack)
        result=service.mock.result
        self.assertEqual(result['execution']['source'],'mock')
        self.assertEqual(result['execution']['control'],'mock')
        with service.lock:
            service.mock.finish('REMOVED')
            with self.assertRaises(ValueError):service.activate(self.root/'package')
            self.assertTrue(service.mock.acknowledge_cycle())
        self.assertEqual(service.journal.metrics()['attempts'],1)
        self.assertEqual(service.journal.metrics()['released'],0)
        self.assertEqual(service.journal.db.execute('SELECT terminal FROM cycles').fetchone()[0],'REMOVED')
        self.assertEqual(service.journal.db.execute("SELECT count(*) FROM events WHERE event_type='MOCK_RESULT_ACK'").fetchone()[0],1)


if __name__=='__main__':unittest.main()
