"""Changed decision boundary, upstream request and field UI; no real hardware."""
from collections import deque
from pathlib import Path
from types import SimpleNamespace as NS
import copy
import json
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'jetson'))
from src.runtime.standalone import StandaloneRuntime, arrival_evidence
from src.control.standalone_plc import LineHandshake, LineGateway, TAGS, WIRE
from src.journal.sqlite import Journal
from src.runtime.standalone_web import configure_line_web
from notebook.tests.test_standalone_line import MemoryPLC
from notebook.tests.assembly_result_fixture import assembly_result


class ArrivalTests(unittest.TestCase):
    def test_source_after_sensor_same_camera_complete_box(self):
        p = dict(monotonic_s=11, camera_epoch='e', generation='g', integrity={'valid':True},
            provider={'observations':[{'bbox':dict(x1=.3,y1=.3,x2=.7,y2=.7)}]})
        z = {'polygon_normalized':[[.2,.2],[.8,.2],[.8,.8],[.2,.8]]}
        self.assertTrue(arrival_evidence(p,10,'e','g',z))
        self.assertFalse(arrival_evidence(p,12,'e','g',z))
        self.assertFalse(arrival_evidence(p,10,'other','g',z))
        self.assertFalse(arrival_evidence(p,10,'e','other',z))
        p['provider']['observations'][0]['bbox']['x1'] = .1
        self.assertFalse(arrival_evidence(p,10,'e','g',z))
        p['provider']['observations'] *= 2
        self.assertFalse(arrival_evidence(p,10,'e','g',z))


class FinalBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.journal = Journal(Path(self.temp.name), min_free_bytes=0)
        self.gateway = MemoryPLC()
        self.h = LineHandshake(self.gateway, lambda e: None, session_id=1)
        self.h.service_tick(0, ready=True, product_clear=True)
        self.gateway.values.update(PLC_RunPermit=True, PLC_CycleId=1, Inspection_Request=True)
        self.h.service_tick(1, ready=True, product_clear=False)
        self.r = StandaloneRuntime.__new__(StandaloneRuntime)
        self.r.service = NS(journal=self.journal, generation='g', active=None,
            allocate_request=lambda: dict(cell_id='test',plc_session_id=1,request_id=1,cycle_id=1,attempt=1),
            package=NS(snapshot=lambda:{'manifest':{'product_id':'engine','release_id':'test'}}))
        self.r.handshake, self.r.gateway = self.h, self.gateway
        self.r.session_id, self.r.epoch = 'session', 'camera'
        self.r.published_ids, self.r.history = set(), deque()
        self.r.assembly_submitted = {}
        self.r._event = Mock()
        from notebook.tests.runtime_fixtures import drain_final_commits
        self.storage = drain_final_commits(self.r)
    def tearDown(self):
        self.storage.close()
        self.journal.close(); self.temp.cleanup()
    def test_deadline_no_raw_is_durable_error_then_plc_code_four(self):
        self.r._finish_without_frames('ERROR', 'NO_INSPECTION', 4)
        entry = self.r.history[0]
        row = self.journal.detail(entry['inspection_id'])
        self.assertEqual(row['decision'], 'ERROR')
        self.assertEqual(self.gateway.values['Jetson_ResultCode'], 4)
        self.assertTrue(self.gateway.values['Jetson_Done'])
        self.assertTrue(self.journal.db.execute("SELECT value FROM service_state WHERE key LIKE 'integrated_decision:%'").fetchone())
    def test_required_assembly_blocks_publication_until_ready(self):
        self.h.bind('a'*32)
        self.r.bridge = NS(inspection_id='a'*32,poll=lambda:None,error=None,phase='INSPECTION_DURABLE')
        self.r.service.journal = NS(detail=lambda i: {'decision':'PASS'})
        result = [None]
        self.r.assembly = NS(submit=Mock(), result=lambda i: result[0],evidence_path=lambda i:'evidence')
        self.r.assembly_submitted, self.r.line_profile, self.r.error = {}, {'assembly_deadline_s':30}, None
        self.r._commit_and_publish = Mock()
        self.r._poll_result(4)
        self.r._commit_and_publish.assert_not_called()
        result[0] = assembly_result('FAIL_CANDIDATE')
        self.r._poll_result(5)
        self.assertEqual(self.r._commit_and_publish.call_args.args[1]['decision'], 'PASS')
        self.assertFalse(self.r._commit_and_publish.call_args.args[1]['assembly_affects_final'])
        self.r.assembly.submit.assert_called_once()
    def test_cancellation_blocks_late_assembly_result(self):
        self.h.bind('a'*32)
        self.h.cancelled = True
        self.r.bridge = NS(inspection_id='a'*32)
        self.r._cancel_pending = Mock()
        self.r._commit_and_publish = Mock()
        self.r._poll_result(5)
        self.r._commit_and_publish.assert_not_called()
        self.r._cancel_pending.assert_called_once()
    def test_final_is_committed_before_any_result_write(self):
        request=self.r.service.allocate_request()
        request['runtime_binding']={'plc_request_token':self.h.token}
        identifier,_=self.journal.admit(request,self.r.service.package.snapshot())
        self.journal.finish(identifier,{'decision':'ERROR','reason':'synthetic unit fixture'})
        self.h.bind(identifier)
        write = self.gateway.write
        def check(name, value):
            if name in ('Jetson_ResultCycleId','Jetson_ResultCode','Jetson_Result','Jetson_Done'):
                self.assertIsNotNone(self.journal.db.execute('SELECT value FROM service_state WHERE key=?',
                    ('integrated_decision:'+identifier,)).fetchone())
            return write(name,value)
        self.gateway.write = check
        self.r._commit_and_publish(identifier, {'decision':'ERROR'}, 5)
        with self.assertRaises(sqlite3.IntegrityError):
            self.r._commit_and_publish(identifier, {'decision':'PASS'}, 6)
    def test_notebook_export_unavailable_does_not_block_but_disk_still_gates(self):
        self.journal.outbox_limit = None
        self.journal.capacity()
        self.journal.min_free_bytes = 2**62
        with self.assertRaisesRegex(OSError,'DISK_SPACE_LOW'): self.journal.capacity()


class TransportTests(unittest.TestCase):
    def test_v3_missing_or_wrong_version_never_writes(self):
        g = LineGateway('192.0.2.1','192.0.2.2')
        g.read_tag = lambda name: False if TAGS[name][0]=='BOOL' else 0
        with self.assertRaisesRegex(Exception,'PLC_V3_PROGRAM_NOT_ACTIVE'): g.probe_contract()
        with self.assertRaises(ValueError): g.write('Jetson_Done',True)
    def test_every_read_is_typed_and_only_documented_outputs_writable(self):
        import struct
        g = LineGateway('192.0.2.1','192.0.2.2')
        g.socket = object()
        for kind,(code,fmt,size) in WIRE.items():
            tag = next(k for k,v in TAGS.items() if v[0]==kind and k!='Jetson_ResultCode')
            value = 1 if kind=='BOOL' else 123
            g._message = lambda *args: struct.pack('<H'+fmt,code,value)
            self.assertEqual(g.read_tag(tag),value)
        g._message=lambda *args:b'\x00\x00\x00\x00'
        with self.assertRaisesRegex(Exception,'TYPE_MISMATCH'): g.read_tag('Jetson_ResultCode')


class WebTests(unittest.TestCase):
    def test_get_never_arms_and_all_remote_mutation_is_blocked(self):
        from fastapi import FastAPI
        import asyncio
        app=FastAPI(); touched=[]
        @app.post('/start')
        def start(): touched.append(1)
        configure_line_web(app,NS(),{'mode':'NO_PUSHER_AUTO_INSPECTION'})
        async def request(method, path):
            inbox=asyncio.Queue();await inbox.put({'type':'http.request','body':b'','more_body':False})
            messages=[]
            async def send(value):messages.append(value)
            await app({'type':'http','asgi':{'version':'3.0'},'http_version':'1.1',
                'method':method,'scheme':'http','path':path,'raw_path':path.encode(),
                'query_string':b'','headers':[],'client':('192.0.2.10',1),'server':('192.0.2.2',80)},
                inbox.get,send)
            return next(x['status'] for x in messages if x['type']=='http.response.start')
        self.assertEqual(asyncio.run(request('GET','/line')),200)
        self.assertEqual(asyncio.run(request('GET','/api/v1/release')),200)
        self.assertEqual(asyncio.run(request('POST','/start')),403)
        self.assertEqual(touched,[])


if __name__=='__main__': unittest.main()
