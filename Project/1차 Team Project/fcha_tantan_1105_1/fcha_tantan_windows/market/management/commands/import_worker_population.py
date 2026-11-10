"""서울시 직장인구 CSV의 최신 분기를 공식 상권 코드로 적재합니다."""
import csv
import hashlib
import json
import re
import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from market.analysis_models import CommercialArea, DataSource, PopulationStat


class Command(BaseCommand):
    help = '직장인구 최신 분기 검증 및 저장 (--commit). 기존 다른 분기·인구 종류는 보존합니다.'

    def add_arguments(self, parser):
        parser.add_argument('path')
        parser.add_argument('--commit', action='store_true')

    def handle(self, *args, **options):
        path = Path(options['path'])
        try:
            with path.open(encoding='cp949', newline='') as handle:
                rows = list(csv.DictReader(handle))
            if not rows:
                raise ValueError('빈 CSV입니다.')
            if any(not re.fullmatch(r'20\d{2}[1-4]', row['기준_년분기_코드']) for row in rows):
                raise ValueError('분기 형식이 잘못되었습니다.')
            latest = max(row['기준_년분기_코드'] for row in rows)
            period = latest[:4] + 'Q' + latest[-1]
            areas = {}
            for area in CommercialArea.objects.all():
                if area.code in areas:
                    raise ValueError(f'상권 경계 버전을 하나로 지정해야 합니다: {area.code}')
                areas[area.code] = area
            records, excluded, renamed, seen = [], [], [], set()
            for row in rows:
                if row['기준_년분기_코드'] != latest:
                    continue
                code = row['상권_코드']
                if code in seen:
                    raise ValueError(f'상권 코드 중복: {code}')
                seen.add(code)
                values = [v for k, v in row.items() if k.endswith('_직장_인구_수')]
                if any(not re.fullmatch(r'\d+', value) for value in values):
                    raise ValueError(f'직장인구는 0 이상의 정수여야 합니다: {code}')
                total = int(row['총_직장_인구_수'])
                ages = {f'{age}대' if age != 60 else '60대 이상': int(row[f'연령대_{age}{"_이상" if age == 60 else ""}_직장_인구_수']) for age in [10, 20, 30, 40, 50, 60]}
                if sum(ages.values()) != total or int(row['남성_직장_인구_수']) + int(row['여성_직장_인구_수']) != total:
                    raise ValueError(f'총 인구와 세부 합계 불일치: {code}')
                area = areas.get(code)
                if area is None:
                    excluded.append(code)
                    continue
                if area.area_type != row['상권_구분_코드_명']:
                    raise ValueError(f'상권 유형 불일치: {code}')
                if area.name != row['상권_코드_명']:
                    renamed.append(code)
                records.append((area, total, ages))
            if not records:
                raise ValueError('연결 가능한 상권이 없습니다.')
        except (OSError, UnicodeError, KeyError, TypeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        report = dict(period=period, matched=len(records), excluded=excluded, renamed=renamed, saved=options['commit'])
        if options['commit']:
            if connection.vendor == 'sqlite' and not connection.creation.is_in_memory_db(connection.settings_dict['NAME']):
                directory = Path(settings.BASE_DIR) / 'data/backups'
                directory.mkdir(parents=True, exist_ok=True)
                backup = directory / f'before_worker_population_{timezone.now():%Y%m%d_%H%M%S_%f}.sqlite3'
                connection.ensure_connection()
                with sqlite3.connect(backup) as target:
                    connection.connection.backup(target)
                report['backup'] = str(backup)
            with transaction.atomic():
                source, _ = DataSource.objects.get_or_create(
                    name='서울시 상권분석서비스(직장인구-상권)',
                    note=f'원본 {path.name}; SHA256 {hashlib.sha256(path.read_bytes()).hexdigest()}; {period}. 공식 상권 코드 연결. 총인구·연령별 인구 저장. 성별 세부값은 원본 CSV 보존.',
                    defaults={'collected_on': timezone.localdate()},
                )
                for area, total, ages in records:
                    PopulationStat.objects.update_or_create(
                        area=area, period=period, kind='worker',
                        defaults=dict(source=source, unit='명', total=total, by_age=ages),
                    )
        self.stdout.write(json.dumps(report, ensure_ascii=False))
