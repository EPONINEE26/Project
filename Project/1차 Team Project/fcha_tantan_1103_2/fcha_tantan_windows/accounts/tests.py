from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from .models import EmailVerification

class AccountSafetyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('member', 'member@example.com', 'Good-password-42')
        self.client.force_login(self.user)

    def test_withdraw_requires_confirmation_password_and_post(self):
        url = reverse('accounts:withdraw')
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.post(url, {'confirmation': '회원탈퇴', 'agree': 'yes', 'password': 'wrong'})
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())
        self.client.post(url, {'confirmation': '회원탈퇴', 'agree': 'yes', 'password': 'Good-password-42'})
        self.assertFalse(get_user_model().objects.filter(pk=self.user.pk).exists())
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_csrf_and_anonymous(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse('accounts:withdraw')).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('accounts:withdraw')).status_code, 302)

    def test_social_account_requires_email_reverification(self):
        self.user.set_unusable_password(); self.user.save()
        self.client.force_login(self.user)
        response = self.client.post(reverse('accounts:withdraw'), {'confirmation': '회원탈퇴', 'agree': 'yes'})
        self.assertContains(response, '현재 계정 이메일로 인증')
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_delivery_failure_does_not_leave_cooldown(self):
        with patch('accounts.email_verify.send_mail', side_effect=OSError('SMTP unavailable')):
            response = self.client.post(reverse('accounts:email_send'), {'email': 'new@example.com'})
        self.assertEqual(response.status_code, 503)
        self.assertFalse(EmailVerification.objects.filter(email='new@example.com').exists())
        response = self.client.post(reverse('accounts:email_send'), {'email': 'new@example.com'})
        self.assertEqual(response.status_code, 200)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
    def test_console_delivery_is_explained(self):
        with patch('accounts.email_verify.send_mail', return_value=1):
            response = self.client.post(reverse('accounts:email_send'), {'email': 'new@example.com'})
        self.assertIn('서버를 실행한 PC', response.json()['message'])
