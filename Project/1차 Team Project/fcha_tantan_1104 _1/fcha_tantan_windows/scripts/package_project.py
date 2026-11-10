"""Create a local project ZIP with a consistent SQLite snapshot."""
from datetime import datetime
from contextlib import closing
from pathlib import Path
import os
import sqlite3
import zipfile
import argparse


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'artifacts'
EXCLUDE = {
    'artifacts', 'backups', 'private_media', '__pycache__', '.git', '.venv',
    '.vscode', '.claude', '.codex', '.agents', '.aws', 'logs', '.validation_deps',
}


def variant_content(relative, variant):
    """Only navigation differs; both versions keep the original community UI."""
    if variant != 'standalone':
        return None
    name = relative.as_posix()
    if name == 'brands/templates/base.html':
        text = (ROOT / relative).read_text(encoding='utf-8')
        text = text.replace("{% if page == 'community' %}", "{% if page == 'community' and community_board != 'closure' %}")
        text = text.replace('>점주 커뮤니티</a></nav>', '>점주 커뮤니티</a>\n<a href="{% url \'community:closure_list\' %}" {% if community_board == \'closure\' %}class="active" aria-current="page"{% endif %}>폐점주 커뮤니티</a></nav>')
        text = text.replace('<a href="{% url \'core:help\' %}"><span aria-hidden="true">?</span>고객센터</a>', '<a href="{% url \'community:closure_list\' %}"><span aria-hidden="true">☷</span>폐점주 커뮤니티</a><a href="{% url \'core:help\' %}"><span aria-hidden="true">?</span>고객센터</a>')
        return text.encode('utf-8')
    if name == 'community/templates/community/index.html' or (name.startswith('community/templates/community/closure/') and name.endswith('.html')):
        text = (ROOT / relative).read_text(encoding='utf-8')
        for include in ('{% include "community/_board_tabs.html" %}', "{% include 'community/_board_tabs.html' %}"):
            text = text.replace(include, '')
        return text.encode('utf-8')
    if name == 'COMMUNITY_FIX_20261104.md':
        text = (ROOT / relative).read_text(encoding='utf-8')
        text = text.replace('기존 점주 커뮤니티(`/community/`) 안의 ‘점주 이야기 / 폐점주 커뮤니티’ 탭으로 이동합니다.', '이 ZIP은 별도 메뉴 버전입니다. 상단의 점주 커뮤니티와 폐점주 커뮤니티에서 각각 이동합니다.')
        text = text.replace('상단과 회원 메뉴에는 기존 ‘점주 커뮤니티’ 진입점만 유지합니다.', '상단과 회원 메뉴에 점주 커뮤니티와 폐점주 커뮤니티 진입점을 각각 제공합니다.')
        text = text.replace('6. 점주 커뮤니티 → 폐점주 커뮤니티로 이동하세요.', '6. 상단의 폐점주 커뮤니티로 이동하세요.')
        return text.encode('utf-8')
    if name == 'community/tests.py':
        text = (ROOT / relative).read_text(encoding='utf-8')
        text = text.replace("self.assertNotIn('href=\"' + reverse('community:closure_list') + '\"', header)",
                            "self.assertIn('href=\"' + reverse('community:closure_list') + '\"', header)")
        return text.encode('utf-8')
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=['integrated', 'standalone'], default='integrated')
    variant = parser.parse_args().variant
    OUTPUT.mkdir(exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive = OUTPUT / f'fcha_tantan_windows_{variant}_{stamp}.zip'
    snapshot = OUTPUT / f'db_snapshot_{variant}_{stamp}.sqlite3'
    print('Preparing database snapshot...', flush=True)
    try:
        with closing(sqlite3.connect(f'{(ROOT / "db.sqlite3").as_uri()}?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(snapshot)) as target:
                source.backup(target)
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
            required = ['manage.py', 'db.sqlite3', 'community/templates/community/_board_tabs.html',
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
