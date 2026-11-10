from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from brands.models import Brand
from .models import TransferInquiry, TransferListing


class TransferChatTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.seller = users.objects.create_user('chat-seller')
        self.buyer = users.objects.create_user('chat-buyer')
        self.stranger = users.objects.create_user('chat-stranger')
        brand = Brand.objects.create(slug='chat-brand', name='Brand', category='Cafe')
        listing = TransferListing.objects.create(owner=self.seller, brand=brand, title='Listing')
        self.inquiry = TransferInquiry.objects.create(listing=listing, sender=self.buyer, message='Original inquiry')
        self.url = reverse('market:transfer_chat', args=[self.inquiry.pk])

    def test_participants_can_exchange_messages(self):
        for user, body in [(self.seller, 'Seller reply'), (self.buyer, 'Buyer reply')]:
            self.client.force_login(user)
            self.assertRedirects(self.client.post(self.url, {'body': body}), self.url)
            self.assertContains(self.client.get(self.url), body)
        self.assertEqual(self.inquiry.chat_messages.count(), 2)
        self.inquiry.refresh_from_db()
        self.assertTrue(self.inquiry.is_read)

    def test_other_users_cannot_read_or_send(self):
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, {'body': 'Intrusion'}).status_code, 404)
        self.assertFalse(self.inquiry.chat_messages.exists())

    def test_login_and_message_validation(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.buyer)
        for body in ['   ', 'a' * 1001]:
            self.assertEqual(self.client.post(self.url, {'body': body}).status_code, 200)
        self.assertFalse(self.inquiry.chat_messages.exists())

    def test_message_html_is_escaped(self):
        self.client.force_login(self.buyer)
        self.client.post(self.url, {'body': '<script>alert(1)</script>'})
        response = self.client.get(self.url)
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')
