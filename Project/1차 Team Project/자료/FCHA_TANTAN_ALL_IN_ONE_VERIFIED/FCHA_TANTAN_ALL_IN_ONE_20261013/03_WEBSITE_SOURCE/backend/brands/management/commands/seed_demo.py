import json
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from brands.models import Brand,AnnualStat,RegionalStat
class Command(BaseCommand):
    help='데모 브랜드 8개를 입력합니다. 같은 식별자의 실데이터는 덮어쓰지 않습니다.'
    @transaction.atomic
    def handle(self,*args,**options):
        data=json.loads((settings.FRONTEND_DIR/'data/brands.json').read_text(encoding='utf-8'))
        for item in data['brands']:
            item=item.copy(); slug=item.pop('id'); stats=item.pop('stats')
            if Brand.objects.filter(slug=slug,is_demo=False).exists():
                raise CommandError(f'{slug}: 실데이터 브랜드가 있어 데모 입력을 취소했습니다.')
            b,_=Brand.objects.update_or_create(slug=slug,defaults={**item,'is_demo':True})
            b.annual_stats.exclude(year__in=data['years']).delete()
            for s in stats:
                s=s.copy(); regions=s.pop('regions');year=s.pop('year')
                annual,_=AnnualStat.objects.update_or_create(brand=b,year=year,defaults={**s,'source_label':data['source_label']})
                for region,count in regions.items():
                    RegionalStat.objects.update_or_create(annual_stat=annual,region=region,defaults={'stores':count})
        self.stdout.write(self.style.SUCCESS('데모 데이터 입력 완료: 8개 브랜드, 16개 연간 통계'))
