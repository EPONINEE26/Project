from django.test import TestCase
from django.utils import timezone
from brands.models import AdSlot, Brand
from brands.views import ad_rows
from .views import InquiryForm

class CpcTests(TestCase):
    def test_highest_bid_per_slot_and_tie_order(self):
        brand = Brand.objects.create(name='입찰 브랜드', slug='bid-test', category='카페', is_demo=False)
        today = timezone.localdate()
        def bid(position, value, active=True):
            return AdSlot.objects.create(brand=brand, position=position, cpc_bid_krw=value, starts_on=today, ends_on=today, is_active=active)
        bid(1, 100); winner = bid(1, 300); bid(1, 300); bid(1, 999, False)
        second = bid(2, 50); bid(2, 0)
        rows = ad_rows(2025, '전국')
        self.assertEqual([r['slot'].pk for r in rows], [winner.pk, second.pk])

    def test_bid_requires_position_and_positive_price(self):
        form = InquiryForm(data={'ad_position': 1, 'cpc_bid_krw': 0})
        self.assertIn('cpc_bid_krw', form.errors)
        form = InquiryForm(data={'cpc_bid_krw': 300})
        self.assertIn('ad_position', form.errors)
