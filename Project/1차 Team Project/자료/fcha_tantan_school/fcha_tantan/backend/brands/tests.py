import csv
import json
import tempfile
from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from .models import Brand,AnnualStat,RegionalStat

class DataFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):call_command('seed_demo',verbosity=0)
    def test_demo_api_and_frontend(self):
        result=self.client.get('/api/v1/brands/')
        self.assertEqual(result.status_code,200)
        data=result.json();self.assertEqual(len(data['brands']),8)
        self.assertEqual(data['years'],[2025,2024]);self.assertTrue(data['is_demo'])
        self.assertEqual(len(data['brands'][0]['stats'][0]['regions']),17)
        self.assertContains(self.client.get('/'), 'brands/css/style.css')
        self.assertEqual(self.client.get('/api/v1/brands/unknown/').status_code,404)
        self.assertEqual(self.client.post('/api/v1/brands/').status_code,405)
    def test_seed_idempotent(self):
        call_command('seed_demo',verbosity=0)
        self.assertEqual(Brand.objects.count(),8)
        self.assertEqual(AnnualStat.objects.count(),16)
        self.assertEqual(RegionalStat.objects.count(),272)
    def test_csv_round_trip_and_demo_guard(self):
        path=settings.BASE_DIR.parent/'docs/sample_stats.csv'
        call_command('import_stats',str(path),demo=True,verbosity=0)
        self.assertEqual(AnnualStat.objects.get(brand__slug='tantan',year=2024).stores,1240)
        with self.assertRaises(CommandError):call_command('import_stats',str(path),verbosity=0)
    def test_bad_csv_rolls_back_and_null_is_preserved(self):
        source=settings.BASE_DIR.parent/'docs/sample_stats.csv'
        with source.open(encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
        for row in rows:row['brand_id']='real-test';row['closed']=''
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'data.csv'
            def write():
                with path.open('w',encoding='utf-8-sig',newline='') as f:
                    w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
            write();call_command('import_stats',str(path),verbosity=0)
            self.assertIsNone(AnnualStat.objects.get(brand__slug='real-test',year=2024).closed)
            api=self.client.get('/api/v1/brands/').json()
            self.assertFalse(api['is_demo']);self.assertEqual(len(api['brands']),1)
            for row in rows:row['brand_id']='bad-test'
            rows[-1]['region_stores']='99999';write()
            with self.assertRaises(CommandError):call_command('import_stats',str(path),verbosity=0)
            self.assertFalse(Brand.objects.filter(slug='bad-test').exists())

class SchoolPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', verbosity=0)

    def test_pages_and_templates(self):
        pages = {'/': 'home/index.html', '/brands/blist/': 'brands/blist.html', '/brands/bview/tantan/': 'brands/bview.html', '/brands/bcompare/': 'brands/bcompare.html', '/brands/bregion/': 'brands/bregion.html', '/brands/bsaved/': 'brands/bsaved.html', '/brands/guide/': 'brands/guide.html'}
        for url, template in pages.items():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)
                self.assertNotContains(response, '#/brand/')
                self.assertNotContains(response, 'js/app.js')
        self.assertEqual(self.client.get('/brands/bview/unknown/').status_code, 404)

    def test_filters(self):
        r = self.client.get('/brands/blist/', {'year': 2024, 'category': '카페', 'region': '서울', 'sort': 'sales'})
        self.assertEqual(len(r.context['rows']), 2)
        self.assertEqual(r.context['rows'][0]['brand'].slug, 'morning')
        self.assertEqual(r.context['rows'][0]['stat'].year, 2024)
        self.assertContains(self.client.get('/brands/blist/?query=없는브랜드'), '조건에 맞는 브랜드가 없어요')
        r = self.client.get('/brands/blist/?year=invalid&region=invalid&sort=invalid')
        self.assertEqual(r.context['year'], 2025)
        self.assertEqual(r.context['region'], '전국')

    def test_compare_and_csv(self):
        ids = list(Brand.objects.values_list('slug', flat=True))
        for slug in ids[:4]: self.client.post(f'/brands/compare/toggle/{slug}/')
        self.assertEqual(len(self.client.session['tantan-compare']), 3)
        r = self.client.get('/brands/bcompare/?year=2024')
        self.assertEqual(len(r.context['rows']), 3)
        r = self.client.get('/brands/compare/csv/?year=2024')
        self.assertTrue(r.content.startswith(b'\xef\xbb\xbf'))
        rows = list(csv.reader(r.content.decode('utf-8-sig').splitlines()))
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[1][1], '2024')
        self.client.post(f'/brands/compare/toggle/{ids[0]}/')
        self.assertEqual(len(self.client.session['tantan-compare']), 2)
        self.client.post('/brands/compare/clear/')
        self.assertEqual(self.client.session['tantan-compare'], [])

    def test_saved_and_post_security(self):
        from django.test import Client
        r = self.client.post('/brands/saved/toggle/tantan/', {'next': '/brands/bsaved/?year=2024'})
        self.assertRedirects(r, '/brands/bsaved/?year=2024')
        self.assertEqual(len(self.client.get('/brands/bsaved/').context['rows']), 1)
        self.client.post('/brands/saved/toggle/tantan/')
        self.assertContains(self.client.get('/brands/bsaved/'), '관심 브랜드가 없어요')
        self.assertEqual(self.client.get('/brands/compare/toggle/tantan/').status_code, 405)
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/brands/saved/toggle/tantan/').status_code, 403)
        client.get('/brands/blist/')
        r = client.post('/brands/saved/toggle/tantan/', {'csrfmiddlewaretoken': client.cookies['csrftoken'].value, 'next': 'https://outside.example/'})
        self.assertRedirects(r, '/brands/blist/')

    def test_detail_and_region(self):
        r = self.client.get('/brands/bview/tantan/?year=2024')
        row = r.context['row']
        self.assertEqual(row['stores'], 1240)
        self.assertEqual(row['monthly'], round(row['stat'].annual_sales_krw / 12 / 10000))
        self.assertEqual(len(r.context['regional_rows']), 17)
        self.assertEqual(sum(x['count'] for x in r.context['regional_rows']), row['stores'])
        r = self.client.get('/brands/bregion/?year=2024&region=서울')
        self.assertEqual(r.context['total'], sum(x['stores'] for x in r.context['rows']))
        self.assertEqual(len(r.context['tiles']), 17)

    def test_real_data_null_escape_and_stale_session(self):
        b = Brand.objects.create(slug='real', name='<script>alert(1)</script>', category='카페', is_demo=False)
        s = AnnualStat.objects.create(brand=b, year=2025, stores=1, opened=0, closed=None, annual_sales_krw=None, source_label='검수된 자료')
        RegionalStat.objects.create(annual_stat=s, region='서울', stores=None)
        self.client.post('/brands/compare/toggle/real/')
        r = self.client.get('/brands/blist/')
        self.assertFalse(r.context['is_demo'])
        self.assertEqual(len(r.context['rows']), 1)
        self.assertContains(r, '미제공')
        self.assertContains(r, '&lt;script&gt;')
        self.assertNotContains(r, '<script>alert(1)</script>')
        self.assertContains(self.client.get('/brands/bregion/?region=서울'), '미제공')
        self.assertEqual(self.client.get('/brands/bview/tantan/').status_code, 404)
        b.delete()
        self.client.get('/brands/bcompare/')
        self.assertEqual(self.client.session['tantan-compare'], [])
