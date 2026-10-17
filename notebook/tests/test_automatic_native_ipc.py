"""Real AF_UNIX C/Python, synthetic PLC/AI; never opens field network sockets."""
import os
import subprocess
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from src.control.opener_cyclic import OpenerGateway, CyclicHandshake


@unittest.skipUnless(os.environ.get('SUPERVISED_IPC_FIXTURE'), 'requires native AF_UNIX-only fixture')
class NativeAutomaticIpc(unittest.TestCase):
    def test_four_outcomes_without_browser_single_START(self):
        with tempfile.TemporaryDirectory(prefix='eai-auto-') as folder:
            root=Path(folder);os.chmod(root,0o700)
            process=subprocess.Popen([os.environ['SUPERVISED_IPC_FIXTURE'],str(root/'ipc'),'automatic'],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            gateway=None
            try:
                deadline=time.monotonic()+3
                while not (root/'ipc').exists() and time.monotonic()<deadline:time.sleep(.01)
                gateway=OpenerGateway(root/'ipc',writes_enabled=True)
                handshake=CyclicHandshake(gateway,lambda e:None)
                clear=False
                def wait(predicate):
                    deadline=time.monotonic()+3
                    while time.monotonic()<deadline:
                        now=time.monotonic();gateway.health_update(True,clear,now)
                        s=gateway.read_snapshot(now)
                        if s and predicate(s):return s
                        time.sleep(.02)
                    self.fail(str(s))
                s=wait(lambda s:s['connected'] and s['fresh'])
                # A completed capture ERROR must not block the next valid cycle.
                for number,decision in enumerate(('PASS','FAIL','REVIEW','ERROR','PASS'),1):
                    self.assertFalse(hasattr(gateway,'automatic_arm'))
                    self.assertFalse(s['approval_id'])
                    if number==1:process.stdin.write('S');process.stdin.flush()
                    wait(lambda s:s['phase']=='IDLE')
                    process.stdin.write('R');process.stdin.flush()
                    s=wait(lambda s:s['phase']=='REQUEST_RECEIVED')
                    handshake.poll(time.monotonic())
                    identifier=uuid.uuid4().hex
                    handshake.bind(identifier)
                    handshake.publish(identifier,decision,True,time.monotonic())
                    s=wait(lambda s:s['phase'] in ('READY_NEXT','IDLE') and s['completed_count']==number)
                    self.assertEqual(s['result_count'],number)
                    self.assertEqual(s['done_count'],number)
                    self.assertEqual(s['raw100'],'00000000')
                    self.assertTrue(s['controls']['Mc_Run'])
            finally:
                if gateway:gateway.close()
                process.stdin.write('Q');process.stdin.flush()
                stdout,stderr=process.communicate(timeout=3)
                print(stdout,stderr)
                self.assertEqual(process.returncode,0)

if __name__=='__main__':unittest.main()
