import gzip
import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from brands.models import AnnualStat, AreaSales, Brand, RegionalStat
from brands.constants import LEGACY_MAJOR, MAJORS, REGIONS, image_for

SOURCE_LABEL = '공정위 가맹사업 정보공개서 (2026-10-19 가공)'
SOURCE_URL = 'https://franchise.ftc.go.kr/'
COST_LABELS = [('franchise_fee_krw', '가맹비'), ('education_fee_krw', '교육비'),
               ('guarantee_deposit_krw', '계약보증금'), ('other_cost_krw', '기타비용')]
JSON_DIR = settings.BASE_DIR / 'data' / 'fcha_json'


def default_json():
    # 전체 업종(brands.json → GitHub용 압축본 brands.json.gz) 순서로 찾고, 없으면 우선 업종(priority_brands.json)을 씁니다.
    for name in ('brands.json', 'brands.json.gz'):
        if (JSON_DIR / name).exists():
            return JSON_DIR / name
    return JSON_DIR / 'priority_brands.json'


def read_json(path):
    if path.suffix == '.gz':
        with gzip.open(path, 'rt', encoding='utf-8') as f:
            return json.load(f)
    return json.loads(path.read_text(encoding='utf-8'))


def count(value):
    # 음수·소수·문자는 확인 불가 값으로 보고 null 처리합니다. 0은 실제 0으로 유지합니다.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value < 0 or int(value) != value:
        return None
    return int(value)


class Command(BaseCommand):
    help = '프차탄탄 JSON(brands.json 전체 업종 또는 priority_brands.json)을 브랜드·연도·지역 통계로 가져옵니다.'

    def add_arguments(self, parser):
        parser.add_argument('json_path', nargs='?', default=None)

    @transaction.atomic
    def handle(self, *args, **opts):
        path = Path(opts['json_path']) if opts['json_path'] else default_json()
        try:
            data = read_json(path)
        except (OSError, ValueError, EOFError) as e:
            raise CommandError(f'JSON을 읽을 수 없습니다: {e}') from e
        if not isinstance(data, list) or not data:
            raise CommandError('최상위가 브랜드 배열인 JSON이 필요합니다.')
        # 브랜드명이 확정되지 않은 ID(is_displayable=false)는 제외합니다.
        items = [b for b in data if b.get('is_displayable') and b.get('name') and b.get('category')]
        slugs = [b['id'] for b in items]
        if len(set(slugs)) != len(slugs):
            raise CommandError('중복된 브랜드 id가 있습니다.')
        demo = list(Brand.objects.filter(slug__in=slugs, is_demo=True).values_list('slug', flat=True))
        if demo:
            raise CommandError(f'예시 브랜드와 id가 충돌합니다: {", ".join(demo[:5])}')

        existing = {b.slug: b for b in Brand.objects.filter(slug__in=slugs)}
        new_brands, changed = [], []
        for item in items:
            history = sorted(item.get('history') or [], key=lambda h: h['year'])
            latest_cost = next((h for h in reversed(history) if count(h.get('startup_cost_krw')) is not None), None)
            major = item.get('source_category_major') or LEGACY_MAJOR.get(item['category'], '')
            values = {
                'name': item['name'], 'category': item['category'], 'category_major': major if major in MAJORS else '',
                'image': image_for(item['category']), 'official_brand_id': item.get('official_brand_id') or '',
                'company': item.get('company') or '', 'source_category': item.get('source_category') or '',
                'is_demo': False, 'area_sqm': None,
                'initial_cost_krw': count(latest_cost['startup_cost_krw']) if latest_cost else None,
                'costs': {label: count((latest_cost.get('startup_cost_breakdown') or {}).get(key)) for key, label in COST_LABELS} if latest_cost else {},
            }
            brand = existing.get(item['id'])
            if brand is None:
                new_brands.append(Brand(slug=item['id'], **values))
            else:
                for key, value in values.items():
                    setattr(brand, key, value)
                changed.append(brand)
        Brand.objects.bulk_create(new_brands, batch_size=500)
        if changed:
            Brand.objects.bulk_update(changed, ['name', 'category', 'category_major', 'image',
                                                'official_brand_id', 'company', 'source_category', 'is_demo', 'area_sqm',
                                                'initial_cost_krw', 'costs'], batch_size=500)
        brand_ids = dict(Brand.objects.filter(slug__in=slugs).values_list('slug', 'id'))

        # 다시 가져오면 해당 브랜드의 연도·지역 통계를 교체합니다. 대량 삭제는 하위 표부터 한 번에 지웁니다.
        targets = Brand.objects.filter(is_demo=False, slug__in=slugs)
        RegionalStat.objects.filter(annual_stat__brand__in=targets).delete()
        AreaSales.objects.filter(annual_stat__brand__in=targets).delete()
        AnnualStat.objects.filter(brand__in=targets).delete()
        stats, regional_payload, per_pyeong_payload = [], [], []
        for item in items:
            for h in item.get('history') or []:
                national = h.get('national_reference') or {}
                stats.append(AnnualStat(
                    brand_id=brand_ids[item['id']], year=h['year'], stores=count(h.get('stores')),
                    opened=count(h.get('opened')), closed=count(h.get('closed')),
                    annual_sales_krw=count(h.get('annual_sales_krw')), source_label=SOURCE_LABEL, source_url=SOURCE_URL,
                    source_accounting_year=count(h.get('source_accounting_year')),
                    direct_stores=count(h.get('direct_stores')), total_stores=count(h.get('total_stores')),
                    contract_ended=count(h.get('contract_ended')), contract_terminated=count(h.get('contract_terminated')),
                    ownership_changed=count(h.get('ownership_changed')),
                    sales_min_krw=count(national.get('annual_sales_min_krw')), sales_max_krw=count(national.get('annual_sales_max_krw')),
                    sales_status=national.get('sales_status') or h.get('annual_sales_status') or '',
                    startup_cost_krw=count(h.get('startup_cost_krw')),
                    startup_cost_breakdown={label: count((h.get('startup_cost_breakdown') or {}).get(key)) for key, label in COST_LABELS}))
                regional_payload.append(h.get('regions') or {})
                per_pyeong_payload.append(count(h.get('annual_sales_per_3_3sqm_krw')))
        AnnualStat.objects.bulk_create(stats, batch_size=500)
        stat_ids = {(s['brand_id'], s['year']): s['id'] for s in AnnualStat.objects.filter(brand__in=targets).values('id', 'brand_id', 'year')}
        regionals = []
        for stat, regions in zip(stats, regional_payload):
            for name, r in regions.items():
                if name not in REGIONS:
                    continue
                regionals.append(RegionalStat(annual_stat_id=stat_ids[(stat.brand_id, stat.year)], region=name,
                                              stores=count(r.get('stores')), sales_min_krw=count(r.get('annual_sales_min_krw')),
                                              sales_max_krw=count(r.get('annual_sales_max_krw')), sales_status=r.get('sales_status') or ''))
        RegionalStat.objects.bulk_create(regionals, batch_size=2000)
        # 3.3㎡당 연평균매출(원). 0은 실제 0원인지 미공개인지 알 수 없어 넣지 않습니다.
        area_sales = [AreaSales(annual_stat_id=stat_ids[(stat.brand_id, stat.year)], annual_sales_per_pyeong_krw=value,
                                source_label=SOURCE_LABEL, source_url=SOURCE_URL)
                      for stat, value in zip(stats, per_pyeong_payload) if value]
        AreaSales.objects.bulk_create(area_sales, batch_size=2000)
        categories = len({b['category'] for b in items})
        self.stdout.write(self.style.SUCCESS(
            f'{path.name}: 브랜드 {len(items)}개·업종 {categories}개(신규 {len(new_brands)}·갱신 {len(changed)}), '
            f'연도 통계 {len(stats)}건, 지역 통계 {len(regionals)}건, 3.3㎡당 매출 {len(area_sales)}건 입력 완료'))
