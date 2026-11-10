from decimal import Decimal
from django.test import TestCase,Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .analysis_models import StartupCondition,DataSource,CommercialArea,PopulationStat,PublicStore
from .analysis_forms import StartupConditionForm
from .analysis import selected_area,candidate_brands
from brands.models import Brand,AnnualStat

class AnalysisTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('analysis-user',password='safe-test-pass')
        self.client.force_login(self.user)
        self.payload={'location':'서울 관악구 신림동','store_status':'none','total_budget_manwon':'10000','operation':'unknown','location_scope':'dong','area_unit':'pyeong','radius_m':'500','condition_action':'save'}
    def test_create_edit_clear_and_delete_across_pages(self):
        a=reverse('brands:bregion');b=reverse('brands:recommend')
        self.assertEqual(self.client.post(a,self.payload).status_code,302)
        row=StartupCondition.objects.get(user=self.user);self.assertEqual(row.total_budget_manwon,10000)
        response=self.client.get(b);self.assertEqual(response.status_code,200);self.assertContains(response,'서울 관악구 신림동')
        data={**self.payload,'rent_manwon':'0','target_profit_manwon':'300'}
        self.client.post(b,data);row.refresh_from_db();self.assertEqual(row.rent_manwon,0)
        self.client.post(a,{**self.payload,'rent_manwon':''});row.refresh_from_db();self.assertIsNone(row.rent_manwon)
        self.assertEqual(self.client.post(b,{'condition_action':'delete'}).status_code,302)
        self.assertFalse(StartupCondition.objects.filter(user=self.user).exists())
    def test_required_validation_and_optional_unknown(self):
        form=StartupConditionForm({**self.payload,'operation':''});self.assertFalse(form.is_valid())
        form=StartupConditionForm(self.payload);self.assertTrue(form.is_valid(),form.errors)
        self.assertIsNone(form.cleaned_data['weekend'])
    def test_region_omits_removed_inputs_and_preserves_saved_values(self):
        from datetime import date
        from .analysis_forms import RegionConditionForm
        row = StartupCondition.objects.create(
            user=self.user, location='서울', store_status='none', total_budget_manwon=10000,
            operation='direct', management_manwon=10, deposit_manwon=2000,
            premium_manwon=500, experience='기존 경험', can_cook=True,
            opening_date=date(2027, 1, 1),
        )
        removed = ['operation', 'management_manwon', 'deposit_manwon', 'premium_manwon',
                   'experience', 'can_cook', 'opening_date']
        response = self.client.get(reverse('brands:bregion'))
        for name in removed:
            self.assertNotContains(response, 'name="' + name + '"')
        payload = {key: value for key, value in self.payload.items() if key not in removed}
        form = RegionConditionForm(payload, instance=row)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(self.client.post(reverse('brands:bregion'), payload).status_code, 302)
        saved = StartupCondition.objects.get(pk=row.pk)
        for name in removed:
            self.assertEqual(getattr(saved, name), getattr(row, name))
    def test_coordinate_precision_and_range(self):
        data={**self.payload,'latitude':'37.123456789012345','longitude':'127.123456789012345'}
        form=StartupConditionForm(data);self.assertTrue(form.is_valid(),form.errors)
        self.assertEqual(form.cleaned_data['latitude'],Decimal(data['latitude']))
        self.assertFalse(StartupConditionForm({**data,'latitude':'91'}).is_valid())
        self.assertFalse(StartupConditionForm({**data,'longitude':''}).is_valid())
    def test_owner_isolation(self):
        other=get_user_model().objects.create_user('other')
        StartupCondition.objects.create(user=other,location='다른 사람 주소',store_status='none',total_budget_manwon=0,operation='unknown')
        self.client.post(reverse('brands:bregion'),{'condition_action':'delete'})
        self.assertTrue(StartupCondition.objects.filter(user=other).exists())
        self.assertNotContains(self.client.get(reverse('brands:bregion')),'다른 사람 주소')
    def test_csrf_and_methods(self):
        c=Client(enforce_csrf_checks=True);c.force_login(self.user)
        self.assertEqual(c.post(reverse('brands:bregion'),self.payload).status_code,403)
        self.assertEqual(self.client.delete(reverse('brands:recommend')).status_code,405)
    def test_area_version_ambiguity(self):
        source=DataSource.objects.create(name='test-source',collected_on='2026-01-01')
        self.client.post(reverse('brands:bregion'),{**self.payload,'latitude':'37.5','longitude':'127.0'})
        condition=StartupCondition.objects.get(user=self.user)
        geo={'type':'Polygon','coordinates':[[[126,37],[128,37],[128,38],[126,38],[126,37]]]}
        kwargs=dict(code='test',name='test',area_type='test',admin_code='test',boundary=geo,effective_on='2026-01-01',verified=True,source=source)
        area=CommercialArea.objects.create(version='v1',**kwargs)
        self.assertEqual(selected_area(condition)[0],area)
        CommercialArea.objects.create(version='v2',**kwargs)
        self.assertIsNone(selected_area(condition)[0])
    def test_budget_zero_and_missing_are_distinct(self):
        self.client.post(reverse('brands:bregion'),{**self.payload,'total_budget_manwon':'0'})
        condition=StartupCondition.objects.get(user=self.user)
        brand=Brand.objects.create(slug='test-cost',name='test-cost',category='coffee',initial_cost_krw=100)
        self.assertEqual(candidate_brands(condition,Brand.objects.filter(pk=brand.pk),2025),[])
    def test_signup_reuses_required_fields(self):
        from accounts.forms import SignupForm
        form=SignupForm(data={'wants_startup':'yes'})
        form.is_valid()
        self.assertIn('plan_location',form.errors)
        self.assertIn('plan_operation',form.errors)
        self.assertNotIn('target_monthly_sales_manwon',form.errors)
    def test_population_source_and_zero_rendering(self):
        source=DataSource.objects.create(name='검증출처',collected_on='2026-01-01')
        area=CommercialArea.objects.create(code='test',version='v1',name='test',area_type='test',admin_code='test',boundary={'type':'Polygon','coordinates':[[[126,37],[128,37],[128,38],[126,38],[126,37]]]},effective_on='2026-01-01',verified=True,source=source)
        PopulationStat.objects.create(area=area,source=source,period='2026Q2',unit='명',kind='floating',total=0,by_age={'20대':0})
        self.client.post(reverse('brands:bregion'),{**self.payload,'latitude':'37.5','longitude':'127'})
        response=self.client.get(reverse('brands:bregion'))
        self.assertContains(response,'검증출처');self.assertContains(response,'0 명');self.assertContains(response,'2026Q2')
