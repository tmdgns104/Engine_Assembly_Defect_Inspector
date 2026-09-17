"""Loopback FastAPI surface. The browser never owns a camera or runs inference."""
import argparse
import json
import secrets
from pathlib import Path
from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from apps.edge_service.inspection import InspectionService
from src.journal.sqlite import ConflictError
from src.recipe.package import PackageError, load_package


def create_app(service, catalog, own_service=False):
    @asynccontextmanager
    async def lifespan(app):
        yield
        if own_service:
            await asyncio.to_thread(service.close)
    app = FastAPI(title='Common Inspection', docs_url=None, redoc_url=None, lifespan=lifespan)
    token = secrets.token_urlsafe(32)

    @app.middleware('http')
    async def protect(request: Request, call_next):
        if request.method not in ('GET','HEAD') and not secrets.compare_digest(request.headers.get('x-inspection-token',''),token):
            return JSONResponse({'error':'SESSION_TOKEN_REQUIRED'},status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; frame-ancestors 'none'"
        return response

    @app.exception_handler(ConflictError)
    async def conflict(request,error): return JSONResponse({'error':str(error)},status_code=409)

    @app.exception_handler(ValueError)
    async def invalid(request,error): return JSONResponse({'error':str(error)},status_code=422)

    @app.exception_handler(OSError)
    async def storage(request,error): return JSONResponse({'error':str(error)},status_code=503)

    @app.get('/',response_class=HTMLResponse)
    def home(): return Path(__file__).with_name('inspection.html').read_text(encoding='utf-8')

    @app.get('/api/v1/session')
    def session(): return {'token':token}

    @app.get('/api/v1/health')
    @app.get('/api/v1/cell/status')
    def status(): return service.status()

    @app.get('/api/v1/preview.jpg')
    def preview():
        if not service.status()['camera_ready']: raise HTTPException(503,'CAMERA_NOT_READY')
        return Response(service.preview['jpeg'],media_type='image/jpeg')

    @app.post('/api/v1/inspection-jobs')
    def inspect(body:dict):
        result,created=service.submit(body)
        return JSONResponse(result,status_code=202 if created else 200)

    @app.post('/api/v1/request-identity')
    def allocate():return service.allocate_request()

    @app.post('/api/v1/mock/{action}')
    def mock(action:str,body:dict):
        with service.lock:
            before=service.mock.state
            if action=='recover':service.mock.recover()
            elif action=='start':
                service.mock.start(False,{})
                service.mock.start(True,body.get('view_assessment'))
            elif action=='finish':service.mock.finish(body.get('disposition'))
            elif action=='cycle-ack':service.mock.acknowledge_cycle()
            else:raise HTTPException(404,'UNKNOWN_MOCK_COMMAND')
            if before!=service.mock.state:
                with service.journal.lock,service.journal.db:
                    service.journal._event('MOCK_STATE_CHANGED',service.mock.status())
            return service.mock.status()

    @app.get('/api/v1/inspection-jobs/{cell}/{session_id}/{request_id}')
    def job_key(cell:str,session_id:int,request_id:int):
        with service.journal.lock:
            row=service.journal.db.execute('SELECT inspection_id FROM inspections WHERE cell_id=? AND plc_session_id=? AND request_id=?',
                                          (cell,session_id,request_id)).fetchone()
        if not row: raise HTTPException(404,'JOB_NOT_FOUND')
        return service.journal.detail(row[0])

    @app.get('/api/v1/inspections')
    def history(product:str=None,decision:str=None,since:str=None,until:str=None,limit:int=30):
        return service.journal.history(product,decision,since,until,limit)

    @app.get('/api/v1/inspections/{identifier}')
    def detail(identifier:str):
        value=service.journal.detail(identifier)
        if not value: raise HTTPException(404,'INSPECTION_NOT_FOUND')
        return value

    @app.post('/api/v1/inspections/{identifier}/cancel')
    def cancel(identifier:str): return service.cancel(identifier)

    @app.post('/api/v1/calibrations/{identifier}/confirm')
    def confirm(identifier:str,body:dict): return service.confirm_calibration(identifier,body.get('confirmed'))

    @app.get('/api/v1/assets/{identifier}')
    def asset(identifier:str):
        value=service.journal.asset(identifier)
        if not value: raise HTTPException(404,'ASSET_NOT_FOUND')
        row,data=value
        return Response(data,media_type='image/png' if row['kind']=='raw' else 'image/jpeg')

    @app.get('/api/v1/metrics')
    def metrics(): return service.journal.metrics()

    @app.get('/api/v1/timings')
    def timings():
        with service.journal.lock:
            rows=service.journal.db.execute("SELECT payload_json FROM events WHERE event_type='INSPECTION_DURABLE_TIMING' ORDER BY occurred_at DESC LIMIT 100").fetchall()
        return [json.loads(row[0])['payload'] for row in rows]

    @app.get('/api/v1/packages')
    def packages():
        items=[]
        for identifier,path in catalog.items():
            try:
                package=load_package(path)
                items.append({'id':identifier,'valid':True,'manifest':package.manifest,'sha256':package.manifest_hash})
            except (ValueError,OSError,KeyError,TypeError) as error:
                items.append({'id':identifier,'valid':False,'reason':str(error)})
        return items

    @app.post('/api/v1/packages/activate')
    def activate(body:dict):
        if body.get('id') not in catalog: raise HTTPException(404,'LOCAL_PACKAGE_NOT_FOUND')
        return service.activate(catalog[body['id']])

    return app


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--package',required=True)
    parser.add_argument('--station',required=True)
    parser.add_argument('--data-root',required=True)
    parser.add_argument('--port',type=int,default=8768)
    parser.add_argument('--collector-url')
    parser.add_argument('--collector-token-file')
    args=parser.parse_args()
    station=json.loads(Path(args.station).read_text(encoding='utf-8'))
    package=Path(args.package).resolve()
    products=package.parent.parent
    catalog={path.parent.relative_to(products).as_posix():path.parent for path in products.glob('*/*/manifest.json')}
    service=InspectionService(package,station,args.data_root)
    if args.collector_url:
        from src.journal.sync import OutboxSender
        token=Path(args.collector_token_file).read_text(encoding='utf-8').strip()
        if len(token)<32:raise ValueError('Strong collector token required')
        service.sender=OutboxSender(service.journal,args.collector_url,token)
        service.sender.start()
    import uvicorn
    try:
        uvicorn.run(create_app(service,catalog,own_service=True),host='127.0.0.1',port=args.port,log_level='info')
    finally:
        service.close()


if __name__=='__main__': main()
