import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'jetson'))
from src.journal.sqlite import Journal
from src.journal.history import HistoryReader,csv_text


class HistoryReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.journal=Journal(self.temp.name,min_free_bytes=1)
        self.reader=HistoryReader(self.temp.name)
        self.ids=[]
        for i,(decision,kind) in enumerate([('PASS','inspect'),('FAIL','inspect'),('ERROR','inspect'),('REVIEW','calibrate')],1):
            request=dict(cell_id='fixture',plc_session_id=1,request_id=i,cycle_id=i,attempt=1,kind=kind)
            identifier,_=self.journal.admit(request,{'manifest':{'product_id':'ENGINE_FIXTURE','model_version':'fixture'}})
            self.ids.append(identifier)
            result={'decision':decision,'reason_code':'=UNTRUSTED' if i==3 else decision+'_REASON','storage_success':True,'assets':[]}
            # Fixture rows exercise history only; they are never counted as field inspections.
            self.journal.db.execute("UPDATE inspections SET state='COMPLETE',decision=?,result_json=?,accepted_at=?,completed_at=? WHERE inspection_id=?",(decision,json.dumps(result),f'2026-10-18T00:00:0{i}+00:00',f'2026-10-18T00:00:1{i}+00:00',identifier))
        self.journal.db.commit()
    def tearDown(self):
        self.journal.db.close();self.temp.cleanup()
    def test_filters_counts_pagination_and_original_decisions(self):
        page=self.reader.search(limit=2)
        self.assertEqual(page['total'],4)
        self.assertEqual(page['items'][0]['decision'],'REVIEW')
        self.assertEqual(self.reader.search(limit=2,offset=2)['items'][0]['decision'],'FAIL')
        self.assertEqual(self.reader.search(kind='inspect')['total'],3)
        self.assertEqual(self.reader.search(decision='ERROR')['items'][0]['inspection_id'],self.ids[2])
        self.assertEqual(self.reader.search(q=self.ids[1])['total'],1)
        self.assertEqual(self.reader.search(q="%' OR 1=1 --")['total'],0)
        self.assertEqual(self.reader.search(product='absent')['total'],0)
    def test_dates_timezone_and_boundaries(self):
        self.assertEqual(self.reader.search(since='2026-10-18T09:00:02+09:00',until='2026-10-18T09:00:04+09:00')['total'],2)
        for value in ('bad','2026-10-18T00:00:00'):
            with self.assertRaises(ValueError):self.reader.search(since=value)
        with self.assertRaises(ValueError):self.reader.search(since='2026-10-19T00:00:00Z',until='2026-10-18T00:00:00Z')
    def test_read_only_independent_of_writer_lock(self):
        with self.reader.connection() as connection:
            with self.assertRaises(sqlite3.OperationalError):connection.execute('DELETE FROM inspections')
        with patch.object(self.journal,'lock',None):self.assertEqual(self.reader.search()['total'],4)
    def test_detail_and_invalid_limits(self):
        self.assertEqual(self.reader.detail(self.ids[2])['result']['decision'],'ERROR')
        self.assertIsNone(self.reader.detail('0'*32))
        for options in ({'limit':-1},{'offset':-1},{'decision':'FAKE'},{'q':'x'*129}):
            with self.assertRaises(ValueError):self.reader.search(**options)
    def test_csv_keeps_original_state_and_blocks_formulas(self):
        exported=csv_text(self.reader.search()['items'])
        self.assertIn("'=UNTRUSTED",exported)
        self.assertIn('ERROR',exported)
        self.assertEqual(self.reader.detail(self.ids[2])['result']['reason_code'],'=UNTRUSTED')


if __name__=='__main__':unittest.main()
