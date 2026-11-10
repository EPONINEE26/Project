from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from market.analysis import candidate_brands
from market.analysis_models import StartupCondition
from .models import AnnualStat, Brand
from .peer import ratio_score


class RatioScoreTests(SimpleTestCase):
    def test_equal_is_50_double_is_capped_and_missing_is_none(self):
        self.assertEqual(ratio_score(10, 10), 50.0)
        self.assertEqual(ratio_score(30, 10), 100.0)
        self.assertEqual(ratio_score(5, 10), 25.0)
        self.assertEqual(ratio_score(5, 0), 100.0)
        self.assertIsNone(ratio_score(None, 10))


class CandidateRankingTests(TestCase):
    def setUp(self):
        rows = [  # slug, name, stores, opened, closed, annual sales, startup cost
            ('a-average', 'A평범', 100, 10, 10, 120_000_000, 50_000_000),
            ('b-best', 'Z최고', 100, 20, 5, 240_000_000, 25_000_000),
            ('c-worst', 'B부진', 100, 5, 20, 60_000_000, 100_000_000),
            ('d-missing', 'C미공개', 100, None, None, None, None),
        ]
        for slug, name, stores, opened, closed, sales, cost in rows:
            brand = Brand.objects.create(slug=slug, name=name, category='카페', is_demo=False, initial_cost_krw=cost)
            AnnualStat.objects.create(brand=brand, year=2025, stores=stores, opened=opened, closed=closed,
                                      annual_sales_krw=sales, startup_cost_krw=cost, source_label='test')
        user = get_user_model().objects.create_user('ranker')
        self.condition = StartupCondition.objects.create(user=user, location='서울', store_status='none',
                                                         total_budget_manwon=20000, operation='unknown', category='카페',
                                                         deposit_manwon=0, premium_manwon=0, reserve_manwon=0)

    def test_highest_combined_score_first_not_name_order(self):
        ranked = candidate_brands(self.condition, Brand.objects.all(), 2025)
        self.assertEqual([r['brand'].slug for r in ranked], ['b-best', 'a-average', 'c-worst', 'd-missing'])
        best = ranked[0]
        self.assertEqual(best['score']['sales'], 85.7)  # 월 2,000만 vs 업계 평균 1,167만 → 50×1.714
        self.assertEqual(best['score']['closure'], 100.0)  # 5% vs 업계 11.7% → 상한
        self.assertEqual(ranked[-1]['score']['total'], 0.0)  # 공시 값 없음 → 0점
        self.assertEqual(best['peer']['closure']['mine'], 5.0)
        self.assertEqual(best['peer']['cost']['average'], 5833)  # (5000+2500+10000)/3 만원

    def test_small_brand_gets_no_closure_score(self):
        tiny = Brand.objects.create(slug='e-tiny', name='D소형', category='카페', is_demo=False, initial_cost_krw=50_000_000)
        AnnualStat.objects.create(brand=tiny, year=2025, stores=29, opened=1, closed=0,
                                  annual_sales_krw=120_000_000, startup_cost_krw=50_000_000, source_label='test')
        item = next(r for r in candidate_brands(self.condition, Brand.objects.all(), 2025) if r['brand'] == tiny)
        self.assertIsNone(item['score']['closure'])  # 폐업 0건이어도 매장 29개(30개 미만)라 100점을 주지 않음
        self.assertTrue(item['score']['few_stores'])
        self.assertEqual(item['peer']['closure']['mine'], 0.0)  # 폐업률 자체는 그대로 표시

    def test_budget_filter_still_applies(self):
        self.condition.total_budget_manwon = 6000
        self.condition.save()
        slugs = [r['brand'].slug for r in candidate_brands(self.condition, Brand.objects.all(), 2025)]
        self.assertNotIn('c-worst', slugs)  # 1억 > 6천만원
