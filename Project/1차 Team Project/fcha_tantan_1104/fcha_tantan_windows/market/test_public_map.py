import hashlib
import json
import tempfile
from datetime import date
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from brands.models import Brand, OwnerVerification
from .analysis_models import DataSource, IndustryCode, PublicStore
from .models import StoreLocation


class PublicMapTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('map-user')
        self.client.force_login(self.user)
        self.source = DataSource.objects.create(name='snapshot', collected_on='2026-11-03')
        self.industry = IndustryCode.objects.create(system='local', code='cafe', name='카페')
        self.bounds = {'west': '126.9', 'south': '37.4', 'east': '127.1', 'north': '37.6'}
        self.url = reverse('market:map_public_stores')

    def store(self, external_id='one', **kwargs):
        return PublicStore.objects.create(**{
            'source': self.source, 'external_id': external_id, 'name': '서울 카페',
            'industry': self.industry, 'address': '서울', 'postcode': '04778',
            'latitude': '37.5', 'longitude': '127.0', 'reference_on': date(2026, 11, 3),
            **kwargs,
        })

    def test_bounds_snapshot_and_industry_keyword_filters(self):
        self.store()
        self.store('outside', latitude='38.5')
        self.store('older', reference_on=date(2025, 1, 1))
        self.store('different', name='마트', industry=None)
        response = self.client.get(self.url, {**self.bounds, 'industry': self.industry.pk, 'query': '카페'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['points'][0]['postcode'], '04778')
        self.assertEqual(data['points'][0]['lat'], 37.5)
        self.assertNotIn('raw', data['points'][0])
        self.assertEqual(data['reference_on'], '2026-11-03')
        self.assertEqual(self.client.get(self.url, {**self.bounds, 'query': '없는매장'}).json()['total'], 0)
        self.assertEqual(len(self.client.get(reverse('market:map_public_industries')).json()['industries']), 1)

    def test_cap_and_invalid_input_and_auth(self):
        PublicStore.objects.bulk_create([
            PublicStore(source=self.source, external_id=str(n), name='store', address='서울',
                        latitude='37.5', longitude='127', reference_on='2026-11-03')
            for n in range(501)
        ])
        data = self.client.get(self.url, self.bounds).json()
        self.assertEqual(data['total'], 501)
        self.assertEqual(len(data['points']), 500)
        self.assertTrue(data['truncated'])
        for params in [{}, {**self.bounds, 'west': 'nan'}, {**self.bounds, 'east': '180'},
                       {**self.bounds, 'industry': '9' * 50}, {**self.bounds, 'reference_on': 'bad'}]:
            self.assertEqual(self.client.get(self.url, params).status_code, 400)
        self.assertEqual(self.client.post(self.url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(self.url, self.bounds).status_code, 302)

    def test_desired_category_mapping_and_unmapped_never_show_all(self):
        self.industry.system = 'local-sbiz-small-20261103'
        self.industry.code = 'I21201'
        self.industry.save()
        self.store()
        self.store('unclassified', industry=None)
        data = self.client.get(self.url, {**self.bounds, 'category': '카페'}).json()
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['category_mapping'], 'preview')
        self.assertEqual(self.client.get(self.url, {**self.bounds, 'category': '치킨'}).json()['total'], 0)
        data = self.client.get(self.url, {**self.bounds, 'category': '미분류'}).json()
        self.assertEqual(data['total'], 0)
        self.assertEqual(data['category_mapping'], 'unmapped')
        self.assertEqual(self.client.get(self.url, {**self.bounds, 'category': '전체'}).json()['total'], 2)

    def test_circle_excludes_bounding_box_corners_before_count_and_limit(self):
        self.store('center')
        self.store('inside', latitude='37.502')
        self.store('outside', latitude='37.504', longitude='127.004')
        data = self.client.get(self.url, {**self.bounds, 'lat': '37.5', 'lng': '127', 'radius': '500'}).json()
        self.assertEqual(data['total'], 2)
        self.assertEqual(len(data['points']), 2)
        for params in [{'lat': 'nan', 'lng': '127', 'radius': '500'}, {'lat': '37.5'}, {'lat': '37.5', 'lng': '127', 'radius': '9999'}]:
            self.assertEqual(self.client.get(self.url, {**self.bounds, **params}).status_code, 400)

    def test_registered_locations_still_require_consent_and_verification(self):
        brand = Brand.objects.create(slug='map-brand', name='brand', category='카페')
        store = StoreLocation.objects.create(owner=self.user, brand=brand, store_name='registered',
                                            status='operating', is_public=False, address='서울', sido='서울',
                                            latitude='37.5', longitude='127')
        OwnerVerification.objects.create(user=self.user, brand=brand, store_name='registered',
                                         contract_start_date='2020-01-01', contract_file='test.pdf', status='approved')
        url = reverse('market:map_locations')
        self.assertEqual(self.client.get(url).json()['total'], 0)
        store.is_public = True
        store.save()
        self.assertEqual(self.client.get(url).json()['total'], 1)
        self.assertEqual(self.client.get(reverse('market:map_areas')).status_code, 200)


class PublicBundleTests(TestCase):
    def bundle(self, directory, invalid=False):
        root = Path(directory)
        original = root / 'source.csv'
        original.write_text('test', encoding='utf-8')
        data = {
            'source.json': [{'model': 'DataSource', 'fields': {'id': 3, 'name': 'test', 'collected_on': '2026-11-03'}}],
            'industries.json': [{'model': 'IndustryCode', 'fields': {'id': 1, 'system': 'local', 'code': 'cafe', 'name': '카페'}}],
        }
        for pk in [1, 2]:
            data[f'stores{pk}.json'] = [{'model': 'PublicStore', 'fields': {
                'id': pk, 'source_id': 3, 'external_id': str(pk), 'industry_id': 1,
                'name': 'test', 'address': '서울', 'latitude': '37.5', 'longitude': '127',
                'reference_on': '2026-11-03',
                'raw': {'위도': '37.5', '경도': '127', '상가업소번호': str(pk)},
            }}]
        if invalid:
            data['stores2.json'][0]['fields']['industry_id'] = 999
        manifest = {
            'source_id': 3, 'original_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
            'process_order': list(data), 'industry_count': 1, 'output_stores': 2, 'files': [],
        }
        for name, rows in data.items():
            path = root / name
            path.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
            manifest['files'].append({'filename': name, 'records': len(rows), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        return original

    def test_dry_run_commit_and_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            original = self.bundle(directory)
            call_command('import_public_store_bundle', directory, original=str(original), stdout=StringIO())
            self.assertFalse(DataSource.objects.exists())
            call_command('import_public_store_bundle', directory, original=str(original), commit=True, stdout=StringIO())
            self.assertEqual(PublicStore.objects.count(), 2)
            with self.assertRaises(CommandError):
                call_command('import_public_store_bundle', directory, original=str(original), commit=True, stdout=StringIO())

    def test_late_failure_rolls_back_all_files_and_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            original = self.bundle(directory, invalid=True)
            with self.assertRaises(CommandError):
                call_command('import_public_store_bundle', directory, original=str(original), commit=True, stdout=StringIO())
            self.assertFalse(PublicStore.objects.exists())
            self.assertFalse(DataSource.objects.exists())
            self.assertFalse(IndustryCode.objects.exists())
            (Path(directory) / 'stores1.json').write_text('[]', encoding='utf-8')
            with self.assertRaises(CommandError):
                call_command('import_public_store_bundle', directory, original=str(original), commit=True, stdout=StringIO())
