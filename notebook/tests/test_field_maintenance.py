"""Approval/ownership guards and bounded supervisor, without hardware or network."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import hashlib
ROOT=Path(__file__).resolve().parents[2]/'jetson'
sys.path.insert(0,str(ROOT))
from field_raw_maintenance import check_state, validate_approval, supervise
import field_raw_maintenance as maintenance


def fake_worker(package,station,generation,commands,results,previews,stopping,cancellation,heartbeat,products,tracking):
    results.put(dict(type='ready',backend={'backend':'SYNTHETIC'},generation=generation))
    command=commands.get(timeout=5)
    assert command['type']=='field_raw_capture'
    assert command['context']['publication_disabled'] is True
    assert tracking.is_set()
    results.put(dict(type='diagnostic_capture',status={'state':'RECORDING'}))
    time.sleep(.04)
    results.put(dict(type='diagnostic_capture',status={'state':'SAVED'}))
    stopping.wait(5)


class MaintenanceTests(unittest.TestCase):
    def test_operating_source_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            device=Path(temp);(device/'current').mkdir()
            source=device/'current/worker.py';source.write_text('original',encoding='utf-8')
            manifest=device/'manifest.json'
            manifest.write_text(json.dumps({'operating_baseline_files':[{'path':'worker.py',
                'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}]}),encoding='utf-8')
            with patch.object(maintenance,'DEVICE',device):
                maintenance.verify_operating_baseline(manifest)
                source.write_text('changed',encoding='utf-8')
                with self.assertRaisesRegex(RuntimeError,'OPERATING_SOURCE_CHANGED'):
                    maintenance.verify_operating_baseline(manifest)

    def test_active_or_unknown_service_blocked(self):
        for state in ({'ActiveState':'active','MainPID':'42'},{'ActiveState':'unknown','MainPID':'0'}):
            with self.assertRaises(RuntimeError):check_state(state,'','',False)

    def test_cip_listener_and_camera_owner_blocked(self):
        inactive={'ActiveState':'inactive','MainPID':'0'}
        for listeners,camera in (('udp UNCONN 0 0 0.0.0.0:2222 0.0.0.0:*',''),('','123')):
            with self.assertRaises(RuntimeError):check_state(inactive,listeners,camera,False)
        check_state(inactive,'tcp LISTEN 0 128 0.0.0.0:22 0.0.0.0:*','',False)

    def test_enabled_or_unknown_publication_blocked(self):
        for value in (True,None):
            with self.assertRaises(RuntimeError):check_state({'ActiveState':'inactive','MainPID':'0'},'','',value)

    def test_approval_is_explicit_and_short_lived(self):
        now=datetime.now(timezone.utc)
        value=dict(mode='FIELD_RAW_CAPTURE_ONLY',approved=True,service_transition_approved=True,
            field_stopped=True,no_motion=True,human_state='SYNTHETIC',
            expires_utc=(now+timedelta(minutes=10)).isoformat(),
            request=dict(clip_id='approval',duration_seconds=5,max_frames=160,max_bytes=128*1024*1024))
        self.assertEqual(validate_approval(value,now)['duration_seconds'],5)
        for update in ({'approved':False},{'service_transition_approved':False},
                       {'expires_utc':(now-timedelta(seconds=1)).isoformat()}):
            with self.assertRaises(ValueError):validate_approval(dict(value,**update),now)

    def test_supervisor_runs_only_capture_command_and_closes_child(self):
        with tempfile.TemporaryDirectory() as folder:
            value=supervise('fixture',{},Path(folder),{}, {},worker_target=fake_worker,startup_timeout=5)
            self.assertTrue(value['worker_stop_confirmed'])
            self.assertEqual(value['plc_writes'],0)
            self.assertFalse(value['runtime_constructed'])
            self.assertFalse(value['journal_opened'])


if __name__=='__main__':unittest.main()
