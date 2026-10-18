"""검사 이력 전용 읽기 연결. 운영 Journal 쓰기 lock/연결을 공유하지 않는다."""
import csv
import io
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import time
from src import config


def date_bound(value):
    if not value:
        return None
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    except (ValueError,AttributeError):
        raise ValueError('날짜 형식을 확인해 주세요.') from None
    if parsed.tzinfo is None:
        raise ValueError('검색 시각에는 시간대가 필요합니다.')
    return parsed.astimezone(timezone.utc).isoformat()


class HistoryReader:
    def __init__(self, data_root):
        self.path=Path(data_root).resolve()/'journal.sqlite3'

    @contextmanager
    def connection(self):
        deadline=time.monotonic()+config.HISTORY_QUERY_TIMEOUT_SECONDS
        db=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True,timeout=.05)
        try:
            db.row_factory=sqlite3.Row
            db.execute('PRAGMA query_only=ON')
            db.set_progress_handler(lambda:int(time.monotonic()>deadline),1000)
            yield db
        finally:
            db.close()

    def filters(self, *, q='', product='', decision='', state='', kind='', since='', until=''):
        if len(q)>128 or len(product)>100:
            raise ValueError('검색어가 너무 깁니다.')
        if decision not in ('','PASS','FAIL','REVIEW','ERROR') or state not in ('','ACCEPTED','COMPLETE','CANCELLED') or kind not in ('','inspect','calibrate'):
            raise ValueError('지원하지 않는 검색 조건입니다.')
        since,until=date_bound(since),date_bound(until)
        if since and until and since>=until:
            raise ValueError('시작 시각은 종료 시각보다 빨라야 합니다.')
        clauses=[];args=[]
        for expression,value in (("json_extract(i.package_json,'$.manifest.product_id')",product),
                ('i.decision',decision),('i.state',state),("json_extract(i.request_json,'$.kind')",kind)):
            if value:clauses.append(expression+'=?');args.append(value)
        if since:clauses.append('i.accepted_at>=?');args.append(since)
        if until:clauses.append('i.accepted_at<?');args.append(until)
        if q:
            escaped=q.replace('!','!!').replace('%','!%').replace('_','!_')
            clauses.append("(i.inspection_id LIKE ? ESCAPE '!' OR i.cell_id LIKE ? ESCAPE '!' OR json_extract(i.result_json,'$.reason_code') LIKE ? ESCAPE '!' OR CAST(i.request_id AS TEXT)=?)")
            args.extend(['%'+escaped+'%']*3+[q])
        return (' WHERE '+' AND '.join(clauses) if clauses else ''),args

    def search(self, *, limit=config.HISTORY_DEFAULT_LIMIT, offset=0, **filters):
        if type(limit) is not int or not 1<=limit<=config.HISTORY_EXPORT_LIMIT or type(offset) is not int or not 0<=offset<=100000:
            raise ValueError('조회 범위를 확인해 주세요.')
        where,args=self.filters(**filters)
        with self.connection() as db:
            # Count and rows belong to one short read snapshot even if a new inspection commits.
            db.execute('BEGIN')
            counts=db.execute('SELECT i.decision,COUNT(*) AS n FROM inspections i'+where+' GROUP BY i.decision',args).fetchall()
            rows=db.execute("""SELECT i.inspection_id,i.request_id,i.cell_id,i.state,i.decision,
                i.accepted_at,i.completed_at,
                json_extract(i.package_json,'$.manifest.product_id') AS product,
                json_extract(i.package_json,'$.manifest.model_version') AS model_version,
                json_extract(i.request_json,'$.kind') AS kind,
                json_extract(i.result_json,'$.reason_code') AS reason,
                json_extract(i.result_json,'$.storage_success') AS storage_success,
                json_extract(s.value,'$.decision') AS final_decision,
                json_extract(s.value,'$.plc_result_value') AS plc_result
                FROM inspections i LEFT JOIN service_state s ON s.key='integrated_decision:'||i.inspection_id"""
                +where+' ORDER BY i.accepted_at DESC,i.inspection_id DESC LIMIT ? OFFSET ?',[*args,limit,offset]).fetchall()
        summary={row['decision'] or 'PENDING':row['n'] for row in counts}
        return {'items':[dict(row) for row in rows],'total':sum(summary.values()),'counts':summary,
                'limit':limit,'offset':offset,'scope':'SAVED_JOURNAL_NOT_LIVE_CONTROL'}

    def detail(self, identifier):
        if len(identifier)!=32 or any(c not in '0123456789abcdef' for c in identifier):
            raise ValueError('검사 ID 형식을 확인해 주세요.')
        with self.connection() as db:
            db.execute('BEGIN')
            row=db.execute('SELECT * FROM inspections WHERE inspection_id=?',(identifier,)).fetchone()
            if row is None:return None
            item=dict(row)
            for key in ('request_json','package_json','result_json'):
                raw=item.pop(key);item[key.removesuffix('_json')]=json.loads(raw) if raw else None
            for key,name in (('integrated_decision:','integrated_result'),('production_publication:','publication')):
                stored=db.execute('SELECT value FROM service_state WHERE key=?',(key+identifier,)).fetchone()
                item[name]=json.loads(stored[0]) if stored else None
            item['dispositions']=[dict(r) for r in db.execute('SELECT disposition,actor,reason,occurred_at FROM dispositions WHERE inspection_id=? ORDER BY occurred_at',(identifier,))]
        return item


def csv_text(rows):
    """Excel 수식으로 해석될 수 있는 텍스트는 값 자체를 바꾸지 않는 CSV 표시용 보호."""
    output=io.StringIO(newline='')
    fields=('inspection_id','accepted_at','product','model_version','kind','state','decision','final_decision','plc_result','reason','storage_success')
    writer=csv.DictWriter(output,fieldnames=fields);writer.writeheader()
    for row in rows:
        safe={}
        for key in fields:
            value=row.get(key)
            if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')):value="'"+value
            safe[key]=value
        writer.writerow(safe)
    return '\ufeff'+output.getvalue()
