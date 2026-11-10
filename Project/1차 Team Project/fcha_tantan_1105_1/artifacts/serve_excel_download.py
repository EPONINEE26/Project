from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FILE = Path(__file__).resolve().parent / 'community_work_20261105_final.xlsx'
ROUTE = '/' + FILE.name


class DownloadHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_file(False)

    def do_HEAD(self):
        self.send_file(True)

    def send_file(self, head_only):
        if self.path.split('?', 1)[0] != ROUTE:
            self.send_error(404)
            return
        data = FILE.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.send_header('Content-Disposition', f'attachment; filename="{FILE.name}"')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        if not head_only:
            self.wfile.write(data)


if __name__ == '__main__':
    if not FILE.is_file():
        raise SystemExit('Excel file missing')
    server = ThreadingHTTPServer(('127.0.0.1', 8877), DownloadHandler)
    print('DOWNLOAD http://127.0.0.1:8877' + ROUTE, flush=True)
    server.serve_forever()
