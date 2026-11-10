from tempfile import TemporaryDirectory
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse
from brands.models import Brand
from .models import TransferListing, TransferDocument, TransferInquiry
from .templatetags.market_tags import transfer_widget


class TransferApprovalTests(TestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.settings = override_settings(MEDIA_ROOT=self.media.name)
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        users = get_user_model()
        self.owner = users.objects.create_user('approval-owner')
        self.buyer = users.objects.create_user('approval-buyer')
        self.staff = users.objects.create_superuser('approval-admin', 'admin@example.com', 'test-password')
        self.brand = Brand.objects.create(slug='approval-brand', name='승인브랜드', category='카페', is_demo=False)
        self.data = dict(brand=self.brand.slug, title='검토할매물', sido='서울', sigungu='마포구',
                         description='매장 인수 조건', contract_status='active', status='open')
        self.client.force_login(self.owner)

    def upload(self, name='lease.pdf'):
        return SimpleUploadedFile(name, b'%PDF-1.4 test contract', content_type='application/pdf')

    def submit(self):
        return self.client.post(reverse('market:transfer_new'), {**self.data, 'documents': [self.upload(), self.upload('other.pdf')]})

    def test_submission_documents_notice_session_and_public_visibility(self):
        response = self.submit()
        self.assertRedirects(response, reverse('market:transfer_list'), fetch_redirect_response=False)
        listing = TransferListing.objects.get()
        self.assertEqual(listing.approval_status, 'pending')
        self.assertEqual(listing.documents.count(), 2)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.owner.pk)
        page = self.client.get(response.url)
        self.assertContains(page, '운영일 기준 2일')
        self.assertNotContains(page, self.data['title'])
        self.assertNotContains(self.client.get(response.url), '매물이 접수되었습니다.')
        self.assertEqual(transfer_widget({})['total'], 0)
        self.client.force_login(self.buyer)
        detail = reverse('market:transfer_detail', args=[listing.pk])
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.assertEqual(self.client.post(detail, {'kind': 'question', 'message': '문의'}).status_code, 404)
        self.assertFalse(TransferInquiry.objects.exists())
        request = RequestFactory().post('/')
        request.user = self.staff
        model_admin = admin.site._registry[TransferListing]
        model_admin.message_user = lambda *args, **kwargs: None
        model_admin.approve(request, TransferListing.objects.all())
        listing.refresh_from_db()
        self.assertEqual(listing.reviewed_by, self.staff)
        self.assertEqual(listing.approval_status, 'approved')
        self.assertContains(self.client.get(response.url), self.data['title'])
        self.assertEqual(transfer_widget({})['total'], 1)
        self.assertEqual(self.client.get(detail).status_code, 200)

    def test_documents_required_and_extensions_validated(self):
        for documents in ([], [self.upload('lease.exe')], [self.upload() for _ in range(6)]):
            response = self.client.post(reverse('market:transfer_new'), {**self.data, 'documents': documents})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors.get('documents'))
        self.assertFalse(TransferListing.objects.exists())

    def test_download_is_admin_only_and_edit_requires_reapproval(self):
        self.submit()
        listing = TransferListing.objects.get()
        listing.approval_status = 'approved'
        listing.save()
        document = TransferDocument.objects.first()
        download = reverse('admin:market_transfer_document', args=[document.pk])
        self.assertEqual(self.client.get(download).status_code, 302)
        self.client.force_login(self.staff)
        result = self.client.get(download)
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result['Content-Disposition'].startswith('attachment;'))
        result.close()
        self.client.force_login(self.owner)
        response = self.client.post(reverse('market:transfer_edit', args=[listing.pk]), self.data)
        self.assertEqual(response.status_code, 302)
        listing.refresh_from_db()
        self.assertEqual(listing.approval_status, 'pending')
        self.assertEqual(listing.documents.count(), 2)
