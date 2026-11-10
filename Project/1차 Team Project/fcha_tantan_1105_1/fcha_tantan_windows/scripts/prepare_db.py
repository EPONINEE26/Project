"""기존 DB에 필요한 migration이 있을 때만 SQLite 백업 후 적용합니다."""
import os
import sys
from pathlib import Path
from datetime import datetime
import sqlite3
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fcha_tantan.settings')
import django
django.setup()
from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.core.management import call_command
executor = MigrationExecutor(connection)
plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
if plan:
    path = Path(settings.DATABASES['default']['NAME'])
    if path.exists():
        folder = root / 'backups'
        folder.mkdir(exist_ok=True)
        destination = folder / ('before_migrate_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.sqlite3')
        with sqlite3.connect(path) as source, sqlite3.connect(destination) as target:
            source.backup(target)
        print('DB 백업:', destination.name)
    call_command('migrate', interactive=False)
else:
    print('DB 구조가 최신 상태입니다.')
# 실데이터 브랜드가 하나도 없으면 data/fcha_json의 JSON(brands.json 우선)을 처음 한 번 가져옵니다.
from brands.models import Brand
from brands.management.commands.import_fcha_json import default_json
if not Brand.objects.filter(is_demo=False).exists() and default_json().exists():
    print('브랜드 데이터를 처음 가져옵니다. 1분 정도 걸릴 수 있어요...')
    call_command('import_fcha_json')
call_command('seed_site_content')
call_command('check')
