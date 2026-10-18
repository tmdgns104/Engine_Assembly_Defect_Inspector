"""기존 앱에 검사 기록 페이지/검색/CSV를 연결한다. 읽기 전용이다."""
from pathlib import Path
import sqlite3
from fastapi import HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from src import config
from src.configuration import snapshot
from src.journal.history import HistoryReader,csv_text


def install_history(app, service):
    active_settings=getattr(service,'configuration',None) or snapshot()

    @app.get('/history',response_class=HTMLResponse)
    def page():return Path(__file__).with_name('history.html').read_text(encoding='utf-8')

    @app.get('/history.js')
    def script():return Response(Path(__file__).with_name('history.js').read_text(encoding='utf-8'),media_type='application/javascript')

    @app.get('/operator.css')
    def stylesheet():return Response(Path(__file__).with_name('operator.css').read_text(encoding='utf-8'),media_type='text/css')

    @app.get('/api/v1/configuration')
    def configuration():
        return active_settings  # import 시점 실행값. 파일을 다시 읽거나 장치를 재설정하지 않는다.

    def query(**arguments):
        try:return HistoryReader(service.journal.root).search(**arguments)
        except sqlite3.Error:
            raise HTTPException(503,'이력 조회가 지연되고 있습니다. 기간을 줄여 다시 조회해 주세요.') from None

    @app.get('/api/v1/history')
    def search(q:str='',product:str='',decision:str='',state:str='',kind:str='',since:str='',until:str='',
               limit:int=Query(config.HISTORY_DEFAULT_LIMIT,ge=1,le=config.HISTORY_MAX_PAGE_SIZE),offset:int=Query(0,ge=0,le=100000)):
        return query(q=q,product=product,decision=decision,state=state,kind=kind,since=since,until=until,limit=limit,offset=offset)

    @app.get('/api/v1/history/export.csv')
    def export(q:str='',product:str='',decision:str='',state:str='',kind:str='',since:str='',until:str=''):
        data=query(q=q,product=product,decision=decision,state=state,kind=kind,since=since,until=until,limit=config.HISTORY_EXPORT_LIMIT)
        if data['total']>config.HISTORY_EXPORT_LIMIT:
            raise HTTPException(422,'내보내기 상한을 초과했습니다. 검색 기간을 줄여 주세요.')
        return Response(csv_text(data['items']),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="inspection-history.csv"'})

    @app.get('/api/v1/history/{identifier}')
    def detail(identifier:str):
        try:value=HistoryReader(service.journal.root).detail(identifier)
        except sqlite3.Error:raise HTTPException(503,'기록을 읽을 수 없습니다. 잠시 후 다시 시도해 주세요.') from None
        if value is None:raise HTTPException(404,'검사 기록이 없습니다.')
        return value
