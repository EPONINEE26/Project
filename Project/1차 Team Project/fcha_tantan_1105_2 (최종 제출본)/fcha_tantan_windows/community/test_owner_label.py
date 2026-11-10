from datetime import date
from types import SimpleNamespace
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
import tempfile
from brands.models import Brand, OwnerVerification
from brands.templatetags.brand_format import owner_label


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class OwnerLabelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('owner')
        self.brand = Brand.objects.create(slug='mega', name='메가커피', category='카페', is_demo=False)

    def verify(self, store, status='approved'):
        OwnerVerification.objects.create(user=self.user, brand=self.brand, store_name=store, status=status,
                                         contract_start_date=date(2025, 1, 1),
                                         contract_file=SimpleUploadedFile('c.pdf', b'%PDF-1.4'))

    def item(self):
        return SimpleNamespace(author_id=self.user.pk, brand_id=self.brand.pk, brand=self.brand)

    def test_store_name_is_shown_with_brand(self):
        self.verify('신림역점')
        self.assertEqual(owner_label(self.item()), '메가커피 신림역점 점주')

    def test_star_reviews_stay_branch_private(self):
        # 2026-11-05: 지점명 공개는 커뮤니티만. 브랜드 상세의 별점 후기 목록은 지점명 비공개 유지.
        from django.template.loader import get_template
        source = get_template('bview.html').template.source
        self.assertIn('인증 점주 · 운영 {{ review.months }}개월', source)
        self.assertNotIn('store_name', source)
        self.assertNotIn('owner_label', source)

    def test_brand_not_repeated_and_pending_ignored(self):
        self.verify('메가커피 강남역점')
        self.assertEqual(owner_label(self.item()), '메가커피 강남역점 점주')
        OwnerVerification.objects.all().update(status='pending')
        self.assertEqual(owner_label(self.item()), '메가커피 점주')  # 승인 전 가맹점명은 표시하지 않음
