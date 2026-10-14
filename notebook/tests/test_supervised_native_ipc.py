"""Native AF_UNIX IPC against the real C/Python owners; synthetic PLC and AI."""
import json
import os
import subprocess
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from src.control.opener_cyclic import OpenerGateway, CyclicHandshake
from src.runtime.supervised_approval import SupervisedApproval, CONFIRMATIONS
from src.journal.sqlite import Journal

@unittest.skipUnless(os.environ.get('SUPERVISED_IPC_FIXTURE'),'requires compiled AF_UNIX-only fixture')
class NativeSupervisedIpc(unittest.TestCase):
    def test_four_results_over_actual_ipc_and_persistent_ledger(self):
        with tempfile.TemporaryDirectory(prefix='eai18-') as folder:
            root=Path(folder);os.chmod(root,0o700)
            process=subprocess.Popen([os.environ['SUPERVISED_IPC_FIXTURE'],str(root/'ipc')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            gateway=None
            try:
                end=time.monotonic()+3
                while not (root/'ipc').exists() and time.monotonic()<end:time.sleep(.01)
                gateway=OpenerGateway(str(root/'ipc'),writes_enabled=True)
                journal=Journal(root/'j',min_free_bytes=0)
                approval=SupervisedApproval(root/'a',gateway.runtime_session)
                previous=None
                def step():
                    now=time.monotonic();gateway.health_update(True,False,now)
                    snapshot=gateway.read_snapshot(now)
                    approval.poll(snapshot,True,'fixture-camera','fixture-worker',now,gateway,journal,
                        settlement=dict(clean=True,previous=previous),prepare=lambda *args:None)
                    return snapshot
                def wait(predicate):
                    end=time.monotonic()+3
                    while time.monotonic()<end:
                        snap=step()
                        if snap and predicate(snap):return snap
                        time.sleep(.02)
                    self.fail(json.dumps(dict(approval=approval.status(),snapshot=snap)))
                handshake=CyclicHandshake(gateway,lambda event:None)
                for number,decision in enumerate(('PASS','FAIL','REVIEW','ERROR'),1):
                    wait(lambda s:bool(approval.challenge and approval.challenge['eligible']))
                    grant=approval.submit(approval.challenge['id'],list(CONFIRMATIONS),time.monotonic())
                    wait(lambda s:s['approval_id']==grant and s['phase']=='SYNC_LOW')
                    handshake.retire_supervised()
                    process.stdin.write('S');process.stdin.flush()
                    wait(lambda s:s['phase']=='IDLE')
                    process.stdin.write('R');process.stdin.flush()
                    snapshot=wait(lambda s:s['phase']=='REQUEST_RECEIVED')
                    handshake.poll(time.monotonic());approval.accept(snapshot,handshake.token)
                    identifier,_=journal.admit(dict(cell_id='fixture',plc_session_id=1,request_id=number,cycle_id=number,attempt=1),{})
                    import cv2, numpy as np
                    raw=cv2.imencode('.png',np.full((8,8,3),120,np.uint8))[1].tobytes()
                    journal.finish(identifier,dict(decision=decision,reason='SYNTHETIC_IPC_TEST',execution={'source':'mock'}),
                        [dict(kind='raw',data=raw,width=8,height=8)])
                    with journal.db:
                        journal.db.execute('INSERT INTO service_state VALUES (?,?)',('integrated_decision:'+identifier,json.dumps(dict(decision=decision,synthetic=True))))
                    handshake.bind(identifier);handshake.publish(identifier,decision,True,time.monotonic())
                    previous=dict(inspection_id=identifier,request_token=handshake.token,decision=decision,durable=True)
                    snapshot=wait(lambda s:s['phase']=='READY_NEXT' and s['completed_count']==number)
                    self.assertEqual(snapshot['result_count'],number);self.assertEqual(snapshot['done_count'],number)
                    for _ in range(3):step();time.sleep(.03)
                    self.assertEqual(approval.prepared_count,number)
                self.assertEqual(journal.db.execute('SELECT count(*) FROM inspections').fetchone()[0],4)
                self.assertEqual(approval.db.execute('SELECT count(*) FROM approvals').fetchone()[0],4)
                self.assertEqual(approval.state,'COMPLETED_WAIT_OPERATOR')
                approval.close();journal.close()
            finally:
                if gateway:gateway.close()
                process.stdin.write('Q');process.stdin.flush()
                stdout,stderr=process.communicate(timeout=3)
                print(stdout,stderr)
                self.assertEqual(process.returncode,0)

if __name__=='__main__':unittest.main()
