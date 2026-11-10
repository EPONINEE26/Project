from decimal import Decimal
from django.test import TestCase,Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .analysis_models import StartupCondition,DataSource,CommercialArea,PopulationStat,PublicStore
from .analysis_forms import StartupConditionForm
from .analysis import selected_area,candidate_brands
from brands.models import Brand,AnnualStat

class AnalysisTests(TestCase):
    def test_preview_area_keeps_unverified_status_and_discloses_limitations(self):
        from types import SimpleNamespace
        source = DataSource.objects.create(name='preview', collected_on='2026-11-03')
        area = CommercialArea.objects.create(
            code='preview', version='project-preview-20261103', name='미리보기 상권',
            area_type='골목상권', admin_code='sample', source=source,
            boundary={'type': 'Polygon', 'coordinates': [[[127, 37], [128, 37], [128, 38], [127, 38], [127, 37]]]},
        )
        condition = SimpleNamespace(longitude=Decimal('127.5'), latitude=Decimal('37.5'))
        selected, note = selected_area(condition)
        self.assertEqual(selected.pk, area.pk)
        self.assertFalse(selected.verified)
        self.assertIn('미리보기', note)
        area.version = 'unreviewed'
        area.save()
        self.assertIsNone(selected_area(condition)[0])

    def setUp(self):
        self.user=get_user_model().objects.create_user('analysis-user',password='safe-test-pass')
        self.client.force_login(self.user)
        self.payload={'location':'서울 관악구 신림동','store_status':'none','total_budget_manwon':'10000','operation':'unknown','location_scope':'dong','area_unit':'pyeong','radius_m':'500','condition_action':'save'}
    def test_create_edit_clear_and_delete_across_pages(self):
        # 2026-11-05 맞춤 브랜드 추천 페이지 삭제: 예전 주소는 지역상권분석으로 이동
        a=reverse('brands:bregion')
        self.assertRedirects(self.client.get(reverse('brands:recommend')),a,fetch_redirect_response=False)
        self.assertEqual(self.client.post(a,self.payload).status_code,302)
        row=StartupCondition.objects.get(user=self.user);self.assertEqual(row.total_budget_manwon,10000)
        response=self.client.get(a);self.assertEqual(response.status_code,200);self.assertContains(response,'서울 관악구 신림동')
        self.client.post(a,{**self.payload,'rent_manwon':'0'});row.refresh_from_db();self.assertEqual(row.rent_manwon,0)
        self.client.post(a,{**self.payload,'rent_manwon':''});row.refresh_from_db();self.assertIsNone(row.rent_manwon)
        self.assertEqual(self.client.post(a,{'condition_action':'delete'}).status_code,302)
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
    def test_region_new_condition_defaults_required_store_status(self):
        # 2026-11-05: 지역상권분석은 위치·업종·반경·예산만 받습니다. 점포 확보 여부는 처음 저장 때 '아직 없음'.
        from .analysis_forms import RegionConditionForm
        form = RegionConditionForm()
        self.assertNotIn('store_status', form.fields)
        self.assertEqual(sorted(n for n in form.fields if n not in ('latitude', 'longitude', 'location_scope', 'rent_manwon', 'target_ages')),
                         ['category', 'location', 'radius_m', 'total_budget_manwon'])
        response = self.client.post(reverse('brands:bregion'), self.payload)
        self.assertEqual(response.status_code, 302)
        row = StartupCondition.objects.get(user=self.user)
        self.assertEqual(row.store_status, 'none')
        page = self.client.get(reverse('brands:bregion'))
        self.assertNotContains(page, '☷ 상세조건')
        self.assertNotContains(page, 'name="channels"')

    def test_region_save_keeps_removed_detail_values(self):
        from .analysis_forms import RegionConditionForm
        row = StartupCondition.objects.create(
            user=self.user, location='서울', store_status='secured', total_budget_manwon=10000, operation='unknown',
            channels=['takeout'], available_slots=['evening'], weekend=True, staff_count=3, reserve_manwon=500,
            target_profit_manwon=300, preferred_area_types=['office'], area=20, floor='1층')
        form = RegionConditionForm({**self.payload, 'radius_m': 1000}, instance=row)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        row.refresh_from_db()
        self.assertEqual(row.radius_m, 1000)
        self.assertEqual((row.store_status, row.channels, row.available_slots, row.weekend, row.staff_count),
                         ('secured', ['takeout'], ['evening'], True, 3))
        self.assertEqual((row.reserve_manwon, row.target_profit_manwon, row.preferred_area_types, row.floor),
                         (500, 300, ['office'], '1층'))

    def test_nearby_area_geometry_without_saving_location(self):
        source = DataSource.objects.create(name='nearby', collected_on='2026-11-03')
        geometry = {'type': 'Polygon', 'coordinates': [[[127, 37], [127.001, 37], [127.001, 37.001], [127, 37.001], [127, 37]]]}
        CommercialArea.objects.create(code='nearby', name='Nearby area', version='project-preview-20261103', area_type='test', admin_code='test', source=source, boundary=geometry)
        url = reverse('market:analysis_geometry')
        data = self.client.get(url, {'lat': '37.0005', 'lng': '127.002'}).json()
        self.assertEqual(len(data['areas']), 1)
        self.assertFalse(data['areas'][0]['contains'])
        self.assertGreater(data['areas'][0]['distance_m'], 0)
        self.assertLess(data['areas'][0]['distance_m'], 1000)
        inside = self.client.get(url, {'lat': '37.0005', 'lng': '127.0005'}).json()
        self.assertTrue(inside['areas'][0]['contains'])
        self.assertEqual(inside['areas'][0]['distance_m'], 0)
        self.assertEqual(self.client.get(url, {'lat': '38', 'lng': '128'}).json()['areas'], [])
        self.assertEqual(self.client.get(url, {'lat': 'nan', 'lng': '127'}).status_code, 400)
        self.assertEqual(self.client.get(url, {'lat': '37'}).status_code, 400)
        self.assertFalse(StartupCondition.objects.filter(user=self.user).exists())

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
        self.assertEqual(self.client.delete(reverse('brands:bregion')).status_code,405)
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
        self.assertContains(response, '검증출처')
        self.assertContains(response, '0 <small>명</small>', html=True)
        self.assertContains(response, '최신유동인구')
        self.assertContains(response, '2026년 2분기')
