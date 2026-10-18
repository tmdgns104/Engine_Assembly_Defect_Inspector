"""Dependency-free, in-process ASGI requests; no sockets or external services."""
import asyncio
import json
from types import SimpleNamespace
from urllib.parse import urlsplit

class LocalAsgiClient:
    def __init__(self,app):self.app=app
    def __enter__(self):return self
    def __exit__(self,*unused):pass
    def get(self,path,**kwargs):return self.request('GET',path,**kwargs)
    def post(self,path,**kwargs):return self.request('POST',path,**kwargs)
    def request(self,method,path,*,json=None,content=None,headers=None,follow_redirects=False):
        import json as codec
        data=codec.dumps(json).encode() if json is not None else (content or '').encode()
        fields={'host':'testserver','content-length':str(len(data)),**{k.lower():v for k,v in (headers or {}).items()}}
        async def call():
            url=urlsplit(path)
            delivered=False;done=asyncio.Event();messages=[]
            async def receive():
                nonlocal delivered
                if not delivered:
                    delivered=True
                    return {'type':'http.request','body':data,'more_body':False}
                await done.wait()
                return {'type':'http.disconnect'}
            async def send(message):
                messages.append(message)
                if message['type']=='http.response.body' and not message.get('more_body'):done.set()
            scope=dict(type='http',asgi={'version':'3.0'},http_version='1.1',method=method,scheme='http',
                path=url.path,raw_path=url.path.encode(),query_string=url.query.encode(),root_path='',
                headers=[(k.encode(),v.encode()) for k,v in fields.items()],client=('127.0.0.1',1234),server=('testserver',80))
            await self.app(scope,receive,send)
            start=next(m for m in messages if m['type']=='http.response.start')
            return SimpleNamespace(status_code=start['status'],headers={k.decode():v.decode() for k,v in start['headers']},
                text=b''.join(m['body'] for m in messages if m['type']=='http.response.body').decode())
        return asyncio.run(call())
