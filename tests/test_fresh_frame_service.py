"""Spawned mock supervision plus independent SQLite publication boundary checks."""

import queue
import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.edge_service.inspection import InspectionService
from src.journal.sqlite import ConflictError, Journal
from src.journal.collector import Collector
from test_fresh_frame import trigger
from test_product_package import write_package


def trigger_worker(package_root, station, generation, commands, results, previews, stopping, cancellation, heartbeat):
    results.put({'type':'ready','generation':generation,'backend':{'backend':'mock'}})
    while not stopping.wait(.01):
        heartbeat.value = time.monotonic()
        try:
            previews.put_nowait({'generation':generation,'jpeg':b'synthetic','freshness':{'camera_epoch':'test-camera'}})
        except queue.Full:
            pass
        try:
            job = commands.get_nowait()
        except queue.Empty:
            continue
        time.sleep(.15)
        results.put({'type':'result','generation':generation,'inspection_id':job['inspection_id'],
                     'result':{'decision':'REVIEW','reason':'SYNTHETIC','fresh_frame':{'trigger':job['trigger']}},
                     'images':[{'kind':'raw','data':b'synthetic','width':1,'height':1}]})


class FreshServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        write_package(self.root/'package')
        station = {'station_id':'test','cell_id':'test','inspection_timeout_seconds':3,'startup_timeout_seconds':5,
                   'max_frame_age_seconds':.35,'frame_spacing_seconds':.15,
                   'fresh_frame':{'boundary_epsilon_ms':0,'max_trigger_to_frame_ms':2500,'inspection_window_ms':2500}}
        self.service = InspectionService(self.root/'package',station,self.root/'data',trigger_worker)
        self.wait_for(lambda:self.service.status()['camera_ready'])

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    def wait_for(self, predicate):
        deadline = time.monotonic()+5
        while not predicate() and time.monotonic()<deadline:
            time.sleep(.01)
        self.assertTrue(predicate())

    def request(self, number=1):
        return {'cell_id':'test','plc_session_id':self.service.session,'request_id':number,'cycle_id':number,
                'attempt':1,'kind':'calibrate','package_sha256':self.service.package.manifest_hash,
                'view_assessment':{'product_identity':'human_confirmed','alignment_confirmed':True,
                                   'visible_slots':{'first':True,'second':True},'basis':'SYNTHETIC ONLY'}}

    def test_trigger_is_server_bound_durable_and_single_active(self):
        before = time.monotonic()
        first,created = self.service.submit(self.request())
        active = self.service.active
        self.assertTrue(created)
        self.assertGreaterEqual(active['trigger']['trigger_received_monotonic'],before)
        self.assertEqual(active['trigger']['capture_epoch'],'test-camera')
        self.assertEqual(active['trigger']['trigger_source'],'LOCAL_TEST')
        with self.service.journal.lock:
            self.assertEqual(self.service.journal.db.execute("SELECT count(*) FROM events WHERE event_type='TRIGGER_ACCEPTED'").fetchone()[0],1)
        same,created = self.service.submit(self.request())
        self.assertFalse(created)
        self.assertEqual(same['inspection_id'],first['inspection_id'])
        with self.assertRaisesRegex(ConflictError,'BUSY'):
            self.service.submit(self.request(2))
        self.wait_for(lambda:self.service.active is None)
        result = self.service.journal.detail(first['inspection_id'])['result']
        self.assertEqual(result['fresh_frame']['trigger'],active['trigger'])
        self.assertTrue(result['storage_success'])

    def test_old_session_trigger_cannot_publish_result(self):
        with self.service.lock:
            first,_ = self.service.submit(self.request())
            self.service.session += 1
        self.wait_for(lambda:self.service.active is None)
        detail = self.service.journal.detail(first['inspection_id'])
        self.assertEqual(detail['state'],'CANCELLED')
        self.assertEqual(detail['result']['reason'],'SESSION_MISMATCH')
        self.assertEqual(detail['result']['assets'],[])

    def test_cancel_then_arrival_keeps_terminal_cancellation(self):
        first,_ = self.service.submit(self.request())
        self.service.cancel(first['inspection_id'])
        self.wait_for(lambda:self.service.active is None)
        result = self.service.journal.detail(first['inspection_id'])['result']
        self.assertEqual(result['reason'],'USER_CANCELLED')
        self.assertEqual(result['assets'],[])

    def test_wrong_trigger_result_is_rejected(self):
        with self.service.lock:
            self.service.submit(self.request())
            self.assertEqual(self.service._result_context_error({'fresh_frame':{'trigger':{}}}), 'TRIGGER_CONTEXT_MISMATCH')


class DurablePublicationTests(unittest.TestCase):
    def test_trigger_and_frame_links_survive_pc_mirror_without_schema_change(self):
        with tempfile.TemporaryDirectory() as folder:
            journal = Journal(Path(folder)/'edge',min_free_bytes=0)
            collector = Collector(Path(folder)/'pc')
            try:
                context = trigger().to_dict()
                request = {'cell_id':'test-cell','plc_session_id':1,'cycle_id':101,'request_id':1,'attempt':1}
                identifier,_ = journal.admit(request,{},trigger=context)
                result = journal.finish(identifier,{'decision':'REVIEW','fresh_frame':{'trigger':context}},
                                        [{'data':b'raw','kind':'raw','width':1,'height':1,'frame_id':'camera-A-4'}])
                for row in journal.db.execute('SELECT payload_json FROM events ORDER BY producer_seq'):
                    self.assertTrue(collector.receive_event(json.loads(row[0]))['event_ack'])
                mirrored = collector.journal.detail(identifier)['result']
                self.assertEqual(mirrored['fresh_frame']['trigger'],context)
                self.assertEqual(mirrored['assets'][0]['frame_id'],'camera-A-4')
                self.assertEqual(mirrored['assets'][0]['sha256'],result['assets'][0]['sha256'])
            finally:
                journal.close()
                collector.journal.close()

    def test_trigger_admission_rolls_back_if_its_event_cannot_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            journal = Journal(folder,min_free_bytes=0)
            try:
                journal.db.execute("CREATE TRIGGER fail_outbox BEFORE INSERT ON outbox BEGIN SELECT RAISE(ABORT,'synthetic'); END")
                request = {'cell_id':'test-cell','plc_session_id':1,'cycle_id':101,'request_id':1,'attempt':1}
                with self.assertRaises(sqlite3.IntegrityError):
                    journal.admit(request,{},trigger=trigger().to_dict())
                self.assertEqual(journal.db.execute('SELECT count(*) FROM inspections').fetchone()[0],0)
                self.assertEqual(journal.db.execute('SELECT count(*) FROM events').fetchone()[0],0)
            finally:
                journal.close()

    def test_no_result_visible_on_other_connection_before_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            journal = Journal(folder,min_free_bytes=0)
            reader = sqlite3.connect(Path(folder)/'journal.sqlite3')
            try:
                request = {'cell_id':'test','plc_session_id':1,'cycle_id':1,'request_id':1,'attempt':1}
                identifier,_ = journal.admit(request,{})
                actual_event = journal._event
                observed = []
                def observe(event_type,payload):
                    actual_event(event_type,payload)
                    observed.append(reader.execute('SELECT result_json FROM inspections WHERE inspection_id=?',(identifier,)).fetchone()[0])
                    self.assertEqual(reader.execute('SELECT count(*) FROM outbox').fetchone()[0],0)
                with patch.object(journal,'_event',side_effect=observe):
                    result = journal.finish(identifier,{'decision':'REVIEW'},[{'data':b'raw','kind':'raw','width':1,'height':1}])
                self.assertEqual(observed,[None])
                self.assertIsNotNone(reader.execute('SELECT result_json FROM inspections').fetchone()[0])
                self.assertTrue(result['storage_success'])
            finally:
                reader.close()
                journal.close()


if __name__ == '__main__':
    unittest.main()
