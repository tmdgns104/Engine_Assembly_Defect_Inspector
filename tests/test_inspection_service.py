"""Real spawned-process supervision; fake camera/model explicitly marked as mock."""
import queue
import tempfile
import time
import unittest
from pathlib import Path

from apps.edge_service.inspection import InspectionService
from src.journal.sqlite import ConflictError
from test_product_package import write_package


def fake_worker(package_root, station, generation, commands, results, previews, stopping, cancellation, heartbeat):
    from src.recipe.package import load_package
    package = load_package(package_root)
    if package.manifest['release_id'] == 'broken':
        results.put({'type':'fault','generation':generation,'error':'SELF_TEST_FAILED'})
        return
    results.put({'type':'ready','generation':generation,'backend':{'backend':'mock','device':'mock'}})
    while not stopping.wait(.02):
        heartbeat.value = time.monotonic()
        try:
            previews.put_nowait({'generation':generation,'jpeg':b'mock','freshness':{}})
        except queue.Full:
            pass
        try:
            job = commands.get_nowait()
        except queue.Empty:
            continue
        # Delayed inference does not block Service status or cancellation.
        time.sleep(.25)
        results.put({'type':'result','generation':generation,'inspection_id':job['inspection_id'],
            'result':{'decision':'REVIEW','reason':'MOCK','defects':[]},
            'images':[{'kind':'raw','data':b'mock png','width':1,'height':1}]})


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        write_package(self.root/'package')
        station = {'station_id':'mock-station','cell_id':'mock-cell','inspection_timeout_seconds':2,'startup_timeout_seconds':5}
        self.service = InspectionService(self.root/'package',station,self.root/'data',fake_worker)
        self.wait_for(lambda:self.service.status()['camera_ready'])

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    def wait_for(self, predicate):
        deadline = time.monotonic()+7
        while not predicate() and time.monotonic()<deadline:
            time.sleep(.03)
        self.assertTrue(predicate())

    def request(self, identifier=1):
        return {'cell_id':'mock-cell','plc_session_id':self.service.session,'request_id':identifier,
            'cycle_id':identifier,'attempt':1,'kind':'calibrate',
            'view_assessment':{'product_identity':'human_confirmed','alignment_confirmed':True,
                               'visible_slots':{'first':True,'second':True},'basis':'synthetic fixture'},
            'package_sha256':self.service.package.manifest_hash}

    def test_idempotent_busy_and_durable_result(self):
        request=self.request()
        first,created=self.service.submit(request)
        self.assertTrue(created)
        duplicate,created=self.service.submit(request)
        self.assertFalse(created)
        self.assertEqual(first['inspection_id'],duplicate['inspection_id'])
        with self.assertRaises(ConflictError): self.service.submit(self.request(2))
        start=time.monotonic()
        self.assertTrue(self.service.status()['worker_alive'])
        self.assertLess(time.monotonic()-start,.15)
        self.wait_for(lambda:self.service.journal.detail(first['inspection_id'])['state']=='COMPLETE')
        result=self.service.journal.detail(first['inspection_id'])['result']
        self.assertTrue(result['storage_success'])
        self.assertIsNotNone(self.service.journal.asset(result['assets'][0]['asset_id']))

    def test_cancel_never_publishes_late_result(self):
        job,_=self.service.submit(self.request())
        self.service.cancel(job['inspection_id'])
        with self.assertRaises(ConflictError): self.service.submit(self.request(2))
        self.wait_for(lambda:self.service.state=='IDLE')
        result=self.service.journal.detail(job['inspection_id'])
        self.assertEqual(result['state'],'CANCELLED')
        self.assertEqual(result['decision'],'ERROR')

    def test_dead_worker_requires_recovery_and_new_session(self):
        session=self.service.session
        self.service.process.terminate()
        self.service.process.join()
        self.wait_for(lambda:self.service.state=='RECOVERY')
        self.assertFalse(self.service.status()['ready'])
        self.assertTrue(self.service.activate(self.root/'package')['activated'])
        self.assertGreater(self.service.session,session)

    def test_failed_package_restores_previous_worker(self):
        import json
        write_package(self.root/'broken')
        path=self.root/'broken'/'manifest.json'
        value=json.loads(path.read_text());value['release_id']='broken'
        path.write_text(json.dumps(value))
        original=self.service.package.manifest_hash
        result=self.service.activate(self.root/'broken')
        self.assertFalse(result['activated'])
        self.assertTrue(result['previous_restored'])
        self.assertEqual(self.service.package.manifest_hash,original)


if __name__=='__main__': unittest.main()
