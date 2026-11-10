import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from brands.models import AnnualStat, AreaSales

class Command(BaseCommand):
    help = '단위가 확인된 평당 평균 연매출(원/평·년)을 기존 브랜드·연도에만 연결합니다.'
    def add_arguments(self, parser):
        parser.add_argument('csv_path')
        parser.add_argument('--demo', action='store_true')
    @transaction.atomic
    def handle(self, *args, **options):
        try:
            with Path(options['csv_path']).open(encoding='utf-8-sig', newline='') as source:
                reader = csv.DictReader(source)
                required = {'brand_id','year','annual_sales_per_pyeong_krw','source_label','source_url'}
                if not required.issubset(reader.fieldnames or []): raise ValueError('CSV 필수 열이 누락되었습니다.')
                records = list(reader)
            if not records: raise ValueError('값이 있는 데이터 행이 없습니다.')
            seen = set()
            for row in records:
                slug = row['brand_id'].strip();year = int(row['year']);key = (slug, year)
                if key in seen: raise ValueError('브랜드·연도 중복 행이 있습니다.')
                seen.add(key)
                stat = AnnualStat.objects.select_related('brand').get(brand__slug=slug,year=year)
                if stat.brand.is_demo != options['demo']: raise ValueError('실제·가상 데이터 구분이 일치하지 않습니다.')
                raw = row['annual_sales_per_pyeong_krw'].strip()
                if raw and (not raw.isdecimal() or int(raw)>10**15): raise ValueError('금액은 0 이상 10^15 이하 정수(원)로 입력하세요.')
                label = row['source_label'].strip()
                if not label: raise ValueError('출처가 필요합니다.')
                url = row['source_url'].strip()
                if url:
                    from django.core.validators import URLValidator
                    URLValidator(schemes=['http','https'])(url)
                AreaSales.objects.update_or_create(annual_stat=stat,defaults={'annual_sales_per_pyeong_krw':int(raw) if raw else None,'source_label':label,'source_url':url})
        except Exception as error:
            from django.core.exceptions import ValidationError
            if not isinstance(error,(ValueError, KeyError, TypeError, OSError, AnnualStat.DoesNotExist, ValidationError)): raise
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS(f'{len(records)}개 평당 매출 연결 완료 (기존 브랜드 통계 유지)'))
