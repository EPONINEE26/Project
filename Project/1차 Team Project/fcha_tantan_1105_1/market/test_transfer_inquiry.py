from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from brands.models import Brand
from .models import TransferInquiry, TransferListing


class ReceivedInquiryButtonTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user('seller')
        self.buyer = User.objects.create_user('buyer')
        brand = Brand.objects.create(slug='inq-brand', name='브랜드', category='카페', is_demo=False)
        self.listing = TransferListing.objects.create(owner=self.seller, brand=brand, title='카페양도', sido='서울', sigungu='마포구', description='-')
        TransferInquiry.objects.create(listing=self.listing, sender=self.buyer, message='양수 희망합니다')

    def test_seller_sees_button_then_new_badge_once(self):
        self.client.force_login(self.seller)
        detail = reverse('market:transfer_detail', args=[self.listing.pk])
        mine = self.client.get(reverse('market:transfer_mine'))
        self.assertContains(mine, f'href="{detail}#inquiries"')
        self.assertContains(mine, '새 문의 확인 1')
        first = self.client.get(detail)
        self.assertContains(first, 'id="inquiries"')
        self.assertContains(first, 'class="inquiry-new"')  # 처음 확인할 때만 NEW
        self.assertContains(self.client.get(reverse('market:transfer_mine')), '문의 보기')  # 읽음 처리 후
        self.assertNotContains(self.client.get(detail), 'class="inquiry-new"')

    def test_no_button_without_inquiries(self):
        TransferInquiry.objects.all().delete()
        self.client.force_login(self.seller)
        self.assertContains(self.client.get(reverse('market:transfer_mine')), '문의 없음')
