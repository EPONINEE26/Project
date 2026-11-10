"""Render both navigation variants in Chrome and save review screenshots."""
import os
import sys
import threading
from pathlib import Path
from wsgiref.simple_server import make_server, WSGIServer
from socketserver import ThreadingMixIn

class PreviewServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fcha_tantan.settings')
import django
django.setup()
import copy
from django.conf import settings
from django.test import override_settings
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.wsgi import get_wsgi_application
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from package_project import variant_content

output = ROOT / 'artifacts'
output.mkdir(exist_ok=True)
options = webdriver.ChromeOptions()
options.add_argument('--headless=new')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-extensions')
options.add_argument('--renderer-process-limit=2')
options.add_argument('--force-prefers-reduced-motion')
options.add_argument('--window-size=1742,1038')
driver_path = Path('C:/Users/mbc/.cache/selenium/chromedriver/win64/155.0.8059.79/chromedriver.exe')
driver = webdriver.Chrome(service=Service(str(driver_path)), options=options)
try:
    for variant in ('integrated', 'standalone'):
        templates = {}
        for path in ROOT.rglob('*.html'):
            if 'templates' not in path.parts or 'artifacts' in path.parts:
                continue
            name = path.as_posix().split('/templates/', 1)[1]
            content = variant_content(path.relative_to(ROOT), variant)
            templates[name] = content.decode('utf-8') if content is not None else path.read_text(encoding='utf-8')
        configuration = copy.deepcopy(settings.TEMPLATES)
        configuration[0]['APP_DIRS'] = False
        configuration[0]['OPTIONS']['loaders'] = [('django.template.loaders.locmem.Loader', templates)]
        with override_settings(TEMPLATES=configuration, ALLOWED_HOSTS=['127.0.0.1', 'localhost']):
            server = make_server('127.0.0.1', 8002, StaticFilesHandler(get_wsgi_application()), server_class=PreviewServer)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                for board, url in [('owners', '/community/'), ('closure', '/community/closure/')]:
                    driver.get('http://127.0.0.1:8002' + url)
                    hero = driver.find_element('css selector', '.community-hero')
                    feed = driver.find_element('css selector', '.community-feed')
                    side = driver.find_element('css selector', '.community-side')
                    assert hero.rect['y'] < feed.rect['y']
                    assert side.rect['x'] > feed.rect['x']
                    tabs = driver.find_elements('css selector', 'nav[aria-label="커뮤니티 게시판"]')
                    assert bool(tabs) == (variant == 'integrated')
                    if tabs:
                        assert tabs[0].rect['y'] >= hero.rect['y'] + hero.rect['height']
                    assert driver.execute_script('return document.documentElement.scrollWidth <= innerWidth')
                    driver.save_screenshot(str(output / f'{variant}_{board}.png'))
                    print('BROWSER_OK', variant, board, hero.rect, flush=True)
            finally:
                server.shutdown()
                server.server_close()
                worker.join()
finally:
    driver.quit()
