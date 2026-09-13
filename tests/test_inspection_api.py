import unittest
from fastapi.testclient import TestClient
import test_inspection_service
from apps.edge_service.inspection_api import create_app


class ApiTests(unittest.TestCase):
    setUp=test_inspection_service.ServiceTests.setUp
    tearDown=test_inspection_service.ServiceTests.tearDown
    wait_for=test_inspection_service.ServiceTests.wait_for
    request=test_inspection_service.ServiceTests.request
    def test_lifespan_stops_camera_process_before_server_exits(self):
        worker=self.service.process
        with TestClient(create_app(self.service,{},own_service=True)) as client:
            self.assertTrue(client.get('/api/v1/health').json()['worker_alive'])
        self.assertFalse(worker.is_alive())
        self.assertTrue(self.service.close_complete)
    def test_api_storage_history_and_protected_mutations(self):
        with TestClient(create_app(self.service,{'fixture':self.root/'package'})) as client:
            self.assertEqual(client.post('/api/v1/inspection-jobs',json=self.request()).status_code,403)
            token=client.get('/api/v1/session').json()['token']
            headers={'X-Inspection-Token':token}
            response=client.post('/api/v1/inspection-jobs',json=self.request(),headers=headers)
            self.assertEqual(response.status_code,202)
            identifier=response.json()['inspection_id']
            self.assertEqual(client.post('/api/v1/inspection-jobs',json=self.request(),headers=headers).status_code,200)
            self.wait_for(lambda:self.service.journal.detail(identifier)['state']=='COMPLETE')
            row=client.get('/api/v1/inspections/'+identifier).json()
            self.assertEqual(row['decision'],'REVIEW')
            self.assertEqual(len(client.get('/api/v1/inspections?decision=REVIEW').json()),1)
            asset=row['result']['assets'][0]['asset_id']
            self.assertEqual(client.get('/api/v1/assets/'+asset).content,b'mock png')
            self.assertEqual(client.get('/api/v1/assets/notfound').status_code,404)
            self.assertIn('현재 미리보기',client.get('/').text)
            self.assertTrue(client.get('/api/v1/packages').json()[0]['valid'])


if __name__=='__main__':unittest.main()
