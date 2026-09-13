import copy,json,tempfile,unittest
from pathlib import Path
from fastapi.testclient import TestClient
from src.journal.sqlite import Journal,ConflictError
from src.journal.collector import Collector
from src.journal.sync import OutboxSender
from apps.pc_service.collector_api import create_app


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.edge=Journal(root/'edge',min_free_bytes=0);self.addCleanup(self.edge.close)
        self.pc=Collector(root/'pc');self.addCleanup(self.pc.journal.close)
        request={'cell_id':'mock','plc_session_id':1,'request_id':1,'cycle_id':1,'attempt':1}
        identifier,_=self.edge.admit(request,{'manifest':{'product_id':'fixture'}})
        self.result=self.edge.finish(identifier,{'decision':'REVIEW','reason':'fixture','defects':[]},
            [{'kind':'raw','data':b'fixture PNG','width':2,'height':2}])
        self.event=json.loads(self.edge.db.execute('SELECT payload_json FROM events').fetchone()[0])

    def test_event_ack_is_not_asset_ack_and_duplicates_do_not_count(self):
        ack=self.pc.receive_event(self.event);self.assertFalse(ack['asset_ack'])
        self.assertEqual(self.pc.status()['pending_assets'],1)
        self.assertTrue(self.pc.receive_event(self.event)['duplicate'])
        asset=self.result['assets'][0]
        for _ in range(2):self.pc.receive_asset(asset['asset_id'],b'fixture PNG')
        self.assertEqual(self.pc.status()['pending_assets'],0)
        self.assertEqual(self.pc.status()['metrics']['attempts'],1)
        self.assertEqual(self.pc.status()['metrics']['cycles'],1)
        self.assertEqual(self.pc.status()['metrics']['released'],0)

    def test_changed_event_or_image_quarantined(self):
        self.pc.receive_event(self.event)
        altered=copy.deepcopy(self.event);altered['payload']['decision']='PASS'
        with self.assertRaises(ConflictError):self.pc.receive_event(altered)
        with self.assertRaises(ConflictError):self.pc.receive_asset(self.result['assets'][0]['asset_id'],b'corruption')
        self.assertEqual(self.pc.journal.db.execute('SELECT count(*) FROM quarantine').fetchone()[0],2)
        self.assertEqual(self.pc.journal.detail(self.result['inspection_id'])['decision'],'REVIEW')

    def test_outage_lost_json_ack_and_recovery(self):
        sender=OutboxSender(self.edge,'http://127.0.0.1:9999','test-token')
        def offline(*args):raise OSError('PC_OFFLINE')
        sender.post=offline
        with self.assertRaises(OSError):sender.once()
        self.assertEqual(self.edge.db.execute('SELECT state FROM outbox').fetchone()[0],'PENDING')
        self.pc.receive_event(self.event) # PC committed, network lost the ACK.
        def deliver(path,data,content):
            if path.endswith('/events'):return self.pc.receive_event(json.loads(data))
            return self.pc.receive_asset(path.rsplit('/',1)[1],data)
        sender.post=deliver;sender.once();sender.once()
        self.assertEqual(self.pc.status()['metrics']['attempts'],1)
        self.assertEqual(self.edge.db.execute('SELECT state FROM outbox').fetchone()[0],'ACKED')
        self.assertEqual(self.edge.db.execute('SELECT sync_state FROM frame_assets').fetchone()[0],'ACKED')

    def test_http_token_and_asset_pending(self):
        with TestClient(create_app(self.pc,'test-token')) as client:
            self.assertEqual(client.post('/internal/v1/events',json=self.event).status_code,403)
            headers={'X-Collector-Token':'test-token'}
            self.assertEqual(client.post('/internal/v1/events',json=self.event,headers=headers).status_code,200)
            self.assertEqual(client.get('/api/v1/status').json()['pending_assets'],1)
            asset=self.result['assets'][0]['asset_id']
            self.assertEqual(client.post('/internal/v1/assets/'+asset,content=b'fixture PNG',headers=headers).status_code,200)
            self.assertEqual(client.get('/api/v1/assets/'+asset).content,b'fixture PNG')


if __name__=='__main__':unittest.main()
