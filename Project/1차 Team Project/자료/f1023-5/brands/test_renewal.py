from decimal import Decimal
import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, Client
from .models import Brand, AnnualStat, AreaSales
from .calculator import calculate
from .views import brand_row

class RenewalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo',verbosity=0)
        cls.user=get_user_model().objects.create_user(username='tester',password='Strong-test-only-739!')
        cls.other=get_user_model().objects.create_user(username='other',password='Another-test-only-739!')
    def test_private_pages_and_no_public_api_leak(self):
        for url in ['/brands/bview/tantan/','/brands/bcompare/','/brands/calculator/','/brands/compare/csv/','/brands/bsaved/','/brands/bregion/']:
            response=self.client.get(url)
            self.assertEqual(response.status_code,302)
            self.assertTrue(response.url.startswith('/accounts/login/?next='))
        self.assertEqual(self.client.get('/api/v1/brands/tantan/').status_code,401)
        public=self.client.get('/api/v1/brands/').json()['brands'][0]
        self.assertNotIn('costs',public);self.assertNotIn('initial_cost_krw',public)
        self.assertNotIn('regions',public['stats'][0])
        self.client.force_login(self.user)
        for url in ['/brands/bview/tantan/','/brands/bcompare/','/brands/calculator/','/accounts/login/']:
            response=self.client.get(url)
            self.assertIn(response.status_code,[200,302])
        self.assertIn('costs',self.client.get('/api/v1/brands/tantan/').json())
    def test_signup_login_logout_and_redirect_safety(self):
        payload={'username':'new-person','first_name':'새회원','password1':'New-safe-password-739!','password2':'New-safe-password-739!','next':'https://evil.example'}
        r=self.client.post('/accounts/signup/',payload)
        self.assertRedirects(r,'/')
        user=get_user_model().objects.get(username='new-person')
        self.assertTrue(user.check_password(payload['password1']))
        self.assertNotEqual(user.password,payload['password1'])
        self.assertContains(self.client.get('/'),'새회원님')
        self.assertEqual(self.client.get('/accounts/logout/').status_code,405)
        self.client.post('/accounts/logout/')
        self.assertNotIn('_auth_user_id',self.client.session)
        self.assertContains(self.client.post('/accounts/login/',{'username':'new-person','password':'wrong'}),'올바른')
        r=self.client.post('/accounts/login/',{'username':'new-person','password':payload['password1'],'next':'/brands/bview/tantan/?year=2024'})
        self.assertRedirects(r,'/brands/bview/tantan/?year=2024')
    def test_csrf_and_saved_isolation(self):
        c=Client(enforce_csrf_checks=True)
        self.assertEqual(c.post('/accounts/signup/',{}).status_code,403)
        self.client.force_login(self.user)
        self.client.post('/brands/saved/toggle/tantan/')
        self.assertEqual(len(self.client.get('/brands/bsaved/').context['rows']),1)
        self.client.force_login(self.other)
        self.assertEqual(len(self.client.get('/brands/bsaved/').context['rows']),0)
        self.client.force_login(self.user)
        self.assertEqual(len(self.client.get('/brands/bsaved/').context['rows']),1)
    def test_compare_limit_legacy_session_and_safe_json(self):
        session=self.client.session
        session['tantan-compare']=['tantan','morning','may','morning','missing'];session.save()
        self.client.get('/')
        self.assertEqual(self.client.session['tantan-compare'],['tantan','morning'])
        self.client.post('/brands/compare/toggle/may/')
        self.assertEqual(len(self.client.session['tantan-compare']),2)
        self.client.force_login(self.user)
        r=self.client.get('/brands/bcompare/')
        self.assertContains(r,'comparison-data')
        self.assertEqual(len(r.context['comparison_data']['brands']),2)
        self.assertEqual(sum(v is not None for v in r.context['comparison_data']['metrics'][3]['values']),2)
    def test_calculation_values_and_boundaries(self):
        v={key:Decimal(value) for key,value in {'investment':'10000','sales':'2000','rent':'200','labor':'500','other':'100','variable_rate':'40'}.items()}
        r=calculate(v);self.assertEqual(r['profit'],Decimal('400'));self.assertEqual(r['months'],25)
        self.assertAlmostEqual(float(r['bep']),1333.333333,places=4)
        v['investment']=Decimal('10001');self.assertEqual(calculate(v)['months'],26)
        v['sales']=Decimal('1000');self.assertIsNone(calculate(v)['months'])
        v['variable_rate']=Decimal('100');self.assertIsNone(calculate(v)['bep'])
        v['variable_rate']=Decimal('0');v['sales']=Decimal('800');self.assertEqual(calculate(v)['profit'],0);self.assertIsNone(calculate(v)['months'])
    def test_calculator_post_does_not_mutate_stats(self):
        self.client.force_login(self.user)
        before=list(AnnualStat.objects.values())
        data={'brand':'tantan','investment':'10000','sales':'2000','rent':'200','labor':'500','other':'100','variable_rate':'40'}
        r=self.client.post('/brands/calculator/?year=2024',data)
        self.assertEqual(r.status_code,200);self.assertEqual(r.context['result']['months'],25)
        self.assertEqual(before,list(AnnualStat.objects.values()))
        for field,value in [('rent','-1'),('sales','NaN'),('variable_rate','101'),('brand','missing')]:
            invalid={**data,field:value};r=self.client.post('/brands/calculator/',invalid)
            self.assertIsNone(r.context['result']);self.assertTrue(r.context['form'].errors)
    def test_area_sales_missing_zero_units_and_atomic_import(self):
        b=Brand.objects.get(slug='tantan');s=b.annual_stats.get(year=2024)
        self.assertIsNone(brand_row(b,2024)['per_pyeong_annual'])
        AreaSales.objects.create(annual_stat=s,annual_sales_per_pyeong_krw=12000000,source_label='검증 자료')
        row=brand_row(b,2024);self.assertEqual(row['per_pyeong_annual'],1200);self.assertEqual(row['per_pyeong_monthly'],100)
        self.assertEqual(s.annual_sales_krw,312000000)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'area.csv';p.write_text('brand_id,year,annual_sales_per_pyeong_krw,source_label,source_url\ntantan,2024,0,확인자료,\nmissing,2024,1200,확인자료,\n',encoding='utf-8')
            with self.assertRaises(CommandError):call_command('import_area_sales',str(p),demo=True,verbosity=0)
            self.assertEqual(AreaSales.objects.get(annual_stat=s).annual_sales_per_pyeong_krw,12000000)
            p.write_text('brand_id,year,annual_sales_per_pyeong_krw,source_label,source_url\ntantan,2024,0,확인자료,\n',encoding='utf-8')
            call_command('import_area_sales',str(p),demo=True,verbosity=0)
            self.assertEqual(brand_row(b,2024)['per_pyeong_annual'],0)

class UsabilityUpdateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', verbosity=0)
        cls.user = get_user_model().objects.create_user(username='ui-member', first_name='민기테스트', password='Test-739-strong!')
    def setUp(self):
        self.client.force_login(self.user)
    def test_optional_cost_fields_and_integer_inputs(self):
        base = {'brand':'day','investment':'7500','sales':'2392','rent':'250','labor':'500'}
        for optional in [{}, {'other':'','variable_rate':''}]:
            r = self.client.post('/brands/calculator/', {**base, **optional})
            self.assertFalse(r.context['form'].errors)
            self.assertEqual(r.context['result']['profit'], Decimal('1642'))
            self.assertEqual(r.context['result']['months'], 5)
            self.assertContains(r, '1,642<small>만원</small>')
            self.assertNotContains(r, '1,642.00')
        from .calculator import CalculatorForm
        form = CalculatorForm(choices=[('day','데이마켓')])
        for key in ['investment','sales','rent','labor','other','variable_rate']:
            self.assertEqual(str(form.fields[key].widget.attrs['step']), '1')
            r = self.client.post('/brands/calculator/', {**base,key:'1.5'})
            self.assertIn(key, r.context['form'].errors)
        self.assertFalse(form.fields['other'].required)
        self.assertFalse(form.fields['variable_rate'].required)
    def test_rounded_display_keeps_exact_arithmetic(self):
        r = self.client.post('/brands/calculator/', {'brand':'day','investment':'7500','sales':'2392','rent':'250','labor':'500','variable_rate':'1'})
        self.assertEqual(r.context['result']['profit'], Decimal('1618.08'))
        self.assertContains(r, '1,618<small>만원</small>')
        self.assertEqual(r.context['result']['months'],5)
    def test_nickname_navigation_and_card_markup(self):
        r = self.client.get('/')
        self.assertContains(r, 'class="header-nickname"><b>민기테스트</b><span>님</span>')
        self.assertContains(r, '>회수 계산기</a>')
        self.assertNotContains(r, '#support">지원 정보</a>')
        self.assertContains(r, 'data-brand-card', count=8)
        self.assertContains(r, 'class="card-main-link"', count=8)
        for page in ['/brands/bcompare/', '/brands/bview/tantan/', '/brands/calculator/']:
            self.assertContains(self.client.get(page),'class="header-nickname"')
