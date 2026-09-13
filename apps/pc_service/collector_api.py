"""Local PC record collection and read-only HMI. No PLC or inference ownership."""
import argparse
import json
import secrets
from pathlib import Path
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import HTMLResponse,JSONResponse,Response
from src.journal.collector import Collector
from src.journal.sqlite import ConflictError


def create_app(collector,token):
    app=FastAPI(title='Inspection PC records',docs_url=None,redoc_url=None)
    @app.middleware('http')
    async def protect(request:Request,call_next):
        if request.url.path.startswith('/internal/') and not secrets.compare_digest(request.headers.get('x-collector-token',''),token):
            return JSONResponse({'error':'COLLECTOR_AUTH_REQUIRED'},status_code=403)
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        return response
    @app.exception_handler(ConflictError)
    async def conflict(request,error):return JSONResponse({'error':str(error)},status_code=409)
    @app.exception_handler(ValueError)
    async def invalid(request,error):return JSONResponse({'error':str(error)},status_code=422)
    @app.exception_handler(KeyError)
    async def missing(request,error):return JSONResponse({'error':str(error)},status_code=404)
    @app.exception_handler(OSError)
    async def storage(request,error):return JSONResponse({'error':str(error)},status_code=503)
    async def bounded_body(request,limit):
        chunks=[];size=0
        async for chunk in request.stream():
            size+=len(chunk)
            if size>limit:raise HTTPException(413,'BODY_TOO_LARGE')
            chunks.append(chunk)
        return b''.join(chunks)
    @app.post('/internal/v1/events')
    async def event(request:Request):return collector.receive_event(json.loads(await bounded_body(request,8_000_000)))
    @app.post('/internal/v1/assets/{identifier}')
    async def receive_asset(identifier:str,request:Request):return collector.receive_asset(identifier,await bounded_body(request,20_000_000))
    @app.get('/api/v1/status')
    def status():return collector.status()
    @app.get('/api/v1/inspections')
    def history(product:str=None,decision:str=None,since:str=None,until:str=None):return collector.journal.history(product,decision,since,until)
    @app.get('/api/v1/inspections/{identifier}')
    def detail(identifier:str):
        row=collector.journal.detail(identifier)
        if not row:raise HTTPException(404)
        with collector.journal.lock:
            row['asset_sync']=dict(collector.journal.db.execute('SELECT asset_id,sync_state FROM frame_assets WHERE inspection_id=?',(identifier,)))
        return row
    @app.get('/api/v1/assets/{identifier}')
    def asset(identifier:str):
        result=collector.journal.asset(identifier)
        if not result:raise HTTPException(404)
        row,data=result
        return Response(data,media_type='image/png' if row['kind']=='raw' else 'image/jpeg')
    @app.get('/',response_class=HTMLResponse)
    def home():return Path(__file__).with_name('collector.html').read_text(encoding='utf-8')
    return app


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data-root',required=True);parser.add_argument('--token-file',required=True)
    parser.add_argument('--port',type=int,default=8769)
    args=parser.parse_args()
    token=Path(args.token_file).read_text(encoding='utf-8').strip()
    if len(token)<32:raise ValueError('Strong collector token required')
    collector=Collector(args.data_root)
    import uvicorn
    try:uvicorn.run(create_app(collector,token),host='127.0.0.1',port=args.port)
    finally:collector.journal.close()


if __name__=='__main__':main()
