import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from brands.models import Brand
from .models import ClosureReview, ClosureVerification


class ClosureCommunityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='closure-owner')
        cls.reader = get_user_model().objects.create_user(username='closure-reader')
        cls.staff = get_user_model().objects.create_superuser(
            username='closure-admin', email='admin@example.com', password='test-only',
        )
        cls.brand = Brand.objects.create(slug='closure-test', name='테스트 브랜드', category='카페', is_demo=False)
        cls.verification = ClosureVerification.objects.create(
            user=cls.owner, brand=cls.brand, store_name='테스트점',
            business_number='1234567890', opened_on=date(2020, 1, 1),
            closed_on=date(2025, 1, 1), closure_file='test/closure.pdf',
            operation_file='test/operation.pdf', consent_at=timezone.now(), status='approved',
        )

    def payload(self, **changes):
        data = dict(verification=self.verification.pk, title='매장 운영 경험',
                    content='매장을 운영하며 배운 경험입니다.', advantages='운영 지원',
                    disadvantages='운영 비용', advice='상권과 비용을 확인하세요.',
                    brand_rating=3, restart_interest=2)
        data.update(changes)
        return data

    def create_review(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('community:closure_write'), self.payload())
        self.assertEqual(response.status_code, 302)
        return ClosureReview.objects.get()

    def test_anonymous_access_and_navigation(self):
        review = self.create_review()
        self.client.logout()
        response = self.client.get(reverse('community:closure_list'))
        self.assertContains(response, '로그인 또는 회원가입')
        self.assertContains(response, reverse('community:closure_list'))
        self.assertIn('no-store', response['Cache-Control'])
        for css_class in ('community-hero', 'community-layout', 'community-feed', 'community-side', 'community-search'):
            self.assertContains(response, css_class)
        self.assertNotContains(response, review.title)
        self.assertNotContains(response, review.content)

    def test_boards_share_community_navigation_and_layout(self):
        index = self.client.get(reverse('community:index'))
        self.assertContains(index, reverse('community:closure_list'))
        self.client.force_login(self.reader)
        response = self.client.get(reverse('community:closure_list'))
        self.assertEqual(response.context['page'], 'community')
        self.assertEqual(response.context['community_board'], 'closure')
        for css_class in ('community-hero', 'community-layout', 'community-feed', 'community-side'):
            self.assertContains(response, css_class)
        self.assertContains(response, '폐점주 커뮤니티')
        header = response.content.decode().split('</header>', 1)[0]
        self.assertIn('href="' + reverse('community:closure_list') + '"', header)
        self.assertIn(reverse('community:index'), header)

    def test_review_lifecycle_and_owner_permissions(self):
        review = self.create_review()
        detail = reverse('community:closure_detail', args=[review.pk])
        edit = reverse('community:closure_edit', args=[review.pk])
        delete = reverse('community:closure_delete', args=[review.pk])
        self.assertContains(self.client.get(detail), review.title)
        self.assertContains(self.client.get(edit), '폐업 경험 수정')
        self.client.force_login(self.reader)
        self.assertContains(self.client.get(reverse('community:closure_list')), review.title)
        self.assertContains(self.client.get(detail), review.content)
        self.assertNotContains(self.client.get(detail), self.verification.business_number)
        self.assertEqual(self.client.post(edit, self.payload()).status_code, 404)
        self.assertEqual(self.client.post(delete).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(edit, self.payload(title='수정한 경험')).status_code, 302)
        review.refresh_from_db()
        self.assertEqual(review.title, '수정한 경험')
        self.assertEqual(self.client.get(delete).status_code, 200)
        self.assertTrue(ClosureReview.objects.exists())
        self.assertEqual(self.client.post(delete).status_code, 302)
        self.assertFalse(ClosureReview.objects.exists())

    def test_unapproved_and_other_users_verifications_are_rejected(self):
        self.client.force_login(self.reader)
        self.assertRedirects(self.client.post(reverse('community:closure_write'), self.payload()),
                             reverse('community:closure_verify'))
        self.verification.status = 'pending'
        self.verification.save()
        self.client.force_login(self.owner)
        self.assertRedirects(self.client.post(reverse('community:closure_write'), self.payload()),
                             reverse('community:closure_verify'))
        self.assertFalse(ClosureReview.objects.exists())

    def test_revocation_hides_review_and_blocks_edit(self):
        review = self.create_review()
        self.verification.status = 'revoked'
        self.verification.save()
        self.client.force_login(self.reader)
        self.assertNotContains(self.client.get(reverse('community:closure_list')), review.title)
        self.assertEqual(self.client.get(reverse('community:closure_detail', args=[review.pk])).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(reverse('community:closure_edit', args=[review.pk]), self.payload()).status_code, 302)
        self.assertEqual(self.client.post(reverse('community:closure_delete', args=[review.pk])).status_code, 302)

    def test_verification_upload_and_admin_approval(self):
        self.client.force_login(self.owner)
        with tempfile.TemporaryDirectory() as directory:
            storage = FileSystemStorage(location=directory)
            fields = [ClosureVerification._meta.get_field(name) for name in ('closure_file', 'operation_file')]
            with patch.object(fields[0], 'storage', storage), patch.object(fields[1], 'storage', storage):
                response = self.client.post(reverse('community:closure_verify'), {
                    'brand': self.brand.slug, 'store_name': '새 지점', 'business_number': '1234567890',
                    'opened_on': '2020-01-01', 'closed_on': '2025-01-01', 'consent': 'on',
                    'closure_file': SimpleUploadedFile('closure.pdf', b'%PDF-1.4 evidence'),
                    'operation_file': SimpleUploadedFile('operation.pdf', b'%PDF-1.4 evidence'),
                })
                self.assertEqual(response.status_code, 302)
                item = ClosureVerification.objects.exclude(pk=self.verification.pk).get()
                self.assertEqual(item.status, 'pending')
                self.assertEqual(item.user, self.owner)
                self.assertTrue(Path(item.closure_file.path).exists())
                url = reverse('community:closure_document', args=[item.pk, 'closure'])
                self.assertEqual(self.client.get(url).status_code, 403)
                self.client.force_login(self.staff)
                download = self.client.get(url)
                self.assertEqual(download.status_code, 200)
                self.assertEqual(b''.join(download.streaming_content), b'%PDF-1.4 evidence')
                download.close()
        self.assertIn(ClosureVerification, admin.site._registry)
        self.assertIn(ClosureReview, admin.site._registry)
        self.client.force_login(self.staff)
        change = reverse('admin:community_closureverification_change', args=[self.verification.pk])
        self.assertEqual(self.client.get(change).status_code, 200)
        response = self.client.post(change, {'status': 'approved', 'decision_reason': ''})
        self.assertContains(response, '승인 전 확인이 필요합니다.')
        response = self.client.post(change, {
            'status': 'approved', 'decision_reason': '', 'identity_checked': 'on',
            'closure_checked': 'on', 'brand_checked': 'on', '_save': '저장',
        })
        self.assertEqual(response.status_code, 302)
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.reviewed_by, self.staff)
