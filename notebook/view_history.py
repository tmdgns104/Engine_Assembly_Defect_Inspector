r"""노트북에서 SQLite 보관본을 읽기 전용으로 조회한다. 장비 제어 API는 없다.

예: .venv\Scripts\python.exe -B -X utf8 notebook/view_history.py --data-root database/snapshots/20261018
"""
import argparse
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'jetson'))
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from apps.edge_service.history_api import install_history


def create_viewer(data_root):
    root = Path(data_root).resolve()
    if not (root/'journal.sqlite3').is_file():
        raise FileNotFoundError('journal.sqlite3 파일이 있는 폴더를 지정하세요.')
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    install_history(app, SimpleNamespace(journal=SimpleNamespace(root=root)))

    @app.middleware('http')
    async def read_only(request: Request, call_next):
        if request.method not in ('GET', 'HEAD'):
            return JSONResponse({'error':'READ_ONLY_DATABASE_COPY'}, status_code=405)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; frame-ancestors 'none'"
        return response

    @app.exception_handler(ValueError)
    async def invalid(request, error):
        return JSONResponse({'error':str(error)}, status_code=422)

    # 기존 템플릿에 사본임을 분명히 표시. 운영 Jetson 화면과 혼동하지 않는다.
    route = next(route for route in app.routes if route.path == '/history')
    app.routes.remove(route)

    @app.get('/history', response_class=HTMLResponse)
    def page():
        text = (ROOT/'jetson/apps/edge_service/history.html').read_text(encoding='utf-8')
        return text.replace('<body><main>', '<body><main><p class="notice">노트북 SQLite 보관본 · 읽기 전용 · 실시간 장치 상태가 아닙니다.</p>')

    @app.get('/')
    def home():
        return RedirectResponse('/history')

    @app.get('/line', response_class=HTMLResponse)
    def unavailable():
        return '<html lang="ko"><meta charset="utf-8"><p>이 서버는 SQLite 보관본 조회 전용입니다. 실제 현장 화면은 Jetson 서비스에 접속하세요.</p><a href="/history">검사 기록으로 돌아가기</a></html>'

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', required=True, type=Path)
    parser.add_argument('--port', type=int, default=18773)
    args = parser.parse_args()
    import uvicorn
    uvicorn.run(create_viewer(args.data_root), host='127.0.0.1', port=args.port, access_log=False)


if __name__ == '__main__':
    main()
