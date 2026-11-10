"""HTTP handler checks without opening sockets or launching a browser."""
import io
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from serve import Handler


class Request:
    def __init__(self, path):
        self.source = io.BytesIO(f'GET {path} HTTP/1.0\r\nHost: localhost\r\n\r\n'.encode())
        self.output = bytearray()

    def makefile(self, *args, **kwargs):
        return self.source

    def sendall(self, data):
        self.output.extend(data)


for path in ['/', '/assets/app.css', '/assets/app.js', '/assets/core.js', '/assets/config.js']:
    request = Request(path)
    Handler(request, ('127.0.0.1', 12345), object(), directory=str(ROOT))
    response = bytes(request.output)
    assert response.startswith(b'HTTP/1.0 200'), path
    assert b'Referrer-Policy: strict-origin-when-cross-origin' in response
    assert b'X-Content-Type-Options: nosniff' in response
    print('PASS', path)
request = Request('/assets/')
Handler(request, ('127.0.0.1', 12345), object(), directory=str(ROOT))
assert bytes(request.output).startswith(b'HTTP/1.0 404')
print('PASS: directory listing disabled')
