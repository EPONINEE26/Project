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
        self.assertContains(self.client.get('/'),'src="/app-config.js"')
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
