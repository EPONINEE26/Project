"""Create a local project ZIP with a consistent SQLite snapshot."""
from datetime import datetime
from contextlib import closing
from pathlib import Path
import os
import sqlite3
import zipfile
import argparse
import re
import sys


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'artifacts'
EXCLUDE = {
    'artifacts', 'backups', 'private_media', '__pycache__', '.git', '.venv',
    '.vscode', '.claude', '.codex', '.agents', '.aws', 'logs', '.validation_deps',
}


def variant_content(relative, variant):
    """현재는 점주 이야기 단일 게시판이며 구형 폐점주 메뉴를 생성하지 않습니다."""
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=['integrated', 'standalone'], default='integrated')
    parser.add_argument('--with-store-tip', action='store_true')
    args = parser.parse_args()
    variant = args.variant
    OUTPUT.mkdir(exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive = OUTPUT / f'fcha_tantan_windows_{variant}_{stamp}.zip'
    snapshot = OUTPUT / f'db_snapshot_{variant}_{stamp}.sqlite3'
    print('Preparing database snapshot...', flush=True)
    try:
        with closing(sqlite3.connect(f'{(ROOT / "db.sqlite3").as_uri()}?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(snapshot)) as target:
                source.backup(target)
        if args.with_store_tip:
            sys.path.insert(0, str(ROOT))
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fcha_tantan.settings')
            from django.conf import settings
            settings.DATABASES['default']['NAME'] = snapshot
            import django
            django.setup()
            from django.core.management import call_command
            from django.test import Client
            from django.db import connections
            from community.models import Post
            from community.management.commands.seed_store_tip import TITLE
            call_command('seed_store_tip')
            post = Post.objects.get(title=TITLE, topic='store_tips', author__username='store-tips-example')
            for url in ['/community/?topic=store_tips', f'/community/{post.pk}/']:
                response = Client().get(url)
                if response.status_code != 200 or TITLE not in response.content.decode('utf-8'):
                    raise RuntimeError(f'Store tip page verification failed: {url}')
            connections.close_all()
            print('STORE_TIP_PAGES_OK: list and detail HTTP 200', flush=True)
        files = []
        for directory, subdirs, names in os.walk(ROOT):
            subdirs[:] = sorted(d for d in subdirs if d not in EXCLUDE and not d.startswith('.venv_backup_'))
            for name in sorted(names):
                path = Path(directory) / name
                if name == '.env' or name.endswith(('.pyc', '.zip', '.sqlite3-wal', '.sqlite3-shm', '.sqlite3-journal')):
                    continue
                files.append(path)
        print(f'Packing {len(files)} project files including database and data...', flush=True)
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=5, allowZip64=True) as bundle:
            for path in files:
                relative = path.relative_to(ROOT)
                overlay = variant_content(relative, variant)
                member = f'fcha_tantan_windows/{relative.as_posix()}'
                if overlay is not None:
                    bundle.writestr(member, overlay)
                else:
                    bundle.write(snapshot if relative.as_posix() == 'db.sqlite3' else path, member)
        print('Checking archive CRC...', flush=True)
        with zipfile.ZipFile(archive) as bundle:
            bad_file = bundle.testzip()
            if bad_file:
                raise RuntimeError(f'Archive validation failed: {bad_file}')
            required = ['manage.py', 'db.sqlite3', 'community/templates/community/index.html',
                        'community/migrations/0002_closureverification_closurereview_and_more.py']
            for name in required:
                bundle.getinfo('fcha_tantan_windows/' + name)
        print(f'ZIP_OK: {archive}', flush=True)
        print(f'ZIP_BYTES: {archive.stat().st_size}', flush=True)
    finally:
        if snapshot.exists():
            snapshot.unlink()


if __name__ == '__main__':
    main()
