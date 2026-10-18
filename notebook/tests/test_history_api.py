"""실제 앱 라우팅·검색·내보내기. 카메라/PLC 없는 합성 Journal만 사용한다."""
import json
from html.parser import HTMLParser
from types import SimpleNamespace
from unittest.mock import patch
from apps.edge_service.inspection_api import create_app
from notebook.tests.supervised_asgi_fixture import LocalAsgiClient
from notebook.tests.test_history_reader import HistoryReaderTests
from src import config


class HistoryApiTests(HistoryReaderTests):
    def setUp(self):
        super().setUp()
        self.app=create_app(SimpleNamespace(journal=self.journal),{})

    def test_pages_query_detail_and_no_mutation_route(self):
        with LocalAsgiClient(self.app) as client:
            for path in ('/history','/history.js','/operator.css'):
                response=client.get(path)
                self.assertEqual(response.status_code,200)
            response=client.get('/api/v1/history?decision=ERROR')
            self.assertEqual(response.status_code,200)
            self.assertEqual(json.loads(response.text)['total'],1)
            detail=client.get('/api/v1/history/'+self.ids[2])
            self.assertEqual(json.loads(detail.text)['result']['decision'],'ERROR')
            self.assertEqual(client.get('/api/v1/history/'+'0'*32).status_code,404)
            for query in ('limit=1001','limit=-1','decision=INVALID','since=bad','offset=-1'):
                self.assertEqual(client.get('/api/v1/history?'+query).status_code,422)
            self.assertEqual(client.post('/api/v1/history',json={}).status_code,403)
            token=json.loads(client.get('/api/v1/session').text)['token']
            self.assertEqual(client.post('/api/v1/history',json={},headers={'x-inspection-token':token}).status_code,405)
            self.assertEqual(self.reader.search()['total'],4)

    def test_csv_route_and_active_snapshot(self):
        with LocalAsgiClient(self.app) as client:
            response=client.get('/api/v1/history/export.csv?decision=ERROR')
            self.assertEqual(response.status_code,200)
            self.assertIn("'=UNTRUSTED",response.text)
            captured=json.loads(client.get('/api/v1/configuration').text)
            with patch.object(config,'ENGINE_PART_CONFIDENCE',.55):
                self.assertEqual(json.loads(client.get('/api/v1/configuration').text),captured)
            with patch.object(config,'HISTORY_EXPORT_LIMIT',2):
                self.assertEqual(client.get('/api/v1/history/export.csv').status_code,422)

    def test_filter_options_are_real_html_options(self):
        class Options(HTMLParser):
            def __init__(self):super().__init__();self.values=[]
            def handle_starttag(self,tag,attributes):
                if tag=='option':self.values.append(dict(attributes).get('value'))
        with LocalAsgiClient(self.app) as client:
            parser=Options();parser.feed(client.get('/history').text)
        self.assertTrue({'PASS','FAIL','REVIEW','ERROR','COMPLETE','ACCEPTED','CANCELLED','inspect','calibrate'}.issubset(parser.values))
