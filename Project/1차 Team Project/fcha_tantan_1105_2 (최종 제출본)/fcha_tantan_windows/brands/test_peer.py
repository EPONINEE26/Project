from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import AnnualStat, Brand
from .views import brand_row, peer_context, with_stats


class PeerComparisonTests(TestCase):
    def setUp(self):
        rows = [  # name, stores, opened, closed, annual sales, startup cost
            ('#알파', 1000, 100, 50, 600_000_000, 80_000_000),
            ('베타', 100, 10, 10, 240_000_000, 40_000_000),
            ('감마', 10, None, None, None, 30_000_000),
        ]
        for i, (name, stores, opened, closed, sales, cost) in enumerate(rows):
            brand = Brand.objects.create(slug=f'peer-{i}', name=name, category='편의점', is_demo=False)
            AnnualStat.objects.create(brand=brand, year=2025, stores=stores, opened=opened, closed=closed,
                                      annual_sales_krw=sales, startup_cost_krw=cost, source_label='test')
        other = Brand.objects.create(slug='other', name='다른업종', category='카페', is_demo=False)
        AnnualStat.objects.create(brand=other, year=2025, stores=99999, source_label='test')
        self.brand = with_stats(Brand.objects.all()).get(slug='peer-0')

    def test_averages_skip_missing_values_and_stay_in_category(self):
        row = brand_row(self.brand, 2025)
        peer = peer_context(self.brand, 2025, row, 80_000_000)
        self.assertEqual(peer['brand_count'], 3)
        self.assertEqual(peer['stores']['average'], 370)  # (1000+100+10)/3, other category excluded
        self.assertEqual(peer['opened']['average'], 55)  # missing value is not counted as 0
        self.assertEqual(peer['opened']['count'], 2)
        self.assertEqual(peer['monthly']['average'], 3500)  # (6억+2.4억)/2/12 in 10,000 KRW
        self.assertEqual(peer['closure'], {'mine': 5.0, 'average': 5.5, 'count': 2})  # (50+10)/(1000+100)
        self.assertEqual(peer['stores']['mine_width'], 100.0)

    def test_cost_position_ratio_and_rank(self):
        row = brand_row(self.brand, 2025)
        cost = peer_context(self.brand, 2025, row, 80_000_000)['cost']
        self.assertEqual(cost['average'], 5000)
        self.assertEqual(cost['ratio'], 160)
        self.assertEqual(cost['difference'], 3000)
        self.assertEqual(cost['rank'], 1)
        self.assertEqual(cost['median'], 40_000_000)
        self.assertEqual(cost['mine_position'], 100.0)
        self.assertEqual(peer_context(self.brand, 2025, row, None)['cost'], None)

    def test_detail_page_shows_cards_without_old_captions(self):
        self.client.force_login(get_user_model().objects.create_user('peer-viewer'))
        response = self.client.get(reverse('brands:bview', args=['peer-0']), {'year': 2025})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="detail-cta" href="#"')
        self.assertContains(response, '업계 평균', count=None)
        self.assertContains(response, '편의점 업종 안에서의 위치')
        self.assertContains(response, '160%')
        self.assertNotContains(response, '선택 연도 말 영업 매장 수')
        self.assertNotContains(response, '선택 연도 내 신규 개업 합계')
