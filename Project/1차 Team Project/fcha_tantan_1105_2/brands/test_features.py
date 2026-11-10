"""2026-10-26 추가 기능 테스트: JSON 연동, 페이지 번호·검색, 광고, 회원가입, 추천, 후기, 파트너, 매장 위치, 양도양수."""
import json
import tempfile
from datetime import date, timedelta
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from accounts.models import MemberProfile
from market.models import FloatingPopulation, StoreLocation, TransferInquiry, TransferListing
from partners.models import BusinessProposal, PartnerAccount, PartnerPlan
from .models import AdSlot, AnnualStat, AreaSales, Brand, BrandReview, OwnerVerification, RegionalStat
from .reviews import add_months, eligible_verification
from .constants import REGIONS

User = get_user_model()


def json_brand(i, category='카페', stores=10, sales=None, cost=50000000, seoul=3, closed=1):
    regions = {r: {'stores': (seoul if r == '서울' else 1), 'annual_sales_min_krw': 100000000, 'annual_sales_max_krw': 120000000,
                   'sales_status': 'range'} for r in REGIONS}
    return {'id': f'test_{i:04d}', 'name': f'테스트브랜드{i:04d}', 'category': category,
            'image': None, 'official_brand_id': f'BRD_{i}', 'company': '(주)테스트', 'source_category': '커피',
            'is_displayable': True, 'history': [{
                'year': 2025, 'source_accounting_year': 2024, 'stores': stores, 'opened': 2, 'closed': closed,
                'annual_sales_krw': sales, 'annual_sales_per_3_3sqm_krw': (12000000 if i == 3 else None), 'startup_cost_krw': cost,
                'startup_cost_breakdown': {'franchise_fee_krw': 1000000, 'education_fee_krw': None, 'guarantee_deposit_krw': 0, 'other_cost_krw': 2000000},
                'national_reference': {'annual_sales_min_krw': 240000000, 'annual_sales_max_krw': 360000000, 'sales_status': 'range'},
                'regions': regions}]}


class ImportedDataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        items = [json_brand(i, stores=100 - i, sales=(360000000 if i == 3 else None)) for i in range(25)]
        items.append(json_brand(99, category='치킨', stores=5))
        items.append({**json_brand(98), 'is_displayable': False})
        path = Path(cls.tmp.name) / 'priority.json'
        path.write_text(json.dumps(items, ensure_ascii=False), encoding='utf-8')
        call_command('seed_demo', verbosity=0)
        call_command('import_fcha_json', str(path), verbosity=0)
        cls.path = path
        cls.user = User.objects.create_user(username='member', password='Test-only-pass-739!')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.tmp.cleanup()

    def setUp(self):
        self.client.force_login(self.user)

    def test_import_values_null_policy_and_idempotent(self):
        self.assertEqual(Brand.objects.filter(is_demo=False).count(), 26)  # 표시 불가 1개 제외
        stat = AnnualStat.objects.get(brand__slug='test_0000', year=2025)
        self.assertIsNone(stat.annual_sales_krw)  # null을 0으로 바꾸지 않음
        self.assertEqual((stat.sales_min_krw, stat.sales_max_krw), (240000000, 360000000))
        self.assertEqual(stat.startup_cost_breakdown['교육비'], None)
        self.assertEqual(stat.startup_cost_breakdown['계약보증금'], 0)
        self.assertEqual(stat.regional_stats.count(), 17)
        self.assertFalse(AreaSales.objects.filter(annual_stat=stat).exists())  # 3.3㎡당 매출 null은 행을 만들지 않음
        call_command('import_fcha_json', str(self.path), verbosity=0)
        self.assertEqual(AnnualStat.objects.filter(brand__is_demo=False).count(), 26)
        self.assertEqual(AreaSales.objects.get(annual_stat__brand__slug='test_0003', annual_stat__year=2025).annual_sales_per_pyeong_krw, 12000000)
        self.assertEqual(AreaSales.objects.filter(annual_stat__brand__is_demo=False).count(), 1)  # 다시 가져와도 중복 없음
        self.assertEqual(RegionalStat.objects.filter(annual_stat__brand__is_demo=False).count(), 26 * 17)

    def test_import_reads_gzip_copy(self):
        import gzip
        gz = Path(self.tmp.name) / 'brands.json.gz'
        with gzip.open(gz, 'wt', encoding='utf-8') as f:
            f.write(self.path.read_text(encoding='utf-8'))
        call_command('import_fcha_json', str(gz), verbosity=0)
        self.assertEqual(Brand.objects.filter(is_demo=False).count(), 26)

    def test_list_pagination_10_per_page_and_range_display(self):
        r = self.client.get('/brands/blist/')
        self.assertEqual(r.context['total_count'], 26)
        self.assertEqual(len(r.context['rows']), 10)
        self.assertEqual(r.context['rows'][0]['brand'].slug, 'test_0000')  # 매장 수 많은 순
        self.assertContains(r, 'class="pagination"')
        self.assertContains(r, '2,000~3,000')  # 범위 매출 2.4억~3.6억 ÷ 12
        page3 = self.client.get('/brands/blist/?page=3')
        self.assertEqual(len(page3.context['rows']), 6)
        self.assertEqual(self.client.get('/brands/blist/?page=99').context['page_obj'].number, 3)
        self.assertEqual(self.client.get('/?category=치킨').context['total_count'], 1)
        self.assertEqual(self.client.get('/brands/blist/?query=0024').context['total_count'], 1)
        sales = self.client.get('/brands/blist/?sort=sales')
        self.assertEqual(sales.context['rows'][0]['brand'].slug, 'test_0003')  # 단일 공시 매출이 하한보다 큼

    def test_region_search_and_pagination(self):
        r = self.client.get('/brands/bregion/?region=서울')
        self.assertEqual(r.context['total_count'], 26)
        self.assertEqual(len(r.context['rows']), 10)
        self.assertEqual(r.context['total'], 26 * 3)
        self.assertContains(r, '833~1,000만원')  # 지역 매출 범위 1억~1.2억 ÷ 12
        searched = self.client.get('/brands/bregion/?region=서울&query=0001')
        self.assertEqual(searched.context['total_count'], 1)
        self.assertEqual(searched.context['total'], 3)
        self.assertEqual(self.client.get('/brands/bregion/?region=서울&category=치킨').context['total_count'], 1)
        self.assertEqual(self.client.get('/brands/bregion/?region=서울&page=3').context['page_obj'].number, 3)

    def test_ad_slots_top_two_regardless_of_sort(self):
        r = self.client.get('/')
        self.assertContains(r, 'ad-empty', count=2)
        small = Brand.objects.get(slug='test_0024')
        today = timezone.localdate()
        AdSlot.objects.create(position=1, cpc_bid_krw=100, brand=small, starts_on=today, ends_on=today + timedelta(days=7))
        AdSlot.objects.create(position=2, cpc_bid_krw=100, brand=small, starts_on=today - timedelta(days=9), ends_on=today - timedelta(days=1))
        for url in ['/', '/brands/blist/?sort=name']:
            r = self.client.get(url)
            self.assertEqual(r.context['ad_rows'][0]['row']['brand'], small)
            self.assertIsNone(r.context['ad_rows'][1]['slot'])  # 기간 지난 광고는 빈 자리
            html = r.content.decode()
            self.assertLess(html.index('data-ad-card="1"'), html.index('data-brand-card'))
        self.assertEqual(self.client.get('/brands/bsaved/').context['ad_rows'], [])

    def test_detail_uses_yearly_startup_cost_and_reviews_section(self):
        r = self.client.get('/brands/bview/test_0001/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['cost_total'], 50000000)
        self.assertContains(r, 'id="reviews"')
        self.assertContains(r, '계약서 인증하기')

    def test_transfer_widget_on_three_pages_only(self):
        for url in ['/', '/brands/blist/', '/brands/bregion/']:
            self.assertContains(self.client.get(url), 'data-transfer-widget')
        self.assertNotContains(self.client.get('/brands/bcompare/'), 'data-transfer-widget')
        self.assertContains(self.client.get('/'), '>양도양수</a>')


def signup_payload(**extra):
    data = {'username': 'founder', 'first_name': '예비사장', 'password1': 'Founder-pass-739!', 'password2': 'Founder-pass-739!',
            'phone': '010 9876 5432', 'email': 'Founder@Example.com', 'postcode': '08754',
            'address': '서울 관악구 신림로 1', 'address_detail': '101호', 'wants_startup': 'yes', 'startup_purpose': 'living',
            'budget_manwon': '6000', 'target_monthly_sales_manwon': '2000', 'desired_region': '서울', 'desired_category': '카페',
            'agree_privacy': 'on'}
    data.update({'plan_location':'서울 관악구 신림동','plan_store_status':'none','plan_total_budget_manwon':'6000','plan_operation':'direct','plan_category':'카페'})
    data.update(extra)
    return data


def verify_email(client, email):
    """인증번호 받기 → 메일에서 6자리 읽기 → 인증 확인 (테스트 메일함 사용)."""
    import re
    from django.core import mail
    r = client.post('/accounts/email/send/', {'email': email})
    assert r.json()['ok'], r.json()
    code = re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1)
    r = client.post('/accounts/email/check/', {'email': email, 'code': code})
    assert r.json()['ok'], r.json()
    return code


class SignupRecommendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        tmp = tempfile.TemporaryDirectory()
        items = [json_brand(1, cost=40000000, seoul=40, closed=0), json_brand(2, cost=90000000), json_brand(3, cost=None, seoul=0),
                 json_brand(4, category='치킨', cost=10000000)]
        path = Path(tmp.name) / 'p.json'
        path.write_text(json.dumps(items, ensure_ascii=False), encoding='utf-8')
        call_command('import_fcha_json', str(path), verbosity=0)
        tmp.cleanup()

    def test_signup_requires_email_verification_and_no_rrn(self):
        page = self.client.get('/accounts/signup/')
        self.assertNotContains(page, 'rrn_front')
        self.assertNotContains(page, '주민등록번호')
        self.assertContains(page, '인증번호 받기')
        r = self.client.post('/accounts/signup/', signup_payload())  # 인증 전
        self.assertIn('이메일 인증', str(r.context['form'].errors['email']))
        verify_email(self.client, 'founder@example.com')
        r = self.client.post('/accounts/signup/', signup_payload(rrn_front='950727'))  # 보내도 저장 안 함
        self.assertEqual(r.status_code, 302)
        user = User.objects.get(username='founder')
        profile = user.member_profile
        self.assertEqual(user.email, 'founder@example.com')
        self.assertIsNone(profile.birth_date)
        self.assertIsNotNone(profile.email_verified_at)
        self.assertTrue(profile.wants_startup)
        self.assertEqual(profile.phone, '010-9876-5432')
        self.assertFalse(profile.agree_marketing)
        # 인증한 이메일과 다른 이메일로는 가입 불가, 필수 동의 없으면 불가
        self.client.logout()
        verify_email(self.client, 'other@example.com')
        r = self.client.post('/accounts/signup/', signup_payload(username='x2', email='third@example.com'))
        self.assertTrue(r.context['form'].errors['email'])
        r = self.client.post('/accounts/signup/', signup_payload(username='x2', email='other@example.com', agree_privacy=''))
        self.assertTrue(r.context['form'].errors['agree_privacy'])
        self.assertEqual(self.client.post('/accounts/email/send/', {'email': 'FOUNDER@example.com'}).json()['message'], '이미 가입된 이메일입니다.')

    def test_email_code_rules(self):
        from accounts.models import EmailVerification
        self.assertFalse(self.client.post('/accounts/email/send/', {'email': 'not-an-email'}).json()['ok'])
        self.assertTrue(self.client.post('/accounts/email/send/', {'email': 'a@example.com'}).json()['ok'])
        self.assertEqual(self.client.post('/accounts/email/send/', {'email': 'a@example.com'}).status_code, 429)  # 60초 재발송 제한
        record = EmailVerification.objects.get()
        self.assertNotRegex(record.code_hash, r'^\d{6}$')  # 번호는 해시로만 저장
        for i in range(5):
            r = self.client.post('/accounts/email/check/', {'email': 'a@example.com', 'code': '000000' if i % 2 else '999999'})
        record.refresh_from_db()
        self.assertEqual(record.attempts, 5)
        self.assertIn('다시 받아주세요', self.client.post('/accounts/email/check/', {'email': 'a@example.com', 'code': '123456'}).json()['message'])
        EmailVerification.objects.update(created_at=timezone.now() - timedelta(minutes=11), attempts=0)
        self.assertIn('만료', self.client.post('/accounts/email/check/', {'email': 'a@example.com', 'code': '123456'}).json()['message'])

    def test_startup_question_controls_extra_fields(self):
        verify_email(self.client, 'founder@example.com')
        r = self.client.post('/accounts/signup/', signup_payload(plan_total_budget_manwon='', plan_location=''))  # 예 → 조건 필수
        self.assertIn('plan_total_budget_manwon', r.context['form'].errors)
        self.assertIn('plan_location', r.context['form'].errors)
        r = self.client.post('/accounts/signup/', signup_payload(wants_startup='no', budget_manwon='', desired_region='', agree_proposal='on'))
        self.assertEqual(r.status_code, 302)
        profile = User.objects.get(username='founder').member_profile
        self.assertFalse(profile.wants_startup)
        self.assertIsNone(profile.budget_manwon)  # 창업 목적이 아니면 조건·사업제안 동의 저장 안 함
        self.assertFalse(profile.agree_proposal)
        self.assertEqual(self.client.get('/brands/bregion/').context['analysis_candidates'], [])

    def test_social_buttons_hidden_without_keys(self):
        r = self.client.get('/accounts/login/')
        self.assertContains(r, '간편하게 시작하기')
        self.assertContains(r, 'disabled')
        self.assertNotContains(r, '/oauth/naver/login/')

    def test_incomplete_social_profile_is_redirected(self):
        user = User.objects.create_user(username='social1', password='x-Test-739!')
        MemberProfile.objects.create(user=user, signup_source='social', is_complete=False)
        self.client.force_login(user)
        self.assertRedirects(self.client.get('/brands/blist/'), '/accounts/profile/', fetch_redirect_response=False)
        self.assertEqual(self.client.get('/accounts/profile/').status_code, 200)
        verify_email(self.client, 'social@example.com')
        r = self.client.post('/accounts/profile/', signup_payload(email='social@example.com'))
        self.assertRedirects(r, '/brands/bregion/', fetch_redirect_response=False)  # 추천 페이지 삭제 → 지역상권분석
        user.member_profile.refresh_from_db()
        self.assertTrue(user.member_profile.is_complete)
        self.assertEqual(self.client.get('/brands/blist/').status_code, 200)
        # 같은(인증된) 이메일로 내 정보를 고칠 때는 다시 인증하지 않아도 됩니다.
        r = self.client.post('/accounts/profile/', signup_payload(email='social@example.com', budget_manwon='7000'))
        self.assertRedirects(r, '/accounts/profile/', fetch_redirect_response=False)

    def test_recommendation_respects_budget_category_and_region(self):
        verify_email(self.client, 'founder@example.com')
        self.client.post('/accounts/signup/', signup_payload())
        r = self.client.get('/brands/bregion/')  # 추천 페이지 삭제 → 같은 후보를 지역상권분석에서 사용
        slugs = [item['brand'].slug for item in r.context['analysis_candidates']]
        self.assertIn('test_0001', slugs)       # 예산 이내 + 서울 매장 많음 + 해지 0
        self.assertNotIn('test_0002', slugs)          # 예산(6,000만원) 초과 제외
        self.assertNotIn('test_0004', slugs)          # 희망 업종(카페) 아님
        self.assertIn('test_0003', slugs)             # 비용 미공개는 감점 후 포함
        self.assertContains(r, '지역 적합도 순위는 아닙니다')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', verbosity=0)
        cls.owner = User.objects.create_user(username='owner', password='Owner-pass-739!')
        cls.admin = User.objects.create_superuser(username='boss', password='Boss-pass-739!', email='b@example.com')

    def test_add_months_month_end(self):
        self.assertEqual(add_months(date(2026, 8, 31), 6), date(2027, 2, 28))

    def test_review_requires_approved_contract_and_6_months(self):
        self.client.force_login(self.owner)
        brand = Brand.objects.get(slug='tantan')
        self.assertRedirects(self.client.get('/brands/bview/tantan/review/'), '/brands/bview/tantan/verify/', fetch_redirect_response=False)
        upload = SimpleUploadedFile('계약서.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        start = timezone.localdate() - timedelta(days=150)  # 약 5개월
        r = self.client.post('/brands/bview/tantan/verify/', {'store_name': '탄탄 신림점', 'contract_start_date': start, 'contract_file': upload, 'business_file': SimpleUploadedFile('business.pdf', b'%PDF-1.4 certificate')})
        self.assertEqual(r.status_code, 302)
        verification = OwnerVerification.objects.get(user=self.owner)
        self.assertNotIn('계약서', verification.contract_file.name)  # 원래 파일명 저장 안 함
        self.assertIsNone(eligible_verification(self.owner, brand))  # 승인 전
        verification.status = 'approved'; verification.save()
        self.assertIsNone(eligible_verification(self.owner, brand))  # 6개월 미만
        verification.contract_start_date = timezone.localdate() - timedelta(days=200); verification.save()
        self.assertIsNotNone(eligible_verification(self.owner, brand))
        r = self.client.post('/brands/bview/tantan/review/', {'rating': '4', 'title': '운영 6개월 후기', 'content': '본사 지원이 꾸준합니다.'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(BrandReview.objects.get().rating, 4)
        page = self.client.get('/brands/bview/tantan/')
        self.assertContains(page, '운영 6개월 후기')
        self.assertEqual(page.context['review_avg'], 4.0)

    def test_contract_file_only_for_staff_and_bad_type_rejected(self):
        self.client.force_login(self.owner)
        r = self.client.post('/brands/bview/tantan/verify/', {'store_name': 'a', 'contract_start_date': '2025-01-01',
                                                              'contract_file': SimpleUploadedFile('x.exe', b'MZ')})
        self.assertTrue(r.context['form'].errors['contract_file'])
        self.client.post('/brands/bview/tantan/verify/', {'store_name': 'a', 'contract_start_date': '2025-01-01',
                                                          'contract_file': SimpleUploadedFile('c.png', b'\x89PNG\r\n\x1a\n'), 'business_file': SimpleUploadedFile('business.pdf', b'%PDF-1.4 certificate')})
        pk = OwnerVerification.objects.get().pk
        self.assertEqual(self.client.get(f'/brands/contracts/{pk}/').status_code, 302)  # 관리자 로그인으로 이동
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(f'/brands/contracts/{pk}/').status_code, 200)


class PartnerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', verbosity=0)
        cls.partner_user = User.objects.create_user(username='brandhq', password='Brand-pass-739!')
        cls.consent = User.objects.create_user(username='yes', first_name='동의회원', email='yes@example.com', password='Yes-pass-739!')
        cls.no_consent = User.objects.create_user(username='no', first_name='거부회원', password='No-pass-739!')
        MemberProfile.objects.create(user=cls.consent, phone='010-1111-2222', desired_region='서울', desired_category='카페',
                                     budget_manwon=5000, agree_proposal=True, agree_privacy_at=timezone.now())
        MemberProfile.objects.create(user=cls.no_consent, phone='010-3333-4444', desired_region='서울', agree_proposal=False)

    def test_pricing_page_plans_and_inquiry(self):
        r = self.client.get('/partners/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context['plans']), 3)
        self.assertContains(r, '예시(확정 전)')
        r = self.client.post('/partners/', {'company': '(주)탄탄', 'brand_name': '탄탄커피', 'contact_name': '김담당', 'phone': '01055556666',
                                            'email': 'hq@example.com', 'plan': PartnerPlan.objects.first().pk, 'message': '광고 문의', 'agree_privacy': 'on'})
        self.assertEqual(r.status_code, 302)

    def test_leads_only_consented_and_contact_after_accept(self):
        self.client.force_login(self.partner_user)
        self.assertRedirects(self.client.get('/partners/leads/'), '/partners/', fetch_redirect_response=False)
        account = PartnerAccount.objects.create(user=self.partner_user, brand=Brand.objects.get(slug='tantan'), company='(주)탄탄',
                                                contact_name='김담당', contact_phone='010-5555-6666', business_number='123-45-67890', status='approved')
        r = self.client.get('/partners/leads/')
        names = [lead['name'] for lead in r.context['leads']]
        self.assertEqual(names, ['동***'])
        self.assertNotContains(r, '010-1111-2222')
        self.assertNotContains(r, '거부회원')
        profile = self.consent.member_profile
        self.client.post(f'/partners/leads/{profile.pk}/propose/', {'title': '서울 신규 출점 제안', 'message': '상담을 제안드립니다.'})
        self.client.post(f'/partners/leads/{profile.pk}/propose/', {'title': '중복', 'message': '중복'})
        self.assertEqual(BusinessProposal.objects.count(), 1)  # 30일 내 중복 제안 차단
        self.assertEqual(self.client.post(f'/partners/leads/{self.no_consent.member_profile.pk}/propose/', {'title': 'a', 'message': 'b'}).status_code, 404)
        self.client.force_login(self.consent)
        proposal = BusinessProposal.objects.get()
        self.assertContains(self.client.get('/partners/proposals/'), '서울 신규 출점 제안')
        self.client.post(f'/partners/proposals/{proposal.pk}/respond/', {'action': 'accepted'})
        self.client.force_login(self.partner_user)
        self.assertContains(self.client.get('/partners/leads/'), '010-1111-2222')

    def test_monthly_limit(self):
        plan = PartnerPlan.objects.create(name='한도1', summary='t', monthly_proposal_limit=1)
        account = PartnerAccount.objects.create(user=self.partner_user, brand=Brand.objects.get(slug='tantan'), company='c', contact_name='n',
                                                contact_phone='010-1-1', business_number='1', status='approved', plan=plan)
        other = User.objects.create_user(username='yes2', password='Yes2-pass-739!')
        p2 = MemberProfile.objects.create(user=other, agree_proposal=True)
        self.client.force_login(self.partner_user)
        self.client.post(f'/partners/leads/{self.consent.member_profile.pk}/propose/', {'title': 'a', 'message': 'b'})
        self.client.post(f'/partners/leads/{p2.pk}/propose/', {'title': 'a', 'message': 'b'})
        self.assertEqual(account.proposals.count(), 1)


class MarketTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', verbosity=0)
        cls.seller = User.objects.create_user(username='seller', first_name='양도인', password='Seller-pass-739!')
        cls.buyer = User.objects.create_user(username='buyer', first_name='양수인', password='Buyer-pass-739!')
        MemberProfile.objects.create(user=cls.buyer, phone='010-7777-8888')

    def test_store_location_and_population(self):
        self.client.force_login(self.seller)
        brand = Brand.objects.get(slug='tantan')
        r = self.client.post('/market/stores/new/', {'store_name': '신림 후보지', 'brand': '탄탄커피 (tantan)', 'status': 'planned', 'postcode': '08754',
                                                    'address': '서울 관악구 신림로 1', 'sido': '서울', 'sigungu': '관악구', 'dong': '신림동',
                                                    'latitude': '37.484200', 'longitude': '126.929700', 'area_pyeong': '15.5'})
        self.assertEqual(r.status_code, 302)
        store = StoreLocation.objects.get()
        bad = self.client.post('/market/stores/new/', {'store_name': 'x', 'status': 'planned', 'address': 'a', 'sido': '서울', 'latitude': '10', 'longitude': '10'})
        self.assertTrue(bad.context['form'].errors)
        self.client.post(f'/market/stores/{store.pk}/', {'measured_on': '2026-10-20', 'day_type': 'weekday', 'time_slot': 'all', 'count': '12000', 'method': 'manual'})
        self.client.post(f'/market/stores/{store.pk}/', {'measured_on': '2026-10-21', 'day_type': 'weekday', 'time_slot': 'all', 'count': '14000', 'method': 'public', 'source_note': '서울시 상권분석'})
        self.assertEqual(FloatingPopulation.objects.count(), 2)
        r = self.client.get(f'/market/stores/{store.pk}/')
        self.assertContains(r, '13,000')
        self.assertContains(r, '카카오 지도 키')
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(f'/market/stores/{store.pk}/').status_code, 404)  # 남의 매장 접근 불가

    def test_transfer_listing_search_inquiry_and_phone_sharing(self):
        brand = Brand.objects.get(slug='tantan')
        self.assertEqual(self.client.get('/market/transfer/new/').status_code, 302)
        self.client.force_login(self.seller)
        r = self.client.post('/market/transfer/new/', {'brand': '탄탄커피', 'title': '신림역 3분 탄탄커피 양도', 'sido': '서울', 'sigungu': '관악구',
                                                      'premium_manwon': '3000', 'contract_status': 'active', 'description': '계약 2년 남음', 'status': 'open'})
        self.assertEqual(r.status_code, 302)
        listing = TransferListing.objects.get()
        for i in range(11):
            TransferListing.objects.create(owner=self.seller, brand=brand, title=f'부산 매물 {i}', sido='부산', sigungu='해운대구', description='-')
        self.client.logout()
        r = self.client.get('/market/transfer/')
        self.assertEqual(r.context['total_count'], 12)
        self.assertEqual(len(r.context['listings']), 10)
        self.assertEqual(self.client.get('/market/transfer/?query=신림').context['total_count'], 1)
        self.assertEqual(self.client.get('/market/transfer/?sido=부산').context['total_count'], 11)
        home = self.client.get('/')  # 우측 고정 패널: 최신 3건 + 전체 건수
        self.assertContains(home, '부산 매물 10')
        self.assertNotContains(home, '부산 매물 7')
        self.assertContains(home, '<em>12</em>')
        self.client.force_login(self.buyer)
        self.assertNotContains(self.client.get(f'/market/transfer/{listing.pk}/'), 'name="share_phone"')
        self.client.post(f'/market/transfer/{listing.pk}/', {'kind': 'acquire', 'message': '양수 희망합니다'})
        self.assertEqual(TransferInquiry.objects.count(), 1)
        self.assertNotContains(self.client.get(f'/market/transfer/{listing.pk}/'), '010-7777-8888')  # 문의자 본인 화면에는 목록 없음
        self.client.force_login(self.seller)
        r = self.client.get(f'/market/transfer/{listing.pk}/')
        self.assertNotContains(r, '010-7777-8888')
        self.assertTrue(TransferInquiry.objects.get().is_read)
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(f'/market/transfer/{listing.pk}/edit/').status_code, 404)


class AllCategoriesTests(TestCase):
    """brands.json 전체 업종: 대분류 칩 + 세부 업종 선택, 브랜드 검색 입력칸."""
    @classmethod
    def setUpTestData(cls):
        tmp = tempfile.TemporaryDirectory()
        items = [json_brand(1, category='한식', stores=50), json_brand(2, category='한식', stores=40),
                 json_brand(3, category='카페', stores=30), json_brand(4, category='세탁', stores=20),
                 json_brand(5, category='편의점', stores=10), json_brand(6, category='세탁', stores=5),
                 json_brand(7, category='화장품', stores=4), json_brand(8, category='의류 / 패션', stores=3),
                 json_brand(9, category='기타 외식', stores=2), json_brand(10, category='새로운업종', stores=1)]
        majors = {'한식': '외식', '카페': '외식', '세탁': '서비스', '편의점': '도소매', '화장품': '도소매',
                  '의류 / 패션': '도소매', '기타 외식': '외식', '새로운업종': '서비스'}
        for item in items:
            item['source_category_major'] = majors[item['category']]
        items[5]['name'] = items[0]['name']  # 다른 업종에 같은 이름 브랜드
        path = Path(tmp.name) / 'brands.json'
        path.write_text(json.dumps(items, ensure_ascii=False), encoding='utf-8')
        call_command('import_fcha_json', str(path), verbosity=0)
        tmp.cleanup()
        cls.user = User.objects.create_user(username='cat', password='Cat-pass-739!')

    def test_group_tiles_and_sub_categories(self):
        r = self.client.get('/brands/blist/')
        # 화면용 업종 묶음 순서(커피·한식·편의점·도소매·세탁·기타), 데이터가 있는 묶음만
        self.assertEqual(r.context['group_names'], ['전체', '커피', '한식', '편의점', '도소매', '세탁·빨래방', '기타'])
        self.assertContains(r, 'name="group" value="세탁·빨래방"')
        self.assertNotContains(r, 'class="sub-chips"')  # 묶음을 고르기 전에는 세부 칩 없음
        groups = {g['name']: [c['name'] for c in g['categories']] for g in r.context['category_groups']}
        self.assertEqual(groups['도소매'], ['의류 / 패션', '화장품'])  # 브랜드 수가 같으면 이름순
        self.assertEqual(sorted(groups['기타']), ['기타 외식', '새로운업종'])  # 애매한 업종·목록에 없는 업종은 기타
        r = self.client.get('/brands/blist/?group=도소매')
        self.assertEqual(r.context['total_count'], 2)
        self.assertContains(r, 'class="sub-chips"')  # 세부 업종이 2개 이상이면 세부 칩
        self.assertNotContains(self.client.get('/brands/blist/?group=한식'), 'class="sub-chips"')  # 1개뿐이면 생략
        r = self.client.get('/brands/blist/?category=세탁')
        self.assertEqual((r.context['group'], r.context['total_count']), ('세탁·빨래방', 2))  # 세부 업종만 오면 묶음 자동 선택
        r = self.client.get('/brands/blist/?group=도소매&category=한식')  # 묶음과 안 맞는 세부 업종은 해제
        self.assertEqual((r.context['category'], r.context['total_count']), ('전체', 2))
        self.assertEqual(self.client.get('/brands/blist/?category=없는업종').context['total_count'], 10)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/brands/bregion/?region=서울&category=세탁').context['total_count'], 2)
        self.assertContains(self.client.get('/brands/bregion/'), '<optgroup label="🧺 세탁·빨래방">')

    def test_brand_lookup_endpoint_and_field(self):
        data = self.client.get('/brands/lookup/?q=0003').json()['results']
        self.assertEqual(data[0]['value'], '테스트브랜드0003 (test_0003)')
        self.assertEqual(self.client.get('/brands/lookup/?q=').json()['results'], [])
        from .lookup import BrandLookupField
        field = BrandLookupField()
        self.assertEqual(field.clean('테스트브랜드0003').slug, 'test_0003')        # 유일한 이름
        self.assertEqual(field.clean('아무거나 (test_0006)').slug, 'test_0006')    # 괄호 안 식별자 우선
        with self.assertRaises(Exception):
            field.clean('테스트브랜드0001')  # 같은 이름 2개 → 목록에서 골라야 함

    def test_profile_category_choices_come_from_db(self):
        from accounts.forms import ProfileForm
        choices = dict(ProfileForm().fields['desired_category'].choices)
        self.assertIn('🧺 세탁·빨래방', choices)  # 드롭다운 묶음·업종에 아이콘 표시
        self.assertEqual(choices['🧺 세탁·빨래방'], [('세탁', '🧺 세탁')])  # 저장 값은 아이콘 없는 업종명

    def test_api_is_paginated(self):
        data = self.client.get('/api/v1/brands/').json()
        self.assertEqual((data['count'], data['page'], len(data['brands'])), (10, 1, 10))
