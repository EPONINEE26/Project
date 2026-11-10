"""선택 상권의 최신 직장·유동 인구 CSV를 원자료 그대로 적재합니다."""
import csv
import hashlib
import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from market.analysis_models import CommercialArea, DataSource, PopulationStat


class Command(BaseCommand):
    help = '선택 상권 인구 검증. --commit으로 저장하고 출처·인구 JSON 동기화.'

    def add_arguments(self, parser):
        parser.add_argument('area_code')
        parser.add_argument('--worker', required=True, type=Path)
        parser.add_argument('--floating', required=True, type=Path)
        parser.add_argument('--commit', action='store_true')

    def handle(self, *args, **options):
        areas = list(CommercialArea.objects.filter(code=options['area_code']))
        if len(areas) != 1:
            raise CommandError('상권 코드에 해당하는 경계는 하나여야 합니다.')
        area = areas[0]
        pending, report = [], []
        try:
            for kind, suffix in [('worker', '직장_인구_수'), ('floating', '유동인구_수')]:
                path = options[kind]
                with path.open(encoding='cp949', newline='') as handle:
                    rows = [r for r in csv.DictReader(handle) if r['상권_코드'] == area.code]
                if not rows or any(not re.fullmatch(r'20\d{2}[1-4]', r['기준_년분기_코드']) for r in rows):
                    raise ValueError(f'{kind}: 상권 데이터 또는 유효한 분기가 없습니다.')
                latest = max(r['기준_년분기_코드'] for r in rows)
                latest_rows = [r for r in rows if r['기준_년분기_코드'] == latest]
                if len(latest_rows) != 1:
                    raise ValueError(f'{kind}: 최신 분기 중복')
                row = latest_rows[0]
                if row['상권_구분_코드_명'] != area.area_type or row['상권_코드_명'] != area.name:
                    raise ValueError(f'{kind}: 상권 이름/유형 불일치')
                def number(key):
                    if not re.fullmatch(r'\d+', row[key]):
                        raise ValueError(f'{kind}: 잘못된 인구 수 {key}')
                    return int(row[key])
                total = number(f'총_{suffix}')
                genders = {label: number(f'{label}_{suffix}') for label in ['남성', '여성']}
                values = dict(total=total, unit='명' if kind == 'worker' else '원자료 수치',
                              by_gender=genders,
                              by_age={f'{age}대' if age != 60 else '60대 이상': number(f'연령대_{age}{"_이상" if age == 60 else ""}_{suffix}') for age in [10,20,30,40,50,60]})
                if kind == 'floating':
                    values['by_day'] = {day: number(f'{day}요일_{suffix}') for day in '월화수목금토일'}
                    values['by_time'] = {label: number(f'시간대_{start}_{end}_{suffix}') for label, start, end in [('0~6시','00','06'),('6~11시','06','11'),('11~14시','11','14'),('14~17시','14','17'),('17~21시','17','21'),('21~24시','21','24')]}
                period = latest[:4] + 'Q' + latest[-1]
                note = f'원본 {path.name}; SHA256 {hashlib.sha256(path.read_bytes()).hexdigest()}; {period}; 공식 상권 코드 연결. 총계·성별·연령별 및 제공되는 요일·시간대 원자료 보존. 세부 합계 차이는 보정하지 않음.'
                pending.append((kind, period, path, note, values))
                report.append(dict(kind=kind, period=period, total=total, by_gender=genders, gender_sum_difference=sum(genders.values())-total))
        except (OSError, UnicodeError, KeyError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        if options['commit']:
            directory = Path(settings.BASE_DIR) / 'data/analysis'
            paths = [directory / '01_sources.json', directory / '04_population.json']
            originals = {p: p.read_bytes() for p in paths}
            backup = Path(settings.BASE_DIR) / 'data/backups' / f'area_population_json_{timezone.now():%Y%m%d_%H%M%S_%f}'
            backup.mkdir(parents=True)
            for path, content in originals.items():
                (backup / path.name).write_bytes(content)
            try:
                with transaction.atomic():
                    for kind, period, path, note, values in pending:
                        source, _ = DataSource.objects.get_or_create(name=path.stem, note=note, defaults={'collected_on': timezone.localdate()})
                        obj, _ = PopulationStat.objects.update_or_create(area=area, kind=kind, period=period, defaults=dict(values, source=source))
                        obj.full_clean()
                    for path, model in [(paths[0], DataSource), (paths[1], PopulationStat)]:
                        records = [{'model': model.__name__, 'fields': {f.attname: getattr(obj, f.attname) for f in model._meta.fields}} for obj in model.objects.order_by('pk')]
                        temporary = path.with_suffix('.json.tmp')
                        temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
                        temporary.replace(path)
            except Exception:
                for path, content in originals.items():
                    path.write_bytes(content)
                raise
        self.stdout.write(json.dumps(report, ensure_ascii=False))
