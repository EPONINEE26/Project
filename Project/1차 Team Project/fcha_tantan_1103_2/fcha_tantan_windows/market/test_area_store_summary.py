from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .analysis import area_store_summary
from .analysis_models import CommercialArea, DataSource, IndustryCode, PublicStore, StartupCondition


class AreaStoreSummaryTests(TestCase):
    def setUp(self):
        self.source = DataSource.objects.create(name='공공 테스트 출처', collected_on='2026-11-03')
        self.area = CommercialArea.objects.create(
            code='summary', name='집계 테스트 상권', area_type='골목상권', admin_code='test',
            version='project-preview-20261103', source=self.source,
            boundary={'type': 'Polygon', 'coordinates': [[[126, 37], [128, 37], [128, 38], [126, 38], [126, 37]]]},
        )
        self.industry = IndustryCode.objects.create(system='local-sbiz-small-20261103', code='I21201', name='카페')
        for key, industry, area, date in [('cafe', self.industry, self.area, '2026-11-03'),
                                          ('unknown', None, self.area, '2026-11-03'),
                                          ('outside', self.industry, None, '2026-11-03'),
                                          ('old', self.industry, self.area, '2025-01-01')]:
            PublicStore.objects.create(source=self.source, external_id=key, name=key, industry=industry,
                                       area=area, address='서울', latitude='37.5', longitude='127', reference_on=date)

    def test_latest_snapshot_category_and_distribution(self):
        result = area_store_summary(self.area, SimpleNamespace(category='카페'))
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['category_total'], 1)
        self.assertEqual(sum(r['total'] for r in result['industries']), 2)
        self.assertEqual(area_store_summary(self.area, SimpleNamespace(category='치킨'))['category_total'], 0)
        self.assertIsNone(area_store_summary(self.area, SimpleNamespace(category='미분류'))['category_total'])
        self.assertEqual(area_store_summary(self.area, SimpleNamespace(category='전체'))['category_total'], 2)
        self.assertFalse(area_store_summary(None, None)['available'])

    def test_saved_condition_renders_counts_and_empty_states(self):
        user = get_user_model().objects.create_user('summary-user')
        self.client.force_login(user)
        condition = StartupCondition.objects.create(user=user, location='서울', total_budget_manwon=10000,
                                                    store_status='none', category='카페', latitude='37.5', longitude='127')
        response = self.client.get(reverse('brands:bregion'))
        self.assertContains(response, '선택 상권의 공공 매장')
        self.assertContains(response, '공공 테스트 출처')
        self.assertContains(response, '상권 경계 기준')
        self.assertEqual(response.context['public_store_summary']['category_total'], 1)
        condition.category = '미분류'
        condition.save()
        self.assertContains(self.client.get(reverse('brands:bregion')), '업종 대응 미연결')
        PublicStore.objects.filter(area=self.area).delete()
        self.assertContains(self.client.get(reverse('brands:bregion')), '실제 매장이 없다는 뜻은 아닙니다.')
