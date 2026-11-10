"""자치구 길단위인구 CSV를 상권 통계와 분리해 저장합니다."""
import csv
import hashlib
import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from market.analysis_models import DataSource, DistrictPopulationStat


def read_records(path):
    with path.open(encoding='cp949', newline='') as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError('빈 CSV입니다.')
    records, seen = [], set()
    for row in rows:
        quarter, code = row['기준_년분기_코드'], row['자치구_코드']
        if not re.fullmatch(r'20\d{2}[1-4]', quarter) or not re.fullmatch(r'11\d{3}', code):
            raise ValueError('분기 또는 서울 자치구 코드 형식 오류')
        key = (code, quarter)
        if key in seen:
            raise ValueError(f'자치구/분기 중복: {key}')
        seen.add(key)
        if not row['자치구_코드_명'].strip() or None in row or any(v is None for v in row.values()):
            raise ValueError(f'누락된 CSV 값: {key}')
        def number(column):
            value = row[column].strip()
            if not re.fullmatch(r'(?:\d+|\d{1,3}(?:,\d{3})+)', value):
                raise ValueError(f'잘못된 인구 수: {key}, {column}')
            return int(value.replace(',', ''))
        records.append(dict(
            district_code=code, district_name=row['자치구_코드_명'],
            period=quarter[:4]+'Q'+quarter[-1], total=number('총 유동'),
            by_gender={g: number(g+' 유동') for g in ['남성', '여성']},
            by_age={f'{age}대': number(f'{age}대 유동') for age in [10,20,30,40,50,60]},
            by_time={label: number(column) for label, column in [('0~6시','0~6시'),('6~11시','6~11시'),('11~14시','11~14시'),('14~17시','14~17시'),('17~21시','17~21'),('21~24시','21~24')]},
            by_day={day: number(day+' 유동') for day in '월화수목금토일'}, raw=row,
        ))
    return records


class Command(BaseCommand):
    help = '자치구 유동인구 전체 분기 검증/적재 (--commit으로 저장)'

    def add_arguments(self, parser):
        parser.add_argument('path', type=Path)
        parser.add_argument('--commit', action='store_true')

    def handle(self, *args, **options):
        path = options['path']
        try:
            records = read_records(path)
        except (OSError, UnicodeError, KeyError, ValueError, TypeError) as exc:
            raise CommandError(str(exc)) from exc
        if options['commit']:
            with transaction.atomic():
                source, _ = DataSource.objects.get_or_create(
                    name=path.stem,
                    note=f'SHA256 {hashlib.sha256(path.read_bytes()).hexdigest()}; 자치구 전체 단위. CSV 원자료 보존, 세부 합계 차이 보정 없음.',
                    defaults={'collected_on': timezone.localdate()},
                )
                for record in records:
                    values = record.copy()
                    code, period = values.pop('district_code'), values.pop('period')
                    obj, _ = DistrictPopulationStat.objects.update_or_create(
                        district_code=code, period=period, defaults=dict(values, source=source),
                    )
                    obj.full_clean()
        self.stdout.write(json.dumps(dict(rows=len(records), districts=len({r['district_code'] for r in records}),
            periods=sorted({r['period'] for r in records}), saved=options['commit'])))
