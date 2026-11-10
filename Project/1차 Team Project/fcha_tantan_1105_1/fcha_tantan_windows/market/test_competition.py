from datetime import date
from decimal import Decimal
from django.test import TestCase
from .analysis_models import CommercialArea, DataSource, IndustryCode, PublicStore
from . import competition


class IndustryCompetitionTests(TestCase):
    def setUp(self):
        competition.seoul_shares.cache_clear()
        self.addCleanup(competition.seoul_shares.cache_clear)
        self.source = DataSource.objects.create(name='공공 상가', collected_on='2026-11-03')
        self.cafe = IndustryCode.objects.create(system='t', code='I21201', name='카페')
        self.chicken = IndustryCode.objects.create(system='t', code='I21001', name='치킨')
        self.bakery = IndustryCode.objects.create(system='t', code='I21101', name='빵/도넛')
        self.lawyer = IndustryCode.objects.create(system='t', code='M11101', name='변호사')
        self.here = self.area('here')
        self.other = self.area('other')
        self.n = 0
        # 이 상권: 카페 30 · 빵 20 · 치킨 0 · 변호사 40(비교 제외)
        self.stores(self.here, self.cafe, 30); self.stores(self.here, self.bakery, 20); self.stores(self.here, self.lawyer, 40)
        # 다른 상권: 카페 10 · 치킨 50 · 빵 0
        self.stores(self.other, self.cafe, 10); self.stores(self.other, self.chicken, 50)

    def area(self, code):
        return CommercialArea.objects.create(code=code, version='v', name=code, area_type='t', admin_code='1', source=self.source)

    def stores(self, area, industry, count):
        for _ in range(count):
            self.n += 1
            PublicStore.objects.create(source=self.source, external_id=str(self.n), name='s', industry=industry, area=area,
                                       address='a', latitude=Decimal('37.5'), longitude=Decimal('127'), reference_on=date(2026, 11, 3))

    def test_location_quotient_crowded_and_scarce(self):
        result = competition.industry_competition(self.here)
        self.assertEqual(result['total'], 50)  # 변호사(M)는 소비자 업종이 아니라 제외
        crowded = {r['name']: r for r in result['crowded']}
        # 서울 비중: 카페 40/110=36.4%, 빵 20/110=18.2%, 치킨 50/110=45.5%
        self.assertEqual(crowded['빵/도넛']['lq'], 2.2)  # 상권 40% ÷ 서울 18.2%
        self.assertAlmostEqual(crowded['카페']['lq'], 1.65, delta=0.06)  # 상권 60% ÷ 서울 36.4%
        self.assertEqual([(r['name'], r['count']) for r in result['scarce']], [('치킨', 0)])

    def test_small_area_skips_scarce_and_none_without_area(self):
        self.assertIsNone(competition.industry_competition(None))
        small = self.area('small')
        self.stores(small, self.cafe, 6)
        result = competition.industry_competition(small)
        self.assertFalse(result['enough'])
        self.assertEqual(result['scarce'], [])
        self.assertEqual(result['crowded'][0]['name'], '카페')  # 과밀은 표본이 작아도 매장 5곳 이상이면 표시
