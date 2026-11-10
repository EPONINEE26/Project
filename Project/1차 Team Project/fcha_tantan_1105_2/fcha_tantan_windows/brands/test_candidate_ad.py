from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import AdSlot, AnnualStat, Brand
from .views import ad_rows, candidate_ad


class RegionCandidateAdTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.low = self.brand('ad-low')
        self.high = self.brand('ad-high')
        self.client.force_login(get_user_model().objects.create_user('ad-viewer'))

    def brand(self, slug):
        brand = Brand.objects.create(slug=slug, name=slug, category='주점', is_demo=False)
        AnnualStat.objects.create(brand=brand, year=2025, stores=40, opened=4, closed=2, annual_sales_krw=360_000_000,
                                  startup_cost_krw=50_000_000, source_label='test')
        return brand

    def slot(self, brand, bid, position=3, days=7):
        return AdSlot.objects.create(brand=brand, position=position, cpc_bid_krw=bid, starts_on=self.today, ends_on=self.today + timedelta(days=days))

    def test_empty_slot_shows_bid_card_first(self):
        self.assertIsNone(candidate_ad(2025)['row'])
        page = self.client.get(reverse('brands:bregion'))
        self.assertContains(page, 'AD · 3번 자리')
        self.assertContains(page, '?ad_position=3#inquiry')

    def test_highest_bid_wins_and_positions_stay_independent(self):
        self.slot(self.low, 100)
        self.slot(self.high, 300)
        self.slot(self.low, 999, position=1)  # 브랜드 탐색 1번 구좌 입찰은 3번 경매와 무관
        ad = candidate_ad(2025)
        self.assertEqual(ad['row']['brand'], self.high)
        self.assertIn('total', ad['score'])
        self.assertEqual([a['position'] for a in ad_rows(2025, '전국')], [1, 2])  # 기존 1·2번 구좌 동작 유지
        page = self.client.get(reverse('brands:bregion'))
        self.assertContains(page, 'AD · 광고')
        self.assertContains(page, 'data-ad-card="3"')
