"""Read-only loopback viewer; only the two explicit experiment roots are served."""
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote,urlsplit
from fit_train import OUTPUT
from investigate import BASELINE,PROJECT
from prepare_alignment import read_rows

RAW={r['display_index']:Path(r['raw_image_path']).resolve() for r in read_rows(BASELINE/'export_validation_candidates.jsonl')}
ROOT=PROJECT/'runs'


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self,path):
        request=unquote(urlsplit(path).path)
        if request.startswith('/__raw/'):
            return str(RAW.get(request.rsplit('/',1)[-1],OUTPUT/'DOES_NOT_EXIST'))
        resolved=(ROOT/request.lstrip('/')).resolve()
        if not any(resolved.is_relative_to(root) for root in [BASELINE,OUTPUT]):return str(OUTPUT/'DOES_NOT_EXIST')
        return str(resolved)

    def list_directory(self,path):
        self.send_error(403,'Directory listing disabled')
        return None


if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',17722),Handler)
    print('READ ONLY http://127.0.0.1:17722/'+(OUTPUT/'visual_report_v001/REPORT.html').relative_to(ROOT).as_posix(),flush=True)
    server.serve_forever()
