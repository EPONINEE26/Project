"""Install/validate local dependencies, prepare the DB, then open a ready server."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / 'logs' / 'startup.log'
LOG_LOCK = threading.Lock()
ENV = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8', 'PYTHONUNBUFFERED': '1'}


def report(message):
    with LOG_LOCK:
        print(message, flush=True)
        LOG_PATH.parent.mkdir(exist_ok=True)
        with LOG_PATH.open('a', encoding='utf-8') as handle:
            handle.write(message + '\n')


def command(args):
    result = subprocess.Popen([sys.executable, *args], cwd=ROOT, env=ENV,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding='utf-8', errors='replace')
    try:
        for line in result.stdout:
            report(line.rstrip('\r\n'))
        code = result.wait()
        if code:
            raise RuntimeError(f'Command failed (exit {code}): python {" ".join(args)}')
    finally:
        if result.poll() is None:
            result.terminate()
            result.wait()


def ensure_dependencies():
    requirements = ROOT / 'requirements.txt'
    fingerprint = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = Path(sys.prefix) / '.fcha_requirements.sha256'
    imports = subprocess.run([sys.executable, '-c',
                              'import django,pandas,openpyxl,allauth,requests,jwt,cryptography'],
                             capture_output=True, env=ENV)
    installed = marker.exists() and marker.read_text().strip() == fingerprint and imports.returncode == 0
    if installed:
        check = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True, env=ENV)
        installed = check.returncode == 0
    if not installed:
        report('[2/5] Installing dependencies. The first run requires internet access; please wait...')
        if subprocess.run([sys.executable, '-m', 'pip', '--version'], capture_output=True, env=ENV).returncode:
            command(['-m', 'ensurepip', '--upgrade'])
        command(['-m', 'pip', 'install', '--disable-pip-version-check', '--prefer-binary',
                 '--timeout', '30', '--retries', '2', '-r', str(requirements)])
        command(['-m', 'pip', 'check'])
        # Do not mark an environment ready if a native module cannot be imported.
        command(['-c', 'import django,pandas,openpyxl,allauth,requests,jwt,cryptography'])
        marker.write_text(fingerprint, encoding='ascii')
    else:
        report('[2/5] Dependencies are ready.')


def find_port():
    # Do not terminate another application already using port 8000.
    for port in range(8000, 8021):
        with socket.socket() as sock:
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                sock.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    raise RuntimeError('Ports 8000-8020 are in use. Close an old server window and retry.')


def open_when_ready(process, url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + 90
    while process.poll() is None and time.monotonic() < deadline:
        try:
            with opener.open(url, timeout=2) as response:
                if response.status < 400:
                    report('[5/5] Server is ready: ' + url)
                    if not webbrowser.open(url):
                        report('Open the URL above in your browser.')
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.5)
    if process.poll() is None:
        report('The browser could not be opened automatically. Check the server output and open: ' + url)


def serve():
    port = find_port()
    url = f'http://127.0.0.1:{port}/'
    report('[4/5] Starting local server: ' + url)
    report('Admin: ' + url + 'admin/ (account details: .env)')
    report('Keep this window open. Press Ctrl+C to stop.')
    process = subprocess.Popen([sys.executable, 'manage.py', 'runserver',
                                f'127.0.0.1:{port}', '--noreload'], cwd=ROOT, env=ENV,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding='utf-8', errors='replace')
    browser_thread = threading.Thread(target=open_when_ready, args=(process, url), daemon=True)
    browser_thread.start()
    try:
        for line in process.stdout:
            report(line.rstrip('\r\n'))
        code = process.wait()
        if code:
            raise RuntimeError(f'The server stopped (exit {code}). See the console output.')
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()


def main():
    os.chdir(ROOT)
    report('Runtime: ' + sys.executable)
    report('Python: ' + sys.version.split()[0])
    try:
        ensure_dependencies()
        report('[3/5] Preparing the database and administrator account...')
        command(['scripts/prepare_db.py'])
        command(['scripts/create_admin.py'])
        serve()
        return 0
    except KeyboardInterrupt:
        report('Server stopped.')
        return 0
    except Exception as error:
        report('ERROR: ' + str(error))
        report('Diagnostic log: ' + str(LOG_PATH))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
