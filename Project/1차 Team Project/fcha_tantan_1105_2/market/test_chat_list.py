from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from brands.models import Brand
from .models import TransferInquiry, TransferListing


class ChatListTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller, self.buyer, self.other = (User.objects.create_user(n) for n in ('seller', 'buyer', 'other'))
        brand = Brand.objects.create(slug='chat-brand', name='브랜드', category='카페', is_demo=False)
        listing = TransferListing.objects.create(owner=self.seller, brand=brand, title='카페양도', sido='서울', sigungu='마포구', description='-')
        self.inquiry = TransferInquiry.objects.create(listing=listing, sender=self.buyer, message='양수 희망합니다')

    def summary(self, user):
        self.client.force_login(user)
        return self.client.get(reverse('market:chat_summary')).json()

    def test_unread_counts_and_reading_clears_them(self):
        self.assertEqual(self.summary(self.seller)['unread'], 1)  # 확인 전 첫 문의
        self.assertEqual(self.summary(self.buyer)['unread'], 0)
        self.client.force_login(self.seller)
        self.client.get(reverse('market:transfer_chat', args=[self.inquiry.pk]))
        self.client.post(reverse('market:transfer_chat', args=[self.inquiry.pk]), {'body': '안녕하세요'})
        self.assertEqual(self.summary(self.seller)['unread'], 0)
        data = self.summary(self.buyer)
        self.assertEqual(data['unread'], 1)  # 상대가 보낸 새 메시지
        self.assertEqual(data['items'][0]['text'], '안녕하세요')
        self.client.get(reverse('market:transfer_chat', args=[self.inquiry.pk]))
        self.assertEqual(self.summary(self.buyer)['unread'], 0)

    def test_list_page_menu_and_privacy(self):
        self.client.force_login(self.seller)
        page = self.client.get(reverse('market:chat_list'))
        self.assertContains(page, '카페양도')
        self.assertContains(page, '새 채팅 1')
        self.assertContains(page, 'href="' + reverse('market:chat_list') + '"')  # 햄버거 '전체 대화'
        self.assertContains(page, 'data-chat-alert')  # 오른쪽 아래 알림
        self.assertEqual(self.summary(self.other)['items'], [])  # 남의 대화는 보이지 않음
        self.client.logout()
        self.assertEqual(self.client.get(reverse('market:chat_summary')).status_code, 302)

    def test_summary_includes_all_rooms_and_unique_unread_people(self):
        for n in range(9):
            TransferInquiry.objects.create(listing=self.inquiry.listing, sender=self.buyer, message=f'Inquiry {n}')
        self.inquiry.chat_messages.create(sender=self.buyer, body='Additional message')
        data = self.summary(self.seller)
        self.assertEqual(len(data['items']), 10)
        self.assertEqual(data['unread'], 11)
        self.assertEqual(data['unread_people'], 1)
        room = next(item for item in data['items'] if item['url'] == reverse('market:transfer_chat', args=[self.inquiry.pk]))
        self.assertEqual(room['unread'], 2)
        self.assertEqual(room['partner'], self.buyer.username)
