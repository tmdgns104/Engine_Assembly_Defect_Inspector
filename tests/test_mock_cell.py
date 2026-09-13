import unittest
from src.control.mock_cell import MockCell


class Port:
    def __init__(self):self.calls=[];self.answer=None;self.online=True;self.ack=True;self.cycle_ack=True
    def recover(self):self.calls.append('recover')
    def prepare(self,view):return {'cell_id':'mock','plc_session_id':1,'request_id':1,'cycle_id':1}
    def submit(self,job):self.calls.append('submit')
    def healthy(self,job):return self.online
    def cancel(self,job):self.calls.append('cancel')
    def poll(self,job):return self.answer
    def ack_result(self,job):self.calls.append('result_ack');return self.ack
    def terminal(self,job,disposition):self.calls.append('terminal');return self.cycle_ack


class MockTests(unittest.TestCase):
    def setUp(self):
        self.time=0;self.port=Port();self.cell=MockCell(self.port,lambda:self.time,timeout=2)
        self.cell.recover()
    def advance(self,seconds):self.time+=seconds;self.cell.tick()
    def start(self):
        self.assertTrue(self.cell.start(True,{'human_confirmed':True}))
        self.advance(.2);self.advance(.2)
        self.assertEqual(self.cell.state,'WAIT_RESULT')
    def answer(self,decision):
        self.port.answer={'decision':decision,'storage_success':True,'request':dict(self.cell.job)}
        self.cell.tick()
    def test_pass_three_acks_and_held_start_no_restart(self):
        self.start();self.port.ack=False;self.answer('PASS')
        self.assertEqual(self.cell.state,'RELEASE')
        with self.assertRaises(ValueError):self.cell.finish('RELEASED')
        self.port.ack=True;self.cell.tick();self.cell.finish('RELEASED')
        self.port.cycle_ack=False;self.assertFalse(self.cell.acknowledge_cycle())
        self.assertEqual(self.cell.state,'COMPLETE')
        self.port.cycle_ack=True;self.assertTrue(self.cell.acknowledge_cycle())
        self.assertFalse(self.cell.start(True,{'human_confirmed':True}))
        self.assertEqual(self.port.calls.count('submit'),1)
        self.assertEqual(sum(x['state']=='RELEASE' for x in self.cell.transitions),1)
    def test_fail_review_hold_error_fault(self):
        for decision,state,disposition in [('FAIL','HOLD','REMOVED'),('REVIEW','HOLD','QUARANTINED'),('ERROR','FAULT','ABORTED')]:
            self.setUp();self.start();self.answer(decision)
            self.assertEqual(self.cell.state,state)
            if decision!='PASS':
                with self.assertRaises(ValueError):self.cell.finish('RELEASED')
            self.cell.finish(disposition);self.cell.acknowledge_cycle()
    def test_timeout_late_pass_is_not_consumed(self):
        self.start();self.advance(2.01)
        self.assertEqual(self.cell.state,'FAULT');self.answer('PASS')
        self.assertEqual(self.cell.state,'FAULT');self.assertFalse(self.cell.consumed)
        self.assertEqual(self.port.calls.count('cancel'),1)
    def test_heartbeat_loss_and_wrong_session(self):
        self.start();self.port.online=False;self.cell.tick()
        self.assertEqual(self.cell.state,'FAULT')
        self.setUp();self.start();self.port.answer={'decision':'PASS','storage_success':True,'request':dict(self.cell.job,plc_session_id=2)}
        self.cell.tick();self.assertEqual(self.cell.reason,'RESULT_KEY_MISMATCH')
    def test_no_start_while_terminal_pending_or_without_visibility(self):
        with self.assertRaises(ValueError):self.cell.start(True,{})
        self.cell.start(False,{})
        self.start();self.answer('PASS');self.cell.finish('RELEASED');self.cell.start(False,{})
        with self.assertRaises(ValueError):self.cell.start(True,{'human_confirmed':True})


if __name__=='__main__':unittest.main()
