import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from brands.models import Brand, CostItem, StartupCost, DataSource

CATEGORIES = {"coffee":"카페", "chicken":"치킨", "convenience":"편의점", "beauty":"미용실"}
CODES = [
    ("franchise_fee_krw", "가맹비"),
    ("education_fee_krw", "교육비"),
    ("guarantee_deposit_krw", "보증금"),
    ("other_cost_krw", "기타 비용"),
]

class Command(BaseCommand):
    help = "Import 19 brands' 2024-2025 startup cost breakdown (dry run by default)"

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Actually save data')

    def handle(self, *args, **options):
        base = Path(__file__).resolve().parents[3] / 'data' / 'startup_cost_19'
        files = [('coffee.json','카페'), ('chicken.json','치킨'), ('convenience.json','편의점'), ('beauty.json','미용실')]
        rows = []
        errors = []
        brands_seen = set()
        for filename, category in files:
            path = base / filename
            if not path.is_file():
                raise CommandError(f'Missing file: {path}')
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            if data.get('source') != 'priority_brands.json' or data.get('category') != category:
                raise CommandError(f'Unexpected data source/category: {filename}')
            for entry in data['brands']:
                slug = entry['id']
                if slug in brands_seen:
                    errors.append(f'Duplicate brand: {slug}')
                brands_seen.add(slug)
                try:
                    brand = Brand.objects.get(slug=slug, is_demo=False)
                except Brand.DoesNotExist:
                    errors.append(f'Brand missing or demo: {slug}')
                    continue
                if brand.category != category:
                    errors.append(f'Category mismatch: {slug} DB={brand.category} JSON={category}')
                    continue
                for i, history in enumerate(entry.get('history', [])):
                    year = history.get('year')
                    if year not in (2024, 2025):
                        errors.append(f'Unexpected year: {slug} {year}')
                        continue
                    breakdown = history.get('startup_cost_breakdown') or {}
                    for order, (code, label) in enumerate(CODES, start=1):
                        amount = breakdown.get(code)
                        if amount is not None and (type(amount) is not int or amount < 0):
                            errors.append(f'Invalid amount: {slug} {year} {code}={amount}')
                            continue
                        json_path = f'brands[{entry["id"]}].history[year={year}].startup_cost_breakdown.{code}'
                        rows.append((brand, year, category, code, label, order, amount, filename, json_path))
        if len(brands_seen) != 19 or len(rows) != 152:
            errors.append(f'Expected 19 brands / 152 cost entries; got {len(brands_seen)} / {len(rows)}')
        if errors:
            raise CommandError('Import validation failed:\n' + '\n'.join(errors))
        missing = sum(row[6] is None for row in rows)
        self.stdout.write(f'Brands: {len(brands_seen)}, records: {len(rows)}, NULL amounts: {missing}')
        if not options['apply']:
            self.stdout.write(self.style.WARNING('DRY RUN ONLY. No database changes. Use --apply after backup.'))
            return
        with transaction.atomic():
            for brand, year, category, code, label, order, amount, filename, json_path in rows:
                item, _ = CostItem.objects.get_or_create(category=category, code=code, defaults={'name':label, 'display_order':order})
                source, _ = DataSource.objects.get_or_create(
                    source_name='priority_brands.json (19-brand category extract)',
                    original_file='priority_brands.json',
                    json_path=f'{filename}: {json_path}',
                    defaults={'verification_status':'needs_review', 'note':'Extracted 19-brand management JSON; original agency record not independently checked.'}
                )
                StartupCost.objects.update_or_create(brand=brand, year=year, item=item, defaults={'amount_krw':amount, 'source':source})
        self.stdout.write(self.style.SUCCESS(f'Saved {len(rows)} startup cost records.'))
