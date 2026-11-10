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
call_command('check')
