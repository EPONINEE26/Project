"""공식 상권 코드로 최신 분기 유동인구를 검증하고 교체합니다."""
import csv
import hashlib
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from market.analysis_models import CommercialArea, DataSource, PopulationStat


class Command(BaseCommand):
    help = '최신 분기만 유지합니다. 기본 검증 전용, --commit으로 백업 후 교체.'

    def add_arguments(self, parser):
        parser.add_argument('path')
        parser.add_argument('--commit', action='store_true')

    def handle(self, *args, **options):
        path = Path(options['path'])
        with path.open(encoding='cp949', newline='') as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            raise CommandError('빈 CSV입니다.')
        period_key = '기준_년분기_코드'
        if any(not re.fullmatch(r'20\d{2}[1-4]', row[period_key]) for row in rows):
            raise CommandError('분기 형식이 잘못되었습니다.')
        latest = max(row[period_key] for row in rows)
        period = latest[:4] + 'Q' + latest[-1]
        areas = {}
        for area in CommercialArea.objects.all():
            if area.code in areas:
                raise CommandError(f'경계 버전 중복: {area.code}')
            areas[area.code] = area
        objects, excluded, renamed, seen = [], [], [], set()
        source = DataSource(
            name='서울시 상권분석서비스(길단위인구-상권)',
            collected_on=timezone.localdate(),
            note=f'원본 {path.name}; SHA256 {hashlib.sha256(path.read_bytes()).hexdigest()}; '
                 f'{period} 최신 분기만 유지. 공식 상권 코드 연결. 단위·평균/누계 정의 미확인으로 원자료 수치 유지. 성별은 원본 CSV에 보존.',
        )
        source.full_clean()
        for row in rows:
            if row[period_key] != latest:
                continue
            code = row['상권_코드']
            if code in seen:
                raise CommandError(f'상권 코드 중복: {code}')
            seen.add(code)
            numeric = [v for k, v in row.items() if k.endswith('_유동인구_수')]
            if any(not re.fullmatch(r'\d+', v) for v in numeric):
                raise CommandError(f'유동인구 숫자 오류: {code}')
            area = areas.get(code)
            if area is None:
                excluded.append({'code': code, 'name': row['상권_코드_명']})
                continue
            if area.area_type != row['상권_구분_코드_명']:
                raise CommandError(f'상권 유형 불일치: {code}')
            if area.name != row['상권_코드_명']:
                renamed.append({'code': code, 'boundary_name': area.name, 'csv_name': row['상권_코드_명']})
            objects.append(PopulationStat(
                area=area, period=period, kind='floating', unit='원자료 수치',
                total=int(row['총_유동인구_수']),
                by_age={f'{age}대': int(row[f'연령대_{age}{"_이상" if age == 60 else ""}_유동인구_수']) for age in [10, 20, 30, 40, 50, 60]},
                by_time={label: int(row[f'시간대_{start}_{end}_유동인구_수']) for label, start, end in [
                    ('0~6시', '00', '06'), ('6~11시', '06', '11'), ('11~14시', '11', '14'),
                    ('14~17시', '14', '17'), ('17~21시', '17', '21'), ('21~24시', '21', '24')]},
                by_day={day: int(row[f'{day}요일_유동인구_수']) for day in '월화수목금토일'},
            ))
        if not objects:
            raise CommandError('연결 가능한 상권이 없습니다.')
        report = {'period': period, 'imported': len(objects), 'excluded': excluded, 'renamed': renamed}
        if options['commit']:
            if connection.vendor != 'sqlite':
                raise CommandError('이 명령의 백업은 SQLite만 지원합니다.')
            backup_dir = Path(settings.BASE_DIR) / 'data/backups'
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup = backup_dir / f'before_latest_population_{datetime.now():%Y%m%d_%H%M%S_%f}.sqlite3'
            connection.ensure_connection()
            with sqlite3.connect(backup) as target:
                connection.connection.backup(target)
            with transaction.atomic():
                source.save()
                PopulationStat.objects.filter(kind='floating').delete()
                for obj in objects:
                    obj.source = source
                    obj.full_clean()
                PopulationStat.objects.bulk_create(objects)
            fields = ['id', 'area_id', 'source_id', 'period', 'unit', 'kind', 'total', 'households', 'single_households', 'by_age', 'by_time', 'by_day']
            out = Path(settings.BASE_DIR) / 'data/analysis'
            population = [{'model': 'PopulationStat', 'fields': r} for r in PopulationStat.objects.values(*fields).order_by('id')]
            sources = [{'model': 'DataSource', 'fields': r} for r in DataSource.objects.values('id', 'name', 'url', 'collected_on', 'note').order_by('id')]
            for filename, records in [('04_population.json', population), ('01_sources.json', sources)]:
                (out / filename).write_text(json.dumps(records, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
            report['backup'] = str(backup)
            (Path(settings.BASE_DIR) / 'data/reports/latest_population_update.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        self.stdout.write(json.dumps(report, ensure_ascii=False))
