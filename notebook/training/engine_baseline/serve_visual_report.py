"""Loopback-only, read-only report preview; raw access is restricted to candidates."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from prepare_alignment import read_rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('run');parser.add_argument('--port',type=int,default=17721);args=parser.parse_args()
    run=Path(args.run).resolve()
    raw={r['display_index']:Path(r['raw_image_path']) for r in read_rows(run/'export_validation_candidates.jsonl')}
    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith('/__raw/'):
                path=raw.get(self.path.removeprefix('/__raw/'))
                if path is None:self.send_error(404);return
                payload=path.read_bytes();self.send_response(200)
                self.send_header('Content-Type','image/png');self.send_header('Content-Length',str(len(payload)))
                self.end_headers();self.wfile.write(payload);return
            super().do_GET()
        def list_directory(self,path):
            self.send_error(404);return None
    ThreadingHTTPServer(('127.0.0.1',args.port),partial(Handler,directory=str(run))).serve_forever()


if __name__=='__main__':main()
