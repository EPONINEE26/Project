"""영역 CSV와 확보한 Polygon으로 길상사 상권을 DB/JSON에 동기화합니다."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fcha_tantan.settings')
import django
django.setup()

from django.db import connection, transaction
from django.utils import timezone
from market.analysis_models import CommercialArea, DataSource


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_path', type=Path)
    parser.add_argument('polygon_path', type=Path)
    args = parser.parse_args()
    with args.csv_path.open(encoding='cp949', newline='') as handle:
        matches = [row for row in csv.DictReader(handle) if row['상권_코드'] == '3110281']
    if len(matches) != 1:
        raise ValueError('길상사 공식 코드 3110281은 CSV에서 정확히 하나여야 합니다.')
    row = matches[0]
    name, kind, text = args.polygon_path.read_text(encoding='utf-8-sig').strip().split('\t', 2)
    if name != row['상권_코드_명'] or kind != 'Polygon':
        raise ValueError('첨부 이름/도형 종류가 길상사 Polygon과 다릅니다.')
    coordinates = json.loads(text)
    if not coordinates:
        raise ValueError('빈 폴리곤입니다.')
    for ring in coordinates:
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise ValueError('닫힌 4개 이상 좌표의 링이 필요합니다.')
        for pair in ring:
            if len(pair) != 2 or any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in pair):
                raise ValueError('유한한 경도·위도 숫자가 필요합니다.')
            if not (126 < pair[0] < 128 and 37 < pair[1] < 38):
                raise ValueError('서울 경위도 범위를 벗어났습니다.')
    geometry = {'type': kind, 'coordinates': coordinates}
    directory = BASE / 'data/analysis'
    area_path = directory / '02_areas.json'
    source_path = directory / '01_sources.json'
    areas = json.loads(area_path.read_text(encoding='utf-8'))
    sources = json.loads(source_path.read_text(encoding='utf-8'))
    if CommercialArea.objects.filter(code='3110281').exclude(version='project-preview-20261103').exists():
        raise ValueError('다른 경계 버전의 길상사가 존재합니다. 먼저 확인하세요.')
    backup_dir = BASE / 'data/backups' / f'gilsangsa_{timezone.now():%Y%m%d_%H%M%S_%f}'
    backup_dir.mkdir(parents=True)
    if connection.vendor != 'sqlite':
        raise ValueError('이 스크립트의 백업은 SQLite만 지원합니다.')
    connection.ensure_connection()
    with sqlite3.connect(backup_dir / 'db.sqlite3') as target:
        connection.connection.backup(target)
    for path in [area_path, source_path]:
        (backup_dir / path.name).write_bytes(path.read_bytes())
    note = json.dumps({
        'metadata_file': args.csv_path.name,
        'metadata_sha256': hashlib.sha256(args.csv_path.read_bytes()).hexdigest(),
        'metadata_row': row,
        'geometry_file': args.polygon_path.name,
        'geometry_sha256': hashlib.sha256(args.polygon_path.read_bytes()).hexdigest(),
        'geometry_note': '사용자 확보 Polygon의 경위도 원본 수치 보존. CSV X/Y로 경계 생성·변환하지 않음. 경계 기준일·좌표계 변환 이력 미확인. 기존 로컬 미리보기 버전으로 추가.',
    }, ensure_ascii=False)
    originals = {area_path: area_path.read_bytes(), source_path: source_path.read_bytes()}
    try:
        with transaction.atomic():
            source, _ = DataSource.objects.update_or_create(
                name='서울시 상권분석서비스(영역-상권) · 길상사 보완',
                defaults={'collected_on': timezone.localdate(), 'note': note},
            )
            area, _ = CommercialArea.objects.update_or_create(
                code='3110281', version='project-preview-20261103',
                defaults=dict(name=row['상권_코드_명'], area_type=row['상권_구분_코드_명'],
                              admin_code=row['행정동_코드'], boundary=geometry,
                              effective_on=None, verified=False, source=source),
            )
            area.full_clean()
            fields = {field.attname: getattr(area, field.attname) for field in area._meta.fields}
            areas = [entry for entry in areas if not (entry['fields']['code'] == area.code and entry['fields']['version'] == area.version)]
            if any(entry['fields']['id'] == area.pk for entry in areas):
                raise ValueError('JSON 상권 ID 충돌')
            areas.append({'model': 'CommercialArea', 'fields': fields})
            sources = [entry for entry in sources if entry['fields']['id'] != source.pk]
            sources.append({'model': 'DataSource', 'fields': {field.attname: getattr(source, field.attname) for field in source._meta.fields}})
            for path, records in [(source_path, sources), (area_path, areas)]:
                temporary = path.with_suffix('.json.tmp')
                temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2, allow_nan=False, default=str) + '\n', encoding='utf-8')
                temporary.replace(path)
    except Exception:
        for path, data in originals.items():
            path.write_bytes(data)
        raise
    exported = next(entry['fields'] for entry in json.loads(area_path.read_text(encoding='utf-8')) if entry['fields']['id'] == area.pk)
    assert exported['boundary'] == CommercialArea.objects.get(pk=area.pk).boundary == geometry
    print(json.dumps({'id': area.pk, 'code': area.code, 'name': area.name, 'vertices': sum(map(len, coordinates)), 'backup': str(backup_dir)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
